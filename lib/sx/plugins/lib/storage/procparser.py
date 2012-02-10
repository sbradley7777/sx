#!/usr/bin/env python
"""
This is a collection of classes that hold data for files that are
located in the /proc directory.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.08
@copyright :  GPLv2
"""
import re
import logging

import sx
from sx.logwriter import LogWriter


class ProcParser:
    def parseProcPartitionsData(procPartitionsData):
        """
        Parses the file in sosreport/sysreport: proc/partitions
        """
        parsedMap = {}
        if (procPartitionsData == None):
            return parsedMap

        for line in procPartitionsData:
            lineSplit = line.split()
            if ((not line.startswith("major")) and ((len(lineSplit) == 4))):
                procPartition = ProcPartitions(lineSplit[0].strip(),lineSplit[1].strip(),
                                               lineSplit[2].strip(),lineSplit[3].strip())
                parsedMap[procPartition.getMajorMinorPair()] = procPartition
        return parsedMap
    parseProcPartitionsData = staticmethod(parseProcPartitionsData)

    def parseProcFilesystemsData(procFilesystemData):
        """
        Parses the file in sosreport/sysreport: proc/filesystems
        """
        parsedList = []
        if (procFilesystemData == None):
            return parsedList

        for line in procFilesystemData:
            lineSplit = line.split()
            if (len(lineSplit) >= 2):
                parsedList.append(ProcFilesystems(lineSplit[0].strip(),lineSplit[1].strip()))
            elif (len(lineSplit) >= 1):
                parsedList.append(ProcFilesystems("",lineSplit[0].strip()))
        return parsedList
    parseProcFilesystemsData = staticmethod(parseProcFilesystemsData)

    def parseProcMountsData(procMountData) :
        """
        Parses the file in sosreport/sysreport: proc/mounts
        """
        parsedList = []
        if (procMountData == None):
            return parsedList
        for line in procMountData:
            lineSplit = line.split()
            parsedList.append(ProcMounts(lineSplit[0].strip(),lineSplit[1].strip(),
                                         lineSplit[2].strip(),lineSplit[3].strip(),
                                         lineSplit[4].strip(),lineSplit[5].strip()))
        return parsedList
    parseProcMountsData =staticmethod(parseProcMountsData)

    def parseProcDevicesData(procDevicesData) :
        """
        Parses the file in sosreport/sysreport: proc/devices
        """
        parsedList = []
        if (procDevicesData == None):
            return parsedList

        deviceType = ""
        for line in procDevicesData:
            lineSplit = line.split()
            if (line.startswith("Character")):
                deviceType = "Character"
            elif (line.startswith("Block")):
                deviceType = "Block"
            elif (len(lineSplit) == 2):
                parsedList.append(ProcDevices(lineSplit[0].strip(),
                                              lineSplit[1].strip(),
                                              deviceType))

        return parsedList
    parseProcDevicesData = staticmethod(parseProcDevicesData)

    def parseProcScsiScsiData(procScsiScsiData) :
        """
        Parses the file in sosreport/sysreport: proc/scsi/scsi
        """
        parsedList = []
        if (procScsiScsiData == None):
            return parsedList

        if (len(procScsiScsiData) == 0):
            return parsedList

        regexStanza1 = "^(?P<host>Host:)" + "(?P<hostData>.*)" + \
            "(?P<channel>Channel:)" + "(?P<channelData>.*)"  + \
            "(?P<channelID>Id:)" + "(?P<channelIDData>.*)"  + \
            "(?P<lun>Lun:)" + "(?P<lunData>.*)"
        remStanza1 = re.compile(regexStanza1)

        regexStanza2 = "^(?P<vendor>  Vendor:)" + "(?P<vendorData>.*)" + \
            "(?P<model>Model:)" + "(?P<modelData>.*)"  + \
            "(?P<rev>Rev:)" + "(?P<revData>.*)"
        remStanza2 = re.compile(regexStanza2)

        regexStanza3 = "^(?P<type>  Type:)" + "(?P<typeData>.*)" + \
            "(?P<ansiRev>ANSI SCSI revision:)" + "(?P<ansiRevData>.*)"
        remStanza3 = re.compile(regexStanza3)

        # Remove that misc text from the data
        if (procScsiScsiData[0].startswith("Attached devices:")):
            procScsiScsiData.pop(0)
        currentScsiDevice = {}
        for line in procScsiScsiData:
            if (line.startswith("Host:")):
                if (len(currentScsiDevice.keys()) == 9):
                    parsedList.append(ProcScsiScsi(currentScsiDevice.get("host"),
                                                   currentScsiDevice.get("channel"),
                                                   currentScsiDevice.get("channelID"),
                                                   currentScsiDevice.get("lun"),
                                                   currentScsiDevice.get("vendor"),
                                                   currentScsiDevice.get("model"),
                                                   currentScsiDevice.get("rev"),
                                                   currentScsiDevice.get("deviceType"),
                                                   currentScsiDevice.get("ansiScsiRevision")))
                currentScsiDevice = {}
                mo = remStanza1.match(line)
                if mo:
                    currentScsiDevice["host"] = mo.group("hostData").strip()
                    currentScsiDevice["channel"] = mo.group("channelData").strip()
                    currentScsiDevice["channelID"] =  mo.group("channelIDData").strip()
                    currentScsiDevice["lun"] =  mo.group("lunData").strip()

            elif (line.startswith("  Vendor:")):
                mo = remStanza2.match(line)
                if mo:
                    currentScsiDevice["vendor"] = mo.group("vendorData").strip()
                    currentScsiDevice["model"] = mo.group("modelData").strip()
                    currentScsiDevice["rev"] =  mo.group("revData").strip()
            elif (line.startswith("  Type:")):
                mo = remStanza3.match(line)
                if mo:
                    currentScsiDevice["deviceType"] = mo.group("typeData").strip()
                    currentScsiDevice["ansiScsiRevision"] = mo.group("ansiRevData").strip()
        return parsedList
    parseProcScsiScsiData = staticmethod(parseProcScsiScsiData)

class ProcPartitions:
    def __init__(self, majorNumber, minorNumber, numberOfBlocks, deviceName):
        """
        This is a class that holds the information contained in the file:
        proc/partitions from a sosreport/sysreport:

        Example Header: major minor  #blocks  name
        """
        self.__majorNumber = int(majorNumber)
        self.__minorNumber = int(minorNumber)
        self.__numberOfBlocks = int(numberOfBlocks)
        self.__deviceName = deviceName

    def __str__(self):
        rstring  = ""
        rstring += "major number:         %d\n" % (self.getMajorNumber())
        rstring += "minor number:         %d\n" %(self.getMinorNumber())
        rstring += "number of blocks:     %d\n" %(self.getNumberOfBlocks())
        rstring += "deviceName:           %s\n" %(self.getDeviceName())
        return rstring

    def getMajorNumber(self):
        return self.__majorNumber

    def getMinorNumber(self):
        return self.__minorNumber

    def getNumberOfBlocks(self):
        return self.__numberOfBlocks

    def getDeviceName(self):
        return self.__deviceName

    def getMajorMinorPair(self):
        return "%d:%d" %(self.getMajorNumber(), self.getMinorNumber())

class ProcFilesystems:
    def __init__(self, devName, fsType):
        """
        This is a class that creates object from the information contained in the file:
        proc/filesystems from a sosreport/sysreport
        """
        self.__devName = devName
        self.__fsType = fsType

    def __str__(self):
        rstring  = ""
        rstring += "dev name:             %s\n" %(self.getDevName())
        rstring += "fs type:              %s\n" %(self.getFSType())
        return rstring

    def getDevName(self):
        return self.__devName

    def getFSType(self):
        return self.__fsType

class ProcMounts:
    def __init__(self, device, mountPoint, fsType, mountOptions, fsDump, fsFsckCheckOrder):
        """
        This is a class that creates object from the information contained in the file:
        proc/mounts from a sosreport/sysreport
        """
        self.__device = device
        self.__mountPoint = mountPoint
        self.__fsType = fsType
        self.__mountOptions = mountOptions
        self.__fsDump = int(fsDump)
        self.__fsFsckCheckOrder = int(fsFsckCheckOrder)

    def __str__(self):
        rstring  = ""
        rstring += "device:               %s\n" %(self.getDevice())
        rstring += "mount point:          %s\n" %(self.getMountPoint())
        rstring += "fs type:              %s\n" %(self.getFSType())
        rstring += "mount options:        %s\n" %(self.getMountOptions())
        rstring += "fs dump:              %d\n" %(self.getFSDump())
        rstring += "fs fsck check order:  %d\n" %(self.getFSFsckCheckOrder())
        return rstring

    def getDevice(self):
        return self.__device

    def getMountPoint(self):
        return self.__mountPoint

    def getFSType(self):
        return self.__fsType

    def getMountOptions(self):
        return self.__mountOptions

    def getFSDump(self):
        return self.__fsDump

    def getFSFsckCheckOrder(self):
        return self.__fsFsckCheckOrder

class ProcDevices:
    def __init__(self, majorNumber, name, deviceType):
        self.__majorNumber = int(majorNumber)
        self.__name = name
        self.__deviceType = deviceType

    def __str__(self):
        rstring  = ""
        rstring += "major number:         %d\n" % (self.getMajorNumber())
        rstring += "name:                 %s\n" %(self.getName())
        rstring += "device type:          %s\n" % (self.getDeviceType())
        return rstring

    def getMajorNumber(self):
        return self.__majorNumber

    def getName(self):
        return self.__name

    def getDeviceType(self):
        # Returns either "Character" or "Block"
        return self.__deviceType

    def isCharacterDevice(self):
        return (self.getDeviceType() == "Character")

    def isBlockDevice(self):
        return (self.getDeviceType() == "Block")

class ProcScsiScsi:
    def __init__(self, host, channel, channelID, lun,
                 vendor, model, rev, deviceType, ansiScsiRevision):
        """
        This is a class that will contain the data for the file:
        proc/scsi/scsi from sosreport/sysreport.

        Example:
        Host: scsi0 Channel: 00 Id: 00 Lun: 00
        Vendor: DGC      Model: RAID 5           Rev: 0326
        Type:   Direct-Access                    ANSI SCSI revision: 04

        """
        self.__host = host
        self.__channel = int(channel)
        self.__channelID = int(channelID)
        self.__lun  = int(lun)
        self.__vendor = vendor
        self.__model = model
        self.__rev = rev
        self.__deviceType = deviceType
        self.__ansiScsiRevision = ansiScsiRevision

    def __str__(self):
        rstring  = ""
        rstring += "host:                 %s\n" %(self.getHost())
        rstring += "channel:              %d\n" %(self.getChannel())
        rstring += "channelID:            %d\n" %(self.getChannelID())
        rstring += "lun:                  %d\n" %(self.getLun())
        rstring += "vendor:               %s\n" %(self.getVendor())
        rstring += "model:                %s\n" %(self.getModel())
        rstring += "rev:                  %s\n" %(self.getRev())
        rstring += "device type:          %s\n" %(self.getDeviceType())
        rstring += "ansi scsi rev:        %s\n" %(self.getAnsiScsiRevision())
        return rstring

    def getHost(self):
        return self.__host

    def getChannel(self):
        return self.__channel

    def getChannelID(self):
        return self.__channelID

    def getLun(self):
        return self.__lun

    def getVendor(self):
        return self.__vendor

    def getModel(self):
        return self.__model

    def getRev(self):
        return self.__rev

    def getDeviceType(self):
        return self.__deviceType

    def getAnsiScsiRevision(self):
        return self.__ansiScsiRevision

    def getHBTLName(self):
        """
        H,B,T,L, are the host, bus, target, and LUN IDs for the
        device. The Bus is the channel, the target is channelID.

        Example:
        5:4:3:1

        The host is 5.
        The channel/bus is 4.
        The channelID/target is 3.
        """
        return "%s:%s:%s:%s" %(self.getHost().strip("scsi"), self.getChannel(), self.getChannelID(), self.getLun())
