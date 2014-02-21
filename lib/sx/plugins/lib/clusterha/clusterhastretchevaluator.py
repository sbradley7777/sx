#!/usr/bin/env python
"""
This class will evalatuate a cluster as a stretch cluster and create a report that will
link in known issues with links to resolution.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.16
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

class ClusterHAStretchEvaluator():

    def __init__(self, cnc):
        self.__cnc = cnc

    def getClusterNodes(self):
        return self.__cnc

    # #######################################################################
    # Evaluate function
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

        for clusternode in self.__cnc.getClusterNodes():
            clusterNodeEvalString = ""
            if (not clusternode.isClusterNode()):
                continue
            # The distro release of this node
            distroRelease = clusternode.getDistroRelease()
            # The clusternode name in /etc/cluster/cluster.conf
            clusterNodeName = clusternode.getClusterNodeName()
            if (not (distroRelease.getDistroName() == "RHEL") and ((distroRelease.getMajorVersion() == 5) or (distroRelease.getMajorVersion() == 6))):
                message = "Stretch Clusters are only supported on RHEL 5 and RHEL6."
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            else:
                # ###################################################################
                # CLVMD and cmirror cannot be enabled on stretch clusters.
                # ###################################################################
                serviceName = "clvmd"
                serviceRunlevelEnabledString = ""
                for chkConfigItem in clusternode.getChkConfigList():
                    if (chkConfigItem.getName() == serviceName):
                        if(chkConfigItem.isEnabledRunlevel3()):
                            serviceRunlevelEnabledString += "3 "
                        if(chkConfigItem.isEnabledRunlevel4()):
                            serviceRunlevelEnabledString += "4 "
                        if(chkConfigItem.isEnabledRunlevel5()):
                            serviceRunlevelEnabledString += "5 "
                if (len(serviceRunlevelEnabledString) > 0):
                    description =  "The service %s should be disabled if this is cluster node is part of a stretch cluster. The service %s is not supported in stretch clusters." %(serviceName, serviceName)
                    description += "The following runlevels have %s enabled: %s." %(serviceName, serviceRunlevelEnabledString.strip())
                    urls = ["https://access.redhat.com/knowledge/solutions/163833"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)

                serviceName = "cmirror"
                serviceRunlevelEnabledString = ""
                for chkConfigItem in clusternode.getChkConfigList():
                    if (chkConfigItem.getName() == serviceName):
                        if(chkConfigItem.isEnabledRunlevel3()):
                            serviceRunlevelEnabledString += "3 "
                        if(chkConfigItem.isEnabledRunlevel4()):
                            serviceRunlevelEnabledString += "4 "
                        if(chkConfigItem.isEnabledRunlevel5()):
                            serviceRunlevelEnabledString += "5 "
                if (len(serviceRunlevelEnabledString) > 0):
                    description =  "The service %s should be disabled if this is cluster node is part of a stretch cluster. The service %s is not supported in stretch clusters." %(serviceName, serviceName)
                    description += "The following runlevels have %s enabled: %s." %(serviceName, serviceRunlevelEnabledString.strip())
                    urls = ["https://access.redhat.com/knowledge/solutions/163833"]
                    clusterNodeEvalString += StringUtil.formatBulletString(description, urls)


            # ###################################################################
            # Add newline to separate the node stanzas
            # ###################################################################
            if (len(clusterNodeEvalString) > 0):
                rstring += "%s(Cluster Node ID: %s):\n%s\n" %(clusterNodeName, clusternode.getClusterNodeID(), clusterNodeEvalString)

            # ###################################################################
        return rstring


