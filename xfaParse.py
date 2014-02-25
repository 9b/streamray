#!/usr/bin/python

__description__ = 'Parse out Adobe XFA data'
__author__ = 'Kiran Bandla'
__version__ = '1.0'
__date__ = '2012/??/??'

try:
	import re
	from lxml import etree
except Exception, e:
	print e 
	
try:
	import jsDOM
except Exception, e:
	print e 
	
class xfaParse:
	'''
	Parse out XFA data from a PDF and do various extractions
	'''
	def __init__(self,xmlData):
		self._xmlData = xmlData
			
	def extractJsFromXml(self):
		'''
		Extract the JS, if found, from the XFA data
		@param	xmlData	data to extract JS from
		@return	list of scripts found within the XML
		'''
		cleaned = self.cleanXfa(self._xmlData)
		tree, scripts = self.parseXml(cleaned)
		return scripts
	
	def cleanXfa(self,xml):
		'''
		Removes any unwanted information from the XML
		@param	xml	xml to be cleaned
		@return	cleaned version of the XML
		'''
		
		mO = re.search("(<\?xml .*?\?>)", xml)
		if mO:
			xml = xml.replace(mO.group(0), '')
		return xml

	def parseXml(self,xmlStr):
		'''
		Takes in a string of XML extracted from the XFA and finds any script elements. 
		Returns a tuple containing two elements:
			1) the root of the parsed XML tree structure
			2) a list of any script elements found in the tree
		'''
		
		# parse XML and look for 'script' elements
		#self.logger.debug("Parsing XML...")

		# all JavaScript executions here are to build the DOM
		is_dom = True

		try:
			# The XML must be wrapped in a root element because there may not be just 1 root 
			# after I smashed together all the xml ;]
			xml = "<xfa>%s</xfa>" % (xmlStr)
			#logger.info("xml: %s" % repr(xml))
			xmlTree = etree.fromstring(xml)
		except Exception, e:
			#self.logger.warn("[lxml] exception from parsing XML: %s" % e)
			#logger.info(" [lxml] going to try with html5lib..")
			return (None, None)
			import html5lib
			from html5lib import treebuilders
			parser = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("lxml"))
			xmlTree = parser.parse(xml)
		except:
			#self.logger.error("[html5lib] failed to parse the XML. Giving up!")
			#TODO: Add more parsers
			return (None,None)

		# We can't just find 'script' tags because the namespace stuff it pushed into the tag
		scriptL = []

		# we now build the xfa DOM
		def buildElements(element):
			jsDOM.removeNamespace(element)
			ancestors = [] 
			for ancestor in element.iterancestors():
				ancestors.append( ancestor.tag )
			ancestors.reverse()
			if element.text and element.text.strip():
				if element.tag == 'script':
					scriptL.append( element.text.strip())

			for key, value in element.items():
				if key.lower() == 'name':
					rawValue = ''
					if element.text:
						rawValue = element.text.strip()
				elif key.lower() == 'contenttype':
					if value in ['image/tif','image/tiff']:
						pass
						#logger.debug('Found a TIFF of size %s bytes'%(len(element.text)))
						#logger.debug('\033[91m Potential TIFF Exploit.\033[0m');
					elif value in ['application/x-javascript']:
						# javascript placeholder. we know about this too. 
						pass
					else:
						#logger.debug("\033[91m Unhandled Content-Type found. Please review")
						pass

			index = 0
			for childElement in element.getchildren():
				if not (type(childElement) is etree._Element and childElement.tag):
					continue
				jsDOM.removeNamespace(childElement)

				buildElements(childElement)
				index += 1

		buildElements(xmlTree)

		#logger.debug("Found %d script elements" % len(scriptL))
		return xmlTree, scriptL
