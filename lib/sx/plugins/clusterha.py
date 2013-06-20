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
@version   :  2.15
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
from sx.plugins.lib.clusterha.clusternodecompare import ClusternodeCompare
from sx.plugins.lib.clusterha.clusterhastorage import ClusterHAStorage

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
                                       "This plugin will analyze the configuration of the High Availability and Resilient Storage cluster from the information gathered in the sosreports.",
                                       ["Sosreport", "Sysreport"], True, True, {"isStretchCluster":"If the option is set 1 then the plugin will analyze the reports as a stretch cluster."}, pathToPluginReportDir)

        # Set the default options for the plugin
        self.setOptionValue("isStretchCluster", "0");
        # A map of all the clusters found. The key is the name of the cluster
        # and value is a ClusterNodes object.
        self.__clusterMap = {}
        # Map of the clusternodes to StorageData
        self.__storageDataMap = {}
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
        logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
        for report in reports:
            if (self.isValidReportType(report)) :
                # Verify that cluster.conf exists because we need to sort the
                # reports into the correct bin in case there are multiple
                # clusters uploaded.
                pathToClusterConfFile = report.getPathForFile("etc/cluster/cluster.conf")
                if ((not len(pathToClusterConfFile) > 0) or (not os.path.exists(pathToClusterConfFile))) :
                    message = "The cluster.conf file could not be located for this report."
                    logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                    return False
                cca = ClusterHAConfAnalyzer(pathToClusterConfFile)
                clusterName = cca.getClusterName()
                if (len(clusterName) > 0):
                    if (not self.__clusterMap.has_key(clusterName)):
                        self.__clusterMap[clusterName] = ClusterNodes()
                    result = self.__clusterMap.get(clusterName).add(report)

    def report(self) :
        """
        This function will write to report files the results of the
        cluster validation tests and report any errors to console.
        """
        if (not len(self.__clusterMap.keys()) > 0):
            message = "There were no cluster nodes found in the list of reports so no report will be generated."
            logging.getLogger(sx.MAIN_LOGGER_NAME).warn(message)
        else:
            message = "Generating report for plugin: %s" %(self.getName())
            logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
            message = "%s is generating a report for the Cluster(s) that were found." %(self.getName())
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)

            # Since we are going to run the plugin and create files in
            # the plugins report directory then we will first remove
            # all the existing files.
            self.clean()

            for clusterName in self.__clusterMap.keys():
                message = "Analyzing and writing the report for the cluster: %s" %(clusterName)
                logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
                cnc = self.__clusterMap.get(clusterName)
                self.__generateReport(cnc)

    def __generateReport(self, cnc):
        # Name of the file that will be used to write the report.
        if (not len(cnc.getClusterNodes()) > 0):
            message = "There were no cluster nodes found for this cluster."
            logging.getLogger(sx.MAIN_LOGGER_NAME).warn(message)
        else:
            baseClusterNode = cnc.getBaseClusterNode()
            if (baseClusterNode == None):
                # Should never occur since node count should be checked first.
                return
            cca = ClusterHAConfAnalyzer(baseClusterNode.getPathToClusterConf())

            # Write a summary of the cluster.conf services
            filename = "%s-services.txt" %(cca.getClusterName())
            clusteredServicesList = cca.getClusteredServices()
            clusteredServicesString = ""
            clusteredVMServicesString = ""
            regServiceCount = 0
            vmServiceCount = 0
            for clusteredService in clusteredServicesList:
                if (not clusteredService.isVirtualMachineService()):
                    sIndex = str(regServiceCount + 1)
                    if ((regServiceCount + 1) < 10):
                        sIndex = " %d" %(regServiceCount + 1)
                    clusteredServicesString += "%s. %s\n\n" %(sIndex, str(clusteredService).rstrip())
                    regServiceCount = regServiceCount + 1
                elif (clusteredService.isVirtualMachineService()):
                    sIndex = str(vmServiceCount + 1)
                    if ((vmServiceCount + 1) < 10):
                        sIndex = " %d" %(vmServiceCount + 1)
                    clusteredVMServicesString += "%s. %s\n\n" %(sIndex, str(clusteredService).rstrip())
                    vmServiceCount = vmServiceCount + 1
            if (regServiceCount > 0):
                self.writeSeperator(filename, "Clustered Services Summary");
                self.write(filename, "There was %d clustered services.\n" %(regServiceCount))
                self.write(filename, "%s\n" %(clusteredServicesString.rstrip()))

            if (vmServiceCount > 0):
                self.writeSeperator(filename, "Clustered Virtual Machine Services Summary");
                self.write(filename, "There was %d clustered virtual machine services.\n" %(vmServiceCount))
                self.write(filename, "%s\n" %(clusteredVMServicesString.rstrip()))

            # List of clusternodes in cluster.conf that do not have
            # corresponding sosreport/sysreport.
            filename = "%s-summary.txt" %(cca.getClusterName())
            missingNodesList = cnc.listClusterNodesMissingReports()
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
            result = cnc.getClusterNodesSystemSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Cluster Nodes Summary");
                self.write(filename, result.rstrip())
                self.write(filename, "")

            # Write qdisk information if it exists.
            result = cca.getQuorumdSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Cluster Quorum Disk Summary");
                self.write(filename, result.rstrip())
                self.write(filename, "")

            result = cnc.getClusterNodesPackagesInstalledSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Cluster/Cluster-Storage Packages Installed");
                self.write(filename, result.rstrip())
                self.write(filename, "")

            result = cnc.getClusterNodesNetworkSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Cluster Nodes Network Summary");
                self.write(filename, "* =   heartbeat network\n** =  bonded slave interfaces\n*** = parent of alias interface\n")
                self.write(filename, result)
                self.write(filename, "")

            clusterHAStorage = ClusterHAStorage(cnc)
            result = clusterHAStorage.getSummary()
            if (len(result) > 0):
                self.write(filename, result.rstrip())
                self.write(filename, "")

            # ###################################################################
            # Check the cluster node services summary
            # ###################################################################
            clusterHAServiceString = ""
            for clusternode in cnc.getClusterNodes():
                chkConfigClusterServiceList = clusternode.getChkConfigClusterServicesStatus()
                if (not len(chkConfigClusterServiceList) > 0):
                    # If there is no chkconfig data then skip
                    continue
                currentEnabledServices = ""
                currentDisabledServices = ""
                sortedChkConfigClusterServicesList = sorted(chkConfigClusterServiceList, key=lambda k: k.getStartOrderNumber())
                for chkConfigClusterService in sortedChkConfigClusterServicesList:
                    if ((chkConfigClusterService.getName() == "openais") or (chkConfigClusterService.getName() == "corosync")
                        or (chkConfigClusterService.getName() == "scsi_reserve")):
                        # These services are checked in evaluator if they are disabled.
                        continue
                    serviceEnabled = False
                    if (not (chkConfigClusterService.isEnabledRunlevel3() and
                        chkConfigClusterService.isEnabledRunlevel4() and
                        chkConfigClusterService.isEnabledRunlevel5())):
                        currentDisabledServices += " %s |" %(chkConfigClusterService.getName())
                    else:
                        currentEnabledServices += " %s |" %(chkConfigClusterService.getName())
                if ((len(currentEnabledServices) > 0) or (len(currentDisabledServices) > 0)):
                    clusterHAServiceString += "%s:\n  Enabled:  %s\n  Disabled: %s\n\n" %(clusternode.getClusterNodeName(), currentEnabledServices.rstrip("|"), currentDisabledServices.rstrip("|"))
                else:
                    clusterHAServiceString += "%s:\n  There was either an error finding the services used by Cluster HA or there was none installed.\n\n" %(clusternode.getClusterNodeName())
            clusterHAServiceString = clusterHAServiceString.rstrip()
            self.writeSeperator(filename, "Cluster Services Summary");
            header =  "The following lists the clustered services that were found runlevel start(enabled) state. Services\nin enabled list have the service enabled in runlevels 3,4,5.\n"
            header += "-  https://access.redhat.com/knowledge/solutions/5898 \n"
            self.write(filename, header)
            if (len(clusterHAServiceString) > 0):
                self.write(filename, "%s\n" %(clusterHAServiceString))
            else:
                self.write(filename, "There was either an error finding the services used by Cluster HA or there was none installed.")

            # ###################################################################
            # Verify the cluster node configuration
            # ###################################################################
            filenameCE = "%s-evaluator.txt" %(cca.getClusterName())
            clusterEvaluator = ClusterEvaluator(cnc)
            evaluatorResult = clusterEvaluator.evaluate()
            if (len(evaluatorResult) > 0):
                if (len(missingNodesList) > 0):
                    self.write(filenameCE, "%s\n\n" %(missingNodesMessage))
                self.writeSeperator(filenameCE, "Known Issues with Cluster");
                self.write(filenameCE, "NOTE: The known issues below may or may not be related to solving")
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
                clusterHAStretchEvaluator = ClusterHAStretchEvaluator(cnc)
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

            # ###################################################################
            # Verify the cluster node configuration
            # ###################################################################
            filenameCE = "%s-clusternode_compare.txt" %(cca.getClusterName())
            clusternodeCompare = ClusternodeCompare(cnc)
            compareResult = clusternodeCompare.compare()
            if (len(compareResult) > 0):
                if (len(missingNodesList) > 0):
                    self.write(filenameCE, "%s\n\n" %(missingNodesMessage))
                self.writeSeperator(filenameCE, "Clusternode Comparison");
                self.write(filenameCE, "The following section will show the difference between the reports when a value in a file is")
                self.write(filenameCE, "compared against all the reports. The section will list the reports with similar values")
                self.write(filenameCE, "and ones that are different then the similar values. The similar values is the highest number")
                self.write(filenameCE, "of reports with the same value.\n")

                self.write(filenameCE, compareResult.rstrip())
                self.write(filenameCE, "")
