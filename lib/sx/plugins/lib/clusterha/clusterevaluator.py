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
from sx.plugins.lib.clusterha.clusterhastorage import ClusterHAStorage
from sx.plugins.lib.rpm.rpmparser import RPMUtils
from sx.plugins.lib.kernel import KernelRelease

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
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)
            message = "Please verify that a cluster.conf files exists for all cluster nodes and that they are identical."
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
        elif (not  len(cca.getClusterNodeNames()) == len(self.__cnc.getClusterNodes())):
            message = "There was only %d cluster.conf compared for the %d node cluster." %(len(self.__cnc.getPathToClusterConfFiles()),
                                                                                           len(cca.getClusterNodeNames()))
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)
        # ###################################################################
        # Fencing evaluations that only require a cluster.conf file.
        # ###################################################################
        result = self.__evaluateClusterNodesFencing(cca)
        if (len(result) > 0):
            rString += result
        return rString

    def __evaluateClusterNodesFencing(self, cca):
        """
        Evaluation on all the clusternodes that do not need report and only need the cluster.conf.

        Could make this easier by using 1 loop, but not sure i want all the list
        or map floating. Probably should create a map so there is just 1 loop.
        """
        rString = ""
        # Check if there is no fence defined  on the cluster nodes.
        fsTable = []
        for clusternodeName in cca.getClusterNodeNames():
            cnFenceDeviceList = cca.getClusterNodeFenceDevicesList(clusternodeName)
            if (not len(cnFenceDeviceList) > 0):
                fsTable.append([clusternodeName])
        if (len(fsTable) > 0):
            description = "There was no fence device defined for the following clusternodes. A fence device is required for each clusternode."
            urls = ["https://access.redhat.com/knowledge/solutions/15575"]
            stringUtil = StringUtil()
            tableOfStrings = stringUtil.toTableStringsList(fsTable, ["clusternode_name"])
            rString += StringUtil.formatBulletString(description, urls, tableOfStrings)

        # Check if fence_manual is defined on a cluster_node.
        fsTable = []
        for clusternodeName in cca.getClusterNodeNames():
            # Check if fence_manual is enabled on a node
            if (cca.isFenceDeviceAgentEnabledOnClusterNode(clusternodeName, "fence_manual")):
                fsTable.append([clusternodeName])
        if (len(fsTable) > 0):
            description = "The fence device \"fence_manual\" is defined as a fence agent for the following clusternodes which is an unsupported fencing method."
            urls = ["https://access.redhat.com/knowledge/articles/36302"]
            stringUtil = StringUtil()
            tableOfStrings = stringUtil.toTableStringsList(fsTable, ["clusternode_name"])
            rString += StringUtil.formatBulletString(description, urls, tableOfStrings)

        # Check to make sure that fence_vmware is not enabled on node
        fsTable = []
        for clusternodeName in cca.getClusterNodeNames():
            # Check if fence_manual is enabled on a node
            if (cca.isFenceDeviceAgentEnabledOnClusterNode(clusternodeName, "fence_vmware")):
                fsTable.append([clusternodeName])
        if (len(fsTable) > 0):
            description =  "The fence device \"fence_vmware\" is defined as a fence agent for the following clusternodes which is an unsupported fencing method. "
            description += "The only supported fencing method for VMWare is fence_vmware_soap and fence_scsi."
            urls = ["https://access.redhat.com/knowledge/articles/29440"]
            stringUtil = StringUtil()
            tableOfStrings = stringUtil.toTableStringsList(fsTable, ["clusternode_name"])
            rString += StringUtil.formatBulletString(description, urls, tableOfStrings)
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
            description =  "The cluster has the option \"cman/@two_nodes\" enabled and also "
            description += "has set the option \"quorumd/@votes\" greater than 0 which is unsupported."
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

    def __evaluateClusterNodeHeartbeatNetwork(self, clusternode):
        rString = ""
        hbNetworkMap = clusternode.getHeartbeatNetworkMap()

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
        # 44475 | requires a firmware upgrade to the nic
        # 35299 | Fixed in RHEL 5.5.z (kernel-2.6.18-194.32.1.el5) and RHEL 5.6 (kernel-2.6.18-238.el5)
        # 46663 | Fixed in RHEL 5.7   (kernel-2.6.18-274.el5)
        netxenUrlsList = ["https://access.redhat.com/knowledge/solutions/44475"]
        kernelRelease = clusternode.getUnameA().getKernelRelease()
        if (str(kernelRelease) > 0):
            # netxenUrlsList.append("https://access.redhat.com/knowledge/solutions/35299")
            kernelRelease.compareGT("2.6.18-194.32.1.el5")
            kernelRelease.compareGT("2.6.18-238.el5")

            # netxenUrlsList.append("https://access.redhat.com/knowledge/solutions/46663")
            kernelRelease.compareGT("2.6.18-274.el5")

            # Need to rewrite the compare on kmod-gfs2.

        solutionNicModuleUrlMap = {"bnx2":[], "netxen": netxenUrlsList, "nx_nic": netxenUrlsList, "netxen_nic":netxenUrlsList}
        if (hbNetworkMap.getNetworkInterfaceModule().strip() in solutionNicModuleUrlMap.keys()):
            description =  "The network interface %s is using the module \"%s\" for cluster communication." %(hbNetworkMap.getInterface(), hbNetworkMap.getNetworkInterfaceModule())
            description += "The module \"%s\" has known network communication issues." %(hbNetworkMap.getNetworkInterfaceModule())
            rString += StringUtil.formatBulletString(description, solutionNicModuleUrlMap.get(hbNetworkMap.getNetworkInterfaceModule().strip()))
        elif (hbNetworkMap.isBondedMasterInterface()):
            # Loop over the bonded interfaces
            bondedMasterInterface = ""
            bondedSlaveInterfacesMap = {}
            for bondedSlaveInterface in hbNetworkMap.getBondedSlaveInterfaces():
                if (bondedSlaveInterface.getNetworkInterfaceModule().strip() in solutionNicModuleUrlMap.keys()):
                    if (not bondedSlaveInterfacesMap.has_key(bondedSlaveInterface.getNetworkInterfaceModule())):
                        bondedMasterInterface = hbNetworkMap.getInterface()
                        bondedSlaveInterfacesMap[bondedSlaveInterface.getNetworkInterfaceModule()] = []
                    bondedSlaveInterfacesMap.get(bondedSlaveInterface.getNetworkInterfaceModule()).append(bondedSlaveInterface.getInterface())
            if (len(bondedMasterInterface) > 0):
                for key in bondedSlaveInterfacesMap.keys():
                    interfacesString = ""
                    for currentNicInterface in bondedSlaveInterfacesMap.get(key):
                        interfacesString += " %s," %(currentNicInterface)
                    description =  "The following network interface(s)%s where using the \"%s\" for cluster communication and is a slave interface to the bond %s." %(interfacesString.rstrip(","),
                                                                                                                                                                      key, bondedMasterInterface)
                rString += StringUtil.formatBulletString(description, solutionNicModuleUrlMap.get(bondedSlaveInterface.getNetworkInterfaceModule().strip()))
        return rString

    def __evaluateClusterNodeFencing(self, cca, clusternode):
        """
        Evaluation on a clusternode for fencing that requires a report. There
        are other evaluations that are done in global section.
        """
        rString = ""
        cnp = clusternode.getClusterNodeProperties()
        fenceDevicesList = cnp.getFenceDevicesList()
        clusternodeName = clusternode.getClusterNodeName()
        if (len(fenceDevicesList) > 0):
            # Check if acpi is disabled if sys mgmt card is fence device
            smFenceDevicesList = ["fence_bladecenter", "fence_drac", "fence_drac5", "fence_ilo",
                                  "fence_ilo_mp", "fence_ipmi", "fence_ipmilan", "fence_rsa"]

            cnFenceDeviceList = cca.getClusterNodeFenceDevicesList(clusternodeName)
            for fd in cnFenceDeviceList:
                if ((fd.getAgent() in smFenceDevicesList) and (not clusternode.isAcpiDisabledinRunlevel())):
                    description = "The service \"acpid\" is not disabled on all runlevels(0 - 6). " + \
                        "This service should be disabled since a system management fence device(%s) "%(fd.getAgent()) + \
                        "was detected. If acpid is enabled the fencing operation may not work as intended."
                    urls = ["https://access.redhat.com/knowledge/solutions/5414"]
                    rString += StringUtil.formatBulletString(description, urls)
                    break;
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

    # Disabling this for now cause it cannot be accurate all the time.
    """
    def __isQDiskLVMDevice(self, pathToDevice):
        # For finding quorum disk.
        from sx.plugins.lib.clusterha.clustercommandsparser import ClusterCommandsParser
        from sx.plugins.lib.storage.devicemapperparser import DeviceMapperParser
        from sx.plugins.lib.storage.devicemapperparser import DMSetupInfoC
        from sx.plugins.lib.storage.lvm import LVM

        if (not len(pathToDevice) > 0):
            return False
        # Cycle through all the nodes till you find a match.
        for clusternode in self.__cnc.getClusterNodes():
            devicemapperCommandsMap =  self.__cnc.getStorageData(clusternode.getClusterNodeName()).getDMCommandsMap()
            lvm = LVM(DeviceMapperParser.parseVGSVData(devicemapperCommandsMap.get("vgs_-v")),
                      DeviceMapperParser.parseLVSAODevicesData(devicemapperCommandsMap.get("lvs_-a_-o_devices")),
                      self.__cnc.getStorageData(clusternode.getClusterNodeName()).getLVMConfData())
            return lvm.isLVMDevice(pathToDevice)
        return False
    """
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
        # Disabling this for now cause it cannot be accurate all the time.
        #pathToQuroumDisk = self.__cnc.getPathToQuorumDisk()
        #if (self.__isQDiskLVMDevice(pathToQuroumDisk)):
        #    description =  "The quorum disk %s cannot be an lvm device." %(pathToQuroumDisk)
        #    urls = ["https://access.redhat.com/knowledge/solutions/41726"]
        #    quorumdConfigString += StringUtil.formatBulletString(description, urls)

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
            result = self.__evaluateClusterNodeHeartbeatNetwork(clusternode)
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
            # Verify that lvm an lvm2-cluster are same major and minor version.
            # ###################################################################
            lvm2PackageMap = RPMUtils.getPackageVersion(clusternode.getInstalledRPMS(), ["lvm2", "lvm2-cluster"])
            if (lvm2PackageMap.has_key("lvm2-cluster")):
                lvm2clusterPackage = lvm2PackageMap.get("lvm2-cluster")[0]
                # Dont going to handle lvm2 not found cause that is highly unlikely.
                if (lvm2PackageMap.has_key("lvm2")):
                    lvm2Package = lvm2PackageMap.get("lvm2")[0]
                    lvm2clusterVersion = lvm2clusterPackage.replace("lvm2-cluster-", "").split(".el5")[0].split("-")[0].strip()
                    lvm2Version = lvm2Package.replace("lvm2-", "").split(".el5")[0].split("-")[0].strip()
                    if (not lvm2clusterVersion == lvm2Version):
                        description = "The packages %s and %s need to be on the same major/minor version number. " %(lvm2Package, lvm2clusterPackage)
                        description += "If the packages do not have the same major/minor version number then there could be communications issues or "
                        description += "problems starting clvmd which is part of the lvm2-cluster package."
                        urls = ["https://access.redhat.com/knowledge/solutions/169913", "https://access.redhat.com/knowledge/solutions/18999"]
                        clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

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
        clusterHAStorage = ClusterHAStorage(self.__cnc)
        resultString = clusterHAStorage.evaluateClusteredFilesystems()
        if (len(resultString) > 0):
            rstring += resultString
        # ###################################################################
        # Check if the fs resources are using HALVM (Disable for now cause
        # having problems with accuracy if files for vg/lv do not exist.
        # ###################################################################
        resultString = clusterHAStorage.evaluateNonClusteredFilesystems()
        if (len(resultString) > 0):
            rstring += resultString
        # ###################################################################
        # Return the result
        return rstring
