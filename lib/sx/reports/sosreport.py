#!/usr/bin/env python
"""
This file contains various containers for working with
sosreports/sysreports reports.

This file contains the container for sosreport report object.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.08
@copyright :  GPLv2
"""
import string
import os.path
import logging
import re

import sx
from sx.reports import Report
from sx.extractors.tarextractor import Tarextractor

class Sosreport(sx.reports.Report) :
    """
    This class is a container for sosreport report object.

    @cvar TYPE_DETECTION_FILE: This is a path to file that can
    uniquely indentify the report object.
    @type TYPE_DETECTION_FILE: String
    @cvar REPORT_NAME: The name of the report.
    @type REPORT_NAME: String
    """
    TYPE_DETECTION_FILE = "sos_logs/sos.log"
    REPORT_NAME = "sosreport"
    def __init__(self) :
        sx.reports.Report.__init__(self,
                                   Sosreport.REPORT_NAME,
                                   "A container for sosreport files")
        self.__hostname = ""

    def getUname(self) :
        """
        This function will return a string of the "uname -a" data.

        @return: Returns a string of the "uname -a" data.
        @rtype String
        """
        unameAData = self.getDataFromFile("sos_commands/kernel/uname_-a")
        if (unameAData == None) :
            return ""
        return unameAData[0]

    def getUptime(self) :
        """
        This function will return a string of the "uptime" data.

        @return: Returns a string of the "uptime" data.
        @rtype String
        """
        uptime = self.getDataFromFile("sos_commands/general/uptime")
        if (uptime == None) :
            uptime = self.getDataFromFile("uptime")
        if (uptime == None) :
            return ""
        elif (len(uptime) > 0):
            return uptime[0].strip()
        return ""

    def getArch(self) :
        """
        This function will return the arch for the report.

        @return: Returns the arch for the report.
        @rtype String
        """
        unameAData = self.getUname()
        regexArch = "(?P<arch>noarch|i386|i586|i686|ia64|ppc|s390|s390x|x86_64)"
        remArch = re.compile(regexArch, re.IGNORECASE)
        moArch = remArch.search(unameAData)
        if moArch:
            return moArch.group("arch")
        return ""

    def getHostname(self) :
        """
        This function will return a string that is the hostname from the
        "uname -a" data.

        @return: Returns a string that is the hostname from the "uname
        -a" data.
        @rtype String
        """
        if (not len(self.__hostname) > 0):
            # If hostname is not set or need from previous extracted report
            unameAData = self.getUname()
            if (not len(unameAData) > 0) :
                # If there is no unameData then try searching hostname
                # file
                hostnameData = self.getDataFromFile("sos_commands/general/hostname")
                if (hostnameData == None) :
                    self.__hostname = "unknown_hostname"
                elif(not len(hostnameData) > 0):
                    self.__hostname = "unknown_hostname"
                else:
                    self.__hostname = hostnameData[0].strip()
            else:
                usplit = unameAData.split()
                if (len(usplit) >= 1):
                    self.__hostname = usplit[1]
                else:
                    self.__hostname = "unknown_hostname"
        return self.__hostname

    def getInstalledRPMSData(self) :
        """
        Returns the data from the file that contains the list of
        installed rpms.

        @returns: Returns the data from the file that contains the
        list of installed rpms.
        @rtype: Array
        """
        pathToInstalledRPMSList = ["sos_commands/rpm/rpm_-qa_--qf_NAME_-_VERSION_-_RELEASE_-_ARCH_INSTALLTIME_date_.b",
                                   "sos_commands/rpm/rpm_-qa_--qf_NAME_-_VERSION_-_RELEASE_._ARCH_INSTALLTIME_date_.b",
                                   "sos_commands/rpm/rpm_-qa_--qf_NAME_-_VERSION_-_RELEASE_-_ARCH" ,
                                   "installed-rpms"]
        installedRPMSData = []
        for pathToInstalledRPMS in pathToInstalledRPMSList:
            installedRPMSData = self.getDataFromFile(pathToInstalledRPMS)
            if (installedRPMSData == None):
                installedRPMSData = []
                continue
            elif (len(installedRPMSData) > 0):
                break;
        return installedRPMSData

    def extract(self, extractor, extractDir):
        """
        This function will extract the report to the extract
        dir.

        This function overrides the parent function. The reason is
        that a new extractDir will be created. Then the parent extract
        function will be called.

        @return: Returns True if there was no fatal errors. TarBall
        errors are ignored because they should not be fatal, if they
        are the child should catch the errors since dir will not
        exist. If there are fatal errors, then False is returned.
        @rtype: boolean

        @param extractor:
        @type extractor: Extractor
        @param extractDir: The full path to directory for extraction.
        @type extractDir: String
        """
        fileContents = extractor.getDataFromFile("/sos_commands/kernel/uname_-a")
        if (len(fileContents) > 0):
            self.__hostname = string.strip(string.split(fileContents[0])[1])
        else:
            fileContents = extractor.getDataFromFile("sos_commands/general/hostname")
            if (len(fileContents) > 0):
                self.__hostname = string.strip(fileContents[0])
            else:
                self.__hostname = "unknown_hostname"
        # Now call the parent function to finish the extraction
        sx.reports.Report.extract(self, extractor, os.path.join(extractDir, self.__hostname))
        if (os.path.exists(os.path.join(self.getPathToExtractedReport(),
                                        Sosreport.TYPE_DETECTION_FILE))):
            return True
        return False







