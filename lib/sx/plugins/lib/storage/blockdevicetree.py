#!/usr/bin/env python
"""
This is port of the perl script that dwysocha wrote:
http://seg.rdu.redhat.com/~dwysocha/seg-tools/seg-dmsetup-ls-tree



Note: We might need to add regex to all these objects for spaces in
names. Currently I am just doing splits on all the lines except for a
couple parsers.


@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.10
@copyright :  GPLv2
"""
import logging

import sx
from sx.logwriter import LogWriter
from sx.plugins.lib.storage.procparser import ProcParser
from sx.plugins.lib.storage.procparser import ProcPartitions
from sx.plugins.lib.storage.procparser import ProcMounts
from sx.plugins.lib.storage.procparser import ProcDevices
from sx.plugins.lib.storage.procparser import ProcScsiScsi
from sx.plugins.lib.storage.devicemapperparser import DeviceMapperParser
from sx.plugins.lib.storage.devicemapperparser import DMSetupInfoC
from sx.plugins.lib.storage.devicemapperparser import DMSetupTable
from sx.plugins.lib.storage.filesysparser import FilesysParser
from sx.plugins.lib.storage.filesysparser import FilesysMount

class BlockDevice:
    def __init__(self, deviceName, majorNumber, minorNumber):
        self.__deviceName = deviceName
        self.__majorNumber = int(majorNumber)
        self.__minorNumber = int(minorNumber)
        self.__mountPoint = ""

    def __str__(self):
        rstring  = ""
        if (len(self.getMountPoint()) > 0):
            rstring += "%s (%s) [%s]" %(self.getDeviceName(), self.getMajorMinorPair(), self.getMountPoint())
        else:
            rstring += "%s (%s)" %(self.getDeviceName(), self.getMajorMinorPair())
        return rstring

    def compare(self, blockDevice):
        # If objects are the same then return true
        if((blockDevice.getMajorNumber() == self.getMajorNumber()) and
           (blockDevice.getMajorNumber() == self.getMinorNumber())):
            return True
        return False

    def getDeviceName(self):
        return self.__deviceName

    def getMajorNumber(self):
        return self.__majorNumber

    def getMinorNumber(self):
        return self.__minorNumber

    def getMajorMinorPair(self):
        return "%d:%d" %(self.getMajorNumber(), self.getMinorNumber())

    def getMountPoint(self):
        return self.__mountPoint

    def setMountPoint(self, mountPoint):
        self.__mountPoint = mountPoint


class DeviceMapperBlockDevice(BlockDevice):
    def __init__(self, deviceName, deviceMapperName, majorNumber, minorNumber):
        BlockDevice.__init__(self, deviceName, majorNumber, minorNumber)

        # Device Mapper name
        self.__deviceMapperName = deviceMapperName

        # The type of target
        self.__targetType = ""

        # A list of all the major:minor dependenies for this BlockDevice
        self.__majorMinorPairDependenciesList = []

        # A map of BlockDevice dependencies on this DeviceMapperBlockDevice
        self.__blockDeviceDependenciesList = []

    def __str__(self):
        # Format the major:minor pairs list to a string
        mmPairs = self.getMajorMinorPairDependenciesList()
        formattedMMPairs = ""
        for mmPair in mmPairs:
            formattedMMPairs += "%s " %(mmPair)
        formattedMMPairs = formattedMMPairs.strip()

        rstring  = ""
        rstring += "%s %s (%s) (%s) (%s) " %(self.getDeviceMapperName(),
                                             self.getDeviceName(),
                                             self.getMajorMinorPair(),
                                             self.getTargetType(),
                                             formattedMMPairs)
        if (len(self.getMountPoint()) > 0):
            rstring += "[%s] " %(self.getMountPoint())
        if (len(self.getBlockDeviceDependenciesList()) > 0):
            rstring += "\n"
            for blockDevice in self.getBlockDeviceDependenciesList():
                rstring += "  %s\n" %(blockDevice)
        return rstring

    def getDeviceMapperName(self):
        return self.__deviceMapperName

    def getTargetType(self):
        return self.__targetType

    def getBlockDeviceDependenciesList(self):
        return self.__blockDeviceDependenciesList

    def getMajorMinorPairDependenciesList(self):
        return self.__majorMinorPairDependenciesList

    def setTargetType(self, targetType):
        self.__targetType = targetType

    def addMajorMinorPairDependency(self, majorMinorPairDependency):
        if (self.getMajorMinorPair() == majorMinorPairDependency):
            return False
        for pair in self.getMajorMinorPairDependenciesList():
            if (pair == majorMinorPairDependency):
                return False
        self.__majorMinorPairDependenciesList.append(majorMinorPairDependency)
        return True

    def addBlockDeviceDependency(self, blockDevice):
        if (blockDevice.compare(self)):
            return False
        for currentlBlockDevice in self.getBlockDeviceDependenciesList():
            if (currentlBlockDevice.compare(blockDevice)):
                return False
        self.__blockDeviceDependenciesList.append(blockDevice)
        return True

class BlockDeviceTree:
    def __init__(self, procPartitionsList, procFilesystemsList,
                 procDevicesList, procScsiScsiList,
                 filesysMountList, dmsetupInfoCData, dmsetupTableData):

        self.__validTargetTypes = ["linear", "striped", "mirror", "snapshot-origin",
                                   "snapshot", "error", "zero", "multipath"]

        self.__procFilesystemsList = procFilesystemsList
        self.__procPartitionsMap = procPartitionsList
        self.__procDevicesList = procDevicesList
        self.__procScsiScsiList = procScsiScsiList
        self.__filesysMountList = filesysMountList

        self.__dmsetupInfoCMap = DeviceMapperParser.parseDMSetupInfoCData(dmsetupInfoCData)
        self.__dmsetupTableList = DeviceMapperParser.parseDMSetupTableData(dmsetupTableData)


    def __str__(self):
        rstring  = ""
        return rstring

    # ###########################################################################
    # These are the get functions to get private vars
    # ###########################################################################
    def getProcPartitionsMap(self):
        return self.__procPartitionsMap

    def getProcFilesystemsList(self):
        return self.__procFilesystemsList

    def getProcDevicesList(self):
        return self.__procDevicesList

    def getProcScsiSciList(self):
        return self.__procScsiScsiList

    def getFilesysMountList(self):
        return self.__filesysMountList

    def getDMSetupInfoMap(self):
        return self.__dmsetupInfoCMap

    def getDMSetupTableList(self):
        return self.__dmsetupTableList

    # ###########################################################################
    # Helper functions
    # ###########################################################################
    def __getDeviceMapperMajorNumber(self):
        for device in self.getProcDevicesList() :
            if (device.getName() == "device-mapper"):
                return device.getMajorNumber()
        # If there is no device with the name "device-mapper" than
        # return default number
        return 253

    def generateDMBlockDeviceMap(self):
        # This map is key == "major:minor" pair and value is the
        # DeviceMapperBlockDevice. This will be based on what is in proc/partitions
        blockDeviceMap = {}
        if (not len(self.getDMSetupInfoMap().keys())):
            message = "The block device tree will not be generated since there was no dmsetup_info data."
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)
            return blockDeviceMap
        elif (not len(self.getProcPartitionsMap().keys())):
            message = "The block device tree will not be generated since there was no /proc/partitions data."
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)
            return blockDeviceMap

        # Generate a map of the devices that are mounted. The key will
        # be devicename with "/dev/" or "/dev/mapper/" string
        # removed. The map will create quicker lookups.
        relativeFilesysMountMap = {}
        for filesysMount in self.getFilesysMountList():
            filesysDeviceName = filesysMount.getDeviceName()
            filesysDeviceName = filesysDeviceName.replace("/dev/mapper/", "")
            filesysDeviceName = filesysDeviceName.replace("/dev/", "")
            relativeFilesysMountMap[filesysDeviceName] = filesysMount

        # Major Number for all major Device Mapper devices
        deviceMapperMajorNumber = self.__getDeviceMapperMajorNumber()

        # Build the map of all the block devices
        for key in self.__procPartitionsMap.keys():
            procPartition = self.__procPartitionsMap.get(key)

            # Create a blockdevice on everything first and we can
            # change to dmmbd if needed.
            blockDevice = BlockDevice(procPartition.getDeviceName(),
                                      procPartition.getMajorNumber(),
                                      procPartition.getMinorNumber())

            if (not (deviceMapperMajorNumber == procPartition.getMajorNumber())):
                # If there is a mount point for this device name then
                # set the mount point.
                if (relativeFilesysMountMap.has_key(blockDevice.getDeviceName())):
                    blockDevice.setMountPoint(relativeFilesysMountMap[blockDevice.getDeviceName()].getMountPoint())
            elif (self.getDMSetupInfoMap().has_key(key)):
                # If this is a devicemapper block device then create a
                # DeviceMapperBlockDevice instead.

                dmsetupInfoItem = self.getDMSetupInfoMap()[key]
                deviceMapperName = dmsetupInfoItem.getDeviceMapperName()
                blockDevice = DeviceMapperBlockDevice(procPartition.getDeviceName(), deviceMapperName,
                                                        dmsetupInfoItem.getMajorNumber(), dmsetupInfoItem.getMinorNumber())

                for dmsetupTable in self.getDMSetupTableList():
                    if(dmsetupTable.getDeviceMapperName() == deviceMapperName):
                        blockDevice.setTargetType(dmsetupTable.getTargetType())
                        for mmPair in dmsetupTable.getMajorMinorPairs():
                            blockDevice.addMajorMinorPairDependency(mmPair)

                # If there is a mount point for this devicemapper name
                # then set the mount point.
                if (relativeFilesysMountMap.has_key(deviceMapperName)):
                    blockDevice.setMountPoint(relativeFilesysMountMap[deviceMapperName].getMountPoint())
            # Add the blockDevice to the map
            blockDeviceMap[key] = blockDevice

        # Now build the dependencies tree
        for key in blockDeviceMap.keys():
            currentBlockDevice = blockDeviceMap[key]
            if ((deviceMapperMajorNumber == currentBlockDevice.getMajorNumber()) and
                (self.getDMSetupInfoMap().has_key(key))):
                mmDepsPairs = currentBlockDevice.getMajorMinorPairDependenciesList()
                for mmPair in mmDepsPairs:
                    if (blockDeviceMap.has_key(mmPair)):
                        currentBlockDevice.addBlockDeviceDependency(blockDeviceMap[mmPair])
        return blockDeviceMap

    def getTargetTypeMap(self, blockDeviceMap, targetType):
        """
        Get maps for certain types:

        The valid target types are: linear, striped, mirror, snapshot-origin,
        snapshot, error, zero, multipath.

        If the target type is not in the list then we return all
        targets.
        """
        if (not (targetType in self.__validTargetTypes)):
            return blockDeviceMap
        rMap = {}
        for key in blockDeviceMap.keys():
            currentBlockDevice = blockDeviceMap[key]
            if(currentBlockDevice.__class__.__name__ == "DeviceMapperBlockDevice"):
                if (currentBlockDevice.getTargetType() == targetType):
                    rMap[key] = currentBlockDevice
        return rMap

    def getSummary(self):
        rstring = ""
        blockDeviceMap = self.generateDMBlockDeviceMap()
        if (not len(blockDeviceMap.keys())):
            return rstring
        # Print a summary of the devicemapper devices. Group by target type.
        for targetType in self.__validTargetTypes:
            currentBlockDeviceMap = self.getTargetTypeMap(blockDeviceMap, targetType)
            if (len(currentBlockDeviceMap) > 0):
                rstring += "Target Type: %s (%d targets)\n------------------------------------------\n" %(targetType, len(currentBlockDeviceMap))
                for key in currentBlockDeviceMap.keys():
                    currentBlockDevice = currentBlockDeviceMap[key]
                    rstring += "\n%s\n-------\n" %str(currentBlockDevice)
                rstring += "\n"

        rstring += "Non-DeviceMapper Devices \n------------------------------------------\n"
        for key in blockDeviceMap.keys():
            currentBlockDevice = blockDeviceMap[key]
            if(not (currentBlockDevice.__class__.__name__ == "DeviceMapperBlockDevice")):
                rstring += "\n%s\n\n-------\n" %str(currentBlockDevice)
        return rstring
