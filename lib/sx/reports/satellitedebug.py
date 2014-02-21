#!/usr/bin/env python
"""
This class is a container for rhnsatellite-debug report object.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.16
@copyright :  GPLv2
"""
import os.path
import re
import logging

import sx
from sx.reports import Report

class Satellitedebug(Report) :
    """
    This class is a container for rhnsatellite-debug report object.

    @cvar TYPE_DETECTION_FILE: This is a path to file that can
    uniquely indentify the report object.
    @type TYPE_DETECTION_FILE: String
    @cvar REPORT_NAME: The name of the report.
    @type REPORT_NAME: String
    """
    TYPE_DETECTION_FILE = "ssl-build/RHN-ORG-TRUSTED-SSL-CERT"
    REPORT_NAME = "satellite debug"
    def __init__(self) :
        sx.reports.Report.__init__(self,
                                   Satellitedebug.REPORT_NAME,
                                   "A container that handles satellite debug files",
                                   3)
        self.__hostname = "unknown_hostname"

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
        # Find the file that will be used to get the hostname: ssl-build/RHN-ORG-TRUSTED-SSL-CERT
        data = extractor.list()
        pathToFile = ""
        if (len(data) > 0) :
            regex = "(.*%s.*)" %(Satellitedebug.TYPE_DETECTION_FILE)
            rem = re.compile(regex)
            for line in data:
                mo = rem.match(line)
                if mo:
                    pathToFile = line
                    break
        # We just want the following: satellite-debug-16690/satellite-debug/ssl-build/RHN-ORG-TRUSTED-SSL-CERT
        splitCount = (len(pathToFile.split("/")) - 4)
        pathToFile = pathToFile.split("/", splitCount)[1]
        # Use regular expression to get the hostname from the file if there is valid path
        # ex: Issuer: C=US, ST=nc, L=raleigh, O=redhat, OU=dhcp243-31.rdu.redhat.com, CN=dhcp243-31.rdu.redhat.com
        # Grab the tail of CN=<.*>, if no file found then use a default one.
        if (len(pathToFile) > 0) :
            fileContents = extractor.getDataFromFile(pathToFile)
            if (len(fileContents) > 0):
                regex = ".*%s.*%s(.*)" %("Issuer", "CN=")
                rem = re.compile(regex)
                for line in fileContents:
                    mo = rem.match(line)
                    if mo:
                        self.__hostname = mo.group(1).strip()
                        break
        # Now call the parent method
        sx.reports.Report.extract(self, extractor, os.path.join(extractDir, "%s-rhnsatDebug" % (self.__hostname)))
        if (os.path.exists(os.path.join(self.getPathToExtractedReport(), Satellitedebug.TYPE_DETECTION_FILE))):
            return True
        return False
