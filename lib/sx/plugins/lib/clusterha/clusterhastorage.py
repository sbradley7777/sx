#!/usr/bin/env python
"""
This script will create a class that will be used to get informaton about GFS,
GFS2, and filesystem resources in the cluster.conf.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""
import re
import os.path
import logging
import textwrap

import sx
from sx.tools import StringUtil
from sx.logwriter import LogWriter
from sx.plugins.lib.clusterha.clusterhaconfanalyzer import ClusterHAConfAnalyzer
from sx.plugins.lib.clusterha.clusternode import ClusterStorageFilesystem

from sx.plugins.lib.storage.lvm import LVM
from sx.plugins.lib.storage.devicemapperparser import DeviceMapperParser
from sx.plugins.lib.storage.devicemapperparser import DMSetupInfoC
from sx.plugins.lib.kernel import KernelRelease

class ClusterHAStorage():
    def __init__(self, cnc):
        self.__cnc = cnc
        # Seperator between sections:
        self.__seperator = "-------------------------------------------------------------------------------------------------"

    def getClusterStorageSummary(self) :
        """
        Returns a string that contains information about the GFS1 and
        GFS2 filesystems found.

        @return: A string that contains information about the GFS1 and
        GFS2 filesystems found.
        @rtype: String
        """
        fsMap = {}
        for clusternode in self.__cnc.getClusterNodes():
            clusternodeName = clusternode.getClusterNodeName()
            csFilesystemList = clusternode.getClusterStorageFilesystemList()
            for fs in csFilesystemList:
                locationFound = ""
                if (fs.isEtcFstabMount()):
                    locationFound += "F"
                if (fs.isFilesysMount()):
                    locationFound += "M"
                if (fs.isClusterConfMount()):
                    locationFound += "C"
                if (not fsMap.has_key(clusternodeName)):
                    fsMap[clusternodeName] = []
                fsMap.get(clusternodeName).append([fs.getDeviceName(), fs.getMountPoint(), fs.getFSType(), locationFound])
        rString  = ""
        fsListHeader = ["device", "mount_point", "fs_type", "location_found"]
        stringUtil = StringUtil()
        for clusternodeName in self.__cnc.getClusterNodeNames():
            # In the future I should probably add a way to only print once if they are all the same .
            if (fsMap.has_key(clusternodeName)):
                listOfFileystems = fsMap.get(clusternodeName)
                if (len(listOfFileystems) > 0):
                    tableString = "%s(%d mounted GFS or GFS2 file-systems)\n%s\n\n" %(clusternodeName, len(listOfFileystems), stringUtil.toTableString(listOfFileystems, fsListHeader))
                    rString += tableString
        if (len(rString) > 0):
            description =  "All GFS or GFS2 filesystem are required to be created on a clustered lvm(clvm) device. All GFS or GFS2 filesystems "
            description += "should be verified that they meet this requirement. The following article describes this requirement:"
            urls = ["https://access.redhat.com/knowledge/solutions/46637"]
            legend = "C = file-system is in /etc/cluster/cluster.conf\nF = file-system is in /etc/fstab\nM = file-system is mounted\n"
            rString = "%s\n%s\n%s" %(StringUtil.wrapParagraphURLs(description, urls), legend, rString)
        return rString.strip()

    # #######################################################################
    # Evaluate Function
    # #######################################################################
    def getSummary(self):
        # Return string for evaluation.
        rString = ""
        # Nodes that are in cluster.conf, so should have report of all these
        baseClusterNode = self.__cnc.getBaseClusterNode()
        if (baseClusterNode == None):
            # Should never occur since node count should be checked first.
            return ""
        cca = ClusterHAConfAnalyzer(baseClusterNode.getPathToClusterConf())
        # ###################################################################
        # Get the GFS/GFS2 storage summary
        # ###################################################################
        result = self.getClusterStorageSummary()
        if (len(result) > 0):
            sectionHeader = "%s\nGFS and GFS2 Filesystem Summary\n%s" %(self.__seperator, self.__seperator)
            rString += "%s\n%s\n\n" %(sectionHeader, result)
        """
        # ###################################################################
        # Get the fs.sh resources and write summary
        # ###################################################################
        result = ""
        fsListHeader = ["device", "mount_point", "fs_type"]
        stringUtil = StringUtil()

        fsTable = []
        filesystemResourcesList = cca.getFilesystemResourcesList()
        if (len(filesystemResourcesList) > 0):
            for clusterConfMount in filesystemResourcesList:
                currentFS = [clusterConfMount.getDeviceName(), clusterConfMount.getMountPoint(), clusterConfMount.getFSType()]
                if (not currentFS in fsTable):
                    fsTable.append(currentFS)
        if (len(fsTable) > 0):
            # Should flag for vgs with no c bit set and no lvm on device path.
            stringUtil = StringUtil()
            sectionHeader =  "%s\nFilesystem and Clustered-Filesystem cluster.conf Summary\n%s" %(self.__seperator, self.__seperator)
            #tableHeader = ["device_name", "mount_point", "fs_type"]
            #tableOfStrings = stringUtil.toTableString(fsTable, tableHeader)
            description =  "There was %d filesystems resources found. It is recommended that all filesystem resources(fs.sh) are created on a HALVM device." %(len(fsTable))
            description += "The following article describes this procedure:"
            urls = ["https://access.redhat.com/knowledge/solutions/3067"]
            # rString += "%s\n%s\n%s\n\n" %(sectionHeader, StringUtil.wrapParagraphURLs(description, urls), tableOfStrings)
            rString += "%s\n%s\n" %(sectionHeader, StringUtil.wrapParagraphURLs(description, urls))
        """
        # ###################################################################
        # Write summary of status of HALVM and CLVM
        # ###################################################################
        lvmSummary = ""
        for clusternode in self.__cnc.getClusterNodes():
            devicemapperCommandsMap =  self.__cnc.getStorageData(clusternode.getClusterNodeName()).getDMCommandsMap()
            lvm = LVM(DeviceMapperParser.parseVGSVData(devicemapperCommandsMap.get("vgs_-v")),
                      DeviceMapperParser.parseLVSAODevicesData(devicemapperCommandsMap.get("lvs_-a_-o_devices")),
                      self.__cnc.getStorageData(clusternode.getClusterNodeName()).getLVMConfData())
            currentSummary =""
            lockingType = lvm.getLockingTypeValue()
            currentSummary += "  /etc/lvm/lvm.conf -> locking_type: %s\n" %(lockingType)

            volume_list = lvm.getVolumeListValues()
            volumesListValues = ""
            for item in volume_list:
               volumesListValues += "%s |" %(item)
            volumesListValues = volumesListValues.rstrip("|")
            if (not len(volumesListValues) > 0):
                volumesListValues = "No volumes found for this configuration option."
            currentSummary += "  /etc/lvm/lvm.conf -> volume_list:  %s\n" %(volumesListValues)

            # Check to see clvmd is enabled at boot.
            serviceName = "clvmd"
            clvmdServiceSummary = "There was either an error finding the status for the service \"%s\" used by Cluster HA.\n" %(serviceName)
            for chkConfigItem in clusternode.getChkConfigList():
                if (chkConfigItem.getName() == serviceName):
                    clvmdServiceSummary = "%s\n" %(chkConfigItem)
                    break;
            currentSummary += "  %s runlevel status -> %s\n" %(serviceName, clvmdServiceSummary)
            # Add current summary to lvm summary
            if (len(currentSummary) > 0):
                lvmSummary += "%s:\n%s" %(clusternode.getClusterNodeName(), currentSummary)
        # List the first 10 vgs and will have to search each report till all the
        # information is found on them. This means taking all the filesystems in
        # cluster.conf, finding vg informaiton on the first 10 found then add to
        # lvm summary. The goal is to print vgs and all the bit set so that you
        # will know if clustered but dont want to spam the report file.


        # Add lvm summary to return string.
        if (len(lvmSummary) > 0):
            sectionHeader = "%s\nLVM Summary\n%s" %(self.__seperator, self.__seperator)
            message = "If there are no values for some options then possible that they are commented out or the files\nfor option was not found."
            rString += "%s\n%s\n\n%s\n\n" %(sectionHeader, message, lvmSummary)
        return rString.rstrip()


    # #######################################################################
    # Evaluate Helper Function
    # #######################################################################
    def __isNFSChildOfClusterStorageResource(self, cca, csFilesystem):
        # Just need to find 1 match. If clusterstorage fs has 1 nfs child then
        # requires localflocks to be enabled.
        clusteredServices = cca.getClusteredServices()
        for clusteredService in clusteredServices:
            resourcesInFlatList = clusteredService.getFlatListOfClusterResources()
            clusterfsResource = None
            for resource in resourcesInFlatList:
                if ((resource.getType() == "clusterfs") and (len(resource.getAttribute("device")) > 0)):
                    if (csFilesystem.getDeviceName() == resource.getAttribute("device")):
                        # Found Match for the filesystem
                        clusterfsResource = resource
                elif (not clusterfsResource == None):
                    # Since the clusterfsResource is not None then next resource
                    # should be nfs export. If not then either no nfs export or
                    # not configured correctly cause nfsexport uses inhertiance
                    # to get fs to use. Break out of loop after this condition
                    # is checked.
                    if ((resource.getLevel() == (clusterfsResource.getLevel() + 1)) and (resource.getType() == "nfsexport")):
                        return True
        return False

    def __doesGFS2ModuleNeedRemoval(self, unameA, packages):
        """
        In Red Hat Enterprise Linux 5.2, GFS2 was provided as a kernel
        module for evaluation purposes. In Red Hat Enterprise Linux
        5.3 GFS2 is now part of the kernel package.

        If the Red Hat Enterprise Linux 5.2 GFS2 kernel modules have
        been installed they must be removed to use GFS2 in Red Hat
        Enterprise Linux 5.3. This function returns true if currently
        running kernel should have kmod-gfs* removed.

        @return: Returns True if kmod-gfs should be removed.
        @rtype: Boolean

        @param unameAData: A data that contains the uname -a fs.
        @type unameA: UnameA
        @param packages: A list of packages.
        @type packages: Array
        """
        kernelRelease = unameA.getKernelRelease()
        if (not len(str(kernelRelease)) > 0):
            return False

        isGFS2moduleInstalled = False
        for package in packages:
            if (package.startswith("kmod-gfs2")) :
                isGFS2moduleInstalled = True
                break;
        return ((isGFS2moduleInstalled) and (int(kernelRelease.getMinorReleaseNumber()) >= 128) and
                (kernelRelease.getMajorReleaseNumber() == "2.6.18"))

    # #######################################################################
    # Evaluate Functions
    # #######################################################################
    def evaluateNonClusteredFilesystems(self):
        """
        This functions verifies that all fs resources are using HALVM. This
        checks to see if clusterbit on lvm vg is set or if they are using
        "volume_list" method in /etc/lvm/lvm.conf.

        Do note that tags in "volume_list" option are not checked.
        """
        rString = ""
        baseClusterNode = self.__cnc.getBaseClusterNode()
        if (baseClusterNode == None):
            return rString
        cca = ClusterHAConfAnalyzer(baseClusterNode.getPathToClusterConf())
        fsTable = []
        filesystemResourcesList = cca.getFilesystemResourcesList()
        if (len(filesystemResourcesList) > 0):
            for clusterConfMount in filesystemResourcesList:
                currentFS = [clusterConfMount.getDeviceName(), clusterConfMount.getMountPoint(), clusterConfMount.getFSType()]
                if (not currentFS in fsTable):
                    fsTable.append(currentFS)
        if (len(fsTable) > 0):
            stringUtil = StringUtil()
            sectionHeader =  "%s\nFilesystem and Clustered-Filesystem cluster.conf Summary\n%s" %(self.__seperator, self.__seperator)
            description =  "There was %d filesystems resources(fs.sh) found in the cluster.conf. It is recommended that all filesystem resource\'s(fs.sh) " %(len(fsTable))
            description += "underlying storage device is using one(not both) of the 2 methods for HALVM as described in article below for the underlying "
            description += "storage device. The following article describes these procedures:"
            urls = ["https://access.redhat.com/knowledge/solutions/3067"]
            rString += StringUtil.formatBulletString(description, urls)
        # Disabled for now and will return an empty string
        """
        baseClusterNode = self.__cnc.getBaseClusterNode()
        if (baseClusterNode == None):
            return rString
        cca = ClusterHAConfAnalyzer(baseClusterNode.getPathToClusterConf())
        fsTable = []
        filesystemResourcesList = cca.getFilesystemResourcesList()
        for clusternode in self.__cnc.getClusterNodes():
            clusterNodeEvalString = ""
            # Check to see if volume_list and locking_type 3 is set for cluster
            # locking.
            if (len(filesystemResourcesList) > 0):
                devicemapperCommandsMap =  self.__cnc.getStorageData(clusternode.getClusterNodeName()).getDMCommandsMap()
                lvm = LVM(DeviceMapperParser.parseVGSVData(devicemapperCommandsMap.get("vgs_-v")),
                          DeviceMapperParser.parseLVSAODevicesData(devicemapperCommandsMap.get("lvs_-a_-o_devices")),
                          self.__cnc.getStorageData(clusternode.getClusterNodeName()).getLVMConfData())
                if (lvm.isVolumeListEnabled() and lvm.isLockingTypeClustering()):
                    description =  "The option \"volume_list\" and \"locking_type = 3\" in /etc/lvm/lvm.conf are both in use. Using "
                    description += "both options at the same time is supported, but not recommended except for certain configurations. "
                    description += "This configuration should be reviewed to verify that configuration is correct."
                    urls = ["https://access.redhat.com/knowledge/solutions/3067"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)
            # Check to see if device is either has volume_list set or has
            # cluster bit set on each fs resource.
            for clusterConfMount in filesystemResourcesList:
                pathToDevice = str(clusterConfMount.getDeviceName().strip().rstrip())
                if (not lvm.isLVMVolumeHALVM(pathToDevice)):
                    currentFS = [clusterConfMount.getDeviceName(), clusterConfMount.getMountPoint(), clusterConfMount.getFSType()]
                    if (not currentFS in fsTable):
                        fsTable.append(currentFS)
        if (len(fsTable) > 0):
            # Should flag for vgs with no c bit set and no lvm on device path.
            stringUtil = StringUtil()
            description =  "The following filesystems appears to not be on a HALVM volume using one of the methods outlined in the article below. "
            description += "A HALVM volume is recommoned for all fs resources. Do note that LVM tags were not searched and compared if they were "
            description += "used in the \"volume_list\" option of the /etc/lvm/lvm.conf file:"
            tableHeader = ["device_name", "mount_point", "fs_type"]
            tableOfStrings = stringUtil.toTableStringsList(fsTable, tableHeader)
            urls = ["https://access.redhat.com/knowledge/solutions/3067"]
            rString += StringUtil.formatBulletString(description, urls, tableOfStrings)
        """
        return rString

    def evaluateClusteredFilesystems(self):
        # Is active/active nfs supported? Sorta
        # urls = ["https://access.redhat.com/knowledge/solutions/59498"]

        rString = ""
        baseClusterNode = self.__cnc.getBaseClusterNode()
        if (baseClusterNode == None):
            return rString
        cca = ClusterHAConfAnalyzer(baseClusterNode.getPathToClusterConf())

        if ((cca.getTransportMode() == "broadcast") or (cca.getTransportMode() == "udpu")):
            for clusternode in self.__cnc.getClusterNodes():
                if (len(clusternode.getClusterStorageFilesystemList()) > 0):
                    description =  "There is known limitations for GFS2 filesystem when using the "
                    description += "following transports: \"%s\"." %(cca.getTransportMode())
                    urls = ["https://access.redhat.com/site/articles/146163", "https://access.redhat.com/site/solutions/459243"]
                    rString += "%s\n" %(StringUtil.formatBulletString(description, urls))
                    break;
        for clusternode in self.__cnc.getClusterNodes():
            stringUtil = StringUtil()
            clusterNodeEvalString = ""
            # ###################################################################
            # Distro Specific evaluations
            # ###################################################################
            # The distro release of this node
            distroRelease = clusternode.getDistroRelease()
            if ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() == 5)):
                # Check if GFS2 module should be removed on RH5 nodes
                if (self.__doesGFS2ModuleNeedRemoval(clusternode.getUnameA(), clusternode.getClusterModulePackagesVersion())) :
                    description = "The kmod-gfs2 is installed on a running kernel >= 2.6.18-128. This module should be removed since the module is included in the kernel."
                    urls = ["https://access.redhat.com/knowledge/solutions/17832"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

            # ###################################################################
            # Analyze the Clustered Storage
            # ###################################################################
            listOfClusterStorageFilesystems = clusternode.getClusterStorageFilesystemList()

            # ###################################################################
            # Verify that GFS/GFS2 filesystem is using lvm with cluster bit set
            # ###################################################################
            fsTable = []
            # Verify the locking_type is set to 3 cause built-in cluster locking is required.
            if (len(listOfClusterStorageFilesystems) > 0):
                devicemapperCommandsMap =  self.__cnc.getStorageData(clusternode.getClusterNodeName()).getDMCommandsMap()
                lvm = LVM(DeviceMapperParser.parseVGSVData(devicemapperCommandsMap.get("vgs_-v")),
                          DeviceMapperParser.parseLVSAODevicesData(devicemapperCommandsMap.get("lvs_-a_-o_devices")),
                          self.__cnc.getStorageData(clusternode.getClusterNodeName()).getLVMConfData())
                if (not lvm.isLockingTypeClustering()):
                    description =  "The locking_type is not set to type 3 for built-in cluster locking. A GFS/GFS2 filesystem requires the filesystem be on a "
                    description += "clustered LVM volume with locking_type 3 enabled in the /etc/lvm/lvm.conf."
                    urls = ["https://access.redhat.com/knowledge/solutions/46637"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

            # Disabling this check for now cause still working on how to do it.
            """
            # Verify that the clustered filesystem has clusterbit set on the vg.
            # Verify the locking_type is set to 3 cause built-in cluster locking is required.
            fsTable = []
            if (len(listOfClusterStorageFilesystems) > 0):
                devicemapperCommandsMap =  self.__cnc.getStorageData(clusternode.getClusterNodeName()).getDMCommandsMap()
                lvm = LVM(DeviceMapperParser.parseVGSVData(devicemapperCommandsMap.get("vgs_-v")),
                          DeviceMapperParser.parseLVSAODevicesData(devicemapperCommandsMap.get("lvs_-a_-o_devices")),
                          self.__cnc.getStorageData(clusternode.getClusterNodeName()).getLVMConfData())
                for csFilesystem in listOfClusterStorageFilesystems:
                   pathToDevice = str(csFilesystem.getDeviceName().strip().rstrip())
                   if (not lvm.isClusteredLVMDevice(pathToDevice)):
                       currentFS = [pathToDevice, csFilesystem.getMountPoint(), csFilesystem.getFSType()]
                       if (not currentFS in fsTable):
                           fsTable.append(currentFS)
            if (len(fsTable) > 0):
                stringUtil = StringUtil()
                description = "The following filesystems appears not to be on a clustered LVM volume. A clustered LVM volume is required for GFS/GFS2 fileystems."
                tableHeader = ["device_name", "mount_point", "fs_type"]
                tableOfStrings = stringUtil.toTableStringsList(fsTable, tableHeader)
                urls = ["https://access.redhat.com/knowledge/solutions/46637"]
                clusterNodeEvalString += StringUtil.formatBulletString(description, urls, tableOfStrings)
            """
            # ###################################################################
            # Verify they are exporting a gfs/gfs2 fs via samba and nfs correctly
            # ###################################################################
            tableHeader = ["device_name", "mount_point", "nfs_mp", "smb_mp"]
            fsTable = []
            for csFilesystem in listOfClusterStorageFilesystems:
                # There are 4 ways of mounting gfs via nfs/smb at same time that
                # needs to be checked:

                # 1) nfs mount via /etc/exports  and smb mount via /etc/samba/smb.conf
                # 2) nfs mount via /etc/cluster/cluster.conf and smb mount via /etc/cluster/cluster.conf
                # 3) nfs mount via /etc/cluster/cluster.conf and smb mount via /etc/samba/smb.conf.
                # 4) nfs mount via /etc/exports and smb mount via /etc/cluster/cluster.conf
                if (csFilesystem.isEtcExportMount() and csFilesystem.isSMBSectionMount()):
                    # 1) nfs mount via /etc/exports  and smb mount via /etc/samba/smb.conf
                    #print "1: %s" %(csFilesystem.getMountPoint())
                    nfsMP = csFilesystem.getEtcExportMount().getMountPoint()
                    smbSectionList = csFilesystem.getSMBSectionMountList()
                    if (len(smbSectionList) > 0):
                        smbMP = smbSectionList.pop().getOptionValue("path").strip()
                        fsTable.append([csFilesystem.getDeviceName(), csFilesystem.getMountPoint(), "%s(EN)" %(nfsMP), "%s(ES)" %(smbMP)])
                        for smbSection in smbSectionList:
                            smbMP = smbSection.getOptionValue("path").strip()
                            fsTable.append(["", "", "", "%s(ES)" %(smbMP)])
                elif ((not csFilesystem.isEtcExportMount()) and (not csFilesystem.isSMBSectionMount())):
                    # 2) nfs mount via /etc/cluster/cluster.conf and smb mount via /etc/cluster/cluster.conf
                    #print "2: %s" %(csFilesystem.getMountPoint())
                    if((self.__isNFSChildOfClusterStorageResource(cca, csFilesystem)) and
                       (len(csFilesystem.getClusteredSMBNames()) > 0)):
                        nfsMP = csFilesystem.getMountPoint()
                        smbPaths = []
                        for name in csFilesystem.getClusteredSMBNames():
                            for smbSection in csFilesystem.getClusteredSMBSectionList(name):
                                currentPath = smbSection.getOptionValue("path").strip()
                                if (len(currentPath) > 0):
                                    smbPaths.append(currentPath)
                        if ((len(nfsMP) > 0) and (len(smbPaths) > 0)):
                            # Pop the first one off the list.
                            smbMP = smbPaths.pop()
                            fsTable.append([csFilesystem.getDeviceName(), csFilesystem.getMountPoint(), "%s(CN)" %(nfsMP), "%s(CS)" %(smbMP)])
                            # IF there any left add those with some blanks.
                            for smbMP in smbPaths:
                                fsTable.append(["", "", "", "%s(CS)" %(smbMP)])
                elif ((csFilesystem.isSMBSectionMount()) and (self.__isNFSChildOfClusterStorageResource(cca, csFilesystem))):
                    # 3) nfs mount via /etc/cluster/cluster.conf and smb mount via /etc/samba/smb.conf.
                    #print "3: %s" %(csFilesystem.getMountPoint())
                    nfsMP = csFilesystem.getMountPoint()
                    smbSectionList = csFilesystem.getSMBSectionMountList()
                    if (len(smbSectionList) > 0):
                        smbMP = smbSectionList.pop().getOptionValue("path").strip()
                        fsTable.append([csFilesystem.getDeviceName(), csFilesystem.getMountPoint(), "%s(CN)" %(nfsMP), "%s(ES)" %(smbMP)])
                        for smbSection in smbSectionList:
                            smbMP = smbSection.getOptionValue("path").strip()
                            fsTable.append(["", "", "", "%s(ES)" %(smbMP)])
                elif ((csFilesystem.isEtcExportMount()) and (len(csFilesystem.getClusteredSMBNames()) > 0)):
                    # 4) nfs mount via /etc/exports and smb mount via /etc/cluster/cluster.conf
                    # print "4: %s" %(csFilesystem.getMountPoint())
                    smbSectionList = []
                    for name in csFilesystem.getClusteredSMBNames():
                        smbSectionList += csFilesystem.getClusteredSMBSectionList(name)
                    if (len(smbSectionList) > 0):
                        smbMP = smbSectionList.pop().getOptionValue("path").strip()
                        fsTable.append([csFilesystem.getDeviceName(), csFilesystem.getMountPoint(), "%s(EN)" %(nfsMP), "%s(CS)" %(smbMP)])
                        for smbSection in smbSectionList:
                            smbMP = smbSection.getOptionValue("path").strip()
                            fsTable.append(["", "", "", "%s(CS)" %(smbMP)])
            # Write the table if it is not empty.
            if (len(fsTable) > 0):
                description =  "The following GFS/GFS2 filesystem(s) are being exported by NFS and SMB(samba) which is unsupported. "
                description += "The mount point(s) that were found will be noted with these symbols below:                          "
                description += "nfs export via /etc/exports (EN)                                                                    "
                description += "nfs export via /etc/cluster/cluster.conf (CN)                                                       "
                description += "samba export via /etc/exports for samba (ES)                                                        "
                description += "samba export via /etc/cluster/cluster.conf for samba (CS)"
                urls = ["https://access.redhat.com/knowledge/solutions/39855"]
                tableOfStrings = stringUtil.toTableStringsList(fsTable, tableHeader)
                clusterNodeEvalString += StringUtil.formatBulletString(description, urls, tableOfStrings)

            # ###################################################################
            # Check for localflocks if they are exporting nfs.
            # ###################################################################
            fsTable = []
            for csFilesystem in listOfClusterStorageFilesystems:
                # If a GFS or GFS2 fs is in /etc/exports or has a child that is
                # nfsexport then localflocks required.
                if ((csFilesystem.isEtcExportMount()) or (self.__isNFSChildOfClusterStorageResource(cca, csFilesystem))):
                    csFilesystemOptions = csFilesystem.getAllMountOptions()
                    if (not csFilesystemOptions.find("localflocks") >= 0):
                        fsTable.append([csFilesystem.getDeviceName(), csFilesystem.getMountPoint()])
            # Write the table if it is not empty.
            if (len(fsTable) > 0):
                tableHeader = ["device_name", "mount_point"]
                description = "Any GFS/GFS2 filesystem that is exported with NFS should have the option \"localflocks\" set."
                description += "The following GFS/GFS2 filesystem do not have the option set."
                tableOfStrings = stringUtil.toTableStringsList(fsTable, tableHeader)
                urls = ["https://access.redhat.com/knowledge/solutions/20327", "http://docs.redhat.com/docs/en-US/Red_Hat_Enterprise_Linux/5/html-single/Configuration_Example_-_NFS_Over_GFS/index.html#locking_considerations"]
                clusterNodeEvalString += StringUtil.formatBulletString(description, urls, tableOfStrings)

            # ###################################################################
            # Check to see if the GFS/GFS2 fs has certain mount options enabled.
            # ###################################################################
            fsTable = []
            for csFilesystem in listOfClusterStorageFilesystems:
                csFilesystemOptions = csFilesystem.getAllMountOptions()
                if (not csFilesystemOptions.find("noatime") >= 0):
                    fsTable.append([csFilesystem.getDeviceName(), csFilesystem.getMountPoint()])
            if (len(fsTable) > 0):
                # Verified that noatime implies nodiratime, so nodiratime check
                # does not need to be done.
                description =  "There were GFS/GFS2 file-systems that did not have the mount option \"noatime\"(no \"nodiratime\" is implied. "
                description += "when noatime is set) enabled. Unless atime support is essential, Red Hat recommends setting the mount option "
                description += "\"noatime\" on every GFS/GFS2 mount point. This will significantly improve performance since it prevents "
                description += "reads from turning into writes because the access time attribute will not be updated."
                urls = ["https://access.redhat.com/knowledge/solutions/35662"]
                clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

            # ###################################################################
            # Make sure GFS/GFS2 filesystems dont have fsck option enable
            # ###################################################################

            for csFilesystem in listOfClusterStorageFilesystems:
                if (csFilesystem.isEtcFstabMount()):
                    if (not csFilesystem.getEtcFstabMount().getFSFsck() == "0"):
                        description =  "There were GFS/GFS2 file-systems that had the fsck option enabled in the /etc/fstab file. This option "
                        description += "should be disabled(set value to 0) or corruption will occur eventually."
                        urls = ["https://access.redhat.com/site/solutions/766393"]
                        clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

            # ###################################################################
            # Add to string with the hostname and header if needed.
            # ###################################################################
            if (len(clusterNodeEvalString) > 0):
                rString += "%s(Cluster Node ID: %s):\n%s\n\n" %(clusternode.getClusterNodeName(), clusternode.getClusterNodeID(), clusterNodeEvalString.rstrip())
        # Return the string
        if (len(rString) > 0):
            sectionHeader = "%s\nCluster Storage Configuration Known Issues\n%s" %(self.__seperator, self.__seperator)
            rString = "%s\n%s" %(sectionHeader, rString)
        return rString
