#!/usr/bin/env python
"""
This is a collection of classes that contain data for files from a
sosreport in the directory:
sos_commands/devicemapper

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.10
@copyright :  GPLv2
"""
import logging

import sx
from sx.logwriter import LogWriter

class DeviceMapperParser:
    def parseDMSetupInfoCData(dmSetupInfoCData):
        """
        Returns a map that has key that is major/minor number
        pair. The value is the DMSetupInfoC object.
        """
        parsedMap = {}
        if (dmSetupInfoCData == None):
            return parsedMap
        elif (not len(dmSetupInfoCData) > 0):
            return parsedMap
        elif (dmSetupInfoCData[0].find("/proc/devices: fopen failed: No such file or directory\n") >= 0):
            # There is no data in the file, just an error.
            return parsedMap
        for line in dmSetupInfoCData:
            lineSplit = line.split()
            if ((not line.startswith("Name ")) and (len(lineSplit) == 8)):
                name = lineSplit[0]
                dmsetupDMSetupInfoC = DMSetupInfoC(name,lineSplit[1],
                                                    lineSplit[2],lineSplit[3],
                                                    lineSplit[4],lineSplit[5],
                                                    lineSplit[6],lineSplit[7])
                parsedMap[dmsetupDMSetupInfoC.getMajorMinorPair()] = dmsetupDMSetupInfoC
        return parsedMap
    parseDMSetupInfoCData = staticmethod(parseDMSetupInfoCData)

    def parseDMSetupTableData(dmSetupTableData):
        """
        This file can have different line value for the different
        target mapping: linear, striped, mirror, snapshot-origin,
        snapshot, error, zero, multipath

        Each line can contain different data. The only guarantee
        columns of data is: name, startOfMap, lengthOfMap, and targetName.


        See this article that shows some examples:
        http://docs.redhat.com/docs/en-US/Red_Hat_Enterprise_Linux/6/html/Logical_Volume_Manager_Administration/device_mapper.html#dm-mappings
        """
        parsedList = []
        if (dmSetupTableData == None):
            return parsedList
        elif (not len(dmSetupTableData) > 0):
            return parsedList
        elif (dmSetupTableData[0].find("/proc/devices: fopen failed: No such file or directory\n") >= 0):
            # There is no data in the file, just an error.
            return parsedList
        for line in dmSetupTableData:
            lineSplit = line.split()
            if (len(lineSplit) >= 4):
                deviceMapperName = lineSplit.pop(0).rstrip(":")
                startOfMap = lineSplit.pop(0)
                lengthOfMap = lineSplit.pop(0)
                targetName = lineSplit[0]

                parsedList.append(DMSetupTable(deviceMapperName, startOfMap,
                                               lengthOfMap, targetName, lineSplit))
        return parsedList
    parseDMSetupTableData = staticmethod(parseDMSetupTableData)

    def parsePVS_AVData(pvs_avData):
        parsedList = []
        if (pvs_avData == None):
            return parsedList
        for line in pvs_avData:
            currentLine = line.strip().rstrip()
            # Column Headers
            # PV VG Fmt Attr PSize PFree DevSize PV UUID
            if ((len(currentLine) > 0) and (currentLine.startswith("/"))):
                splitLine = currentLine.split()
                if (len(splitLine) == 8):
                    parsedList.append(PVS_AV(splitLine[0], splitLine[1], splitLine[2], splitLine[3],
                                    splitLine[4], splitLine[5], splitLine[6], splitLine[7]))
                elif (len(splitLine) == 5):
                    # This is for cases where there is no VG, Format, PV UUID specified.
                    parsedList.append(PVS_AV(splitLine[0], "", "", splitLine[1], splitLine[2], splitLine[3], splitLine[4], ""))
        return parsedList
    parsePVS_AVData = staticmethod(parsePVS_AVData)

    def parseVGSVData(vgsvData):
        parsedList = []
        if (vgsvData == None):
            return parsedList
        foundHeader = False
        for line in vgsvData:
            currentLine = line.strip().rstrip()
            if (len(currentLine) > 0):
                splitLine = currentLine.split()
                if (not len(splitLine) >= 2):
                    continue
                elif ((len(splitLine) == 9) and (foundHeader)):
                        parsedList.append(VolumeGroups(splitLine[0], splitLine[1], splitLine[2], splitLine[3], splitLine[4],
                                                       splitLine[5], splitLine[6], splitLine[7], splitLine[8]))
                elif ((splitLine[0].strip() == "VG") and (splitLine[1].strip() == "Attr")):
                    foundHeader = True
                    continue
        return parsedList
    parseVGSVData = staticmethod(parseVGSVData)

    def parseLVSDevicesData(lvsDevicesData):
        parsedList = []
        if (lvsDevicesData == None):
            return parsedList
        foundHeader = False
        for line in lvsDevicesData:
            currentLine = line.strip().rstrip()
            if (len(currentLine) > 0):
                splitLine = currentLine.split()
                if (len(splitLine) >= 5):
                    if ((splitLine[0].strip() == "LV") and (splitLine[1].strip() == "VG")):
                        foundHeader = True
                        continue
                    elif (foundHeader):
                        parsedList.append(LVSDevices(splitLine[(len(splitLine) - 1)], splitLine[1], splitLine[0], splitLine[2], splitLine[3]))
        return parsedList
    parseLVSDevicesData = staticmethod(parseLVSDevicesData)

class PVS_AV:
    def __init__(self, pvName, vgName, formatType, attributes, pSize, pFree, deviceSize, pvUUID):
        self.__pvName = pvName
        self.__vgName = vgName
        self.__formatType = formatType
        self.__attributes = attributes
        self.__pSize = pSize
        self.__pFree = pFree
        self.__deviceSize = deviceSize
        self.__pvUUID = pvUUID

    def __str__(self):
        return "%s %s %s %s %s %s %s %s" %(self.__pvName, self.__vgName, self.__formatType, self.__attributes,
                                           self.__pSize, self.__pFree, self.__deviceSize, self.__pvUUID)
    def getPVName(self):
        return self.__pvName

    def getVGName(self):
        return self.__vgName

    def getFormatType(self):
        return self.__formatType

    def getAttributes(self):
        return self.__attributes

    def getPSize(self):
        return self.__pSize

    def getPFree(self):
        return self.__pfree

    def getDeviceSize(self):
        return self.__deviceSize

    def getPVUUID(self):
        return self.__pvUUID

class VolumeGroups:
    def __init__(self, vgName, attributes, extendSize, pvCount, lvCount, snapShotCount, vgSize, vgFree, uuid):
        # used with sos_commands/devicemapper/vgs_-v
        # output information is at: http://git.fedorahosted.org/git/?p=lvm2.git --> lib/report/columns.h
        self.__vgName = vgName
        self.__attributes = attributes
        self.__extendSize = extendSize
        self.__pvCount = int(pvCount)
        self.__lvCount = int(lvCount)
        self.__snapShotCount = int(snapShotCount)
        self.__vgSize = vgSize
        self.__vgFree = vgFree
        self.__uuid = uuid

    def __str__(self):
        return "%s(%s)" %(self.__vgName, self.__uuid)

    def getVGName(self):
        return self.__vgName

    def getAttributes(self):
        return self.__attributes

    def getAttributesMap(self):
        attributesMap = {}
        attributesAsList = list(self.__attributes)
        # Permissions: (w)riteable, (r)ead-only
        attributesMap["permissions"] = attributesAsList[0]
        # Resi(z)eable
        attributesMap["resizeable"] = attributesAsList[1]
        # E(x)ported
        attributesMap["exported"] = attributesAsList[2]
        # (p)artial: one or more physical volumes belonging to the volume group are missing from the system
        attributesMap["partial"] = attributesAsList[3]
        # Allocation policy: (c)ontiguous, c(l)ing, (n)ormal, (a)nywhere, (i)nherited
        attributesMap["allocation_policy"] = attributesAsList[4]
        # (c)lustered
        attributesMap["clustered"] = attributesAsList[5]
        return attributesMap

    def getExtendSize(self):
        return self.__extendSize

    def getPVCount(self):
        return self.__pvCount

    def getLVCount(self):
        return self.__lvCount

    def getSnapShotCount(self):
        return self.__snapShotCount

    def getVGSize(self):
        return self.__vgSize

    def getVGFree(self):
        return self.__vgFree

    def getUUID(self):
        return self.__uuid

class LVSDevices:
    def __init__(self, pathToDevice, vgName, lvName, attributes, lSize):
        splitPathToDevice = pathToDevice.split("(")
        self.__pathToDevice = splitPathToDevice[0]
        self.__physicalExtendSize = splitPathToDevice[1].rstrip(")")
        self.__vgName = vgName
        self.__lvName = lvName
        self.__attributes = attributes
        self.__lSize = lSize

    def __str__(self):
        return "%s --> %s/%s" %(self.__pathToDevice, self.__vgName, self.__lvName)

    def getPathToDevice(self):
        return self.__pathToDevice

    def getVGName(self):
        return self.__vgName

    def getLVName(self):
        return self.__lvName

    def getAttributes(self):
        return self.__attributes

    def getAttributesMap(self):
        attributesMap = {}
        attributesAsList = list(self.__attributes)
        # Volume type: (m)irrored, (M)irrored without initial sync, (o)rigin,
        # (O)rigin with merging snapshot, (s)napshot, merging (S)napshot,
        # (p)vmove, (v)irtual, mirror (i)mage, mirror (I)mage out-of-sync, under
        # (c)onversion
        attributesMap["volume_type"] = attributesAsList[0]
        # Permissions: (w)riteable, (r)ead-only
        attributesMap["permissions"] = attributesAsList[1]
        # Allocation policy: (c)ontiguous, c(l)ing, (n)ormal, (a)nywhere,
        # (i)nherited This is capitalised if the volume is currently locked
        # against allocation changes, for example during pvmove
        attributesMap["allocation_policy"] = attributesAsList[2]
        # fixed (m)inor
        attributesMap["fixed"] = attributesAsList[3]
        # State: (a)ctive, (s)uspended, (I)nvalid snapshot, invalid (S)uspended
        # snapshot, mapped (d)evice present without tables, mapped device
        # present with (i)nactive table
        attributesMap["state"] = attributesAsList[4]
        # device (o)p
        attributesMap["device"] = attributesAsList[5]
        return attributesMap

    def getLSize(self):
        return self.__lSize

    def getPhysicalExtendSize(self):
        return self.__physicalExtendSize

    def getVGLVName(self):
        return "%s-%s" %(self.__vgName, self.__lvName)


class DMSetupInfoC:
    def __init__(self, deviceMapperName, majorNumber, minorNumber, attributes,
                 openRefCount, targetCount, lastEventSequenceNumber, uuid):
        """
        This is a class that holds the information contained in the file:
        sos_commands/devicemapper/dmsetup_info_-c from a sosreport

        This is a description of the information contained. Outputs
        some brief information about the device in the form:
        Example Header: Name  Maj Min Stat Open Targ Event  UUID

        Major and minor device number
        State: SUSPENDED|ACTIVE, READ-ONLY
        Tables present: LIVE and/or INACTIVE
        Open reference count
        Number of targets in the live table
        Last event sequence number (used by wait)
        UUID

        """
        self.__deviceMapperName = deviceMapperName
        self.__majorNumber = int(majorNumber)
        self.__minorNumber = int(minorNumber)
        self.__attributes = attributes
        self.__openRefCount = int(openRefCount)
        self.__targetCount = int(targetCount)
        self.__lastEventSequenceNumber = int(lastEventSequenceNumber)
        self.__uuid = uuid

    def __str__(self):
        rstring  = ""
        rstring += "deviceMapperName:     %s\n" %(self.getDeviceMapperName())
        rstring += "major number:         %d\n" % (self.getMajorNumber())
        rstring += "minor number:         %d\n" %(self.getMinorNumber())
        rstring += "attributes:           %s\n" %(self.getAttributes())
        rstring += "open Ref Count:       %d\n" %(self.getOpenRefCount())
        rstring += "target Count:         %d\n" %(self.getTargetCount())
        rstring += "last event seq num:   %d\n" %(self.getLastEventSequenceNumber())
        rstring += "uuid:                 %s\n" %(self.getUUID())
        return rstring

    def getDeviceMapperName(self):
        return self.__deviceMapperName

    def getMajorNumber(self):
        return self.__majorNumber

    def getMinorNumber(self):
        return self.__minorNumber

    def getAttributes(self):
        return self.__attributes

    def getOpenRefCount(self):
        return self.__openRefCount

    def getTargetCount(self):
        return self.__targetCount

    def getLastEventSequenceNumber(self):
        return self.__lastEventSequenceNumber

    def getUUID(self):
        return self.__uuid

    def getMajorMinorPair(self):
        return "%d:%d" %(self.getMajorNumber(), self.getMinorNumber())


class DMSetupTable:
    def __init__(self, deviceMapperName, startOfMap, lengthOfMap, targetType, targetParameters):
        """
        This is a class that holds the information contained in the file:
        sos_commands/devicemapper/dmsetup_table from a sosreport
        """
        self.__deviceMapperName = deviceMapperName
        self.__startOfMap = int(startOfMap)
        self.__lengthOfMap = int(lengthOfMap)
        self.__targetType = targetType
        self.__targetParameters = targetParameters
        self.__majorMinorPairs = self.__findMajorMinorPairs()

    def __str__(self):
        rstring  = ""
        rstring += "deviceMapperName:     %s\n" %(self.getDeviceMapperName())
        rstring += "start of map:         %d\n" %(self.getStartOfMap())
        rstring += "length of map:        %d\n" %(self.getLengthOfMap())
        rstring += "target type:          %s\n" %(self.getTargetType())
        rstring += "target parameters:    %s\n" %(str(self.getTargetParameters()))
        rstring += "majorminor pairs:      %s\n" %(str(self.getMajorMinorPairs()))
        return rstring

    def __findMajorMinorPairs(self):
        majorMinorPairs = []
        import re
        rem = re.compile("^(?P<majorNumber>\d+):(?P<minorNumber>\d+)")
        for item in self.getTargetParameters():
            mo = rem.match(item)
            if mo:
                majorMinorPairs.append("%s:%s" %(mo.group("majorNumber"), mo.group("minorNumber")))
        return majorMinorPairs

    def getDeviceMapperName(self):
        return self.__deviceMapperName

    def getStartOfMap(self):
        return self.__startOfMap

    def getLengthOfMap(self) :
        return self.__lengthOfMap

    def getTargetType(self):
        return self.__targetType

    def getTargetParameters(self):
        return self.__targetParameters

    def getMajorMinorPairs(self):
        return self.__majorMinorPairs
