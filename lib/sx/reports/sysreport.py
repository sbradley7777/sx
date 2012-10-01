#!/usr/bin/env python
"""
This class is a container for sysreport report object.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.12
@copyright :  GPLv2
"""
import string
import os.path
import logging
import re

import sx
from sx.reports import Report
from sx.extractors.tarextractor import Tarextractor

class Sysreport(sx.reports.Report) :
    """
    This class is a container for sysreport report object. This is a
    child class of the SReport object that contains various functions
    that sosreport/sysreport use.

    @cvar TYPE_DETECTION_FILE: This is a path to file that can
    uniquely indentify the report object.
    @type TYPE_DETECTION_FILE: String
    @cvar REPORT_NAME: The name of the report.
    @type REPORT_NAME: String
    """
    TYPE_DETECTION_FILE = "sysreport.log"
    REPORT_NAME = "sysreport"
    def __init__(self) :
        sx.reports.Report.__init__(self,
                                   Sysreport.REPORT_NAME,
                                   "A container for sysreport files")
        self.__hostname = ""

    # ##########################################################################
    # Helper functions
    # ##########################################################################

    def getDate(self):
        """
        This function will return a string for the date which is when the report
        was generated.

        @return: This function will return a string for the date which is when
        the report was generated.
        @rtype: String
        """
        dateData = self.getDataFromFile("date")
        # Return empty string if data object was not found.
        date = ""
        if (not dateData == None):
            if (len(dateData) > 0):
                date = dateData[0].rstrip()
        return date

    def getUname(self) :
        """
        This function will return a string of the "uname -a" data.

        @return: Returns a string of the "uname -a" data.
        @rtype String
        """
        unameData = self.getDataFromFile("uname")
        if (unameData == None) :
            return ""
        return unameData[1].strip()

    def getUptime(self) :
        """
        This function will return a string of the "uptime" data.

        @return: Returns a string of the "uptime" data.
        @rtype String
        """
        uptime = self.getDataFromFile("uptime")
        if (uptime == None) :
            return ""
        elif (len(uptime) > 1):
            return uptime[1].strip()
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
                self.__hostname = "unknown_hostname"
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
        return self.getDataFromFile("installed-rpms")

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
        fileContents = extractor.getDataFromFile("uname")
        if (len(fileContents) > 1):
            self.__hostname = string.strip(string.split(fileContents[1])[1])
        else:
            self.__hostname = "unknown_hostname"
        # Now call the parent function to finish the extraction
        sx.reports.Report.extract(self, extractor, os.path.join(extractDir, self.__hostname))
        if (os.path.exists(os.path.join(self.getPathToExtractedReport(),
                                        Sysreport.TYPE_DETECTION_FILE))):
            return True
        return False

