#!/usr/bin/env python
"""
This plugin will analyze and summarize a collection of sosreports that are using gluster.

This plugin only supports RHEL 6+ using gluster currently.

TODO:
* /var/lib/glusterd/vols/*/*-fuse.vol should be the same on all nodes, error if they are not.
* /var/lib/glusterd/vols/*/*/info file should be the same on all nodes, error if they are not.
* md5sum `find . -name cksum|paste -s`
* gawk '/gfid self-heal/ || /selfhealing/ || /split brain/ || / E /' *

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
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
                                       ["Sosreport"], True, True, {},
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
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)
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
            result = self.__getHostsSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Gluster Peer Nodes Summary");
                self.write(filename, result.rstrip())
                self.write(filename, "")

            # ###################################################################
            # Write out all the gluster peer nodes
            # ###################################################################
            result = self.__getPeerNodesSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Gluster Peer Nodes Summary");
                self.write(filename, result.rstrip())
                self.write(filename, "")

            # ###################################################################
            # Write out all the gluster processes
            # ###################################################################
            result = self.__getProcessesSummary()
            if (len(result) > 0):
                self.writeSeperator(filename, "Gluster Peer Nodes Process Summary");
                self.write(filename, result.rstrip())
                self.write(filename, "")


    # #######################################################################
    # Private functions to create a string of summary information
    # #######################################################################
    def __getPeerNodesSummary(self) :
        stringUtil = StringUtil()
        pTable = []
        rString  = ""
        for glusterPeerNode in self.__glusterPeerNodes.getGlusterPeerNodes():
            pTable = []
            for peerNodeMap in glusterPeerNode.getPeerNodes():
                pnHostname1 = ""
                if (peerNodeMap.has_key("hostname1")):
                    pnHostname1 = peerNodeMap.get("hostname1")
                pnUUID = ""
                if (peerNodeMap.has_key("uuid")):
                    pnUUID = peerNodeMap.get("uuid")
                pnState = ""
                if (peerNodeMap.has_key("state")):
                    pnState = peerNodeMap.get("state")
                pTable.append([pnHostname1, pnUUID, pnState])
            if (len(pTable) > 0):
                rString += "%s(%d peers):\n%s\n\n" %(glusterPeerNode.getHostname(), len(pTable), stringUtil.toTableString(pTable, ["hostname1", "uuid", "state"]))
        return rString

    def __getProcessesSummary(self) :
        stringUtil = StringUtil()
        rString  = ""
        for glusterPeerNode in self.__glusterPeerNodes.getGlusterPeerNodes():
            pTable = []
            for process in glusterPeerNode.getGlusterProcesses():
                command = process.getCommand()
                if (len(command) > 70):
                    endStringIndex = len(command.split()[0]) + 50
                    command = command[0:endStringIndex]
                pTable.append([process.getPID(), process.getCPUPercentage(), process.getMemoryPercentage(), "%s ...." %(command)])
            if (len(pTable) > 0):
                rString += "%s(%d processes):\n%s\n\n" %(glusterPeerNode.getHostname(), len(pTable), stringUtil.toTableString(pTable, ["pid", "cpu%", "mem%", "command"]))
        return rString

    def __getHostsSummary(self) :
        rString  = ""
        for glusterPeerNode in self.__glusterPeerNodes.getGlusterPeerNodes():
            if (len(rString) > 0):
                rString += "\n"
            unameASplit = glusterPeerNode.getUnameA().split()
            unameA = ""
            for i in range (0, len(unameASplit)):
                if (i == 5) :
                    unameA += "\n\t      "
                unameA += "%s " %(unameASplit[i])
                i = i + 1
            rString += "Hostname:     %s\n" %(glusterPeerNode.getHostname())
            rString += "Date:         %s\n" %(glusterPeerNode.getDate())
            rString += "RH Release:   %s\n" %(glusterPeerNode.getDistroRelease())
            rString += "Uptime:       %s\n" %(glusterPeerNode.getUptime())
            rString += "Uname -a:     %s\n" %(unameA)
            rString += "UUID:         %s\n" %(glusterPeerNode.getUUID())
        return rString
