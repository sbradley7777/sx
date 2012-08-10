#!/usr/bin/env python
"""

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.08
@copyright :  GPLv2
"""
import logging

import sx
from sx.logwriter import LogWriter
from sx.tools import ConfigurationFileParser
from sx.plugins.lib.gluster.glusterpeernode import GlusterPeerNode
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

from sx.plugins.lib.general.processparser import ProcessParser

class GlusterPeerNodes:
    def __init__(self):
        self.__glusterPeerNodes = []

    def getGlusterPeerNodes(self):
        return self.__glusterPeerNodes

    def add(self, report) :
        distroRelease = DistroReleaseParser.parseEtcRedHatReleaseRedhatReleaseData(report.getDataFromFile("etc/redhat-release"))
        # ###############################################################
        # If distro release is not supported or cluster.conf
        # does not validate to be true then the node will not
        # be added.
        # ###############################################################
        if (distroRelease == None) :
            message = "The distribution release file was either not valid or unknown type."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif (not ((distroRelease.getDistroName() == "RHEL") and
                   ((distroRelease.getMajorVersion() == 6)))):
            message = "This distribution release is not supported: %s." %(distroRelease)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        # Create the network maps
        ifconfigData = report.getDataFromFile("sos_commands/networking/ifconfig_-a")
        if (ifconfigData == None):
            ifconfigData = report.getDataFromFile("ifconfig")
        networkInterfaces = NetworkDeviceParser.parseIfconfigData(ifconfigData)

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
        # Check the services
        # ###############################################################
        chkConfigData = report.getDataFromFile("chkconfig")
        if (chkConfigData == None):
            chkConfigData = report.getDataFromFile("sos_commands/startup/chkconfig_--list")
        chkConfigList = RunLevelParser.parseChkConfigData(chkConfigData)

        # ###############################################################
        # Find Filesystems
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
        # Get Processes
        # ###############################################################
        psData = report.getDataFromFile("ps")
        if (psData == None):
            psData = report.getDataFromFile("sos_commands/process/ps_auxwww")
        psList = ProcessParser.parsePSData(psData)

        # ###############################################################
        # Grab configuration files for gpn(GlusterPeerNode)
        # ###############################################################

        # The config files directory can be located in two places, if uuid if
        # found then that will be the config dir base path.
        glusterRootDir = "var/lib/glusterd"
        glusterdInfoData = report.getDataFromFile("%s/glusterd.info" %(glusterRootDir))
        if (glusterdInfoData == None):
            glusterRootDir = "etc"
            glusterdInfoData = report.getDataFromFile("%s/glusterd.info" %(glusterRootDir))
        # If there was no glusterd.info file found then return False.
        if (not len(glusterdInfoData) > 0):
            return False

        gpnUUID = glusterdInfoData[0].split("=")[1]
        gpnPeersMap = report.getDataFromDir("%s/peers" %(glusterRootDir))
        listOfPeerNodes = []
        for key in gpnPeersMap.keys():
            configFileParser = ConfigurationFileParser(gpnPeersMap.get(key), {}, enforceEmptyValues=False)
            gpnPeerMap = configFileParser.getMap()
            listOfPeerNodes.append(gpnPeerMap)
        # ###############################################################
        # Create the node since it is valid then append to collection
        # ###############################################################
        glusterPeerNode = GlusterPeerNode(distroRelease,
                                          report.getDate(),
                                          report.getUname(),
                                          report.getHostname(),
                                          report.getUptime(),
                                          networkMaps,
                                          chkConfigList,
                                          report.getInstalledRPMSData(),
                                          filesysMountsList,
                                          etcFstabList,
                                          psList,
                                          gpnUUID,
                                          listOfPeerNodes)
        # ###############################################################
        # Now append the fully formed object to the node and resort the
        # nodes so they are kept in node id order.
        # ###############################################################
        self.__glusterPeerNodes.append(glusterPeerNode)
        self.__glusterPeerNodes.sort(key=lambda g: str(g.getHostname()))
        return True
