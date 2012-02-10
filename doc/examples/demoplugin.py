#!/usr/bin/env python
"""
This is a demo plugin to demostrate how to add plugins in. This plugin
uses sysreport/sosreports.

The plugin can be placed in the directory: $HOME/.sx/sxplugins/
$ cp demo.py $HOME/.sx/sxplugins/

It will need to be enabled.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.02
@copyright :  GPLv2
"""
import logging

import sx
import sx.plugins
from sx.logwriter import LogWriter

class Demoplugin(sx.plugins.PluginBase):
    """
    This is an example of a plugin.
    """
    def __init__(self, pathToPluginReportDir=""):
        """
        This init takes the root path to where the reports will be
        written. The parent class will then create the correct
        directory structure for the plugin.

        All plugin classes will need to call the parent class which is
        PluginBase.

        @param pathToPluginReportDir: This is the root path to where
        the report files will be written.
        @type pathToPluginReportDir: String
        """
        sx.plugins.PluginBase.__init__(self, "DemoPlugin",
                                       "This plugin is just a demo and does nothing useful. Just testing.",
                                       ["Sosreport", "Sysreport"], False, True,
                                       {"john_crichton_mode":"Enables the Farscape module for reports."},
                                       pathToPluginReportDir)

        # Set the options to their default values
        self.setOptionValue("john_crichton_mode", "on");

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
        # Always print this message if you going to call this function
        # so that logging is notified that this function has been called.
        message = "Running setup for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).log(LogWriter.STATUS_LEVEL, message)


        # Create some variable to store some value. In most cases
        # instead of keeping a bunch of dictionaries it is better to
        # create a class as a container. For instance the plugin for
        # cluster has two container. A container for a clusternode and
        # a container for a cluster(which is a collection of
        # clusternodes).
        self.__uptime = {}
        self.__etcHostsData = {}
        self.__pathToModprobeConf = {}

        # Loop through all the report objects and gather data if this
        # plugin supports the report type. In this instance we only
        # support sosreports/sysreports. All other report types will
        # be skipped.
        for report in reports:
            if (self.isValidReportType(report)) :
                # Hostname will be the key and there is built in
                # function for sysreport/sosreports to get hostname
                # data.
                hostname = report.getHostname()

                # Get the uptime data to be set as a value and there
                # is built in function for sysreport/sosreports to get
                # uptime data.
                self.__uptime[hostname] = report.getUptime()

                # Get the data from the /etc/hosts file for a
                # report. The path to the file is relative to the root
                # directory of the report.
                dataEtcHosts = report.getDataFromFile("etc/hosts")
                if (not dataEtcHosts == None) :
                    # If data is None then the path to the file was
                    # invalid or file does not exist so there is no
                    # data to return.
                    self.__etcHostsData[hostname] = dataEtcHosts

                # Get the path to the location of the file that
                # contains the /etc/modprobe.conf information. The
                # path to the file is relative to the root directory
                # of the report.
                pathToModprobeConf = report.getPathForFile("etc/modprobe.conf")
                if (len(pathToModprobeConf) > 0) :
                    # If empty string is returned then path was not found.
                    self.__pathToModprobeConf[hostname] = pathToModprobeConf

    def execute(self) :
        """
        This function should be overriden by the child if any
        intensive tasks needs be ran. This function should be used for
        writing to report files with write() functions or reporting
        any test results to console.
        """
        # Always print this message if you going to call this function
        # so that logging is notified that this function has been called.
        message = "Running execute for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).log(LogWriter.STATUS_LEVEL, message)

    def report(self) :
        """
        This function is where the reporting is done to console or to
        report files via the write() function.
        """
        # Always print this message if you going to call this function
        # so that logging is notified that this function has been called.
        message = "Generating report for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).log(LogWriter.STATUS_LEVEL, message)

        # #######################################################################
        # Check any options that have been set and that will give
        # control flow of how to do something.
        # #######################################################################
        if ("on" == self.getOptionValue("john_crichton_mode")) :
            message = "John Crichton mode enabled."
        elif ("off" == self.getOptionValue("john_crichton_mode")) :
            message = "John Crichton mode disabled."
        else:
            message = "John Crichton mode has unrecongized state."
        logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)

        # #######################################################################
        # Write information gathered to console
        # #######################################################################
        print "\t  This is the uptime information generated:"
        for key in self.__uptime.keys() :
            print "\t  %s: %s" %(key, self.__uptime[key])

        # #######################################################################
        # Write information gathered to a report file.
        # #######################################################################
        # This is the filename where we will write all the report
        # files we want to generate.
        filename = "demo_summary.txt"
        # Write a header
        self.writeSeperator(filename, "Demo Summary of Extracting Data");
        # Loop over all the data and write the informatio to a file.
        for key in self.__etcHostsData.keys() :
            self.write(filename,  "%s:" %(key))
            for line in self.__etcHostsData[key]:
                self.write(filename, "\t %s"%(line.strip()))
            self.write(filename, "")

        # #######################################################################
        # Write information gathered to a report file.
        # #######################################################################
        # Write the path to the modprobe.conf file. This will show
        # that that path is to a temporary file. All paths to reports
        # are to temperary files that are removed after the
        # application is ran. The reason is that we do not want to
        # modify the orginal files.
        self.writeSeperator(filename, "Demo Summary of Extracting a Path");
        # Loop over all the data and write the informatio to a file.
        for key in self.__pathToModprobeConf.keys() :
            self.write(filename,  "%s: \n\t  %s" %(key, self.__pathToModprobeConf[key]))
            self.write(filename, "")


    def action(self) :
        """
        This function performs some external task such as opening web
        browser or file viewer to view a file.
        """
        # Always print this message if you going to call this function
        # so that logging is notified that this function has been called.
        message = "Performing action for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).log(LogWriter.STATUS_LEVEL, message)

