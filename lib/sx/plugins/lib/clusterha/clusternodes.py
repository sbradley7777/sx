#!/usr/bin/env python
"""
This file contains a container class for a collection of clusternode
objects.

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
from sx.tools import StringUtil
from sx.plugins.lib.clusterha.clusterhaconfanalyzer import ClusterHAConfAnalyzer
from sx.plugins.lib.clusterha.clusternode import ClusterNode
from sx.plugins.lib.clusterha.clusternode import ClusterNodeNetworkMap
from sx.plugins.lib.clusterha.clusternode import ClusterStorageFilesystem
from sx.plugins.lib.clusterha.clustercommandsparser import ClusterCommandsParser

from sx.plugins.lib.networking.networkdeviceparser import NetworkDeviceParser
from sx.plugins.lib.networking.networkdeviceparser import NetworkMap
from sx.plugins.lib.networking.networkdeviceparser import NetworkMaps
from sx.plugins.lib.general.distroreleaseparser import DistroReleaseParser
from sx.plugins.lib.general.distroreleaseparser import DistroRelease
from sx.plugins.lib.general.runlevelserviceparser import RunLevelParser
from sx.plugins.lib.general.runlevelserviceparser import ChkConfigServiceStatus
from sx.plugins.lib.kernel.modulesparser import ModulesParser

from sx.plugins.lib.storage.filesysparser import FilesysParser
from sx.plugins.lib.storage.filesysparser import FilesysMount
from sx.plugins.lib.storage.procparser import ProcParser
from sx.plugins.lib.storage.procparser import ProcFilesystems

from sx.plugins.lib.storage import StorageData
from sx.plugins.lib.storage import StorageDataGenerator

class ClusterNodes:
    def __init__(self) :
        """
        This function will init a single private variable for list of
        ClusterNode objects.
        """
        self.__clusterNodes = []
        # Map of clusternode names to their storage data.
        self.__clusternodesStorageDataMap = {}
    # #######################################################################
    # Private helper methods for functions
    # #######################################################################
    def __findHeartBeatNetworkMap(self, networkMaps, pathToClusterConf, clusterCommandsMap) :
        """
        The function returns a ClusterNodeNetworkMap based on
        NetworkMaps. It uses cluster.conf and
        soscommands/cluster/cman_tool_status to get multicast and node
        name information.

        @return: Returns a ClusterNodeNetworkMap for heartbeat network.
        @rtype: ClusterNodeNetworkMap

        @param networkMaps: A list of NetworkMap objects for the
        cluster node.
        @type networkMaps: Array
        @param pathToClusterConf: This is the path to the
        /etc/cluster/cluster.conf file.
        @type pathToClusterConf: String
        """
        # First see if the heartbeat network information is in the
        # cman_tool_status file. All the keys have to be in file or it
        # will return None when parsed.
        cmanToolStatusCommand = None
        if (clusterCommandsMap.has_key("cman_tool_status")):
            cmanToolStatusCommand = ClusterCommandsParser.parseCmanToolStatusData(clusterCommandsMap.get("cman_tool_status"))
            if (not cmanToolStatusCommand == None):
                # For now we will just get the first address returned.
                clusterNodeNameFromStatus = cmanToolStatusCommand.getNodeName()
                hbAddress = ""
                if (len(cmanToolStatusCommand.getNodeAddresses()) > 0):
                    hbAddress = cmanToolStatusCommand.getNodeAddresses()[0]
                    for networkMap in networkMaps.getListOfNetworkMaps():
                        ipAddress = networkMap.getIPv4Address()
                        if (ipAddress == hbAddress):
                            clusternodeNetworkMap = ClusterNodeNetworkMap(networkMap.getInterface(),
                                                                          networkMap.getHardwareAddress(),
                                                                          networkMap.getIPv4Address(),
                                                                          networkMap.getSubnetMask(),
                                                                          networkMap.getListOfStates(),
                                                                          networkMap.getMTU(),
                                                                          networkMap.getEtcHostsMap(),
                                                                          networkMap.getNetworkScriptMap(),
                                                                          networkMap.getModprobeConfCommands(),
                                                                          networkMap.getProcNetMap(),
                                                                          networkMap.getNetworkingCommandsMap(),
                                                                          clusterNodeNameFromStatus)
                            for slaveInterface in networkMap.getBondedSlaveInterfaces():
                                clusternodeNetworkMap.addBondedSlaveInterfaces(slaveInterface)
                            clusternodeNetworkMap.setParentAliasNetworkMap(networkMap.getParentAliasNetworkMap())
                            clusternodeNetworkMap.setVirtualBridgedNetworkMap(networkMap.getVirtualBridgedNetworkMap())
                            return clusternodeNetworkMap
        # If the information was not found in the cman_tool_status
        # then manually search for it which requires valid name in
        # /etc/hosts. This will require us to filter all the hostnames
        # on the various interface. Not sure if there is an optimal
        # approach to this.
        cca = ClusterHAConfAnalyzer(pathToClusterConf)
        nodeNames = cca.getClusterNodeNames()
        # This NetworkMap is returned if exact match is not
        # found. Kind of a best guess at which interface that the
        # clusternode will communicate over.
        possibleClusterNodeNetworkMapMatch = None

        # Search Hostnames
        for networkMap in networkMaps.getListOfNetworkMaps():
            if ((networkMap.getInterface() == "lo") or (networkMap.getIPv4Address() == "127.0.0.1")):
                continue
            # If this is heartbeat nic for cluster
            # communication set the clusterNodeName to
            # hostname that matches clusternode name
            hostnames = networkMap.getHostnames()
            for nodeName in nodeNames:
                if ((nodeName in hostnames) or (nodeName == networkMap.getIPv4Address())):
                    # Exact match found, so go ahead and return the NetworkMap
                    # since we found a hostname that matches node name or node
                    # name is the ipv4 address.
                    clusternodeNetworkMap = ClusterNodeNetworkMap(networkMap.getInterface(),
                                                                  networkMap.getHardwareAddress(),
                                                                  networkMap.getIPv4Address(),
                                                                  networkMap.getSubnetMask(),
                                                                  networkMap.getListOfStates(),
                                                                  networkMap.getMTU(),
                                                                  networkMap.getEtcHostsMap(),
                                                                  networkMap.getNetworkScriptMap(),
                                                                  networkMap.getModprobeConfCommands(),
                                                                  networkMap.getProcNetMap(),
                                                                  networkMap.getNetworkingCommandsMap(),
                                                                  nodeName)
                    for slaveInterface in networkMap.getBondedSlaveInterfaces():
                        clusternodeNetworkMap.addBondedSlaveInterfaces(slaveInterface)
                    clusternodeNetworkMap.setParentAliasNetworkMap(networkMap.getParentAliasNetworkMap())
                    clusternodeNetworkMap.setVirtualBridgedNetworkMap(networkMap.getVirtualBridgedNetworkMap())
                    return clusternodeNetworkMap
                elif (nodeName.split(".")[0] in hostnames):
                    # Try and see if we can match based on subset name
                    # of string up until first peroid:
                    # 192.168.1.100 rh5node1 (/etc/hosts) == rh5node1.examplerh.com (cluster.conf)
                    possibleClusterNodeNetworkMapMatch = ClusterNodeNetworkMap(networkMap.getInterface(),
                                                                               networkMap.getHardwareAddress(),
                                                                               networkMap.getIPv4Address(),
                                                                               networkMap.getSubnetMask(),
                                                                               networkMap.getListOfStates(),
                                                                               networkMap.getMTU(),
                                                                               networkMap.getEtcHostsMap(),
                                                                               networkMap.getNetworkScriptMap(),
                                                                               networkMap.getModprobeConfCommands(),
                                                                               networkMap.getProcNetMap(),
                                                                               networkMap.getNetworkingCommandsMap(),
                                                                               nodeName)
                    for slaveInterface in networkMap.getBondedSlaveInterfaces():
                        possibleClusterNodeNetworkMapMatch.addBondedSlaveInterfaces(slaveInterface)
                    possibleClusterNodeNetworkMapMatch.setParentAliasNetworkMap(networkMap.getParentAliasNetworkMap())
                    possibleClusterNodeNetworkMapMatch.setVirtualBridgedNetworkMap(networkMap.getVirtualBridgedNetworkMap())
        # If the heartbeat network is not found then return
        # possibleClusterNodeNetworkMapMatch. Which will be None or
        # best guess at match.

        # Should I print warning if not EXACT MATCH?
        return possibleClusterNodeNetworkMapMatch

    def __findFSMatch(self, listOfFSPaths, pathToDir):
        """
        This function returns a path to a filesystem that is in a list of paths
        to filesystems. It returns the path only when it is the closes match to
        the pathToDir. Usefully for finding the correct filesystem for
        /etc/exports and /etc/samba/smb.conf mount points. Returns empty string
        if no match is found.
        """
        pathToDir = pathToDir.rstrip()
        while ((not pathToDir == "/") and
               (len(pathToDir) > 0)):
            if (pathToDir in listOfFSPaths):
                return pathToDir
            else:
                pathToDirSplit = os.path.split(pathToDir)
                if (len(pathToDirSplit) >= 1):
                    pathToDir = pathToDirSplit[0]
        return ""

    def __getClusterStorageFilesystemList(self, filesysMountsList, etcFstabList, pathToClusterConf,
                                          etcExportsList, etcSambaSectionsList,
                                          etcClusterSambaSectionsListMap):

        # Create a Map to make lookup faster for duplicates Key will be
        # "Mountpoint" and value will be a clusterstorage object.
        csFSMap = {}
        for fs in filesysMountsList:
            if ((fs.getFSType().lower() == "gfs") or
                (fs.getFSType().lower() == "gfs2")):
                key = fs.getMountPoint()
                if (not csFSMap.has_key(key)):
                    csFSMap[key] = ClusterStorageFilesystem(fs.getDeviceName(),
                                                            fs.getMountPoint(),
                                                            fs.getFSType(),
                                                            fs.getMountOptions())
                csFilesystem = csFSMap.get(key)
                csFilesystem.setFilesysMount(fs)

        for fs in etcFstabList:
            if ((fs.getFSType().lower() == "gfs") or
                (fs.getFSType().lower() == "gfs2")):
                key = fs.getMountPoint()
                if (not csFSMap.has_key(key)):
                    csFSMap[key] = ClusterStorageFilesystem(fs.getDeviceName(),
                                                            fs.getMountPoint(),
                                                            fs.getFSType(),
                                                            fs.getMountOptions())
                csFilesystem = csFSMap.get(key)
                csFilesystem.setEtcFstabMount(fs)

        if (not pathToClusterConf == None):
            cca = ClusterHAConfAnalyzer(pathToClusterConf)
            for fs in cca.getClusterFilesystemResourcesList():
                key = fs.getMountPoint()
                if (not csFSMap.has_key(key)):
                    csFSMap[key] = ClusterStorageFilesystem(fs.getDeviceName(),
                                                            fs.getMountPoint(),
                                                            fs.getFSType(),
                                                            fs.getMountOptions())
                csFilesystem = csFSMap.get(key)
                csFilesystem.setClusterConfMount(fs)

        # Search nfs/smb configuration files for GFS/GFS2 file-systems
        for etcExport in etcExportsList:
            pathToDir = etcExport.getMountPoint()
            pathToFS = self.__findFSMatch(csFSMap.keys(), pathToDir)
            if ((len(pathToFS) > 0) and (csFSMap.has_key(pathToFS))):
                fs = csFSMap.get(pathToFS)
                # There can be only 1 fs export line. So we will use the first
                # one we get.
                fs.setEtcExportMount(etcExport)

        for smbSection in etcSambaSectionsList:
            pathToDir = smbSection.getOptionValue("path")
            pathToFS = self.__findFSMatch(csFSMap.keys(), pathToDir)
            if ((len(pathToFS) > 0) and (csFSMap.has_key(pathToFS))):
                fs = csFSMap.get(pathToFS)
                fs.addSMBSectionMount(smbSection)

        # Iterate over the map to see if any GFS/GFS2 fs are present.
        for key in etcClusterSambaSectionsListMap.keys():
            clusterSMBSectionsList = etcClusterSambaSectionsListMap.get(key)
            for smbSection in clusterSMBSectionsList:
                pathToDir = smbSection.getOptionValue("path")
                #print pathToDir
                pathToFS = self.__findFSMatch(csFSMap.keys(), pathToDir)
                if ((len(pathToFS) > 0) and (csFSMap.has_key(pathToFS))):
                    fs = csFSMap.get(pathToFS)
                    fs.addClusteredSMBSection(key, smbSection)
        # Return all the ClusterStorageFilesystem objects
        return csFSMap.values()

    # #######################################################################
    # Public helper methods for functions
    # #######################################################################
    def getStorageData(self, clusternodeName):
        if(self.__clusternodesStorageDataMap.has_key(clusternodeName)):
            return self.__clusternodesStorageDataMap.get(clusternodeName)
        return None

    def count(self):
        """
        Returns the number of nodes.

        @return: Returns the number of nodes that are in the array.
        @rtype: Int
        """
        return len(self.__clusterNodes)

    def getClusterNodes(self) :
        """
        Returns an array of ClusterNode objects sorted by cluster
        nodes node_id value. They are kept in sorted order as they
        are added.

        @return: Returns an array of ClusterNode objects sorted by
        cluster nodes node_id value.
        @rtype: Array
        """
        return self.__clusterNodes

    def getClusterNodeNames(self) :
        """
        Returns an array of cluster node names. If name is not found
        then the following is used for the name:
        "%s-unknown_node_name" %(node.getHostname().

        @return: Returns a list of cluster node names.
        @rtype: Array
        """
        nodeNameList = []
        nodes = self.getClusterNodes()
        for node in nodes:
            nodeName = "%s-unknown_node_name" %(node.getHostname())
            hNetworkMap = node.getHeartbeatNetworkMap()
            if (not hNetworkMap == None):
                nodeName = hNetworkMap.getClusterNodeName()
            nodeNameList.append(nodeName)
        return nodeNameList

    def getBaseClusterNode(self) :
        """
        Returns that will be used for any base
        comparison. None will be returned if there is not one.

        @return: Returns that will be used for any base
        comparison. None will be returned if there is not one.
        @rtype: ClusterNode
        """
        if (len(self.__clusterNodes) > 0):
            return self.__clusterNodes[0]
        return None

    def getPathToClusterConfFiles(self) :
        """
        Returns an array of all cluster.conf paths.

        @return: Returns an array of all cluster.conf paths.
        @rtype: String
        """
        pathToClusterConfFilesList = []
        for clusterNode in self.getClusterNodes():
            pathToFile = clusterNode.getPathToClusterConf()
            if (len(pathToFile) > 0) :
                pathToClusterConfFilesList.append(pathToFile)
        return pathToClusterConfFilesList

    def listClusterNodesMissingReports(self):
        """
        Returns a list of clusternodes that did not have a report
        extracted.

        @return: Returns a list of clusternodes that did not have a
        report extracted.
        @rtype: Array
        """
        # Nodes that are in cluster.conf, so should have report of all these
        baseClusterNode = self.getBaseClusterNode()
        if (baseClusterNode == None):
            # Should never occur since node count should be checked first.
            return []
        ccaList = ClusterHAConfAnalyzer(baseClusterNode.getPathToClusterConf()).getClusterNodeNames()
        # Nodes that are in this collection that actual did have correct report
        cncList = self.getClusterNodeNames()
        return list(set(ccaList) - set(cncList))

    def add(self, report) :
        """
        This function will add only valid reports from clusternodes to
        this object.

        @param report: A SReport object that will be added to list of
        clusternodes if it is valid clusternode.
        @type report: SReport
        """
        # Verify that cluster.conf exists and plugin will work
        # with the distro release
        pathToClusterConfFile = report.getPathForFile("etc/cluster/cluster.conf")
        if ((not len(pathToClusterConfFile) > 0) or (not os.path.exists(pathToClusterConfFile))) :
            message = "The cluster.conf file could not be located for this report."
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            return False
        # cca will verify that cluster.conf is valid xml
        cca = ClusterHAConfAnalyzer(pathToClusterConfFile)
        distroRelease = DistroReleaseParser.parseEtcRedHatReleaseRedhatReleaseData(report.getDataFromFile("etc/redhat-release"))
        # ###############################################################
        # If distro release is not supported or cluster.conf
        # does not validate to be true then the node will not
        # be added.
        # ###############################################################
        if (distroRelease == None) :
            message = "The disto release file was either not valid or unknown type."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif (not ((distroRelease.getDistroName() == "RHEL") and
                   ((distroRelease.getMajorVersion() == 6) or
                    (distroRelease.getMajorVersion() == 5) or
                    (distroRelease.getMajorVersion() == 4)))):
            message = "The distrobution release is not supported."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        #elif (not cca.isXMLValid()):
        #    message = "The cluster.conf file is not a valid xml file: %s" %(report.getHostname())
        #    logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        #    return False
        # ###############################################################
        # Find the clusternode name in the sosreport, if the clusternode
        # name can be found then add the node to the list of cluster nodes.
        # ###############################################################
        clusterCommandsMap = report.getDataFromDir("sos_commands/cluster")
        # Create the network maps
        ifconfigData = report.getDataFromFile("sos_commands/networking/ifconfig_-a")
        if (ifconfigData == None):
            ifconfigData = report.getDataFromFile("ifconfig")
        networkInterfaces = NetworkDeviceParser.parseIfconfigData(ifconfigData)

        # ###############################################################
        # Get more network interfaces might need to add this at some point for
        # cases where ifconfig fails. Not sure how to combine the data yet
        # ###############################################################
        #ip_addressData = report.getDataFromFile("sos_commands/networking/ip_address")
        #networkInterfacesFromIP_Address = NetworkDeviceParser.parseIPAddressData(ip_addressData)
        # ###############################################################

        etcHostsMap = NetworkDeviceParser.parseEtcHostsData(report.getDataFromFile("etc/hosts"))
        modprobeConfCommands = ModulesParser.parseEtcModprobeConf(report.getDataFromFile("etc/modprobe.conf"))
        # Appears this is not collect on rhel6, so collecting all the
        # files will not work. Need to ask sosreport why that is?
        # modprobeConfdList = report.getDataFromDir("etc/modprobe.conf.d")

        # Read in all the /etc/sysconfig/network-scripts/ifcfg* files
        # that have known interface.
        networkScriptsDataMap = {}
        for networkInterface in networkInterfaces:
            networkScriptData = report.getDataFromFile("etc/sysconfig/network-scripts/ifcfg-%s" %(networkInterface.getInterface()))
            if (networkScriptData == None):
                networkScriptData = None
            networkScriptsDataMap[networkInterface.getInterface()] = networkScriptData
        # Get all the data from proc/net including the bonding data.
        procNetMap = report.getDataFromDir("proc/net")
        bondingMap = report.getDataFromDir("proc/net/bonding")
        procNetMap = dict(procNetMap.items() + bondingMap.items())
        # Get all the data in the sos_commands/networking directory.
        networkingCommandsMap = report.getDataFromDir("sos_commands/networking")
        # Build networkmaps from all the network related information.
        networkMaps = NetworkMaps(networkInterfaces, etcHostsMap, networkScriptsDataMap, modprobeConfCommands, procNetMap, networkingCommandsMap)
        # ###############################################################
        #clusternodeName = ""
        #etcSysConfigCluster = report.getDataFromFile("etc/sysconfig/cluster")
        #i f (not etcSysConfigCluster == None):
        #    pass
        # ###############################################################

        # Using Heartbeat network to determine if this is a
        # clusternode. It will capture almost all nodes correctly
        # except when there is no entry in /etc/hosts or cman_status
        # is not captured.
        heartbeatNetworkMap = self.__findHeartBeatNetworkMap(networkMaps, pathToClusterConfFile, clusterCommandsMap)
        # Return False if the heartbeatNetworkMap is not found and do not add the node.
        if (heartbeatNetworkMap == None):
            message = "The network device used for cluster communication was not found and this report will not be added as a clusternode."
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            return False

        # ###############################################################
        # Check the services
        # ###############################################################
        chkConfigData = report.getDataFromFile("chkconfig")
        if (chkConfigData == None):
            chkConfigData = report.getDataFromFile("sos_commands/startup/chkconfig_--list")
        chkConfigList = RunLevelParser.parseChkConfigData(chkConfigData)

        # ###############################################################
        # Find any GFS1/GFS2 filesystems
        # ###############################################################
        fsTypes = []
        for procFilesystem in ProcParser.parseProcFilesystemsData(report.getDataFromFile("proc/filesystems")):
            fsTypes.append(procFilesystem.getFSType())

        mountData = report.getDataFromFile("mount")
        if (mountData == None):
            mountData = report.getDataFromFile("sos_commands/filesys/mount_-l")
        filesysMountsList = FilesysParser.parseFilesysMountData(mountData, fsTypes)
        etcFstabList = FilesysParser.parseEtcFstabData(report.getDataFromFile("etc/fstab"))
        # ###############################################################
        # Get Storage Related Configuration Files
        # ###############################################################
        etcExportsList = FilesysParser.parseEtcExportsbData(report.getDataFromFile("etc/exports"))
        etcSambaSectionsList = FilesysParser.parseEtcSambaSmbConfData(report.getDataFromFile("etc/samba/smb.conf"))
        etcClusterSambaDataMap = report.getDataFromDir("etc/cluster/samba/*")
        etcClusterSambaSectionsListMap = {}
        for key in etcClusterSambaDataMap.keys():
            sambaSectionList = FilesysParser.parseEtcSambaSmbConfData(etcClusterSambaDataMap.get(key))
            if (len(sambaSectionList) > 0):
                etcClusterSambaSectionsListMap[key] = sambaSectionList
        clusterStorageFilesystemList = self.__getClusterStorageFilesystemList(filesysMountsList, etcFstabList, pathToClusterConfFile,
                                                                              etcExportsList, etcSambaSectionsList,
                                                                              etcClusterSambaSectionsListMap)

        # ###############################################################
        # Create the node since it is valid then append to collection
        # ###############################################################
        clusterNode = ClusterNode(pathToClusterConfFile,
                                  distroRelease,
                                  report.getDate(),
                                  report.getUname(),
                                  report.getHostname(),
                                  report.getUptime(),
                                  networkMaps,
                                  heartbeatNetworkMap,
                                  chkConfigList,
                                  clusterCommandsMap,
                                  report.getInstalledRPMSData(),
                                  clusterStorageFilesystemList)
        # ###############################################################
        # Now append the fully formed object to the node and resort the
        # nodes so they are kept in node id order.
        # ###############################################################
        self.__clusterNodes.append(clusterNode)
        self.__clusterNodes.sort(key=lambda c: int(c.getClusterNodeProperties().getNodeID()))
        storageData = StorageDataGenerator().generate(report)
        if (not storageData == None):
            self.__clusternodesStorageDataMap[clusterNode.getClusterNodeName()] = storageData

        return True

    # #######################################################################
    # Public string functions for returning a string that is a summary
    # of all the clusternodes.
    # #######################################################################
    def getClusterNodesSystemSummary(self) :
        """
        Returns a string that contains information about the system
        information for each node.

        @return: A string that contains information about the system
        information for each node.
        @rtype: String
        """
        rstring  = ""
        for clusternode in self.getClusterNodes():
            if (len(rstring) > 0):
                rstring += "\n"
            unameASplit = clusternode.getUnameA().split()
            unameA = ""
            for i in range (0, len(unameASplit)):
                if (i == 5) :
                    unameA += "\n\t      "
                unameA += "%s " %(unameASplit[i])
                i = i + 1
            rstring += "Hostname:     %s\n" %(clusternode.getHostname())
            rstring += "Date:         %s\n" %(clusternode.getDate())
            rstring += "RH Release:   %s\n" %(clusternode.getDistroRelease())
            rstring += "Uptime:       %s\n" %(clusternode.getUptime())
            rstring += "Uname -a:     %s\n" %(unameA)
            rstring += "%s" %(str (clusternode))
        return rstring

    def getClusterNodesNetworkSummary(self):
        rstring = ""
        stringUtil = StringUtil()
        for clusternode in self.getClusterNodes():
            networkMaps = clusternode.getNetworkMaps()
            hbNetworkMap = clusternode.getHeartbeatNetworkMap()

            if (not len(networkMaps.getListOfNetworkMaps()) > 0):
                # Skip if there is no maps
                continue
            if (len(rstring) > 0):
                rstring += "\n"

            # Get the hb interface so we can flag interface and if
            # bonded its slave interfaces are put into a list.
            hbInterfaceBondedSlaves = []
            for slaveInterface in hbNetworkMap.getBondedSlaveInterfaces():
                hbInterfaceBondedSlaves.append(slaveInterface.getInterface())

            # Find alias if there is one and if parent alias is bond
            # then add to the list slave interfaces.
            parentAliasInterface = ""
            if (not hbNetworkMap.getParentAliasNetworkMap() == None):
                parentAliasInterface = hbNetworkMap.getParentAliasNetworkMap().getInterface()
                if (hbNetworkMap.getParentAliasNetworkMap().isBondedMasterInterface()):
                    for slaveInterface in hbNetworkMap.getParentAliasNetworkMap().getBondedSlaveInterfaces():
                        hbInterfaceBondedSlaves.append(slaveInterface.getInterface())

            # Add netork informaton to string that will be returned.
            rstring += "%s:\n" %(clusternode.getHostname())
            networkInterfaceTable = []
            for networkMap in networkMaps.getListOfNetworkMaps():
                isHBInterface = ""
                if (networkMap.getInterface().strip() == hbNetworkMap.getInterface().strip()):
                    isHBInterface = "*"
                elif ((networkMap.getInterface().strip() == parentAliasInterface) and (parentAliasInterface > 0)):
                    isHBInterface = "***"
                elif (networkMap.getInterface().strip() in hbInterfaceBondedSlaves):
                    isHBInterface = "**"
                networkInterfaceTable.append([networkMap.getInterface(), networkMap.getNetworkInterfaceModule(),
                                              networkMap.getHardwareAddress(), networkMap.getIPv4Address(), isHBInterface])
            tableHeader = ["device", "module", "hw_addr", "ipv4_addr", "hb_interface"]
            rstring += "%s\n" %(stringUtil.toTableString(networkInterfaceTable, tableHeader))
        return rstring.strip("\n")

    def getClusterNodesPackagesInstalledSummary(self) :
        """
        Returns a string that contains information about the
        cluster/cluster-storage packages installed for each node.

        @return: A string that contains information about the
        cluster/cluster-storage package installed for each node.
        @rtype: String
        """
        rstring  = ""
        stringUtil = StringUtil()
        for clusternode in self.getClusterNodes():
            if (len(rstring) > 0):
                rstring += "\n"
            rstring += "%s:" %(clusternode.getHostname())

            # Verify cluster packages
            packages = clusternode.getClusterPackagesVersion()
            keys = packages.keys()
            keys.sort()
            index = 0
            fsTable  = []
            currentTable = []
            for key in keys:
                cPackages = packages[key]
                cPackages.sort()
                for cPackage in cPackages:
                    if (index % 2 == 0):
                        if (len(currentTable) > 0):
                            fsTable.append(currentTable)
                        currentTable = []
                        currentTable.append("%s      " %(cPackage))
                    else:
                        currentTable.append(cPackage)
                    index += 1
            if (len(currentTable) > 0):
                startIndex = len(currentTable)
                for i in range(len(currentTable), 2):
                    currentTable.append(" ")
                fsTable.append(currentTable)
            if (len(fsTable) > 0):
                packageTableString = stringUtil.toTableString(fsTable)
                rstring += ("\n%s\n") %(packageTableString)
            else:
                rstring += "\nThere was no High Availability Packages Found.\n"

            # Verify cluster-storage package
            packages = clusternode.getClusterModulePackagesVersion()
            keys = packages.keys()
            keys.sort()
            index = 0
            fsTable  = []
            currentTable = []
            for key in keys:
                cPackages = packages[key]
                cPackages.sort()
                for cPackage in cPackages:
                    if (index % 2 == 0):
                        if (len(currentTable) > 0):
                            fsTable.append(currentTable)
                        currentTable = []
                        currentTable.append("%s      " %(cPackage))
                    else:
                        currentTable.append(cPackage)
                    index += 1
            if (len(currentTable) > 0):
                startIndex = len(currentTable)
                for i in range(len(currentTable), 2):
                    currentTable.append(" ")
                fsTable.append(currentTable)
            if (len(fsTable) > 0):
                packageTableString = stringUtil.toTableString(fsTable)
                rstring += ("\n%s\n") %(packageTableString)
            else:
                rstring += "\nThere was no Resilient Storage Packages Found.\n"
        # Remove an extra newline
        rstring = rstring.rstrip("\n")
        return rstring

    # #######################################################################
    # Helper functions
    # #######################################################################
    def getPathToQuorumDisk(self):
        baseClusterNode = self.getBaseClusterNode()
        if (baseClusterNode == None):
            # Should never occur since node count should be checked first.
            return ""
        cca = ClusterHAConfAnalyzer(baseClusterNode.getPathToClusterConf())
        quorumd = cca.getQuorumd()
        if (not quorumd == None):
            # Check to see if the qdisk is an lvm device.
            pathToQuroumDisk = quorumd.getDevice()
            quorumDiskLabel = quorumd.getLabel()
            for clusternode in self.getClusterNodes():
                # Find out qdisk device if there is one
                clustatCommand = ClusterCommandsParser.parseClustatData(clusternode.getClusterCommandData("clustat"))
                pathToQuroumDisk = clustatCommand.findQuorumDisk()
                if ((pathToQuroumDisk) > 0):
                    return pathToQuroumDisk
        return ""

    def isClusterNodeNamesInHostsFile(self, clusternodeNames, networkMaps) :
        """
        This function returns True if all the node names that are in
        cluster.conf are in /etc/hosts.

        @return: Returns True if all the node names are in /etc/hosts.
        @rtype: Boolean

        @param clusternodeNames: The node names in the cluster.conf.
        @type clusternodeNames: Array
        @param networkMaps: A list of NetworkMaps for a clusternode.
        @type networkMaps: Array
        """
        # Iterate over ever nodename, we only need to search one
        # networkMap since all contain same mapping of /etc/hosts. If
        # 1 nodename is not found in /etc/hosts map  then
        # return False.
        if (len(networkMaps) > 0):
            nmap = networkMaps[0]
            for nodename in clusternodeNames:
                if(not nmap.hasHostnameMapped(nodename)):
                    return False
            return True
        return False

    def doesGFS2ModuleNeedRemoval(self, unameAData, packages):
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

        @param unameAData: A string containing uname data.
        @type unameAData: String
        @param packages: A list of packages.
        @type packages: Array
        """
        isGFS2moduleInstalled = False
        for package in packages:
            if (package.startswith("kmod-gfs2")) :
                isGFS2moduleInstalled = True
                break;
        unameSplit = unameAData.split()
        kernelVersionMinor = 0
        if (len(unameSplit) >= 2):
            kernelVersionMinor = unameSplit[2].split("-")[1].split(".")[0]

        return ((kernelVersionMinor > 128) and (isGFS2moduleInstalled))
