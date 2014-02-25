'''
jsDOM.py

This module provides methods for transforming both PDF objects and XML (xfa/xdp) into a single structure of linked objects
in javascript. The idea is that any *DOM interaction will play out in javascript land, where the DOMs are created and
maintained as the PDF is 'rendered'.
'''
from lxml import etree
DEBUG = True

def removeNamespace(element):
	'''
	Removes the namespace stuff from an element's tag attr. Probably a bad idea.
	'''
	if not element.nsmap:
		#logger.info("empty nsmap")
		return
	
	for key in element.nsmap:
		val = element.nsmap[key]
		s = "{%s}" % val
		element.tag = element.tag.replace(s, "")

def elementToJS(element, jsStrL, logger):
	origTag = element.tag
	removeNamespace(element, logger)
	
	# add element first
	jsStrL.append("%s = new Element('%s');" % (element.tag, element.tag))
	
	# see if there's any text
	if element.text:
		# we will likely need to escape chars like ' and " to make this work...
		jsStrL.append("%s.text = \"%s\";" % (element.tag, element.text.strip()))
		
	# add children both by their tagname and as integers
	index = 0
	for childElement in element.getchildren():
		# create child recursively
		elementToJS(childElement, jsStrL, logger)
		
		if element.tag == 'subform':
			#TODO: process subform for field names
			pass
		# now, add this child both as a property and something accessible via index
		jsStrL.append("%s.%s = %s;" % (element.tag, childElement.tag, childElement.tag))
		jsStrL.append("%s[%d] = %s;" % (element.tag, index, childElement.tag))
		
		index += 1



def xmlToJS(xml):
	'''
	Takes an LXML element tree and converts it into javascript code that, when executed by
	a javascript engine, will create a very similar structure that can be manipulated in
	javascript land by other scripts.
	
	Returns a string of javascript suitable for eval()'ing.
	'''
	# Prepare the javascript string with a defintion of our 'Element' object
	jsStrL = ["""
	function Element(tag) {
		this.tag = tag;
		// this needs a lot more stuff added to it...
	}

	"""]

	# Convert XML elements into a tree of javascript objects
	try:
		elementToJS(xml, jsStrL, logger)
	except Exception,e:
		logger.warn(e)
		pass
	return '\n'.join(jsStrL)


def getExposedObjects():
	'''
	Adobe Reader has all sorts of objects that are defined under the hood and exposed to javascript.
	This method returns a string of javascript which contains definitions for those objects.
	'''
	defsStr = """
	var app = Object();
	"""

	return defsStr
