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

            # Write a summary of the machine
            filenameSummary = "%s-summary.txt" %(storageData.getHostname())
            self.writeSeperator(filenameSummary, "System Summary", False)
            self.write(filenameSummary, storageData.getSummary())
            self.write(filenameSummary, "")

            # The block device tree has some of the information that
            # is needed to report on.
            bdt = storageData.getBlockDeviceTree()

            # Write all the mounts on the machine
            mountedFSList = bdt.getFilesysMountList()
            if (len(mountedFSList) > 0):
                self.writeSeperator(filenameSummary, "Mounted Filesystems")
                fsTable = []

                for fs in mountedFSList:
                    fsTable.append([fs.getDeviceName(), fs.getMountPoint(),
                                    fs.getFSType(), fs.getFSAttributes(),
                                    fs.getMountOptions()])
                tableHeader = ["device", "mount_point", "fs_type", "fs_attributes", "fs_options"]
                self.write(filenameSummary, stringUtil.toTableString(fsTable, tableHeader))
                self.write(filenameSummary, "")

            # Write out any multipath data
            blockDeviceMap = bdt.generateDMBlockDeviceMap()
            multipathMap = bdt.getTargetTypeMap(blockDeviceMap, "multipath")
            if (len(multipathMap.keys()) > 0):
                self.writeSeperator(filenameSummary, "Multipath Summary", True)
                for key in multipathMap.keys():
                    self.write(filenameSummary, "%s" %(str(multipathMap.get(key)).strip()))
                self.write(filenameSummary, "")

            # ###################################################################
            # Run the evaluator to look for know issues
            # ###################################################################
            storageEvaluator = StorageEvaluator(storageData)
            rstring = storageEvaluator.evaluate()
            if (len(rstring) > 0):
                self.writeSeperator(filenameSummary, "Known Issues with Storage")
                self.write(filenameSummary, rstring)

            # ###################################################################
            # Create the blockDeviceTree file
            # ###################################################################
            blockDeviceTreeFilename = "%s-block_device_tree.txt" %(storageData.getHostname())
            blockDeviceTreeSummary = bdt.getSummary()
            if (len(blockDeviceTreeSummary) > 0):
                self.writeSeperator(blockDeviceTreeFilename, "Block Device Tree  Summary", False)
                self.write(blockDeviceTreeFilename, blockDeviceTreeSummary)
