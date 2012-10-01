#!/usr/bin/env python
"""
This classes are for cluster nodes in the sosreport/sysreport. They
represnet configs files paths and other items that are needed for all
cluster tools.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.11
@copyright :  GPLv2
"""
import re
import os.path
import logging

import sx
from sx.logwriter import LogWriter
from sx.plugins.lib.clusterha.clusterhaconfanalyzer import ClusterHAConfAnalyzer
from sx.plugins.lib.clusterha.clusterhaconfanalyzer import ClusterNodeProperties
from sx.plugins.lib.networking.networkdeviceparser import NetworkMap
from sx.plugins.lib.rpm.rpmparser import RPMUtils
from sx.plugins.lib.storage.filesysparser import FilesysMount
from sx.plugins.lib.clusterha.clusterhaconfanalyzer import ClusterConfMount

class ClusterStorageFilesystem(FilesysMount):
    def __init__(self, deviceName, mountPoint, fsType, mountOptions):
        # /etc/fstab does not have attributes section so we just set to empty string.
        FilesysMount.__init__(self, deviceName, mountPoint, fsType, "", mountOptions)

        # These values will be set False and only change to True if know to be True.
        self.__filesysMount = None
        self.__clusterConfMount = None
        self.__etcFstabMount = None
        # There can only be 1 for /etc/exports
        self.__etcExportMount = None
        # This has to be a list because we are not just looking for exact path,
        # but looking for any path that starts with this mountpoint. Multiple
        # entries valid with /etc/samba/smb.conf.
        self.__smbSectionList = []

        # This is a map for each cluster.conf samba resource's smb.conf. The key
        # is the name of samba resource and value is the list of smb.conf
        # sections.
        self.__smbClusteredSectionsMap = {}

    def __eq__(self, fs):
        return  ((fs.getDeviceName() == self.getDeviceName()) and (fs.getMountPoint() == self.getMountPoint()))

    def equal(self, fs):
        return  self.__eq__(fs)

    def isFilesysMount(self):
        return (not self.__filesysMount == None)

    def isClusterConfMount(self):
        return (not self.__clusterConfMount == None)

    def isEtcFstabMount(self):
        return (not self.__etcFstabMount == None)

    def isEtcExportMount(self):
        return (not self.__etcExportMount == None)

    def isSMBSectionMount(self):
        return (len(self.__smbSectionList) > 0)

    def getFilesysMount(self):
        return self.__filesysMount

    def getClusterConfMount(self):
        return self.__clusterConfMount

    def getEtcFstabMount(self):
        return self.__etcFstabMount

    def getEtcExportMount(self):
        return self.__etcExportMount

    def getSMBSectionMountList(self):
        return self.__smbSectionList

    def getClusteredSMBNames(self):
        return self.__smbClusteredSectionsMap.keys()

    def getClusteredSMBSectionList(self, name):
        if (self.__smbClusteredSectionsMap.has_key(name)):
            return self.__smbClusteredSectionsMap.get(name)
        return []

    def getAllMountOptions(self):
        mountOptions = self.getMountOptions()
        if (not self.__filesysMount == None):
            mountOptions += self.__filesysMount.getMountOptions()
        if (not self.__etcFstabMount == None):
            mountOptions += self.__etcFstabMount.getMountOptions()
        if (not self.__clusterConfMount == None):
            mountOptions += self.__clusterConfMount.getMountOptions()
        return mountOptions

    def setFilesysMount(self, filesysMount):
        self.__filesysMount = filesysMount

    def setClusterConfMount(self, clusterConfMount):
        self.__clusterConfMount = clusterConfMount

    def setEtcFstabMount(self, etcFstabMount):
        self.__etcFstabMount = etcFstabMount

    def setEtcExportMount(self, etcExportMount):
        self.__etcExportMount = etcExportMount

    def addSMBSectionMount(self, smbSection):
        self.__smbSectionList.append(smbSection)

    def addClusteredSMBSection(self, name, smbSection):
        # Overwrite existing list if it is already in map.
        if (self.__smbClusteredSectionsMap.has_key(name)):
            self.__smbSectionList = self.__smbClusteredSectionsMap.get(name)
        else:
            self.__smbClusteredSectionsMap[name]  = [smbSection]

class ClusterNodeNetworkMap(NetworkMap):
    """
    Container for network information for network information.
    """
    def __init__(self, interface, hwAddr, ipv4Addr, subnetMask, listOfStates, mtu,
                 etcHostsMap, networkScriptMap, modprobeConfCommands, procNetMap,
                 networkingCommandsMap, clusterNodeName):
        NetworkMap.__init__(self, interface, hwAddr, ipv4Addr, subnetMask, listOfStates, mtu,
                            etcHostsMap, networkScriptMap, modprobeConfCommands, procNetMap,
                            networkingCommandsMap)
        self.__clusterNodeName = clusterNodeName

    def getClusterNodeName(self) :
        """
        If empty string is returned hen no clusternode name is associated with
        this interface/ip address. However, if not empty string then
        this is the NetworkMap that clusternode uses for
        communication.

        @return: If empty string is returned hen no clusternode name
        is associated with this interface/ip address. However, if not
        empty string then this is the NetworkMap that clusternode uses
        for communication.
        @rtype: String
        """
        return self.__clusterNodeName

# ###############################################################################
# ClusterNode
# ###############################################################################
class ClusterNode:
    """
    This classes are for cluster nodes in the
    sosreport/sysreport. They represnet configs files paths and other
    items that are needed for all cluster tools.
    """

    RHEL4_PACKAGE_LIST = ["ccs", "cman", "fence", "magma", "magma-plugins", "rgmanager",
                          "dlm", "GFS", "gfs-utils", "gfs2-utils", "lvm2-cluster",
                          "system-config-cluster", "ricci", "modcluster", "gulm",
                          "cluster-snmp", "cluster-cim"]

    RHEL5_PACKAGE_LIST = ["cman", "cluster-cim", "cluster-snmp", "luci", "openais",
                          "modcluster", "rgmanager", "ricci", "system-config-cluster",
                          "cmirror", "gfs-utils", "gfs2-utils", "gnbd", "lvm2-cluster",
                          "ctdb", "ctdb-devel", "isns-utils", "scsi-target-utils"]

    RHEL6_PACKAGE_LIST = ["cman", "ccs", "omping", "rgmanager", "cluster-cim", "modcluster",
                          "corosync", "fence-agents", "clusterlib", "fence-virt",
                          "openais", "openaislib", "pexpect", "resource-agents",
                          "cluster-glue-libs-devel", "cluster-snmp", "clusterlib-devel",
                          "corosynclib-devel", "fence-virtd-checkpoint", "foghorn",
                          "libesmtp-devel", "openaislib-devel", "pacemaker", "python-tw-forms",
                          "pacemaker-libs-devel", "python-repoze-what-quickstart",
                          "luci", "ricci", "gfs2-utils", "lvm2-cluster", "cmirror",
                          "ctdb", "ctdb-devel", "dlm-pcmk", "gfs-pcmk"]

    # Packages that are modules for the kernel
    RHEL4_MODULE_LIST = ["cman-kernel", "cman-kernel-smp", "cman-kernel-largesmp", "cman-kernel-xenU", "cman-kernel-hugemem", "cman-kernel-xen",
                         "dlm-kernel", "dlm-kernel-smp", "dlm-kernel-largesmp", "dlm-kernel-xenU", "dlm-kernel-hugemem", "dlm-kernel-xen",
                         "cmirror-kernel", "cmirror-kernel-smp", "cmirror-kernel-largesmp", "cmirror-kernel-xenU", "cmirror-kernel-hugemem", "cmirror-kernel-xen",
                         "GFS-kernel", "GFS-kernel-smp", "GFS-kernel-largesmp", "GFS-kernel-xenU", "GFS-kernel-hugemem", "GFS-kernel-xen"]

    RHEL5_MODULE_LIST = ["kmod-gfs2", "kmod-gfs2-xen", "kmod-gfs", "kmod-gfs-xen"]

    RHEL6_MODULE_LIST = []


    OPENSHARED_ROOT_PACKAGE_LIST = ["comoonics-cs-py", "comoonics-pythonosfix-py", "comoonics-bootimage-listfiles-rhel",
                                    "comoonics-cdsl-py", "comoonics-cluster-py", "comoonics-cs-xml",
                                    "comoonics-ec-py", "comoonics-bootimage-listfiles-all", "comoonics-bootimage-listfiles-rhel4",
                                    "comoonics-bootimage-compat", "comoonics-fenceacksv-plugins-py", "comoonics-bootimage-initscripts",
                                    "comoonics-bootimage", "comoonics-bootimage-fenceclient-ilo", "comoonics-bootimage-extras-dm-multipath-rhel",
                                    "comoonics-bootimage-extras-dm-multipath", "comoonics-bootimage-fenceacksv", "comoonics-cmdb-py",
                                    "comoonics-cs", "comoonics-bootimage-listfiles", "comoonics-db-py",
                                    "comoonics-cs-xsl-ec", "comoonics-fenceacksv-py",]

    # The services openais and corosync are not in map because other
    # services start them.
    RHEL4_CLUSTER_SERVICES = { 1:"ccsd", 2:"cman", 3:"qdiskd", 4:"fenced", 5:"clvmd",
                               6:"gfs", 7:"rgmanager", 8:"modclusterd", 9:"ricci" }

    RHEL5_CLUSTER_SERVICES = { 0:"openais", 1:"cman", 2:"qdiskd", 3:"cmirror", 4:"clvmd", 5:"scsi_reserve",
                               6:"gfs", 7:"gfs2", 8:"rgmanager", 9:"modclusterd", 10:"ricci", 11:"luci"}

    RHEL6_CLUSTER_SERVICES = { 0:"corosync", 1:"cman", 2:"cmirror", 3:"clvmd", 4:"gfs2",
                               5:"rgmanager", 6:"modclusterd", 7:"ricci", 8:"luci"}

    def __init__(self, pathToClusterConf, distroRelease, date, uname_a, hostname,
                 uptime, networkMaps, heartbeatNetworkMap, chkConfigList,
                 clusterCommandsMap, installedRPMS, clusterStorageFilesystemList):
        """
        Requries the cluster.conf(and file has to exist) so we know
        that this node is apart of cluster. The pathToClusterConf
        should not be equal to None. The path must exist.

        If cluster.conf does not exist then this class should not be
        created.

        @param pathToClusterConf: This is the path to the
        /etc/cluster/cluster.conf file.
        @type pathToClusterConf: String
        @param distroRelease: A DistroRelease object that describes
        the type of Operating System Distrobution this cluster.conf is
        from.
        @type distroRelease: DistroRelease
        @param uname_a: The uname -a data for the node
        @type uname_a: String
        @param hostname: The hostname of the node.
        @type hostname: String
        @param date: A string that is timestamp the report was taken.
        @type date: String
        @param uptime: The uptime data for the node.
        @type uptime: String
        @param networkMaps: Array of NetworkMap objects
        @type networkMaps: Array
        @param heartbeatNetworkMap: A network map object of the heartbeat
        network for this node.
        @type heartbeatNetworkMap: ClusterNodeNetworkMap
        @param chkConfigList: List of ChkConfigServiceStatus objects.
        @type chkConfigList: Array
        @param clusterCommandsMap: Map of the cluster commands file contents.
        @type clusterCommandsMap: Dictionary
        @param installedRPMS: List of installed rpms for this node.
        @type installedRPMS: Array
        @param clusterStorageFilesystemList: Array of cluster storage filesystems
        in this report that were found.
        @type clusterStorageFilesystemList: Array
        """
        self.__pathToClusterConf = pathToClusterConf
        self.__distroRelease = distroRelease
        self.__date = date
        self.__uname_a = uname_a
        self.__hostname = hostname
        self.__uptime = uptime
        self.__networkMaps = networkMaps
        self.__heartbeatNetworkMap = heartbeatNetworkMap
        self.__chkConfigList = chkConfigList
        self.__clusterCommandsMap = clusterCommandsMap
        self.__installedRPMS = installedRPMS
        self.__clusterStorageFilesystemList = clusterStorageFilesystemList

        # Find out which rpms are installed
        self.__clusterPackageVersions = {}
        self.__clusterModulePackageVersions = {}
        if ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() == 4)):
            self.__clusterPackageVersions = RPMUtils.getPackageVersion(self.__installedRPMS, ClusterNode.RHEL4_PACKAGE_LIST)
            self.__clusterModulePackageVersions = RPMUtils.getPackageVersion(self.__installedRPMS, ClusterNode.RHEL4_MODULE_LIST)
        elif ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() == 5)):
            self.__clusterPackageVersions = RPMUtils.getPackageVersion(self.__installedRPMS, ClusterNode.RHEL5_PACKAGE_LIST)
            self.__clusterModulePackageVersions = RPMUtils.getPackageVersion(self.__installedRPMS, ClusterNode.RHEL5_MODULE_LIST)
        elif ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() == 6)):
            self.__clusterPackageVersions = RPMUtils.getPackageVersion(self.__installedRPMS, ClusterNode.RHEL6_PACKAGE_LIST)
            self.__clusterModulePackageVersions = RPMUtils.getPackageVersion(self.__installedRPMS, ClusterNode.RHEL6_MODULE_LIST)

        # this is properties of the node in the cluster.conf section
        # <clusternode>, by default it is Node and will need to be set
        # on first call to get.
        self.__clusterNodeProperties = None
        if (len(self.getClusterNodeName()) > 0):
            cca = ClusterHAConfAnalyzer(self.__pathToClusterConf)
            self.__clusterNodeProperties = cca.getClusterNodeProperties(self.getClusterNodeName())

    def __str__(self) :
        """
        Returns a string that is composed of the name and description.

        @return: Returns a string that is composed of the name and
        description.
        @rtype: String
        """
        if (not self.isClusterNode()):
            return ""
        cnp = self.getClusterNodeProperties()
        if (cnp.isEmpty()):
            return ""
        nameMessage = "Node Name:    %s\n" %(self.getClusterNodeName())
        nodeIDMessage = "Node ID :     %s\n" %(self.getClusterNodeID())
        hbNetworkMap = self.getHeartbeatNetworkMap()
        hbNetworkMessage = ""
        if (not hbNetworkMap == None) :
            if ((len(hbNetworkMap.getIPv4Address()) > 0) and (len(hbNetworkMap.getInterface()) > 0)):
                hbNetworkMessage = "HB Address:   %s\n"%(hbNetworkMap.getIPv4Address())
                hbInterfaceMessage = "HB Interface: %s\n" %(hbNetworkMap.getInterface())
                # Search the bonding interface list and if this is a bond then pretty some more information.
                bondedInterfaceList = self.getNetworkMaps().getListOfBondedNetworkMaps()
                for bondedInterface in bondedInterfaceList:
                    if (bondedInterface.getInterface().strip() == hbNetworkMap.getInterface().strip()):
                        hbInterfaceMessage = "HB Interface: %s(Mode: %s | %s)\n" %(bondedInterface.getInterface(),
                                                                                   bondedInterface.getBondedModeNumber(),
                                                                                   bondedInterface.getBondedModeName())
                hbNetworkMessage += hbInterfaceMessage

        multicastMessage = ""
        cmanMulticastAddress = cnp.getCmanMulticastAddress()
        if (len(cmanMulticastAddress) > 0):
            multicastMessage += "CMAN MC Addr: %s \n" %(cmanMulticastAddress)
        multicastAddress = cnp.getMulticastAddress()
        multicastInterface = cnp.getMulticastInterface()
        if ((len(multicastAddress) > 0) and (len(multicastInterface) > 0)):
            multicastMessage += "Node MC Addr: %s(%s) \n" %(multicastAddress, multicastInterface)

        fenceMessage = ""
        fenceDevicesList = cnp.getFenceDevicesList()
        for fd in fenceDevicesList:
            if (not len(fenceMessage) > 0) :
                fenceMessage += "Fence Dev:    %s(Level %s)\n" %(fd.getName(), fd.getMethodName())
            else:
                fenceMessage += "              %s(Level %s)\n" %(fd.getName(), fd.getMethodName())
        return  "%s%s%s%s%s" %(nameMessage, nodeIDMessage, hbNetworkMessage, multicastMessage, fenceMessage)


    # #######################################################################
    # Is methods
    # #######################################################################
    def isClusterNode(self):
        """
        Returns True if this is a clusternode.

        @return: Returns True if this is a clusternode.
        @rtype: Boolean
        """
        if (self.getClusterNodeProperties == None):
            return False
        elif (self.getHeartbeatNetworkMap() == None):
            return False
        return True

    def isOpenSharedRootClusterNode(self):
        """
        Returns True if this cluster is open shared root cluster.

        @return: Returns True if this is an opensharedroot cluster.
        @rtype: Boolean
        """
        return (len(RPMUtils.getPackageVersion(self.getInstalledRPMS(), ClusterNode.OPENSHARED_ROOT_PACKAGE_LIST)) > 0)

    def isAcpiDisabledinRunlevel(self) :
        """
        Returns True if acpi is disabled in runleve

        @return: True if acpi is disabled in runlevel.
        @rtype: Boolean
        """
        for chkConfigItem in self.getChkConfigList():
            if ((chkConfigItem.getName() == "acpid") and
                (chkConfigItem.isEnabledRunlevel3() or
                 chkConfigItem.isEnabledRunlevel4() or
                 chkConfigItem.isEnabledRunlevel5())):
                return False
        return True

    def isManualFencingEnabled(self) :
        cnp = self.getClusterNodeProperties()
        fenceDevicesDict = cnp.getFenceDevices()
        for key in fenceDevicesDict.keys():
            for fenceDevice in fenceDevicesDict.get(key):
                fenceAgent = fenceDevice.get("agent")
                if(fenceAgent == "fence_manual"):
                    return True
        return False

    # #######################################################################
    # Get methods
    # #######################################################################
    def getPathToClusterConf(self) :
        """
        Returns the path to the cluster.conf file.

        @return: Returns the path to the cluster.conf.
        file.
        @rtype: String
        """
        return self.__pathToClusterConf

    def getDistroRelease(self) :
        """
        Returns the DistroRelease Object for this node.

        @return: Returns the DistroRelease Object for this node.
        @rtype: DistroRelease
        """
        return self.__distroRelease

    def getDate(self):
        """
        Returns the date string for when the report was taken.

        @return: Returns the date string for when the report was taken.
        @rtype: String
        """
        return self.__date

    def getUnameA(self) :
        """
        Returns the data from the uname_a file.

        @return: Returns the data from the uname_a file.
        @rtype: String
        """
        return self.__uname_a

    def getHostname(self) :
        """
        Returns the hostname.

        @return: Returns the hostname.
        @rtype: String
        """
        return self.__hostname

    def getClusterNodeName(self):
        """
        Returns the cluster node name that is in cluster.conf for this
        node. Empty string returned if no node name found.

        @return:Returns the cluster node name that is in cluster.conf
        for this node.
        @rtype: String
        """
        if (not self.__heartbeatNetworkMap == None):
            return  self.__heartbeatNetworkMap.getClusterNodeName()
        return ""

    def getClusterNodeID(self):
        """
        Returns the cluster node ID.

        @return: Returns the cluster node ID.
        @rtype: String
        """
        return self.getClusterNodeProperties().getNodeID()

    def getClusterCommandData(self, key) :
        """
        Returns the data for the particular key in the map.

        @return: Returns the data for the particular key in the map.
        @rtype: Array

        @param key: This is the key to which item in map that will be
        returned.
        @type key: String
        """
        if (self.__clusterCommandsMap.has_key(key)):
            return self.__clusterCommandsMap.get(key)
        return ""

    def getClusterCommandsKeys(self) :
        """
        Returns an array of keys for cluster commmands.

        @return: Returns an array of keys.
        @rtype: Array
        """
        return self.__clusterCommandsMap.keys()

    def getClusterPackagesVersion(self) :
        """
        Returns an array of installed cluster packages.

        @return: Returns an array of installed cluster
        packages.
        @rtype: Array
        """
        return self.__clusterPackageVersions

    def getClusterModulePackagesVersion(self) :
        """
        Returns an array of installed cluster module packages.

        @return: Returns an array of installed cluster module
        packages.
        @rtype: Array
        """
        return self.__clusterModulePackageVersions

    def getChkConfigList(self) :
        """
        Returns an array of ChkConfigServiceStatus objects..

        @return: Returns an array of ChkConfigServiceStatus objects.
        @rtype: Array
        """
        return self.__chkConfigList

    def getUptime(self) :
        """
        Returns the uptime for the cluster node.

        @return: Returns the uptime for the cluster node.
        @rtype: String
        """
        return self.__uptime

    def getNetworkMaps(self) :
        """
        Returns all the generated NetworkMaps Objects for this
        clusternode.

        @return: Returns all the generated NetworkMaps Objects for
        this clusternode.
        @rtype: Array
        """
        return self.__networkMaps

    def getHeartbeatNetworkMap(self) :
        """
        Returns the NetworkMap object associated with heartbeat or
        cluster communication network. If None is returned then
        heartbeat network was not found.

        @return: Returns the NetworkMap object associated with
        heartbeat or cluster communication network.
        @rtype: NetworkMap
        """
        return self.__heartbeatNetworkMap

    def getClusterNodeProperties(self) :
        """
        Returns the clusternode properties from the cluster.conf as
        dictionary.

        @return: Returns the clusternode properties from the
        cluster.conf as dictionary.
        @rtype: Dictionary
        """
        return self.__clusterNodeProperties

    def getInstalledRPMS(self):
        """
        Returns the list of installed rpms.

        @return: Returns the list of installed rpms.
        @rtype: Array
        """
        return self.__installedRPMS

    def getClusterStorageFilesystemList(self):
        """
        Returns an array of ClusterStorageFileystems for this report.

        @return: Returns an array of ClusterStorageFilesystems for this report.
        @rtype: Dictionary
        """
        return self.__clusterStorageFilesystemList

    def getChkConfigClusterServicesStatus(self) :
        """
        Returns an array of ChkConfigServiceStatus objects.

        @return: Returns an array of ChkConfigServiceStatus
        objects
        @rtype: Array
        """
        distroMajorVersion = self.getDistroRelease().getMajorVersion()
        chkConfigClusterServiceList = []
        clusterServices = {}
        # Set Distro dependent variables
        if (distroMajorVersion  == 4):
            clusterServices = ClusterNode.RHEL4_CLUSTER_SERVICES
        elif (distroMajorVersion  == 5):
            clusterServices = ClusterNode.RHEL5_CLUSTER_SERVICES
        elif (distroMajorVersion  == 6):
            clusterServices = ClusterNode.RHEL6_CLUSTER_SERVICES
        else:
            return chkConfigClusterServiceList

        for chkConfigItem in self.getChkConfigList():
            for key in clusterServices.keys():
                if (chkConfigItem.getName() == clusterServices.get(key)):
                    # Set the order so we know the correct start order
                    # of services.
                    chkConfigItem.setStartOrderNumber(key)
                    chkConfigClusterServiceList.append(chkConfigItem)
        return chkConfigClusterServiceList

