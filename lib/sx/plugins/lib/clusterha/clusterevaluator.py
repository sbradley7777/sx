#!/usr/bin/env python
"""
This class will evalatuate a cluster and create a report that will
link in known issues with links to resolution.

This plugin is documented here:
- https://fedorahosted.org/sx/wiki/SX_clusterplugin

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.11
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
from sx.plugins.lib.clusterha.clusternode import ClusterNode
from sx.plugins.lib.clusterha.clusternode import ClusterNodeNetworkMap
from sx.plugins.lib.clusterha.clusternode import ClusterStorageFilesystem

# For finding quorum disk.
from sx.plugins.lib.storage.devicemapperparser import DeviceMapperParser
from sx.plugins.lib.storage.devicemapperparser import DMSetupInfoC
from sx.plugins.lib.clusterha.clustercommandsparser import ClusterCommandsParser

class ClusterEvaluator():
    def __init__(self, cnc):
        self.__cnc = cnc
        # Seperator between sections:
        #self.__seperator = "------------------------------------------------------------------"
        self.__seperator = "-------------------------------------------------------------------------------------------------"
    def getClusterNodes(self):
        return self.__cnc

    # #######################################################################
    # Evaluate Private Function
    # #######################################################################
    def __evaluateClusterGlobalConfiguration(self, cca):
        rString = ""
        clusterNameCharSize = len(list(cca.getClusterName()))
        if (clusterNameCharSize > 16):
            description = "The name of the cluster cannot be more than 16 characters in size. The cluster's name "
            description += "\%s\" is %d characters long." %(cca.getClusterName(), clusterNameCharSize)
            urls = ["https://access.redhat.com/knowledge/solutions/32111"]
            rString += StringUtil.formatBulletString(description, urls)

        if (cca.isCleanStartEnabled()):
            description =  "The clean_start option in the /etc/cluster/cluster.conf was enabled and is not supported "
            description += "for production clusters. The option is for testing and debugging only."
            urls = ["https://access.redhat.com/knowledge/solutions/23238"]
            rString += StringUtil.formatBulletString(description, urls)

        # Disable the post_join_delay check for now
        if (not int(cca.getPostJoinDelay()) > 3):
            description =  "The post_join_delay option was 3 (which is the default value) in the /etc/cluster/cluster.conf file. "
            description += "In some cluster environments a value of 3 for post_join_delay is to too low."
            urls = ["https://access.redhat.com/knowledge/solutions/21742", "https://access.redhat.com/knowledge/solutions/3641"]
            rString += StringUtil.formatBulletString(description, urls)
        if (not (int(cca.getPostFailDelay()) == 0)):
            description =  "The post_fail_delay option in the /etc/cluster/cluster.conf file was not zero(default). "
            description += "Most clusters should not modify the default value of zero."
            urls = ["https://access.redhat.com/knowledge/solutions/21742", "https://access.redhat.com/knowledge/solutions/5929"]
            rString += StringUtil.formatBulletString(description, urls)
        # Check for single node configurations and clusters that are larger than 16 nodes.
        clusterNodeCount = len(cca.getClusterNodeNames())
        if (clusterNodeCount == 1):
            description =  "This is a single node cluster and does not meet the minimum number of cluster nodes required for "
            description += "high-availibility. Red Hat recommends that clusters always have a minimum of two nodes to protect "
            description += "against hardware failures."
            urls = ["https://access.redhat.com/knowledge/articles/5892"]
            rString += StringUtil.formatBulletString(description, urls)
        elif (clusterNodeCount > 16):
            descriptioin = "The maximum number of cluster nodes supported by the High Availability Add-On is 16, and the same "
            description += "is true for the Resilient Storage Add-On that includes GFS2 and CLVM. "
            description += "This cluster currently has %d number of cluster nodes which exceeds the supported 16 number of cluster nodes." %(clusterNodeCount)
            urls = ["https://access.redhat.com/knowledge/articles/40051"]
            rString += StringUtil.formatBulletString(description, urls)
        # Check if two_node is 1 and if expected_votes is 1
        if ((cca.isCmanTwoNodeEnabled()) and ((not cca.getCmanExpectedVotes() == "1") or (not len(cca.getCmanExpectedVotes()) > 0))):
            description = "If the \"cman/@two_node\" option is set to 1 then the option \"cman/@expected_votes\" should be set to 1."
            urls = ["https://access.redhat.com/knowledge/solutions/30398"]
            rString += StringUtil.formatBulletString(description, urls)
        # Compare the cluster.conf files
        if ((not cca.isClusterConfFilesIdentical(self.__cnc.getPathToClusterConfFiles())) and (len(self.__cnc.getPathToClusterConfFiles()) > 1)):
            description  = "The /etc/cluster/cluster.conf files were not identical on all the cluster node's cluster.conf files that were analyzed."
            if (not  len(cca.getClusterNodeNames()) == len(self.__cnc.getClusterNodes())):
                # More than 2 nodes compared and all cluster nodes cluster.confs
                # were compared, but not all nodes in the cluster's cluster.conf
                # was compared.
                description += "There was only %d cluster.conf files compared for the %d node cluster. " %(len(self.__cnc.getPathToClusterConfFiles()),
                                                                                                          len(cca.getClusterNodeNames()))
            urls = ["https://access.redhat.com/knowledge/solutions/19808"]
            rString += StringUtil.formatBulletString(description, urls)
        # ###################################################################
        # Warning messages to console about comparing cluster.confs.
        # ###################################################################
        if ((not len(self.__cnc.getPathToClusterConfFiles()) > 1) and (clusterNodeCount > 1)):
            # Need more than 1 node to compare cluster.confs
            message =  "There was only 1 cluster.conf file found for a %d node cluster. " %(len(cca.getClusterNodeNames()))
            message += "The comparing of cluster.conf files will be skipped since there is not enough files to compare."
            message += "Please verify that a cluster.conf files exists for all cluster nodes and that they are identical."
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)
        elif (not  len(cca.getClusterNodeNames()) == len(self.__cnc.getClusterNodes())):
            message = "There was only %d cluster.conf compared for the %d node cluster." %(len(self.__cnc.getPathToClusterConfFiles()),
                                                                                           len(cca.getClusterNodeNames()))
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)
        return rString

    def __evaluateQuorumdConfiguration(self, cca, distroRelease):
        rString = ""
        quorumd = cca.getQuorumd()
        if (quorumd == None):
            return rString
        # ###################################################################
        # Configuration options that are unsupported in production clusters.
        # ###################################################################
        if (len(quorumd.getStatusFile()) > 0):
            description =  "The \"status_file\" option for quorumd should be removed prior to production "
            description += "cause it is know to cause qdiskd to hang unnecessarily."
            urls = ["https://access.redhat.com/knowledge/solutions/54460"]
            rString += StringUtil.formatBulletString(description, urls)
        if (not quorumd.getUseUptime() == "1"):
            description =  "The changing of the internal timers used by qdisk by setting "
            description += "\"use_uptime\" to a value that is not 1, is not supported."
            urls = []
            rString += StringUtil.formatBulletString(description, urls)

        qPriority = int(quorumd.getPriority())
        if (qPriority > quorumd.getPriorityMax(quorumd.getScheduler())):
            description  = "The quorumd \"priority\" %s is set too high and can preempt kernel threads that are being managed by the  " %(qPriority)
            description += "scheduler %s. The maximum value for the scheduler is %s." %(quorumd.getScheduler(), quorumd.getPriorityMax(quorumd.getScheduler()))
            urls = []
            rString += StringUtil.formatBulletString(description, urls)
        elif (qPriority < quorumd.getPriorityMin(quorumd.getScheduler())):
            description  = "The quorumd \"priority\" %s is not equal or greater than the minimum priority for the " %(qPriority)
            description += "scheduler %s. The minimum value for the scheduler is %s." %(quorumd.getScheduler(), quorumd.getPriorityMin(quorumd.getScheduler()))
            urls = []
            rString += StringUtil.formatBulletString(description, urls)

        """
        Here is the unsupported conditions for master_wins. On RHEL 6
        master_wins is automagic, so they really should not be changing these
        options.

        If master_wins is 1 and no heuristics = PASS
        If master_wins is 1 and 1 or more heuristics = FAIL
        If 2 node cluster and master_wins is 0 and no heuristics = FAIL
        urls = ["https://access.redhat.com/knowledge/solutions/24037"]
        """
        heurisitcCount = len(quorumd.getHeuristics())
        masterWins = quorumd.getMasterWins()
        if ((len(masterWins) > 0) and (distroRelease.getMajorVersion() == "5")):
            # In RHEL 6 it is autocalculated, but in RHEL 5 it will default to 0
            # if it is not set.
            masterWins = "0"
        # If master_wins is 1 and 1 or more heuristics = FAIL
        if ((masterWins == "1") and (heurisitcCount > 0)):
            description = "There cannot be any heuristics set in the cluster.conf if \"master_wins\" is enabled."
            urls = ["https://access.redhat.com/knowledge/solutions/24037"]
            rString += StringUtil.formatBulletString(description, urls)
        # If master_wins is 1 and 1 or more heuristics = FAIL
        if ((masterWins == "0") and (heurisitcCount == 0) and (len(cca.getClusterNodeNames()) >= 2)):
            description =  "If a quorumd tag is in the cluster.conf and there is no heuristic defined then "
            description += "enabled \"master_wins\" or define some heuristics for quorumd."
            urls = ["https://access.redhat.com/knowledge/solutions/24037"]
            rString += StringUtil.formatBulletString(description, urls)

        # cman/@two_node: Must be set to 0 when qiskd is in use with one EXCEPTION and
        # that is if quorumd/@votes is set to 0, two_node is allowed.
        if ((int(quorumd.getVotes()) > 0) and (cca.isCmanTwoNodeEnabled())):
            description =  "The cluster has the option \"cman/@two_nodes\" enabled and also"
            description += "have set \"quorumd/@votes\" greater than 0 which is unsupported."
            urls = []
            rString += StringUtil.formatBulletString(description, urls)

        # ###################################################################
        # Configurations that should print a warning message, but are still
        # supported in production.
        # ###################################################################
        if ((len(quorumd.getLabel()) > 0) and (len(quorumd.getDevice()) > 0)):
            description =  "The quorumd option should not have a \"quorumd/@device\" and "
            description += "\"quorumd/@label\" configured. The label option will override the device option."
            urls = []
            rString += StringUtil.formatBulletString(description, urls)
        if (quorumd.getReboot() == "0"):
            description =  "If the quorumd option reboot is set to 0 then this option only prevents "
            description += "rebooting on loss of score. The option does not change whether qdiskd "
            description += "reboots the host as a result of hanging for too long and getting "
            description += "evicted by other nodes in the cluster."
            urls = []
            rString += StringUtil.formatBulletString(description, urls)
        if (quorumd.getAllowKill() == "0"):
            description =  "If the quorumd option allow_kill is set to 0 (off), qdiskd will not instruct cman to kill "
            description += "the cluster nodes that openais or corosync think are dead cluster nodes. Cluster nodes "
            description += "are still evicted via the qdiskd which will cause a reboot to occur. By default this option "
            description += "is set to 1."
            urls = []
            rString += StringUtil.formatBulletString(description, urls)

        # ###################################################################
        # Heuristics Evaluations
        # ###################################################################
        stringUtil = StringUtil()
        remPing = re.compile("^(?P<command>ping|/bin/ping) .*")
        remPingDT = re.compile("^(?P<command>ping|/bin/ping) .*-(?P<deadlineTimeout>w\d?\d?\d|w \d?\d?\d).*")

        # The list of heuristics that are using the "ping" command for the
        # program that does not have -w option enabled or the -w option is <= 0.
        heuristicsWithPingNoDTList = []
        for heuristic in quorumd.getHeuristics():
            hProgram = heuristic.getProgram()
            moPing = remPing.search(hProgram)
            if (moPing):
                # Found Ping
                moPingDT = remPingDT.search(hProgram)
                if (moPingDT):
                    deadlineTimeout = moPingDT.group("deadlineTimeout").replace("w", "").strip()
                    if (not int(deadlineTimeout) > 0):
                        heuristicsWithPingNoDTList.append(heuristic)

                else:
                    heuristicsWithPingNoDTList.append(heuristic)

        if (len(heuristicsWithPingNoDTList) > 0):
            description =  "Any heuristic that is using the ping command must enabled the "
            description += "-w (deadline timeout) with a value equal to or larger than one. "
            description += "The following heuristic program values were invalid: \n"
            urls = ["https://access.redhat.com/knowledge/solutions/64633"]

            tableHeader = ["program", "interval", "min_score", "tko"]
            fsTable = []
            for heuristic in heuristicsWithPingNoDTList:
                fsTable.append([heuristic.getProgram(), heuristic.getInterval(),
                               heuristic.getScore(), heuristic.getTKO()])

            tableOfStrings = stringUtil.toTableStringsList(fsTable, tableHeader)
            rString += StringUtil.formatBulletString(description, urls, tableOfStrings)
        return rString.rstrip()

    def __evaluateClusterNodeHeartbeatNetwork(self, hbNetworkMap):
        rString = ""
        # ###################################################################
        # Check if bonding is being used on the heartbeat network
        # ###################################################################
        if ((hbNetworkMap.isBondedMasterInterface()) and (not hbNetworkMap.getBondedModeNumber() == "1")):
            # The currently only supported mode for RHEL
            # clustering heartbeat network is mode
            # 1(Active-backup)
            description =  "The only supported bonding mode on the heartbeat network is mode 1(active-backup)."
            description += "The heartbeat network(%s) is currently using bonding mode %s(%s).\n" %(hbNetworkMap.getInterface(),
                                                                                                   hbNetworkMap.getBondedModeNumber(),
                                                                                                   hbNetworkMap.getBondedModeName())
            urls = ["https://access.redhat.com/knowledge/solutions/27604"]
            rString += StringUtil.formatBulletString(description, urls)
        # ###################################################################
        # Check if heartbeat network interface is netxen or bnx2 network module
        # ###################################################################
        if (hbNetworkMap.getNetworkInterfaceModule().strip() == "bnx2"):
            description =  "The network interface %s that the cluster communication is using is on a network device that " %(hbNetworkMap.getInterface())
            description += "is using the module: %s. This module has had known issues with network communication." %(hbNetworkMap.getNetworkInterfaceModule())
            urls = []
            rString += StringUtil.formatBulletString(description, urls)
        elif ((hbNetworkMap.getNetworkInterfaceModule().strip() == "netxen") or
              (hbNetworkMap.getNetworkInterfaceModule().strip() == "nx_nic") or
              (hbNetworkMap.getNetworkInterfaceModule().strip() == "netxen_nic")):
            description =  "The network interface %s that the cluster is using for communication is using the module: %s. " %(hbNetworkMap.getInterface(),
                                                                                                                                  hbNetworkMap.getNetworkInterfaceModule())
            description += "This module has had known issues with network communication."
            urls = ["https://access.redhat.com/knowledge/solutions/44475",
                    "https://access.redhat.com/knowledge/solutions/35299",
                    "https://access.redhat.com/knowledge/solutions/46663",
                    "https://access.redhat.com/knowledge/solutions/35299"]
            rString += StringUtil.formatBulletString(description, urls)
        elif (hbNetworkMap.isBondedMasterInterface()):
            # Loop over the bonded interfaces
            for bondedSlaveInterface in hbNetworkMap.getBondedSlaveInterfaces():
                description =  "The network interface that the cluster is using for communication is using the module: %s." %(bondedSlaveInterface.getNetworkInterfaceModule())
                description += "This network interface is a slave interface(%s) that is part of the bond: %s." %(bondedSlaveInterface.getInterface(),
                                                                                                                 hbNetworkMap.getInterface())
                description += "This module has had known issues with network communication."

                if (bondedSlaveInterface.getNetworkInterfaceModule().strip() == "bnx2"):
                    urls = []
                    rString += StringUtil.formatBulletString(description, urls)
                elif ((bondedSlaveInterface.getNetworkInterfaceModule().strip() == "netxen") or
                      (bondedSlaveInterface.getNetworkInterfaceModule().strip() == "nx_nic") or
                      (bondedSlaveInterface.getNetworkInterfaceModule().strip() == "netxen_nic")):
                    description += "Here are a couple articles that may or may not be related:"
                    urls = ["https://access.redhat.com/knowledge/solutions/44475",
                            "https://access.redhat.com/knowledge/solutions/35299",
                            "https://access.redhat.com/knowledge/solutions/46663",
                            "https://access.redhat.com/knowledge/solutions/35299"]
                    rString += StringUtil.formatBulletString(description, urls)
        return rString

    def __evaluateClusterNodeFencing(self, cca, clusternode):
        rString = ""
        cnp = clusternode.getClusterNodeProperties()
        fenceDevicesList = cnp.getFenceDevicesList()
        if (len(fenceDevicesList) > 0):
            # Check if acpi is disabled if sys mgmt card is fence device
            smFenceDevicesList = ["fence_bladecenter", "fence_drac", "fence_drac5", "fence_ilo",
                                  "fence_ilo_mp", "fence_ipmi", "fence_ipmilan", "fence_rsa"]

            cnFenceDeviceList = cca.getClusterNodeFenceDevicesList(clusternode.getClusterNodeName())
            for fd in cnFenceDeviceList:
                if ((fd.getAgent() in smFenceDevicesList) and (not clusternode.isAcpiDisabledinRunlevel())):
                    description = "The service \"acpid\" is not disabled on all runlevels(0 - 6). " + \
                        "This service should be disabled since a system management fence device(%s) "%(fd.getAgent()) + \
                        "was detected. If acpid is enabled the fencing operation may not work as intended."
                    urls = ["https://access.redhat.com/knowledge/solutions/5414"]
                    rString += StringUtil.formatBulletString(description, urls)
                    break;
            # Check if fence_manual is enabled on a node
            if (cca.isFenceDeviceAgentEnabledOnClusterNode(clusternode.getClusterNodeName(), "fence_manual")):
                description = "The fence device \"fence_manual\" is defined as a fence agent for this node which is an unsupported fencing method."
                urls = ["https://access.redhat.com/knowledge/articles/36302"]
                rString += StringUtil.formatBulletString(description, urls)
            # Check to make sure that fence_vmware is not enabled on node
            if (cca.isFenceDeviceAgentEnabledOnClusterNode(clusternode.getClusterNodeName(), "fence_vmware")):
                description =  "The fence device \"fence_vmware\" is defined as a fence agent for this node which is an unsupported fencing method. "
                description += "The only supported fencing method for VMWare is fence_vmware_soap and fence_scsi."
                urls = ["https://access.redhat.com/knowledge/articles/29440"]
                rString += StringUtil.formatBulletString(description, urls)
        else:
            description = "There was no fence device defined for the clusternode. A fence device is required for each clusternode."
            urls = ["https://access.redhat.com/knowledge/solutions/15575"]
            rString += StringUtil.formatBulletString(description, urls)
        return rString

    def __evaluateServiceIsEnabled(self, clusternode, serviceName):
        rString = ""
        for chkConfigItem in clusternode.getChkConfigList():
            if (chkConfigItem.getName() == serviceName):
                if(chkConfigItem.isEnabledRunlevel3()):
                    rString += "3 "
                if(chkConfigItem.isEnabledRunlevel4()):
                    rString += "4 "
                if(chkConfigItem.isEnabledRunlevel5()):
                    rString += "5 "
        return rString

    def __evaluateClusterStorage(self, cca):
        # Is active/active nfs supported? Sorta
        # urls = ["https://access.redhat.com/knowledge/solutions/59498"]
        rString = ""
        for clusternode in self.__cnc.getClusterNodes():
            clusterNodeEvalString = ""
            if (not clusternode.isClusterNode()):
                continue
            # ###################################################################
            # Distro Specific evaluations
            # ###################################################################
            # The distro release of this node
            distroRelease = clusternode.getDistroRelease()
            if ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() == 5)):
                # Check if GFS2 module should be removed on RH5 nodes
                if (self.__cnc.doesGFS2ModuleNeedRemoval(clusternode.getUnameA(), clusternode.getClusterModulePackagesVersion())) :
                    description = "The kmod-gfs2 is installed on a running kernel >= 2.6.18-128. This module should be removed since the module is included in the kernel."
                    urls = ["https://access.redhat.com/knowledge/solutions/17832"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

            # ###################################################################
            # Analyze the Clustered Storage
            # ###################################################################
            listOfClusterStorageFilesystems = clusternode.getClusterStorageFilesystemList()
            stringUtil = StringUtil()

            # Check to see if they are exporting a gfs/gfs2 fs via samba and nfs.
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
                tableOfStrings = stringUtil.toTableStringsList(fsTable, tableHeader)
                urls = ["https://access.redhat.com/knowledge/solutions/39855"]
                clusterNodeEvalString += StringUtil.formatBulletString(description, urls, tableOfStrings)

            # Check for localflocks if they are exporting nfs.
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

            # Check to see if the GFS/GFS2 fs has certain mount options enabled.
            fsTable = []
            for csFilesystem in listOfClusterStorageFilesystems:
                csFilesystemOptions = csFilesystem.getAllMountOptions()
                if (not ((csFilesystemOptions.find("noatime") >= 0) and
                         (csFilesystemOptions.find("nodiratime") >= 0))):
                    fsTable.append([csFilesystem.getDeviceName(), csFilesystem.getMountPoint()])
            if (len(fsTable) > 0):
                tableHeader = ["device_name", "mount_point"]
                description =  "The following GFS/GFS2 file-systems did not have the mount option noatime or nodiratime set. "
                description += "Unless atime support is essential, Red Hat recommends setting the mount option \"noatime\" and "
                description += "\"nodiratime\" on every GFS/GFS2 mount point. This will significantly improve performance since "
                description += "it prevents reads from turning into writes."
                tableOfStrings = stringUtil.toTableStringsList(fsTable, tableHeader)
                urls = ["https://access.redhat.com/knowledge/solutions/35662"]
                clusterNodeEvalString += StringUtil.formatBulletString(description, urls, tableOfStrings)

            # ###################################################################
            # Add to string with the hostname and header if needed.
            # ###################################################################
            if (len(clusterNodeEvalString) > 0):
                if (not len(rString) > 0):
                    sectionHeader = "%s\nCluster Storage Configuration Known Issues\n%s" %(self.__seperator, self.__seperator)
                    rString += "%s\n%s(Cluster Node ID: %s):\n%s\n\n" %(sectionHeader, clusternode.getClusterNodeName(), clusternode.getClusterNodeID(), clusterNodeEvalString.rstrip())
                    sectionHeaderAdded = True
                else:
                    rString += "%s(Cluster Node ID: %s):\n%s\n\n" %(clusternode.getClusterNodeName(), clusternode.getClusterNodeID(), clusterNodeEvalString.rstrip())
        # Return the string
        return rString

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

    def __getPathToQuorumDisk(self, cca):
        quorumd = cca.getQuorumd()
        if (not quorumd == None):
            # Check to see if the qdisk is an lvm device.
            pathToQuroumDisk = quorumd.getDevice()
            quorumDiskLabel = quorumd.getLabel()
            for clusternode in self.__cnc.getClusterNodes():
                # Find out qdisk device if there is one
                clustatCommand = ClusterCommandsParser.parseClustatData(clusternode.getClusterCommandData("clustat"))
                pathToQuroumDisk = clustatCommand.findQuorumDisk()
                if ((pathToQuroumDisk) > 0):
                    return pathToQuroumDisk
        return ""

    def __isLVMDevice(self, pathToDevice, lvsDevices):
        filenameOfDevice = os.path.basename(pathToDevice)
        for lvsDevice in lvsDevices:
            if ((pathToDevice.endswith("%s-%s" %(lvsDevice.getVGName(), lvsDevice.getLVName()))) or
                (pathToDevice.endswith("%s/%s" %(lvsDevice.getVGName(), lvsDevice.getLVName())))):
                # vgName-lvName or /dev/vgName/lvName or /dev/mapper/vgName-lvName
                return True
        return False

    def __isQDiskLVMDevice(self, pathToDevice):
        if (not len(pathToDevice) > 0):
            return False
        # Cycle through all the nodes till you find a match.
        for clusternode in self.__cnc.getClusterNodes():
            clusternodeName = clusternode.getClusterNodeName()
            storageData = self.__cnc.getStorageData(clusternodeName)
            devicemapperCommandsMap =  storageData.getDMCommandsMap()
            lvsDevices = DeviceMapperParser.parseLVSDevicesData(devicemapperCommandsMap.get("lvs_-a_-o_devices"))
            if (self.__isLVMDevice(pathToDevice, lvsDevices)):
                return True
        return False

    # #######################################################################
    # Evaluate Function
    # #######################################################################
    def evaluate(self):
        """
         * If two node cluster, check if hb and fence on same network. warn qdisk required if not or fence delay.
         """
        # Return string for evaluation.
        rstring = ""
        # Nodes that are in cluster.conf, so should have report of all these
        baseClusterNode = self.__cnc.getBaseClusterNode()
        if (baseClusterNode == None):
            # Should never occur since node count should be checked first.
            return ""
        cca = ClusterHAConfAnalyzer(baseClusterNode.getPathToClusterConf())
        # ###################################################################
        # Check global configuration issues:
        # ###################################################################
        clusterConfigString = self.__evaluateClusterGlobalConfiguration(cca)
        if (len(clusterConfigString) > 0):
            sectionHeader = "%s\nCluster Global Configuration Known Issues\n%s" %(self.__seperator, self.__seperator)
            rstring += "%s\n%s:\n%s\n" %(sectionHeader, cca.getClusterName(), clusterConfigString)

        # ###################################################################
        # Check qdisk configuration:
        # ###################################################################
        quorumdConfigString = ""
        pathToQuroumDisk = self.__getPathToQuorumDisk(cca)
        #print "Is LVM Device %s? %s" %(pathToQuroumDisk, str(self.__isLVMDevice(pathToQuroumDisk)))
        if (self.__isQDiskLVMDevice(pathToQuroumDisk)):
            description =  "The quorum disk %s cannot be an lvm device." %(pathToQuroumDisk)
            urls = ["https://access.redhat.com/knowledge/solutions/41726"]
            quorumdConfigString += StringUtil.formatBulletString(description, urls)

        distroRelease = baseClusterNode.getDistroRelease()
        quorumdConfigString += self.__evaluateQuorumdConfiguration(cca, distroRelease)
        if (len(quorumdConfigString) > 0):
            sectionHeader = "%s\nQuorumd Disk Configuration Known Issues\n%s" %(self.__seperator, self.__seperator)
            rstring += "%s\n%s:\n%s\n\n" %(sectionHeader, cca.getClusterName(), quorumdConfigString)

        # ###################################################################
        # Check cluster nodes configuration
        # ###################################################################
        # Will be set to true if a node has a string was added to evaluation string.
        sectionHeaderAdded = False
        for clusternode in self.__cnc.getClusterNodes():
            clusterNodeEvalString = ""
            if (not clusternode.isClusterNode()):
                continue

            # Check if this is using Open Shared root
            if (clusternode.isOpenSharedRootClusterNode()):
                description = "This is an openshared-root cluster node. This is a special cluster using 3rd party rpms that is only supported on RHEL4."
                urls = ["http://www.open-sharedroot.org/"]
                clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

            # Checking all clusternode names in /etc/hosts
            if (not self.__cnc.isClusterNodeNamesInHostsFile(cca.getClusterNodeNames(), clusternode.getNetworkMaps().getListOfNetworkMaps())) :
                description = "The clusternode names were not all defined in the /etc/hosts file. This is not a requirement, but does "
                description += "make troubleshooting a cluster a lot easier."
                urls = ["https://access.redhat.com/knowledge/articles/5934"]
                clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

            # Check the networking configuration of the cluster node's
            # heartbeat network.
            hbNetworkMap = clusternode.getHeartbeatNetworkMap()
            result = self.__evaluateClusterNodeHeartbeatNetwork(hbNetworkMap)
            if (len(result) > 0):
                clusterNodeEvalString += result

            # Fencing checks
            result = self.__evaluateClusterNodeFencing(cca, clusternode)
            if (len(result) > 0):
                clusterNodeEvalString += result

            # ###################################################################
            # Check if there are clustered vm services and if so that
            # libvirt-guests is not enabled.
            # ###################################################################
            serviceName = "libvirt-guests"
            serviceRunlevelEnabledString = self.__evaluateServiceIsEnabled(clusternode, serviceName)
            if (len(serviceRunlevelEnabledString) > 0):
                for clusteredService in cca.getClusteredServices():
                    if (clusteredService.isVirtualMachineService()):
                        description =  "The service %s should be disabled since there are virtual machines that are " %(serviceName)
                        description += "being managed by rgmanager in the /etc/cluster/cluster.conf file. "
                        description += "The following runlevels have %s enabled: %s." %(serviceName, serviceRunlevelEnabledString.strip())
                        urls = ["https://access.redhat.com/knowledge/solutions/96543"]
                        clusterNodeEvalString += StringUtil.formatBulletString(description, urls)
                        # Break out because if we find a vm then we break out
                        # cause we just need one instance.
                        break;
            # ###################################################################
            # Distro specfic evaluations
            # ###################################################################
            # The distro release of this node
            distroRelease = clusternode.getDistroRelease()
            # RHEL5 and greater checks
            cnp = clusternode.getClusterNodeProperties()
            if ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() >= 5)):
                # Make sure that multicast tags are not on clusternode stanzas
                if (((len(cnp.getMulticastAddress()) > 0) or (len(cnp.getMulticastInterface()) > 0))) :
                    description = "The multicast tags should not be in the <clusternodes> stanzas. These tags are only supported on RHEL 4."
                    urls = ["https://access.redhat.com/knowledge/solutions/32242"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

            # ###################################################################
            # RHEL 5 Specific Checks
            # ###################################################################
            if ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() == 5)):
                # Check if the service openais is enabled because it should be disabled if this is a cluster node.
                serviceName = "openais"
                serviceRunlevelEnabledString = self.__evaluateServiceIsEnabled(clusternode, serviceName)
                if (len(serviceRunlevelEnabledString) > 0):
                    description =  "The service %s should be disabled if the host is part of a cluster since the service cman starts the service %s." %(serviceName, serviceName)
                    description += "The following runlevels have %s enabled: %s." %(serviceName, serviceRunlevelEnabledString.strip())
                    urls = ["https://access.redhat.com/knowledge/solutions/5898"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

                # Check if scsi_reserve service is enabled with no scsi fencing device in cluster.conf
                serviceName = "scsi_reserve"
                if (not cca.isFenceDeviceAgentEnabledOnClusterNode(clusternode.getClusterNodeName(), "fence_scsi")):
                    serviceRunlevelEnabledString = self.__evaluateServiceIsEnabled(clusternode, serviceName)
                    if (len(serviceRunlevelEnabledString) > 0):
                        description =  "The service %s should be disabled since there was no fence_scsi device detected for this node." %(serviceName)
                        description += "The following runlevels have %s enabled: %s." %(serviceName, serviceRunlevelEnabledString.strip())
                        urls = ["https://access.redhat.com/knowledge/solutions/42530", "https://access.redhat.com/knowledge/solutions/17784"]
                        clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

            # ###################################################################
            # RHEL6 specific
            # ###################################################################
            if ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() == 6)):
                # Check if the service corosync is enabled because it should be disabled if this is a cluster node.
                serviceName = "corosync"
                serviceRunlevelEnabledString = self.__evaluateServiceIsEnabled(clusternode, serviceName)
                if (len(serviceRunlevelEnabledString) > 0):
                    description =  "The service %s should be disabled if the host is part of a cluster since the service cman starts the service %s." %(serviceName, serviceName)
                    description += "The following runlevels have %s enabled: %s." %(serviceName, serviceRunlevelEnabledString.strip())
                    urls = ["https://access.redhat.com/knowledge/solutions/5898"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)
            # ###################################################################
            if (len(clusterNodeEvalString) > 0):
                if (not sectionHeaderAdded):
                    sectionHeader = "%s\nCluster Node Configuration Known Issues\n%s" %(self.__seperator, self.__seperator)
                    rstring += "%s\n%s(Cluster Node ID: %s):\n%s\n\n" %(sectionHeader, clusternode.getClusterNodeName(), clusternode.getClusterNodeID(), clusterNodeEvalString.rstrip())
                    sectionHeaderAdded = True
                else:
                    rstring += "%s(Cluster Node ID: %s):\n%s\n\n" %(clusternode.getClusterNodeName(), clusternode.getClusterNodeID(), clusterNodeEvalString.rstrip())

        # ###################################################################
        # Evaluate the Cluster Storage
        # ###################################################################
        resultString = self.__evaluateClusterStorage(cca)
        if (len(resultString) > 0):
            rstring += resultString
        return rstring
