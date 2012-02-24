#!/usr/bin/env python
"""
This class will run various validation tests and gather information
about Report Objects that are cluster nodes.

TODO: For now I will leave plugin called "cluster" instead of
"clusterha" because it will break scripts. Something that can be
changed at a latter date.

TODO: Currently either "cluster or clusterha" will call plugin because
of the fuction basePlugin.__init__.py.isNamed(str). This should be
fixed latter for just True on the plugin name and not class name.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.09
@copyright :  GPLv2
"""
import string
import logging
import os
import re

import sx
import sx.plugins
from sx.logwriter import LogWriter

from sx.plugins.lib.clusterha.clusterhaconfanalyzer import ClusterHAConfAnalyzer
from sx.plugins.lib.clusterha.clusternodes import ClusterNodes
from sx.plugins.lib.clusterha.clusternode import ClusterNode
from sx.plugins.lib.clusterha.clusterevaluator import ClusterEvaluator
from sx.plugins.lib.clusterha.clusterhastretchevaluator import ClusterHAStretchEvaluator

from sx.reports.sosreport import Sosreport
from sx.reports.sysreport import Sysreport

class Clusterha(sx.plugins.PluginBase):
    """
    This class will run various validation tests and gather
    information about Report Objects that are cluster nodes.
    """
    def __init__(self, pathToPluginReportDir="") :
        """
        This init takes the root path to where the reports will be
        written. The parent class will then create the correct
        directory structure for the plugin.

        @param pathToPluginReportDir: This is the root path to where
        the report files will be written.
        @type pathToPluginReportDir: String
        """
        sx.plugins.PluginBase.__init__(self, "Cluster",
                                       "This plugin will verify configuartion of the cluster(high availability) and analyze cluster(high availability) information gathered from sosreports/sysreports.",
                                       ["Sosreport", "Sysreport"], True, True, {"isStretchCluster":"If the option is set 1 then the plugin will analyze the reports as a stretch cluster."}, pathToPluginReportDir)

        # Set the default options for the plugin
        self.setOptionValue("isStretchCluster", "0");
        self.__cnc = ClusterNodes()

    # #######################################################################
    # Functions that should be overwritten in the plugin
    # #######################################################################
    def setup(self, reports) :
        """
        This function will setup data structure to hold any data/path
        to files that are needed to use in this plugin.

        @param reports: This is the list of Report Objects.
        @type reports: Array
        """
        message = "Running setup for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).log(LogWriter.STATUS_LEVEL, message)
        for report in reports:
            if (self.isValidReportType(report)) :
                self.__cnc.add(report)

    def report(self) :
        """
        This function will write to report files the results of the
        cluster validation tests and report any errors to console.
        """
        if (not len(self.__cnc.getClusterNodes()) > 0):
            message = "There were no cluster nodes found in the list of reports so no report will be generated."
            logging.getLogger(sx.MAIN_LOGGER_NAME).warn(message)
        else:
            message = "Generating report for plugin: %s" %(self.getName())
            logging.getLogger(sx.MAIN_LOGGER_NAME).log(LogWriter.STATUS_LEVEL, message)
            message = "%s is generating a report of various information about the nodes in the cluster." %(self.getName())
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)

            # Since we are going to run the plugin and create files in
            # the plugins report directory then we will first remove
            # all the existing files.
            self.clean()

            # Name of the file that will be used to write the report.
            baseClusterNode = self.__cnc.getBaseClusterNode()
            if (baseClusterNode == None):
                # Should never occur since node count should be checked first.
                return
            cca = ClusterHAConfAnalyzer(baseClusterNode.getPathToClusterConf())

            # Write a summary of the cluster.conf services
            filename = "%s-services.txt" %(cca.getClusterName())
            clusteredServicesList = cca.getClusteredServices()
            clusteredServicesString = ""
            index = 1
            for clusteredService in clusteredServicesList:
                sIndex = str(index)
                if (index < 10):
                    sIndex = " %d" %(index)
                clusteredServicesString += "%s. %s\n" %(sIndex, str(clusteredService))
                index = index + 1
            if (len(clusteredServicesString) > 0):
                self.writeSeperator(filename, "Cluster Services Summary");
                self.write(filename, "There was %d clustered services.\n" %(len(clusteredServicesList)))
                self.write(filename, "%s\n" %(clusteredServicesString))

            # List of clusternodes in cluster.conf that do not have
            # corresponding sosreport/sysreport.
            filename = "%s-summary.txt" %(cca.getClusterName())
            missingNodesList = self.__cnc.listClusterNodesMissingReports()
            missingNodesMessage = ""
            if (len(missingNodesList) > 0):
                missingNodesMessage = "The following cluster nodes could not be matched to a report that was analyzed:"
                for nodeName in missingNodesList:
                    missingNodesMessage +="\n\t  %s" %(nodeName)
                logging.getLogger(sx.MAIN_LOGGER_NAME).warn(missingNodesMessage)
                self.write(filename, "%s\n" %(missingNodesMessage))

            # ###################################################################
            # Summary of each node in collection
            # ###################################################################
            result = self.__cnc.getClusterNodesSystemSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Cluster Nodes Summary");
                self.write(filename, result.rstrip())
                self.write(filename, "")
            result = self.__cnc.getClusterNodesPackagesInstalledSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Cluster/Cluster-Storage Packages Installed");
                self.write(filename, result.rstrip())
                self.write(filename, "")
            result = self.__cnc.getClusterNodesNetworkSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Cluster Nodes Network Summary");
                self.write(filename, "* =   heartbeat network\n** =  bonded slave interfaces\n*** = parent of alias interface\n")
                self.write(filename, result)
                self.write(filename, "")
            result = self.__cnc.getClusterStorageSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Cluster Storage Summary for GFS/GFS2");
                self.write(filename, result)
                self.write(filename, "")

            # ###################################################################
            # Check the cluster node services summary
            # ###################################################################
            self.writeSeperator(filename, "Cluster Services Summary");
            self.write(filename, "NOTE: The state(Enabled/Disabled) of each service can vary with each")
            self.write(filename, "      cluster, since some configurations do not need all services.")
            self.write(filename, "      The following articles explains the cluster services:")
            self.write(filename, "      -  https://access.redhat.com/knowledge/solutions/5898 \n")
            self.write(filename, "NOTE: The following services are required to be disabled because")
            self.write(filename, "      the service cman will start and stop these services:")
            self.write(filename, "      RHEL 5: openais")
            self.write(filename, "      RHEL 6: corosync\n")

            for clusternode in self.__cnc.getClusterNodes():
                chkConfigClusterServiceList = clusternode.getChkConfigClusterServicesStatus()
                if (not len(chkConfigClusterServiceList) > 0):
                    # If there is no chkconfig data then skip
                    continue
                self.write(filename, "%s:" %(clusternode.getHostname()))

                sortedChkConfigClusterServicesList = sorted(chkConfigClusterServiceList, key=lambda k: k.getStartOrderNumber())
                for chkConfigClusterService in sortedChkConfigClusterServicesList:
                    serviceEnabled = False
                    if (chkConfigClusterService.isEnabledRunlevel3() and
                        chkConfigClusterService.isEnabledRunlevel4() and
                        chkConfigClusterService.isEnabledRunlevel5()):
                        serviceEnabled = True
                    message = "Testing if the service \"%s\" is enabled for runlevels 3-5."%(chkConfigClusterService.getName())
                    self.writeEnabledResult(filename, message.rstrip(), serviceEnabled)

                # Add newline to separate the node stanzas
                self.write(filename, "")
            # ###################################################################
            # Verify the cluster node configuration
            # ###################################################################
            filenameCE = "%s-evaluator.txt" %(cca.getClusterName())
            clusterEvaluator = ClusterEvaluator(self.__cnc)
            evaluatorResult = clusterEvaluator.evaluate()
            if (len(evaluatorResult) > 0):
                if (len(missingNodesList) > 0):
                    self.write(filenameCE, "%s\n\n" %(missingNodesMessage))
                self.writeSeperator(filenameCE, "Known Issues with Cluster");
                self.write(filenameCE, "NOTE: The known issues below may or may not be releated to solving")
                self.write(filenameCE, "      the current issue or preventing a issue. These are meant to")
                self.write(filenameCE, "      be a guide in making sure that the cluster is happy and")
                self.write(filenameCE, "      healthy all the time. Please use report as a guide in")
                self.write(filenameCE, "      reviewing the cluster.\n")
                self.write(filenameCE, evaluatorResult.rstrip())
                self.write(filenameCE, "")

            # ###################################################################
            # Evaluate the reports as stretch cluster if that option is enabled.
            # ###################################################################
            isStretchCluster = self.getOptionValue("isStretchCluster")
            if (not isStretchCluster == "0"):
                filenameCE = "%s-stretch_evaluator.txt" %(cca.getClusterName())
                clusterHAStretchEvaluator = ClusterHAStretchEvaluator(self.__cnc)
                evaluatorResult = clusterHAStretchEvaluator.evaluate()
                if (len(evaluatorResult) > 0):
                    if (len(missingNodesList) > 0):
                        self.write(filenameCE, "%s\n\n" %(missingNodesMessage))
                    self.writeSeperator(filenameCE, "Known Issues with Stretch Cluster");
                    self.write(filenameCE, "NOTE: The known issues below may or may not be releated to solving")
                    self.write(filenameCE, "      the current issue or preventing a issue. These are meant to")
                    self.write(filenameCE, "      be a guide in making sure that the cluster is happy and")
                    self.write(filenameCE, "      healthy all the time. Please use report as a guide in")
                    self.write(filenameCE, "      reviewing the cluster.\n")
                    self.write(filenameCE, evaluatorResult.rstrip())
                    self.write(filenameCE, "")
