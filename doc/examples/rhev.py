#!/usr/bin/env python
"""
This is a basic report for rhev.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.02
@copyright :  GPLv2
"""
import logging
import os.path

import sx
import sx.plugins
from sx.logwriter import LogWriter

class Rhev(sx.plugins.PluginBase):
    """
    This is that will do a report on RHEV log collector.
    """
    def __init__(self, pathToPluginReportDir=""):
        """
        This init takes the root path to where the reports will be
        written. The parent class will then create the correct
        directory structure for the plugin.

        @param pathToPluginReportDir: This is the root path to where
        the report files will be written.
        @type pathToPluginReportDir: String
        """
        sx.plugins.PluginBase.__init__(self, "RHEV",
                                       "This plugin will run on report on RHEV log collector report files.",
                                       ["Rhevlogcollector", "sosreport", "sysreport"], True, True, {},
                                       pathToPluginReportDir)

        self.__psDataMap = {}
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
            if ((self.isValidReportType(report))  and
                ((report.getName().lower() == "sosreport") or (report.getName().lower() == "sysreport"))):
                psData = report.getDataFromFile("ps")
                if (psData == None):
                    psData = report.getDataFromFile("sos_commands/process/ps_alxwww")
                if (not psData == None):
                    self.__psDataMap[report.getHostname()] = psData

    def action(self) :
        """
        Does the action for rhev log collector report.
        """
        message = "Performing action for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)

        if (len(self.__psDataMap.keys()) > 0):
            # Since we are going to run the plugin and create files in
            # the plugins report directory then we will first remove
            # all the existing files.
            self.clean()

        summaryFilename = "summary.txt"
        for key in self.__psDataMap.keys():
            psData = self.__psDataMap.get(key)
            for line in psData:
                if (line.find("/usr/libexec/vdsm/spmprotect.sh") >= 0):
                    # If there is more than one spm server found then that is problem.
                    dataout = "%s is a SPM server." %(key)
                    self.write(summaryFilename, dataout)


