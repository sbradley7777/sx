#!/usr/bin/env python
"""
This is a collection of classes that hold data for files that are
located in the sos_commands/filesys directory.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.10
@copyright :  GPLv2
"""
import re
import logging

import sx
from sx.logwriter import LogWriter


class FilesysParser:
    def parseEtcExportsbData(etcExportsData):
        """
        /               master(rw) trusty(rw,no_root_squash)
        /projects       proj*.local.domain(rw)
        /usr            *.local.domain(ro) @trusted(rw)
        /home/joe       pc001(rw,all_squash,anonuid=150,anongid=100)
        /pub            *(ro,insecure,all_squash)
        """
        parsedList = []
        if (etcExportsData == None):
            return parsedList

        # The re match for clients
        regex = "(?P<clients>.*)\((?P<clientsOptions>.*)\)"
        rem = re.compile(regex)

        for line in etcExportsData:
            lineSplit = line.split()
            if (len(lineSplit) >= 2):
                # Get the mountpoint
                mountPoint = lineSplit.pop(0)
                # Loop over the clients and add to the map
                clientsOptionsMap = {}
                for item in lineSplit:
                    mo = rem.match(item.strip())
                    if mo:
                        # Add this client and options to the map
                        clientsOptionsMap[mo.group("clients")] = mo.group("clientsOptions").split(",")
                    parsedList.append(EtcExport(mountPoint, clientsOptionsMap))
        return parsedList
    parseEtcExportsbData = staticmethod(parseEtcExportsbData)

    def parseEtcSambaSmbConfData(etcSambaSmbConfData):
        parsedList = []
        if (etcSambaSmbConfData == None):
            return parsedList
        lastSectionName = ""
        lastSectionMap = {}
        for line in etcSambaSmbConfData:
            line = line.strip()
            if (line.startswith("#") or
                line.startswith(";") or
                (not len(line) > 0)):
                # skip comments and empty lines
                continue
            elif (line.startswith("[") and line.endswith("]")):
                if ((len(lastSectionName) > 0) or (len(lastSectionMap.keys()) > 0)):
                    parsedList.append(EtcSambaSmbConfSection(lastSectionName, lastSectionMap))
                lastSectionName = line.strip("[").rstrip("]")
                lastSectionMap = {}
            elif(line.find("=") > 0):
                optionValueSplit = line.split("=", 1)
                if (len(optionValueSplit) ==  2):
                    lastSectionMap[optionValueSplit[0].strip()] = optionValueSplit[1].strip()
        # Add last section:
        if ((len(lastSectionName) > 0) or (len(lastSectionMap.keys()) > 0)):
            parsedList.append(EtcSambaSmbConfSection(lastSectionName, lastSectionMap))
        return parsedList
    parseEtcSambaSmbConfData = staticmethod(parseEtcSambaSmbConfData)

    def parseEtcFstabData(etcFstabData, fsTypeList):
        parsedList = []
        if (etcFstabData == None):
            return parsedList

        fsTypesString = ""
        for fsType in fsTypeList:
            if (not len(fsTypesString) == 0):
                fsTypesString += "|"
            fsTypesString += "%s"%(fsType)
        fsTypesRegex = "(?P<fsType>%s)" %(fsTypesString)


        for line in etcFstabData:
            if (not line.startswith("#") and (len(line) > 0)):
                splitLine = line.strip().split()
                try :
                    parsedList.append(EtcFstabMount(splitLine[0].strip(), splitLine[1].strip(),
                                                    splitLine[2].strip(), splitLine[3].strip(),
                                                    splitLine[4].strip(), splitLine[5].strip()))
                except IndexError:
                    continue
        return parsedList
    parseEtcFstabData = staticmethod(parseEtcFstabData)

    def parseFilesysMountData(filesysMountData, fsTypeList) :
        """
        Example:
        none on /proc type proc (rw)
        /dev/mapper/vgdbprod-lvnagios on /usr/local/nagios-dbprod type ext3 (rw)
        """
        parsedList = []
        if (filesysMountData == None):
            return parsedList


        fsTypesString = ""
        for fsType in fsTypeList:
            if (not len(fsTypesString) == 0):
                fsTypesString += "|"
            fsTypesString += "%s"%(fsType)
        fsTypesRegex = "(?P<fsType>%s)" %(fsTypesString)

        # Need way to get all possible devices
        regex = "^(?P<device>none|usbfs|automount.*|/.*)" + " on " + \
            "(?P<mountPoint>/.*)" + " type " +  \
            fsTypesRegex + " " + \
            "(?P<fsOptions>\(.*\))" + \
            "(?P<fsAttributes>.*)"
        rem = re.compile(regex)

        for line in filesysMountData:
            mo = rem.match(line.strip())
            if mo:
                fsOptions = mo.group("fsOptions").strip()
                if (not len(fsOptions) > 0):
                    fsOptions = ""
                parsedList.append(FilesysMount(mo.group("device").strip(),
                                               mo.group("mountPoint").strip(),
                                               mo.group("fsType").strip(),
                                               mo.group("fsAttributes").strip(),
                                               fsOptions))
        return parsedList
    parseFilesysMountData =staticmethod(parseFilesysMountData)

class EtcExport:
    def __init__(self, mountPoint, clientsOptionsMap):
        self.__mountPoint = mountPoint
        self.__clientsOptionsMap = clientsOptionsMap

    def __str__(self):
        rString = self.getMountPoint()
        for client in self.getClients():
            rString += "\n\t %s " %(client)
            for option in self.getClientOptions(client):
                rString += "%s " %(option)
        return rString.strip()

    def getMountPoint(self):
        return self.__mountPoint

    def getClients(self):
        return self.__clientsOptionsMap.keys()

    def getClientOptions(self, client):
        if (self.__clientsOptionsMap.has_key(client)):
            return self.__clientsOptionsMap.get(client)
        return []

class EtcSambaSmbConfSection:
    def __init__(self, sectionName, sectionMap):
        self.__sectionName = sectionName
        self.__sectionMap = sectionMap

    def __str__(self):
        rString = self.getSectionName()
        for key in self.__sectionMap.keys():
            rString += "\n\t%s = %s" %(key, self.__sectionMap.get(key))
        return rString

    def getSectionName(self):
        return self.__sectionName

    def getOptionsNames(self):
        return self.__sectionMap.keys()

    def getOptionValue(self, optionName):
        if (self.__sectionMap.has_key(optionName)):
            return self.__sectionMap.get(optionName).strip()
        return ""

class FilesysMount:
    def __init__(self, deviceName, mountPoint, fsType, fsAttributes, mountOptions):
        """
        This is a class that creates object from the information contained in the file:
        proc/mounts from a sosreport/sysreport

        /dev/mapper/vgdbprod-lvnagios on /usr/local/nagios-dbprod type ext3 (rw)

        """
        self.__deviceName = deviceName
        self.__mountPoint = mountPoint
        self.__fsType = fsType
        self.__fsAttributes = fsAttributes
        self.__mountOptions = mountOptions

    def __str__(self):
        return"%s  %s  %s  %s  %s"%(self.getDeviceName(), self.getMountPoint(),
                                    self.getFSType(), self.getFSAttributes(),
                                    self.getMountOptions())

    def getDeviceName(self):
        return self.__deviceName

    def getMountPoint(self):
        return self.__mountPoint

    def getFSType(self):
        return self.__fsType

    def getFSAttributes(self):
        return self.__fsAttributes

    def getMountOptions(self):
        return self.__mountOptions


class EtcFstabMount(FilesysMount):
    def __init__(self, deviceName, mountPoint, fsType, mountOptions, fsDump, fsFsck):
        # /etc/fstab does not have attributes section so we just set to empty string.
        FilesysMount.__init__(self, deviceName, mountPoint, fsType, "", mountOptions)

        self.__fsDump = fsDump
        self.__fsFsck = fsFsck

    def getFSDump(self):
        return self.__fsDump

    def getFSFsck(self):
        return self.__fsFsck

