#!/usr/bin/env python
"""
This is a plugin for rhnsatellite debug that will perform various
validation tests.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.15
@copyright :  GPLv2
"""
import logging
import os

import sx
import sx.plugins
from sx.logwriter import LogWriter
from sx.reports.satellitedebug import Satellitedebug

class Satellitedebug(sx.plugins.PluginBase):
    """
    This is a plugin for rhnsatellite debug that will perform various
    validation tests.
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
        sx.plugins.PluginBase.__init__(self, "SatelliteDebug",
                                       "This plugin verifies an rhn satellite server debug file that is created.",
                                       ["Satellitedebug"], False, True, {},
                                       pathToPluginReportDir)

        self.__rhnSatDebugReports = []

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
                timestamp = report.getDataFromFile("timestamp")
                if (timestamp == None) :
                    timestamp = [""]
                rsdr = RHNSatelliteDebugReport(timestamp[0].rstrip())
                self.__rhnSatDebugReports.append(rsdr)
                rsdr.setInstalledSatellitePackages(report.getPathForFile("rpm-manifest"))

    def report(self) :
        """
        This function will report about the information gather.
        """
        message = "Generating report for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
        if(len(self.__rhnSatDebugReports) > 0):
            # Since we are going to run the plugin and create files in
            # the plugins report directory then we will first remove
            # all the existing files.
            self.clean()

        for report in self.__rhnSatDebugReports:
            # Send to console the timestamp data
            message = "The timestamp for this rhnsatellite debug: %s" %(report.getTimestamp())
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)

            # create report files
            installedSatellitePackagesString = ""
            for package in report.getInstalledSatellitePackages():
                if "rhns-server" in package:
                    message = "The version of RHN Satelliete Server: %s" %(package.split()[0])
                    logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
                installedSatellitePackagesString += package
            if (len(installedSatellitePackagesString) > 0):
                # We will not append the data because we are only writing once.
                self.write("installedPackages.txt", installedSatellitePackagesString, False)

class RHNSatelliteDebugReport:
    def __init__(self, timestamp) :
        """
        @param timestamp: The timestamp of the report.
        @type timestamp: String
        """
        self.__timestamp = timestamp
        self.__installedSatellitePackages = []

    def setInstalledSatellitePackages(self, pathToRpmManifest):
        """
        Function sets the path to the rpm-manifest file.

        @param pathToRpmManifest: The path to the rpm manifest file.
        @type pathToRpmManifest: String
        """
        print pathToRpmManifest
        try:
            fin = open(pathToRpmManifest, "r")
            lines = fin.readlines()
            fin.close()
        except (IOError, os.error):
            message = "An i/o error occured in reading the file getting the file: \n\t%s" %(pathToRpmManifest)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return []
        for package in lines:
            if "rhns" in package:
                self.__installedSatellitePackages.append(package)
            elif "rhnmd" in package:
                self.__installedSatellitePackages.append(package)

    def getTimestamp(self) :
        """
        Returns the timestamp.

        @return: Returns the timestamp.
        @rtype: String
        """
        return self.__timestamp

    def getInstalledSatellitePackages(self) :
        """
        Returns the installed satellite packages.

        @return: Returns the installed satellite packages.
        @rtype: Array
        """
        return self.__installedSatellitePackages
