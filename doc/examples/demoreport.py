#!/usr/bin/env python
"""
This class is a container for a demoreport which does not exist and
just an example.

The report can be placed in the directory: $HOME/.sx/sxreports/
$ cp demoreport.py $HOME/.sx/sxreports/


@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""
import os.path
import logging

import sx
from sx.reports import Report

class Demoreport(Report) :
    """
    This class is a container for demoreport object.

    @cvar TYPE_DETECTION_FILE: This is a path to file that can
    uniquely indentify the report object.
    @type TYPE_DETECTION_FILE: String
    @cvar REPORT_NAME: The name of the report.
    @type: String
    """
    TYPE_DETECTION_FILE = "demo/demo.txt"
    REPORT_NAME = "Demoreport"
    def __init__(self) :
        sx.reports.Report.__init__(self, Demoreport.REPORT_NAME,
                                   "This is just an example report.", 3)

    def extract(self, pathToReportFile, extractDir):
        """
        This function will extract the report to the extract
        dir. Currently all reports have to be a tarfile archive.

        This function overrides the parent function. The reason is
        that a new extractDir will be created. Then the parent extract
        function will be called.

        @return: Returns True if there was no fatal errors. TarBall
        errors are ignored because they should not be fatal, if they
        are the child should catch the errors since dir will not
        exist. If there are fatal errors, then False is returned.
        @rtype: boolean

        @param pathToReportFile: This is the path to the report file.
        @type pathToReportFile: String
        @param extractDir: The full path to directory for extraction.
        @type extractDir: String
        """
        sx.reports.Report.extract(self, pathToReportFile, extractDir)
        if (os.path.exists(os.path.join(self.getPathToExtractedReport(),
                                     Demoreport.TYPE_DETECTION_FILE))):
            return True
        return False

        return True
