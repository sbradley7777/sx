#!/usr/bin/env python
"""
A class that can run analyze the storage aspect of a sosreport.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""
import sys
import os
import os.path
import logging

import sx
import sx.plugins
from sx.logwriter import LogWriter
from sx.reports.sosreport import Sosreport
from sx.reports.sysreport import Sysreport
from sx.tools import StringUtil
from sx.plugins.lib.storage import StorageData
from sx.plugins.lib.storage import StorageDataGenerator
from sx.plugins.lib.storage.storageevaluator import StorageEvaluator

from sx.analysisreport import AnalysisReport
from sx.analysisreport import ARSection
from sx.analysisreport import ARSectionItem
class Storage(sx.plugins.PluginBase):
    """
    A class that can run analyze the storage aspect of a sosreport.
    """
    def __init__(self, pathToPluginReportDir="") :
        """
        This init takes the root path to where the reports will be
        written. The parent class will then create the correct
        directory structure for the plugin.

        This is going to be a sosreport only plugin. There is to many
        dependencies for sos_commands/* files.

        @param pathToPluginReportDir: This is the root path to where
        the report files will be written.
        @type pathToPluginReportDir: String
        """
        sx.plugins.PluginBase.__init__(self, "Storage",
                                       "This plugin analyzes the storage data colleted from sosreports.",
                                       ["Sosreport"], True, True, {}, pathToPluginReportDir)

        # This will contain a list of StorageData objects that
        # contains information found in sosreports.
        self.__listOfStorageData = []

    # ###########################################################################
    # Overwriting function of parent
    # ###########################################################################
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
            message = "Getting the files for the report for report with  hostname of: %s." %(report.getHostname())
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            if (self.isValidReportType(report)) :
                storageData = StorageDataGenerator().generate(report)
                if (not storageData == None):
                    self.__listOfStorageData.append(storageData)

    def report(self) :
        """
        This function will write the data that was analyzed to a file.
        """
        message = "Generating report for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)

        if (len(self.__listOfStorageData) > 0):
            # Since we are going to run the plugin and create files in
            # the plugins report directory then we will first remove
            # all the existing files.
            self.clean()
        stringUtil = StringUtil()
        for storageData in self.__listOfStorageData:
            message = "Writing the storage report for: %s." %(storageData.getHostname())
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)

            # could be a problem if they are all using localhost.
            ar = AnalysisReport("storage_summary-%s" %(storageData.getHostname()), "Storage Summary")
            self.addAnalysisReport(ar)
            arSectionSystemSummary = ARSection("storage-system_summary", "System Summary")
            ar.add(arSectionSystemSummary)
            arSectionSystemSummary.add(ARSectionItem(storageData.getHostname(), storageData.getSummary()))

            # The block device tree has some of the information that
            # is needed to report on.
            bdt = storageData.getBlockDeviceTree()

            # Get all the mounted filesystems.
            mountedFSList = bdt.getFilesysMountList()
            if (len(mountedFSList) > 0):
                fsTable = []

                for fs in mountedFSList:
                    fsTable.append([fs.getDeviceName(), fs.getMountPoint(),
                                    fs.getFSType(), fs.getFSAttributes(),
                                    fs.getMountOptions()])
                tableHeader = ["device", "mount_point", "fs_type", "fs_attributes", "fs_options"]
                arSectionMountedFS = ARSection("storage-mounted_fs", "Mounted Filesystems")
                ar.add(arSectionMountedFS)
                arSectionMountedFS.add(ARSectionItem(storageData.getHostname(), stringUtil.toTableString(fsTable, tableHeader)))

            # Write out any multipath data
            blockDeviceMap = bdt.generateDMBlockDeviceMap()
            multipathMap = bdt.getTargetTypeMap(blockDeviceMap, "multipath")
            if (len(multipathMap.keys()) > 0):
                multipathSummary = ""
                for key in multipathMap.keys():
                    multipathSummary += "%s\n" %(str(multipathMap.get(key)).strip())
                arSectionMultipathSummary = ARSection("storage-multipath_summary", "Multipath Summary")
                ar.add(arSectionMultipathSummary)
                arSectionMultipathSummary.add(ARSectionItem(storageData.getHostname(), multipathSummary.strip().rstrip()))

            # ###################################################################
            # Run the evaluator to look for know issues
            # ###################################################################
            storageEvaluator = StorageEvaluator(storageData)
            rstring = storageEvaluator.evaluate()
            if (len(rstring) > 0):
                arSectionKnownIssues = ARSection("storage-known_issues", "Known Issues with Storage")
                ar.add(arSectionKnownIssues)
                arSectionKnownIssues.add(ARSectionItem(storageData.getHostname(), rstring))

            # ###################################################################
            # Create the blockDeviceTree file
            # ###################################################################
            blockDeviceTreeFilename = "%s-block_device_tree.txt" %(storageData.getHostname())
            blockDeviceTreeSummary = bdt.getSummary()
            if (len(blockDeviceTreeSummary) > 0):
                arBDT = AnalysisReport("storage_block_device_tree-%s" %(storageData.getHostname()), "Block Device Tree")
                self.addAnalysisReport(arBDT)
                arSectionBDT = ARSection("storage_block_device_tree-block_device_tree_summary", "Block Device Tree Summary")
                arBDT.add(arSectionBDT)
                arSectionBDT.add(ARSectionItem(storageData.getHostname(), blockDeviceTreeSummary))
                self.write("%s.txt" %(arBDT.getName()), "%s\n" %(str(arBDT)))
            # Wrtite the output to a file.
            self.write("%s.txt" %(ar.getName()), "%s\n" %(str(ar)))
