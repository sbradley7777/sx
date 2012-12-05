#!/usr/bin/env python
"""
This class is a container for rhev log collector report object.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.13
@copyright :  GPLv2
"""
import os.path
import re
import logging

import sx
from sx.reports import Report

class Rhevlogcollector(Report) :
    """
    This class is a container for Rhevlogcollector report object.

    @cvar TYPE_DETECTION_FILE: This is a path to file that can
    uniquely indentify the report object.
    @type TYPE_DETECTION_FILE: String
    @cvar REPORT_NAME: The name of the report.
    @type REPORT_NAME: String
    """
    TYPE_DETECTION_FILE = "RhevManager.exe.config"
    REPORT_NAME = "rhev log collector"
    def __init__(self) :
        sx.reports.Report.__init__(self,
                                   Rhevlogcollector.REPORT_NAME,
                                   "A container that handles the RHEV log collector")
        self.__hostname = "unknown_hostname"

    def includesOtherReports(self):
        """
        By default it will return False. If the other report contains
        other report types then set to True. The reason is that if
        True we can add the reports within the report to extraction
        process.

        @return: Returns True if there are other report types within
        this report that should be extracted.
        @rtype: Boolean
        """
        return True

    def getHostname(self):
        return self.__hostname

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
        # Find the strings that '<add baseAddress="net.tcp://localhost:8006/backend" />' in the file RhevManager.exe.config
        fileContents = extractor.getDataFromFile(Rhevlogcollector.TYPE_DETECTION_FILE)
        # Do the regex to find that string, there might be more than one so just grab the first one.
        if (len(fileContents) > 0):
            #regex = ".*%s%s%s.*" %("<add baseAddress=\"net.tcp://", "localhost", ":8006/backend\"")
            #regex = ".*%s%s%s.*" %("<add baseAddress=\"net.tcp://", "(?P<hostname>localhost)", ":8006/backend\"")
            regex = ".*%s%s%s.*" %("<add baseAddress=\"net.tcp://", "(?P<hostname>\w+)", ":8006/backend\"")
            rem = re.compile(regex)
            for line in fileContents:
                mo = rem.match(line)
                if mo:
                    self.__hostname = mo.group("hostname").strip()
                    break
        # Now call the parent method
        sx.reports.Report.extract(self, extractor, os.path.join(extractDir, "%s-rhevlogcollector" % (self.__hostname)))
        if (os.path.exists(os.path.join(self.getPathToExtractedReport(), Rhevlogcollector.TYPE_DETECTION_FILE))):
            return True
        return False

