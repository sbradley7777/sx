#!/usr/bin/env python
"""

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.16
@copyright :  GPLv2
"""
from sx.tools import StringUtil
class DmiDecodeParser:
    def parseDmiDecodeData(dmidecodeData):
        stanzas = []
        currentStanza = []
        if (not dmidecodeData == None):
            for line in dmidecodeData:
                line = line.rstrip()
                if (line.startswith("Handle")):
                    if (len(currentStanza) > 0):
                        stanzas.append(DMIDecodeStanza(currentStanza))
                        currentStanza = []
                    currentStanza.append(line)
                elif ((len(line) > 0) and (len(currentStanza) > 0)):
                    currentStanza.append(line)
            if (len(currentStanza) > 0):
                stanzas.append(DMIDecodeStanza(currentStanza))
        return stanzas
    parseDmiDecodeData = staticmethod(parseDmiDecodeData)

class DMIDecodeStanzaAttribute:
    def __init__(self, name, value):
        self.__name = name
        self.__value = value

    def __str__(self):
        return "%s: %s" %(self.getName(), self.getValue())

    def getName(self):
        return self.__name

    def getValue(self):
        return self.__value

class DMIDecodeStanza:
    def __init__(self, data):
        self.__handle = ""
        self.__type = -1
        self.__name = ""
        self.__size = 0
        self.__attributesMap = {}
        if (len(data) > 0):
            dataSplit = data.pop(0).strip().rstrip().split()
            if (len(dataSplit) >= 6):
                self.__handle = dataSplit[1].rstrip(",").strip().rstrip()
                self.__type = int(dataSplit[4].rstrip(",").strip().rstrip())
                self.__size = int(dataSplit[5].rstrip(",").strip().rstrip())
        if (len(data) > 0):
            self.__name = data.pop(0).strip().rstrip().strip().rstrip()

        for pair in data:
            currentTabCount = (len(pair) - len(pair.lstrip("\t")))
            splitPair = pair.strip().rstrip().split(":", 1)
            if (not len(splitPair) > 1):
                continue
            attributeName = splitPair[0].strip().rstrip()
            attributeValue = splitPair[1].strip().rstrip()
            if (currentTabCount == 1 or (len(attributeValue) > 0)):
                # could add index to DMIDecodeStanzaAttribute to preserve order
                # if I want to in the future.
                self.__attributesMap[attributeName] = DMIDecodeStanzaAttribute(attributeName, attributeValue)
            # else: Need to do something with attributes that contain their own attribute/value list.

    def __str__(self):
        rString = "handle: %s(type: %d bytes: %d): %s\n" %(self.getHandle(), self.getType(), self.getSize(), self.getName())
        for attributeName in self.__attributesMap.keys():
            rString += "\t%s\n" %(self.__attributesMap.get(attributeName))
        return rString.rstrip()

    def getHandle(self):
        return self.__handle

    def getType(self):
        return self.__type

    def getSize(self):
        return self.__size

    def getName(self):
        return self.__name

    def getAttributeNames(self):
        return self.__attributesMap.keys()

    def getAttribute(self, attributeName):
        if (self.__attributesMap.has_key(attributeName)):
            return self.__attributesMap.get(attributeName)
        return None
