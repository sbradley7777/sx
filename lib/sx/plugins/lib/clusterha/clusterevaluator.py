#!/usr/bin/env python
"""
This class will evalatuate a cluster and create a report that will
link in known issues with links to resolution.

This plugin is documented here:
- https://fedorahosted.org/sx/wiki/SX_clusterplugin

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
            urls = ["https://access.redhat.com/solutions/32.17"]
            rString += StringUtil.formatBulletString(description, urls)

        if (cca.hasAttributeCleanStart()):
            description =  "The clean_start option in the /etc/cluster/cluster.conf is not supported "
            description += "for production clusters and is set to %s. The option is for testing and debugging only." %(cca.getCleanStart())
            urls = ["https://access.redhat.com/solutions/23238"]
            rString += StringUtil.formatBulletString(description, urls)

        # Disable the post_join_delay check for now
        if (not int(cca.getPostJoinDelay()) > 3):
            description =  "The post_join_delay option was 3 (which is the default value) in the /etc/cluster/cluster.conf file. "
            description += "In some cluster environments a value of 3 for post_join_delay is to too low."
            urls = ["https://access.redhat.com/solutions/21742", "https://access.redhat.com/solutions/3641"]
            rString += StringUtil.formatBulletString(description, urls)
        if (not (int(cca.getPostFailDelay()) == 0)):
            description =  "The post_fail_delay option in the /etc/cluster/cluster.conf file was not zero(default). "
            description += "Most clusters should not modify the default value of zero."
            urls = ["https://access.redhat.com/solutions/21742", "https://access.redhat.com/solutions/5929"]
            rString += StringUtil.formatBulletString(description, urls)
        # Check for single node configurations and clusters that are larger than 16 nodes.
        clusterNodeCount = len(cca.getClusterNodeNames())
        if (clusterNodeCount == 1):
            description =  "This is a single node cluster and does not meet the minimum number of cluster nodes required for "
            description += "high-availibility. Red Hat recommends that clusters always have a minimum of two nodes to protect "
            description += "against hardware failures."
            urls = ["https://access.redhat.com/articles/5892"]
            rString += StringUtil.formatBulletString(description, urls)
        elif (clusterNodeCount > 16):
            descriptioin = "The maximum number of cluster nodes supported by the High Availability Add-On is 16, and the same "
            description += "is true for the Resilient Storage Add-On that includes GFS2 and CLVM. "
            description += "This cluster currently has %d number of cluster nodes which exceeds the supported 16 number of cluster nodes." %(clusterNodeCount)
            urls = ["https://access.redhat.com/articles/40051"]
            rString += StringUtil.formatBulletString(description, urls)
        # Check if two_node is 1 and if expected_votes is 1
        if ((cca.isCmanTwoNodeEnabled()) and ((not cca.getCmanExpectedVotes() == "1") or (not len(cca.getCmanExpectedVotes()) > 0))):
            description = "If the \"cman/@two_node\" option is set to 1 then the option \"cman/@expected_votes\" should be set to 1."
            urls = ["https://access.redhat.com/solutions/30398"]
            rString += StringUtil.formatBulletString(description, urls)

        # ###################################################################
        # Compare the cluster.conf files
        # ###################################################################
        if ((not cca.isClusterConfFilesIdentical(self.__cnc.getPathToClusterConfFiles())) and (len(self.__cnc.getPathToClusterConfFiles()) > 1)):
            description  = "The /etc/cluster/cluster.conf files were not identical on all the cluster node's cluster.conf files that were analyzed."
            if (not  len(cca.getClusterNodeNames()) == len(self.__cnc.getClusterNodes())):
                # More than 2 nodes compared and all cluster nodes cluster.confs
                # were compared, but not all nodes in the cluster's cluster.conf
                # was compared.
                description += "There was only %d cluster.conf files compared for the %d node cluster. " %(len(self.__cnc.getPathToClusterConfFiles()),
                                                                                                          len(cca.getClusterNodeNames()))
            urls = ["https://access.redhat.com/solutions/19808"]
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
        # Check if the fs resources are using HALVM (Disable for now cause
        # having problems with accuracy if files for vg/lv do not exist.
        # ###################################################################
        clusterHAStorage = ClusterHAStorage(self.__cnc)
        resultString = clusterHAStorage.evaluateNonClusteredFilesystems()
        if (len(resultString) > 0):
            rString += resultString
        return rString

    def __evaluateClusterTransportMode(self, clusternode):
        rString = ""
        transportMode = clusternode.getCmanTransportMode()
        distroRelease = clusternode.getDistroRelease()

        description = ""
        urls = []
        if (transportMode == "broadcast"):
            # RHEL 4 and RHEL 5 is fully supported. RHEL 6, Tech Preview.
            urls = ["https://access.redhat.com/articles/146163", "https://access.redhat.com/articles/32881"]
            if (distroRelease.getMajorVersion() == 5):
                description = "There is known limitations with \"broadcast\" mode as noted in the following articles: "
            elif (distroRelease.getMajorVersion() >= 5):
                description =  "The transport mode \"broadcast\" mode is technology preview in RHEL 6. "
                description += "There is known limitations with \"broadcast\" mode as noted in the following articles: "
        elif (transportMode == "udpu"):
            # Only RHEL 6.0 6.1 is TP, RHEL 6.2+ fully supported. RHEL 4 and RHEL 5 not included.
            description = "The transport mode udpu is only support on RHEL 6.2+."
            if ((distroRelease.getMajorVersion() == 6) and (distroRelease.getMajorVersion() >= 2)):
                description = "There is known limitations with \"udpu\" mode as noted in the following articles: "
            urls = ["https://access.redhat.com/articles/146163", "https://access.redhat.com/solutions/178423"]

        if (len(description) > 0):
            return StringUtil.formatBulletString(description, urls)
        return ""

    def __evaluateClusterPacemakerConfiguration(self):
        rString = ""
        evaluationMap = {"01-isPacemakerCluster":"", "02-supportedVersion":"", "03-pacemakerRPMSInstalled":""}
        for clusternode in self.__cnc.getClusterNodes():
            distroRelease = clusternode.getDistroRelease()
            if (clusternode.isPacemakerClusterNode()):
                # List of pacemaker limitiations to add:
                # - https://access.redhat.com/solutions/509783
                if (not len(evaluationMap.get("01-isPacemakerCluster")) > 0):
                    description =  "This is a pacemaker cluster which requires special configuration as outlined in the following document. "
                    description += "Our recommendation is to use rgmanager unless rgmanager does not provide support for a particular "
                    description += "use case, whereas pacemaker does."
                    urls = ["https://access.redhat.com/solutions/509783"]
                    evaluationMap["01-isPacemakerCluster"] = StringUtil.formatBulletString(description, urls)
                if ((not ((distroRelease.getMajorVersion() == 6) and (distroRelease.getMinorVersion() >= 5))) and (not len(evaluationMap.get("02-supportedVersion")) > 0)):
                    # if not greater that 6.5 then print msg about tech preview and openstack suppport only.
                    description =  "This appears to be a RHEL %d.%d cluster. Pacemaker is only supported in the " %(distroRelease.getMajorVersion(), distroRelease.getMinorVersion())
                    description += "following configurations: RHEL 6.4 when using openstack, RHEL 6.5. Pacemaker was technology preview "
                    description += "on RHEL 6.4 except for when using with openstack."
                    urls = ["https://access.redhat.com/solutions/509783"]
                    evaluationMap["02-supportedVersion"] = StringUtil.formatBulletString(description, urls)
                    # Print message about pacemaker installed but not coonfigured. check for pacemaker rpms or that pacemaker service
                if (not len(evaluationMap.get("03-pacemakerRPMSInstalled")) > 0):
                    for rpm in clusternode.getClusterPackagesVersion():
                        if (rpm.find("pacemaker") >= 0):
                            # If any pacemaker rpm is found installed then considered this a
                            # pacemaker cluster.
                            fenceDeviceList = clusternode.getClusterNodeProperties().getFenceDevicesList()
                            description =  "There was rpms related to pacemaker found installed on one of the cluster node(s), but the fencing agent "
                            description += "fence_pcmk was not found configured for that cluster node(s)."
                            for fenceDevice in fenceDeviceList:
                                # A cluster that uses cman for membership and pacemaker to manage
                                # services requires a specific fencing agent.
                                if (fenceDevice.getAgent() == "fence_pcmk"):
                                    description = ""
                            if ((not len(evaluationMap.get("03-pacemakerRPMSInstalled")) > 0) and (len(description) > 0)):
                                evaluationMap["03-pacemakerRPMSInstalledNoFenceAgent"] = StringUtil.formatBulletString(description, [])
        keys = evaluationMap.keys()
        keys.sort()
        for key in keys:
            if (len(evaluationMap.get(key)) > 0):
                rString += "%s" %(evaluationMap.get(key))
        return rString

    def __evaluateClusterNodesFencing(self, cca):
        """
        Evaluation on all the clusternodes that do not need report and only need the cluster.conf.

        Could make this easier by using 1 loop, but not sure i want all the list
        or map floating. Probably should create a map so there is just 1 loop.
        """
        fenceEvaluationsMap = {}
        for clusternodeName in cca.getClusterNodeNames():
            cnFenceDeviceList = cca.getClusterNodeFenceDevicesList(clusternodeName)
            # Check to see if there exists a fence device on each cluster node.
            if (not len(cnFenceDeviceList) > 0):
                description = "There was no fence device defined for one or more cluster nodes. A fencing device is required for all cluster nodes."
                urls = ["https://access.redhat.com/solutions/15575"]
                stringUtil = StringUtil()
                fenceEvaluationsMap["fence_devices_none"] = StringUtil.formatBulletString(description, urls)
            # Check if fence_manual is enabled on any node.
            if (cca.isFenceDeviceAgentEnabledOnClusterNode(clusternodeName, "fence_manual")):
                description = "The fence device \"fence_manual\" is defined as a fence agent on one or more cluster nodes. This fencing agent \"fence_manual\" is unsupported. "
                urls = ["https://access.redhat.com/articles/36302"]
                stringUtil = StringUtil()
                fenceEvaluationsMap["fence_manual"] = StringUtil.formatBulletString(description, urls)

            # Check to make sure that fence_vmware is not enabled on node
            if (cca.isFenceDeviceAgentEnabledOnClusterNode(clusternodeName, "fence_vmware")):
                description =  "The fence device \"fence_vmware\" is defined as a fence agent on one or more cluster nodes. This fencing agent \"fence_vmware\" is unsupported. "
                description += "The only supported fencing method for VMWare is fence_vmware_soap and fence_scsi."
                urls = ["https://access.redhat.com/articles/29440"]
                stringUtil = StringUtil()
                fenceEvaluationsMap["fence_vmware"] = StringUtil.formatBulletString(description, urls)
            # Make sure there is secondary fence device configured.
            if (not len(list(set(map(lambda m: m.getMethodName(), cnFenceDeviceList)))) > 1):
                description = "One or more cluster nodes did not have a secondary fence device. A secondary fence device is recommended on all cluster nodes."
                urls = ["https://access.redhat.com/solutions/15575" , "https://access.redhat.com/solutions/16657"]
                stringUtil = StringUtil()
                fenceEvaluationsMap["fence_secondary_agent"] = StringUtil.formatBulletString(description, urls)

            # List of devices that can use the unfence flag: fence_scsi + fence_sanlock + fence agents with option "fabric_fencing" enabled.
            # $ grep "fabric_fencing" ~/git/fence-agents/ -r
            # This does not validate the configuration, but looks for instances when unfence  will not work with certain agents.
            listOfUnfenceDevices = ["fence_scsi", "fence_cisco_mds", "fence_ifmib", "fence_sanbox2", "fence_brocade", "fence_sanlock"]
            if (cca.isUnfenceEnabledOnClusterNode(clusternodeName)):
                foundUnfenceableFenceAgent = False
                for fd in cca.getClusterNodeFenceDevicesList(clusternodeName):
                    if (fd.getAgent() in listOfUnfenceDevices):
                        foundUnfenceableFenceAgent = True
                        break
                if (not foundUnfenceableFenceAgent):
                    description = "The <unfence/> tag is only used for fabric fencing, fence_sanlock, and fence_scsi for enabling the shared storage device. "
                    description += " There was no fencing agent found that can use the <unfence/> tag. The <unfence/> tag(s) should be removed."
                    urls = ["https://access.redhat.com/solutions/789203"]
                    stringUtil = StringUtil()
                    fenceEvaluationsMap["fence_unfence_invalid"] = StringUtil.formatBulletString(description, urls)
        # Build the evaluation string that will be returned.
        rString = ""
        for key in fenceEvaluationsMap.keys():
            rString += fenceEvaluationsMap.get(key)
        return rString.rstrip()

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
                    urls = ["https://access.redhat.com/solutions/5414"]
                    rString += StringUtil.formatBulletString(description, urls)
                    break;
            # Check to verify that if fence_scsi is used on virtual machines that iscsi is used on all shared storage.
            for fd in cnFenceDeviceList:
                if (fd.getAgent() == "fence_scsi"):
                    if ((clusternode.getMachineType().lower().find("vmware") >= 0) or (clusternode.getMachineType().lower().find("rhev") >= 0)):
                        description = "This fencing agent fence_scsi requires that all shared storage is over iscsi when the cluster node is a %s. " %(clusternode.getMachineType().strip())
                        description += "Make sure that all the shared storage will be over iscsi if fence_scsi agent is used on this clusternode that is a vitual machine."
                        urls = ["https://access.redhat.com/articles/29440", "https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/6/html-single/High_Availability_Add-On_Overview/index.html#s2-virt-guestcluster-scsi"]
                        rString += StringUtil.formatBulletString(description, urls)
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
            urls = ["https://access.redhat.com/solutions/35941", "https://access.redhat.com/solutions/456123"]
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

        # Here is the unsupported conditions for master_wins. On RHEL 6
        # master_wins is automagic, so they really should not be changing these
        # options.

        # Master-wins mode is automatically configured on RHEL 6 when:
        # * There are only 2 nodes in the cluster
        # * There is a quorum disk configured that has no heuristics.

        # If master_wins is 1 and no heuristics = PASS
        # If master_wins is 1 and 1 or more heuristics = FAIL
        # If 2 node cluster and master_wins is 0 and no heuristics = FAIL
        # urls = ["https://access.redhat.com/solutions/24037"]

        heurisitcCount = len(quorumd.getHeuristics())
        masterWins = quorumd.getMasterWins()
        # Set default values with respect to distro release.
        if (not (len(masterWins) > 0) and (distroRelease.getMajorVersion() == 5)):
            # In RHEL 6 it is autocalculated, but in RHEL 5 it will default to 0
            # if it is not set.
            masterWins = "0"
        elif (not (len(masterWins) > 0) and (distroRelease.getMajorVersion() == 6) and
            (not heurisitcCount > 0)):
            #Master-wins mode is automatically configured on RHEL 6 when:
            # * There are only 2 nodes in the cluster
            # * There is a quorum disk configured that has no heuristics.
            masterWins = "1"
        # Verify the configuration of qdisk.
        # If master_wins is 1 and 1 or more heuristics = FAIL
        if ((masterWins == "1") and (heurisitcCount > 0)):
            description = "There cannot be any heuristics set in the cluster.conf if \"master_wins\" is enabled."
            urls = ["https://access.redhat.com/solutions/24037", "https://access.redhat.com/solutions/708393"]
            rString += StringUtil.formatBulletString(description, urls)
        # If master_wins is 1 and 1 or more heuristics = FAIL
        if ((masterWins == "0") and (heurisitcCount == 0) and (len(cca.getClusterNodeNames()) >= 2)):
            description =  "If a quorumd tag is in the cluster.conf and there is no heuristic defined then "
            description += "enabled \"master_wins\" or define some heuristics for quorumd."
            urls = ["https://access.redhat.com/solutions/24037", "https://access.redhat.com/solutions/708393"]
            rString += StringUtil.formatBulletString(description, urls)

        # cman/@two_node: Must be set to 0 when qiskd is in use with one EXCEPTION and
        # that is if quorumd/@votes is set to 0, two_node is allowed.
        if ((int(quorumd.getVotes()) > 0) and (cca.isCmanTwoNodeEnabled())):
            description =  "The cluster has the option \"cman/@two_nodes\" enabled and also "
            description += "has set the option \"quorumd/@votes\" greater than 0 which is unsupported."
            urls = []
            rString += StringUtil.formatBulletString(description, urls)

        # In previous version of ClusterHA scsi timeouts could cause a problem
        # with qdisk and it was recommened to increase totem/token and
        # cman/quorum_dev_poll to account for this. These high values will cause
        # detection of a dead member take longer, but in a later cman errata a
        # fix was added to address this so that the values could be set to a
        # normal value.

        # The values of quorum_dev_poll or token will be empty string if they
        # are not in cluster.conf.

        # If we are evaluating this part of code, then there is a <quorumd>
        # section.

        # * In RHEL 5 the quorum_dev_poll and totem/token values should be set.

        # * Ideally the expected_votes value for the cman tag should be equal to
        #   the total number of cluster nodes times 2 and minus. Unless they are
        #   using last man standing mode which would be:
        #   (number of cluster nodes == <quorumd votes/>).

        # * If cman/quorum_dev_poll is not set, then assume they token/totem value
        #   set they want.
        #   Then: Do nothing

        # * If cman/quorum_dev_poll is set then make sure it equals totem/token, if not.
        #   Then: Warn that cman/quorum_dev_poll and totem/token should be the
        #   same or whatever the math is for it.

        # * If cman/quorum_dev_poll is higher than 20000ms(or 20 seconds).
        #   Then: State that an errata has been relased that addresses this
        #   issue and large values for these are no longer needed.

        # The various quorumd and quorum_dev_poll values should be based around
        # the value of token.
        #     Check if quorum_dev_poll is >= token, you're set.
        #     Check if tko*interval is less than token/2, you're set
        if (len(cca.getCmanQuorumDevPoll()) > 0):
            if (not len(cca.getTotemToken()) > 0):
                description =  "There was no <totem token/> value set. If <cman quorum_dev_poll/> is defined in cluster.conf then the "
                description += "<totem token/> value should be the same as the <cman quorum_dev_poll/>."
                urls = ["https://access.redhat.com/solutions/128083", "https://access.redhat.com/articles/216443"]
                rString += StringUtil.formatBulletString(description, urls)
            else:
                try:
                    quorum_dev_poll = int(cca.getCmanQuorumDevPoll()) # in milliseconds
                    totem_token = int(cca.getTotemToken())            # in milliseconds
                    if (distroRelease.getMajorVersion() == 6):
                        description =  "It is recommended on RHEL 6+ that the <cman quorum_dev_poll/> and <totem token/> are not manually configured in "
                        description += "the cluster.conf because they will be auto-calculated which is not done on previous versions. The only time these "
                        description += "values should be set on RHEL 6+ is when there is issues with the storage or network that prevents the cluster "
                        description += "from using the defaults that will be auto-calculated."
                        urls = ["https://access.redhat.com/solutions/128083", "https://access.redhat.com/articles/216443"]
                        rString += StringUtil.formatBulletString(description, urls)
                    # Check to verify values are correct.
                    try:
                        # Need to convert to milliseconds on interval and tko comapare
                        if (not (totem_token / 2) > ((int(quorumd.getInterval()) * int(quorumd.getTKO())) * 1000)):
                            description = "The <quorumd tko=%s> multiplied by <quorumd interval=%s> is not less than <totem token=%d> divided by 2. " %(quorumd.getInterval(), quorumd.getTKO(), totem_token)
                            description += "These values should be changed as described in the articles below."
                            urls = ["https://access.redhat.com/solutions/128083", "https://access.redhat.com/articles/216443"]
                            rString += StringUtil.formatBulletString(description, urls)
                    except ValueError:
                        pass
                    if (not quorum_dev_poll >= totem_token):
                        description = "The <cman quorum_dev_poll/> value should be equal to or higher than the <totem token/> value."
                        urls = ["https://access.redhat.com/solutions/128083", "https://access.redhat.com/articles/216443"]
                        rString += StringUtil.formatBulletString(description, urls)
                    if ((quorum_dev_poll > 22000) or (totem_token > 22000)):
                        # There is no reason(or some rule) for choosing 22000, but allows for some networks that have congestion.
                        description =  "Setting a large <totem token=%d/> value and/or <cman quorum_dev_poll=%d/> value are no longer needed in order to " %(quorum_dev_poll, totem_token)
                        description += "account for scsi timeouts. Ideally the attribute <totem token/> value should be as low a value as possible as described in "
                        description += "in the articles below. See the requirements for this feature in the articles below."
                        urls = ["https://access.redhat.com/solutions/128083", "https://access.redhat.com/articles/216443"]
                        rString += StringUtil.formatBulletString(description, urls)
                    # Not sure exactly what I was checking here. expected_votes
                    # should equal expected, maybe what I was looking to checks
                    # is if the configuration is simple qdisk configuration of
                    # (cluster node vote count + 1 vote for qdisk) or (cluster
                    # node vote count + last man standing votes from qdisk). But
                    # what if the nodes are not using 1 vote for each cluster
                    # node.
                    # Check votes, this does not take into consideration of last man standing mode.
                    #try:
                    #    if (not int(cca.getCmanExpectedVotes()) == (len(cca.getClusterNodeNames()) * 2 - 1)):
                    #        description =  "The <cman expected_votes=%d/> ideally should equal the number of cluster nodes(found: %d) multiplied by 2 minus 1. " %(int(cca.getCmanExpectedVotes()), len(cca.getClusterNodeNames()))
                    #        description += "Based on the configuration found in the cluster.conf that would be \n  (%d cluster nodes * 2 - 1) = %d. Ideally the <cman expected_votes/> " %(len(cca.getClusterNodeNames()), len(cca.getClusterNodeNames()) * 2 - 1)
                    #        description += "should be %d unless a \"last man standing\" or other special configuration is being used." %(len(cca.getClusterNodeNames()) * 2 - 1)
                    #        urls = ["https://access.redhat.com/solutions/128083", "https://access.redhat.com/articles/216443"]
                    #        rString += StringUtil.formatBulletString(description, urls)
                    #except ValueError:
                    #    message = "The corrected expected_votes could not be analyzed because of a parsing error."
                    #    logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                except ValueError:
                   description = "There was an invalid value found in the cluster.conf for either <totem/token /> and/or <cman/quorum_dev_poll />."
                   urls = ["https://access.redhat.com/solutions/128083", "https://access.redhat.com/articles/216443"]
                   rString += StringUtil.formatBulletString(description, urls)
        elif ((not len(cca.getCmanQuorumDevPoll()) > 0) and (distroRelease.getMajorVersion() == 5)):
            description =  "When using a quorum disk with RHEL 5, the <cman quorum_dev_poll/> and <totem token/> should be configured "
            description += "as stated in the following articles."
            urls = ["https://access.redhat.com/solutions/128083", "https://access.redhat.com/articles/216443"]
            rString += StringUtil.formatBulletString(description, urls)
        # ###################################################################
        # Configurations that should print a warning message, but are still
        # supported in production.
        # ###################################################################
        if ((len(quorumd.getLabel()) > 0) and (len(quorumd.getDevice()) > 0)):
            description =  "The quorumd option should not have a \"device\" and "
            description += "\"label\" configured in the /etc/cluster/cluster.conf. The label option will override the device option."
            urls = []
            rString += StringUtil.formatBulletString(description, urls)
        if (quorumd.getReboot() == "0"):
            description =  "If the quorumd option reboot is set to 0 in the /etc/cluster/cluster.conf. This option only prevents "
            description += "rebooting on loss of score. The option does not change whether qdiskd "
            description += "reboots the host as a result of hanging for too long and getting "
            description += "evicted by other nodes in the cluster."
            urls = []
            rString += StringUtil.formatBulletString(description, urls)
        if (quorumd.getAllowKill() == "0"):
            description =  "If the quorumd option allow_kill is set to 0 (disabled) in the /etc/cluster/cluster.conf. qdiskd will not instruct cman to kill "
            description += "the cluster nodes that openais or corosync think are dead cluster nodes when disabled. Cluster nodes "
            description += "are still evicted via the qdiskd which will cause a reboot to occur. By default this option "
            description += "is set to 1(enabled)."
            urls = ["https://access.redhat.com/solutions/266683"]
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
            urls = ["https://access.redhat.com/solutions/64633"]

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
        distroRelease = clusternode.getDistroRelease()
        bondingModeNumber = -1
        try:
            bondingModeNumber = int(hbNetworkMap.getBondedModeNumber())
        except ValueError:
            pass
        if (hbNetworkMap.isBondedMasterInterface() and (not hbNetworkMap.getBondedModeNumber() == "1")):
            description = ""
            # Is Bonded master and is not mode 1.
            if (hbNetworkMap.getBondedModeNumber() == "-1"):
                # Unknown bonding mode.
                description += "The bonding mode for this host could not be determined."
            elif ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() >= 6) and
                   (distroRelease.getMinorVersion() >= 6) and (bondingModeNumber > 4)):
                description += "The heartbeat network(%s) is currently using bonding mode %s(%s).\n" %(hbNetworkMap.getInterface(),
                                                                                                       hbNetworkMap.getBondedModeNumber(),
                                                                                                       hbNetworkMap.getBondedModeName())
            elif ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() >= 6) and
                  (distroRelease.getMinorVersion() in range(4,5)) and (bondingModeNumber > 2)):
                    # RHEL 6.4 or higher and not modes 0,1,2.
                description += "The heartbeat network(%s) is currently using bonding mode %s(%s).\n" %(hbNetworkMap.getInterface(),
                                                                                                       hbNetworkMap.getBondedModeNumber(),
                                                                                                       hbNetworkMap.getBondedModeName())
            elif ((distroRelease.getDistroName() == "RHEL") and (distroRelease.getMajorVersion() >= 6) and
                  (distroRelease.getMinorVersion() in range(0,3))):
                # Bonding mode detected is not mode 1 and not RHEL 6.4 or higher.
                description += "The heartbeat network(%s) is currently using bonding mode %s(%s).\n" %(hbNetworkMap.getInterface(),
                                                                                                       hbNetworkMap.getBondedModeNumber(),
                                                                                                       hbNetworkMap.getBondedModeName())
            if (len(description) > 0):
                descriptionHeader =  "The only supported bonding mode on the heartbeat network is mode 1(active-backup) on releases "
                descriptionHeader += "prior to RHEL 6.4. RHEL 6.4 supports the following bonding modes 0, 1, 2. RHEL 6.6 added support for mode 4."
                urls = ["https://access.redhat.com/solutions/27604"]
                rString += StringUtil.formatBulletString("%s %s" %(descriptionHeader, description), urls)

        """
        # DISABLING THIS CHECK TILL I REVEVALUTE IT CAUSE CURRENTLY CONFUSING.
        # ###################################################################
        # Check if heartbeat network interface is netxen or bnx2 network module
        # ###################################################################
        # 44475 | requires a firmware upgrade to the nic
        # 35299 | Fixed in RHEL 5.5.z (kernel-2.6.18-194.32.1.el5) and RHEL 5.6 (kernel-2.6.18-238.el5)
        # 46663 | Fixed in RHEL 5.7   (kernel-2.6.18-274.el5)
        netxenUrlsList = ["https://access.redhat.com/solutions/44475"]
        kernelRelease = clusternode.getUnameA().getKernelRelease()
        if (str(kernelRelease) > 0):
            # netxenUrlsList.append("https://access.redhat.com/solutions/35299")
            result = kernelRelease.compareGT("2.6.18-194.32.1.el5")
            result = kernelRelease.compareGT("2.6.18-238.el5")

            # netxenUrlsList.append("https://access.redhat.com/solutions/46663")
            result = kernelRelease.compareGT("2.6.18-274.el5")

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
        """
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
        clusterConfigString = self.__evaluateClusterGlobalConfiguration(cca).rstrip()
        transportModeString =  self.__evaluateClusterTransportMode(baseClusterNode)
        if (len(transportModeString) > 0):
            clusterConfigString += "\n%s" %(transportModeString)
        pacemakerClusterString = self.__evaluateClusterPacemakerConfiguration()
        if (len(pacemakerClusterString) > 0):
            clusterConfigString += "\n%s" %(pacemakerClusterString)

        if (len(clusterConfigString) > 0):
            clusterConfigString = clusterConfigString.rstrip()
            sectionHeader = "%s\nCluster Global Configuration Known Issues (%s)\n%s" %(self.__seperator, cca.getClusterName(), self.__seperator)
            rstring += "%s\n%s\n\n" %(sectionHeader, clusterConfigString)


        # ###################################################################
        # Check qdisk configuration:
        # ###################################################################
        quorumdConfigString = ""
        # Disabling this for now cause it cannot be accurate all the time.
        #pathToQuroumDisk = self.__cnc.getPathToQuorumDisk()
        #if (self.__isQDiskLVMDevice(pathToQuroumDisk)):
        #    description =  "The quorum disk %s cannot be an lvm device." %(pathToQuroumDisk)
        #    urls = ["https://access.redhat.com/solutions/41726"]
        #    quorumdConfigString += StringUtil.formatBulletString(description, urls)
        distroRelease = baseClusterNode.getDistroRelease()
        quorumdConfigString += self.__evaluateQuorumdConfiguration(cca, distroRelease)
        if (len(quorumdConfigString) > 0):
            sectionHeader = "%s\nQuorumd Disk Configuration Known Issues (%s)\n%s" %(self.__seperator, cca.getClusterName(), self.__seperator)
            rstring += "%s\n%s\n\n" %(sectionHeader, quorumdConfigString)

        # ###################################################################
        # Fencing evaluations
        # ###################################################################
        fencingString = self.__evaluateClusterNodesFencing(cca)
        if (len(fencingString) > 0):
            sectionHeader = "%s\nFencing Configuration Known Issues (%s)\n%s" %(self.__seperator, cca.getClusterName(), self.__seperator)
            rstring += "%s\n%s\n\n" %(sectionHeader, fencingString)
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
                urls = ["https://access.redhat.com/articles/5934",
                        "https://access.redhat.com/solutions/81123"]
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
                        urls = ["https://access.redhat.com/solutions/96543"]
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
                        urls = ["https://access.redhat.com/solutions/169913", "https://access.redhat.com/solutions/18999",
                                "https://access.redhat.com/solutions/58778"]
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
                    urls = ["https://access.redhat.com/solutions/32242"]
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
                    urls = ["https://access.redhat.com/solutions/5898"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

                # Check if scsi_reserve service is enabled with no scsi fencing device in cluster.conf
                serviceName = "scsi_reserve"
                if (not cca.isFenceDeviceAgentEnabledOnClusterNode(clusternode.getClusterNodeName(), "fence_scsi")):
                    serviceRunlevelEnabledString = self.__evaluateServiceIsEnabled(clusternode, serviceName)
                    if (len(serviceRunlevelEnabledString) > 0):
                        description =  "The service %s should be disabled since there was no fence_scsi device detected for this node." %(serviceName)
                        description += "The following runlevels have %s enabled: %s." %(serviceName, serviceRunlevelEnabledString.strip())
                        urls = ["https://access.redhat.com/solutions/42530", "https://access.redhat.com/solutions/17784"]
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
                    urls = ["https://access.redhat.com/solutions/5898"]
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
        # Return the result
        return rstring
