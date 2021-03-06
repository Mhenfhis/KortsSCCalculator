# ScOptions.py: Dark Age of Camelot Spellcrafting Calculator
#
# See http://kscraft.sourceforge.net/ for updates
#
# See NOTICE.txt for copyrights and grant of license

import XMLHelper
import sys
import os.path
import stat
from xml.dom.minidom import *
from MyStringIO import UnicodeStringIO
from Singleton import Singleton

class ScOptions(Singleton):
    def __init__(self):
        Singleton.__init__(self)
        self.__options = {}

    def getAppDirectory():
        if sys.platform == 'win32':
            extradirs = 'KSCraft'
            path = os.environ.get('APPDATA', '')
            if not os.path.isdir(path):
                path = os.path.dirname(os.path.abspath(sys.argv[0]))
        else:
            extradirs = '.kscraft'
            path = os.environ.get('HOME', '')
            if not os.path.isdir(path):
                path = os.path.dirname(os.path.abspath(sys.argv[0]))

        path = os.path.join(path, extradirs)
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except error:
                print 'Error creating subdirectories'
                path = os.path.dirname(os.path.abspath(sys.argv[0]))

        return path
    getAppDirectory = staticmethod(getAppDirectory)


    def getOption(self, name, defaultValue):
        if isinstance(defaultValue, str):
            defaultValue = unicode(defaultValue)
        if self.__options.has_key(name) and \
                (isinstance(self.__options[name], type(defaultValue)) or \
                defaultValue is None):
            return self.__options[name]

        return defaultValue

    def setOption(self, name, val):
        if isinstance(val, str):
            val = unicode(val)
        self.__options[name] = val

    def asXML(self):
        document = Document()
        rootnode = document.createElement('DefaultOptions')
        document.appendChild(rootnode)
        for key, val in self.__options.items():
            rootnode.appendChild(self.writeOption(document, key, val))
        return document

    def writeOption(self, doc, key, val):
        if key[0].isdigit():
            key = 'N__' + key
        elem = doc.createElement(key)
        if isinstance(val, dict):
            elem.setAttribute('type', 'dict')
            for subkey, subval in val.items():
                elem.appendChild(self.writeOption(doc, subkey, subval))
            return elem
        elif isinstance(val, list):
            elem.setAttribute('type', 'list')
            for v in val:
                elem.appendChild(self.writeOption(doc, key + 'Item', v))
        else:
            elem.appendChild(doc.createTextNode(unicode(val)))

        return elem
            
    def parseOption(self, node):
        hasElements = False
        sameElements = True
        ptag = None

        
        for child in node.childNodes:
            if child.nodeType == Node.ELEMENT_NODE:
                hasElements = True
                if ptag and ptag != child.nodeName:
                    sameElements = False
                ptag = child.nodeName

        if not node.hasAttribute('type') and not hasElements:
            val = XMLHelper.getText(node.childNodes)
            if val.lower() == 'true': return True
            elif val.lower() == 'false': return False
            else:
                try:
                    return int(val)
                except ValueError:
                    pass
                try:
                    return float(val)
                except ValueError:
                    pass
                return val
        else:
            if node.getAttribute('type') == 'dict' or \
                    (not node.hasAttribute('type') and not sameElements):
                vals = {}
                for child in node.childNodes:
                    if child.nodeType == Node.TEXT_NODE: continue
                    nodeName = child.nodeName
                    if len(nodeName) > 3 and nodeName[:3] == 'N__': 
                        nodeName = nodeName[3:]
                    elif len(nodeName) >= 2 and nodeName[0] == 'L' and nodeName[1].isdigit():  # old style
                            nodeName = nodeName[1:]
                    vals[nodeName] = self.parseOption(child)

                return vals
            elif node.getAttribute('type') == 'list' or \
                    (not node.hasAttribute('type') and sameElements):
                vals = []
                for child in node.childNodes:
                    if child.nodeType == Node.TEXT_NODE: continue
                    vals.append(self.parseOption(child))

                return vals

    def loadFromXML(self, xmldoc):
        self.__options.clear()
        for child in xmldoc.childNodes:
            if child.nodeType == Node.TEXT_NODE: continue
            nodeName = child.nodeName
            if len(nodeName) > 3 and nodeName[:3] == 'N__':
                nodeName = nodeName[3:]
            self.__options[nodeName] = self.parseOption(child)
            
    def load(self):
        scfile = os.path.join(ScOptions.getAppDirectory(),
            'Spellcraft.xml')
        oldscfile = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                              'Spellcraft.xml')
        if not os.path.exists(scfile) and os.path.exists(oldscfile):
            if os.access(os.path.dirname(scfile), os.W_OK):
                f = open(oldscfile, 'r') 
                f2 = open(scfile, 'w')
                f2.write(f.read())
                f.close()
                f2.close()
                os.unlink(oldscfile)

        if os.path.exists(scfile):
            try:
                f = open(scfile, 'r')
                xmldoc = parseString(f.read())
                template = xmldoc.getElementsByTagName('DefaultOptions')
                self.loadFromXML(template[0])
                f.close()
            except xml.parsers.expat.ExpatError, ex: 
                print 'Error parsing XML document, code: %d line: %d offset %d', (
                    ex.code, ex.lineno, ex.offset)
                pass

    def save(self):        
        scfile = os.path.join(ScOptions.getAppDirectory(),
            'Spellcraft.xml')
        if os.access(os.path.dirname(scfile), os.W_OK):
            try:
                f = open(scfile, 'w')
                f.write(XMLHelper.writexml(self.asXML(), UnicodeStringIO(), '', '\t', '\n'))
                f.write('\n')
                f.close()
            except Exception, ex:
                print 'Error saving Spellcraft.xml!! ', ex
                pass
            try:
                os.chmod(scfile, stat.S_IRUSR | stat.S_IWUSR)
            except:
                pass
