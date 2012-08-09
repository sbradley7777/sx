#!/usr/bin/env python
"""
This plugin will analyze and summarize a collection of sosreports that are using gluster.

This plugin only supports RHEL 6+ using gluster currently.
- https://bugzilla.redhat.com/show_bug.cgi?id=818149

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.08
@copyright :  GPLv2
"""
import string
import logging
import os
import re

import sx
import sx.plugins
from sx.logwriter import LogWriter
from sx.tools import StringUtil

from sx.reports.sosreport import Sosreport

from sx.plugins.lib.gluster.glusterpeernodes import GlusterPeerNodes
from sx.plugins.lib.gluster.glusterpeernode import GlusterPeerNode

class Gluster(sx.plugins.PluginBase):
    def __init__(self, pathToPluginReportDir="") :
        sx.plugins.PluginBase.__init__(self, "Gluster",
                                       "This plugin will analyze sosreports that are using gluster.",
                                       ["Sosreport"], False, True, {},
                                       pathToPluginReportDir)

        self.__glusterPeerNodes = GlusterPeerNodes()

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
        logging.getLogger(sx.MAIN_LOGGER_NAME).log(LogWriter.STATUS_LEVEL, message)
        for report in reports:
            if (self.isValidReportType(report)) :
                self.__glusterPeerNodes.add(report)

    def report(self) :
        """
        This function will write to report files the results of the
        cluster validation tests and report any errors to console.
        """
        if (not len(self.__glusterPeerNodes.getGlusterPeerNodes()) > 0):
            message = "There were no gluster peer nodes found in the list of reports so no report will be generated."
            logging.getLogger(sx.MAIN_LOGGER_NAME).warn(message)
        else:
            message = "Generating report for plugin: %s" %(self.getName())
            logging.getLogger(sx.MAIN_LOGGER_NAME).log(LogWriter.STATUS_LEVEL, message)
            message = "%s is generating a report of various information about the peer nodes in the gluster." %(self.getName())
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)

            # Since we are going to run the plugin and create files in
            # the plugins report directory then we will first remove
            # all the existing files.
            self.clean()

            # Not sure if there is a gluster global name or something
            filename = "%s-summary.txt" %("gluster")
            # ###################################################################
            # Summary of each node in collection
            # ###################################################################
            result = self.__glusterPeerNodes.getGlusterPeerNodesSystemSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Gluster Peer Nodes Summary");
                self.write(filename, result.rstrip())
                self.write(filename, "")
            for glusterPeerNode in self.__glusterPeerNodes.getGlusterPeerNodes():
                pass
