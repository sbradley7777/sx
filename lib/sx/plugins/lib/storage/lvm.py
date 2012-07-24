#!/usr/bin/env python
"""

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.11
@copyright :  GPLv2
"""
import os.path

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
        return self.__pFree

    def getDeviceSize(self):
        return self.__deviceSize

    def getPVUUID(self):
        return self.__pvUUID

class VGS_V:
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

    def getAttribute(self, attributeName):
        attributesMap = self.getAttributesMap()
        if (attributesMap.has_key("clustered")):
            return attributesMap.get("clustered")
        return ""

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

    def isClusteredBitEnabled(self):
        return (self.getAttribute("clustered") == "c")

class LVS_AO:
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

class LVM:
    def __init__(self, pathToDevice, vgsvList, lvsaoList, lvmConfData):
        self.__pathToDevice = pathToDevice
        # This is a list of object from sparsed output of the command: "vgs_-v"
        self.__vgsvList = vgsvList
        # This is a list of object from sparsed output of the command:
        # "lvs_-a_-o_devices"
        self.__lvsaoList = lvsaoList
        # Parse lvm.conf file in a list of lines.
        self.__lvmConfData = lvmConfData

    def getPathToDevice(self):
        return self.__pathToDevice

    # #######################################################################
    # LVM helper functions - EVENTUALLY NEED TO MOVE TO STORAGE LIB
    # #######################################################################
    def getVolumeGroupForDevice(self):
        for lvs in self.__lvsaoList:
            vgName = lvs.getVGName().strip().rstrip()
            lvName = lvs.getLVName().strip().rstrip()
            # Possible vglv paths
            pathToVGLVList = [os.path.join("/dev/mapper", "%s-%s" %(vgName, lvName)),
                              os.path.join("/dev", "%s/%s" %(vgName, lvName))]
            if (self.__pathToDevice in pathToVGLVList):
                for vgs in self.__vgsvList:
                    if (vgs.getVGName() == vgName):
                        return vgs
        return None

    def getLogicalVolumeForDevice(self):
        filenameOfDevice = os.path.basename(self.__pathToDevice)
        for lvs in self.__lvsaoList:
            vgName = lvs.getVGName().strip().rstrip()
            lvName = lvs.getLVName().strip().rstrip()
            # Possible vglv paths
            pathToVGLVList = [os.path.join("/dev/mapper", "%s-%s" %(vgName, lvName)),
                              os.path.join("/dev", "%s/%s" %(vgName, lvName))]
            if (self.__pathToDevice in pathToVGLVList):
                return lvs
        return None

    def isLVMDevice(self):
        return (self.getLogicalVolumeForDevice() == None)

    def isClusteredLVMDevice(self):
        # This assumes that volume is in the list and vg will be found.
        vg = self.getVolumeGroupForDevice()
        if (not vg == None):
            return vg.isClusteredBitEnabled()
        # Return False if vg is not found.
        return False

    def getVolumelistValues(self):
        volumelistValues = []
        volumelistLine = ""
        for line in self.__lvmConfData:
            currentLine = line.strip().rstrip()
            if (currentLine.startswith("volume_list")):
                # Set the most recent occurance
                volumelistLine = currentLine

        # If not empty then the volume_list line is enabled.
        if (len(volumelistLine) > 0):
            splitLine = volumelistLine.split("=")
            if (len(splitLine) == 2):
                # Do some crazy splitting to remove white spaces and [] and all
                # the quotes around the value.
                configValues = splitLine[1].strip().rstrip().strip("[").rstrip("]").strip().rstrip().replace('"', "")
                volumelistValues = configValues.split(",")
        return volumelistValues

    def isLVMVolumeInVolumelist(self, volumelistValues, lvs):
        if (len(volumelistValues) > 0):
            vgName = lvs.getVGName().strip().rstrip()
            lvName = lvs.getLVName().strip().rstrip()
            vglvName = "%s/%s" %(vgName, lvName)
            # Search the use cases that are documented in /etc/lvm/lvm.conf and
            # "man lvm.conf" sections "Host tag settings" and "volume_list"
            if (vgName in volumelistValues):
                # "vgname" matched exactly
                return True
            elif (vglvName in volumelistValues):
                # "vgname/lvname" are matched exactly.
                return True
            elif ("@*" in volumelistValues):
                # They are activating all volume groups and logical volume groups
                return True
            # Need to code in searching for tags in next elif statement.  This
            # directory contains the latest backup of the metadata for the
            # volumegroups/etc/lvm/backup/ so that i can get "tag" information.
            # Current matching tags and vg/lv is not supported.
        return False

    def isLVMVolumeHALVM(self):
        # This assumes that volume is in the list and vg will be found.
        if (self.isClusteredLVMDevice()):
            # Might want to check the release since CLVMD support was not added to version 5.6.
            return True
        # The vg does not have the cluster bit set, so check to see if
        # volume_list is set.
        vgs = self.getVolumeGroupForDevice()
        if (vgs == None):
            return False
        lvs = self.getLogicalVolumeForDevice()
        if (lvs == None):
            return False
        volumelistValues = self.getVolumelistValues()
        if (len(volumelistValues) > 0):
            # If volume_list is defined and the vg or vg/lv is not defined in
            # volume_list return True. Now rgmanager(clusterHA clustered service manager
            # uses tags so that it adds the hostname as tag and then adds that
            # tag to the volume_group.
            return (not self.isLVMVolumeInVolumelist(volumelistValues, lvs))
        return False
