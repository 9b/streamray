#!/usr/bin/python

__description__ = 'Extract metadata from a PDF'
__author__ = 'Brandon Dixon'
__version__ = '1.0'
__date__ = '2012/05/01'

try: #general imports
	import logging
	import re
	import hashlib
	import traceback
	import simplejson as json
except Exception, e:
	print e 
					
try: #custom imports
	from peepdf_r91.bsdPDFCore import PDFParser
	from xfaParse import *
except Exception, e:
	print e 


class PDFMeta:
	'''
	Class to extract all metadata from a PDF documet
	'''
	def __init__(self,parsed,logging="_"):
		'''
		Init for the PDFMeta class
		@param	parsed	instance of peepdf pdf object
		@param	logging	level of logging to set for the class
		'''
		self._parsed = parsed
		self._logger(logging)
		
		#throw this into handle function
		self._statsHandle = self._parsed.getStats()
		
		#General Structure
		self._containsBody = False
		self._containsXref = False
		self._containsTrailer = False
		self._containsPostEof = False
		self._containsPostEofTmp = []
		self._multipleVersions = False
		self._pageCount = 0
		self._definedLanguage = []
		self._containsImages = False
		self._containsEmbeddedFiles = False
		self._containsJs = False
		self._containsEncryption = False
		self._containsFlash = False
		
		#Hashing of contents
		self._ssdPostEof = None
		self._hashPostEof = None
		self._ssdDocumentText = None
		self._hashDocumentText = None
		self._ssdImages = None
		self._hashImages = []
		self._ssdEmbeddedFiles = None
		self._hashEmbeddedFiles = []
		self._ssdJs = None
		self._hashJs = []
		self._ssdFlash = None
		self._hashFlash = []
		
		self._summary = {"flash":{},"js":{},"embedded":{},"images":{},"xfa":{}}
		
		self.shredder()
		
	def _logger(self,level):
		self._log = logging.getLogger('PDFMeta')
		if level == "INFO":
			logging.basicConfig(level=logging.INFO)
		elif level == "ERROR":
			logging.basicConfig(level=logging.ERROR)
		else:
			pass
		
	def shredder(self):
		#self.metadataExtract()
		#self.generalStructure()
		#self.standardEncrypt()
		#self.algEncrypt()
		self.artifactExtraction()
		self.jsonify()
		
	def handle_object(self,obj,id,parent=None):
	
		try:
			oType = obj.getType()
		except Exception,e:
			return
	
		#check for the two items we know JS has to end up in
		if parent == "/JS" or parent == "/JavaScript":
			js = True
		else:
			js = False	
		if parent == "/XFA":
			xfa = True
		else:
			xfa = False
		if parent == "/Subtype":
			subtype = True
		else:
			subtype = False
		if parent == "/Type":
			ptype = True
		else:
			ptype = False
	
		if oType == "dictionary":
			dItems = obj.getElements()
			self._log.info("found dict %s inside %s" % (','.join(dItems.keys()),parent))
			for k,v in dItems.iteritems():
				self._log.info("handling %s of type %s" % (k,v))
				self.handle_object(dItems[k],id,k)					
			
		elif oType == "array":
			dItems = obj.getElements()
			for item in dItems:
				self.handle_object(item,id,parent)
	
		elif oType == "reference":
			#self._log.info("%s references object %s" % (parent,obj.id))
			rObj = self._parsed.getObject(obj.id)
			if rObj != None:
				if rObj.getType() == "stream" and js:
					#self._log.info("%s reference contains %s" % (obj.id,rObj.decodedStream))
					self._log.info("JS found in %s" % (obj.id))
					#self._log.info("============\n\n%s\n==============" % (rObj.decodedStream))
					
					if rObj.decodedStream not in self.jsCode:
						self.jsCode.append(rObj.decodedStream)
						self._summary['js'][obj.id] = rObj
											
				if rObj.getType() == "stream" and xfa:
					#self._log.info("%s reference contains %s" % (obj.id,rObj.decodedStream))
					self._log.info("XFA found in %s" % (obj.id))
					#self._log.info("============\n\n%s\n==============" % (rObj.decodedStream))
					
					self.xfaData += rObj.decodedStream
					self._summary['xfa'][obj.id] = rObj
	
		elif oType == "string":
			if js:
				self._log.info("%s has string values %s" % (parent,obj.value))
				if obj.value not in self.jsCode:
					self.jsCode.append(obj.value)
					rObj = self._parsed.getObject(id)
					if rObj != None:
						self._summary['js'][id] = rObj
					
		elif oType == "stream":
			dItems = obj.getElements()
			self._log.info("found dict %s inside %s" % (','.join(dItems.keys()),parent))
			
			#sanity check the stream for Flash before we leave
			if obj.decodedStream[:3] == "CWS" or obj.decodedStream[:3] == "FWS":
				if obj.decodedStream not in self.flashFiles:
					if obj.decodedStream != '':
						self.flashFiles.append(obj.decodedStream)
					else:
						self.flashFiles.append(obj.encodedStream)	
						
					self._summary['flash'][id] = obj
			
			for k,v in dItems.iteritems():
				self._log.info("handling %s of type %s" % (k,v))
				self.handle_object(dItems[k],id,k)	
				
		elif oType == "name":
			if obj.value == "/Image" and id != None:
				sObj = self._parsed.getObject(id)
				if sObj.getType() == "stream" and subtype:
					self._log.info("Image found in %s" % (id))
					if sObj.decodedStream not in self.imageStreams:
						if sObj.decodedStream != '':
							self.imageStreams.append(sObj.decodedStream)
						else:
							self.imageStreams.append(sObj.encodedStream)
							
						self._summary['images'][id] = sObj
						
			if obj.value == "/application/x-shockwave-flash" and id != None:
				sObj = self._parsed.getObject(id)
				if sObj.getType() == "stream" and subtype:
					self._log.info("Flash found in %s" % (id))
					if sObj.decodedStream not in self.flashFiles:
						if sObj.decodedStream != '':
							self.flashFiles.append(sObj.decodedStream)
						else:
							self.flashFiles.append(sObj.encodedStream)	
							
						self._summary['flash'][id] = sObj		
						
			if obj.value == "/EmbeddedFile" and id != None:
				sObj = self._parsed.getObject(id)
				if sObj.getType() == "stream" and ptype:
					self._log.info("Embedded file found in %s" % (id))
					if sObj.decodedStream not in self.embeddedFiles:
						if sObj.decodedStream != '':
							self.embeddedFiles.append(sObj.decodedStream)
						else:
							self.embeddedFiles.append(sObj.encodedStream)
	
						self._summary['embedded'][id] = sObj
	
	def artifactExtraction(self):
		self.xfaData = ''
		self.jsCode = []
		self.processed = []		
		self.imageStreams = []	
		self.embeddedFiles = []	
		self.flashFiles = []			
			
		#main processing loop
		if len(self._parsed.body) > 0:
			for b in self._parsed.body:
				objs = b.objects
				for id,obj in objs.iteritems():
					if id not in self.processed:
						#self._log.info("handling object %s" % (str(id)))
						self.handle_object(obj.object,id)	
						self.processed.append(id)
		
		if self.xfaData != '':
			xParse = xfaParse(self.xfaData)
			self.xfaScripts = xParse.extractJsFromXml()
			if self.xfaScripts != None:
				if len(self.xfaScripts) > 0:
					for s in self.xfaScripts:
						if s not in self.jsCode:
							self.jsCode.append(s)
						
		#override the booleans since we have more insight
		if len(self.jsCode) > 0:
			self._containsJs = True	
			for item in self.jsCode:
				try:
					h = hashlib.md5(item).hexdigest()
					self._hashJs.append(h)
				except Exception,e:
					pass
		if len(self.imageStreams) > 0:
			self._containsImages = True
			for item in self.imageStreams:
				try:
					h = hashlib.md5(item).hexdigest()
					self._hashImages.append(h)
				except Exception,e:
					pass
		if len(self.flashFiles) > 0:
			self._containsFlash = True
			for item in self.flashFiles:
				try:
					h = hashlib.md5(item).hexdigest()
					self._hashFlash.append(h)
				except Exception,e:
					pass
		if len(self.embeddedFiles) > 0:
			self._containsEmbeddedFiles = True
			for item in self.embeddedFiles:
				try:
					h = hashlib.md5(item).hexdigest()
					self._hashEmbeddedFiles.append(h)
				except Exception,e:
					pass
				
		#print "Images hashes: %s" % ','.join(str(x) for x in self._summary['images'])
		#print "Embedded hashes: %s" % ','.join(str(x) for x in self._summary['embedded'])
		#print "JS hashes: %s" % ','.join(str(x) for x in self._summary['js'])
		#print "Flash hashes: %s" % ','.join(str(x) for x in self._summary['flash'])
		#print "XFA hashes: %s" % ','.join(str(x) for x in self._summary['xfa'])
		
		#self._log.info("Images hashes: %s" % ','.join(self._summary['images']))
		#self._log.info("Embedded hashes: %s" % ','.join(self._summary['embedded']))
		#self._log.info("JS hashes: %s" % ','.join(self._summary['js']))
		#self._log.info("Flash hashes: %s" % ','.join(self._summary['flash']))
		
	def jsonify(self):
		
		#JS
		for k,obj in self._summary['js'].iteritems():
			if obj.type == "stream":
				j = {}
				j['id'] = k
				j['stream_size'] = obj.size
				j['object_definition'] = obj.rawValue
				j['references'] = obj.references
				j['encrypted'] = obj.encrypted
				j['filter'] = obj.filter.rawValue
				j['obj_def_hash'] = hashlib.md5(obj.rawValue).hexdigest()
				j['encoded_stream_hash'] = hashlib.md5(obj.encodedStream).hexdigest()
				j['decoded_stream_hash'] = hashlib.md5(obj.decodedStream).hexdigest()
				j['decoded_stream'] = obj.encodedStream
				j['encoded_stream'] = obj.decodedStream
				j['tag'] = "javascript"
				
				tmp = json.dumps(j)
				loaded = json.loads(tmp)
				#j['offset'] = obj.offset
				#j['suspicious_events'] = obj.suspiciousEvents
				#j['suspicious_actions'] = obj.suspiciousActions
				#j['suspicious_elements'] = obj.suspiciousElements
				#print j
			else:
				j = {}
				j['id'] = k
				j['size'] = len(obj.rawValue)
				j['object_definition'] = obj.rawValue
				j['references'] = obj.references
				j['encrypted'] = obj.encrypted
				j['obj_def_hash'] = hashlib.md5(obj.rawValue).hexdigest()
				j['tag'] = "javascript"
				tmp = json.dumps(j)
				loaded = json.loads(tmp)
				#j['suspicious_events'] = obj.suspiciousEvents
				#j['suspicious_actions'] = obj.suspiciousActions
				#j['suspicious_elements'] = obj.suspiciousElements
				#print j
		
		#Flash
		
		#Embedded
		
		#XFA
					
import glob
import signal
from time import time

files = glob.glob('/home/bsdixon/training_data/targeted/*')

def grim(segnum,frame):
	signal.alarm(0)
	raise Exception("\ndeath has come...\n")

s = time()
count = 0
for x in files:
	old_handler = signal.signal(signal.SIGALRM, grim)
	signal.alarm(10)
	try:
		t = time()
		pdfParser = PDFParser()
		ret,pdf = pdfParser.parse(x, True, False) 
		signal.alarm(0)
		obj = PDFMeta(pdf,"_")
		print "process time: \t" + str(time() - t) + " : \t" + str(count) + " : \t" + str(x)
	except Exception, e:
		print e
		print str(traceback.print_exc())
		continue
	finally:
		signal.signal(signal.SIGALRM, old_handler)
	
	signal.alarm(0)
	count += 1

print "processed in " + str(time() - s)



	
	
