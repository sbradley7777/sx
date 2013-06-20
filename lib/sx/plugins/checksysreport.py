#!/usr/bin/env python
"""
A class that can run checksysreport against a report and then write
the checksysreport data to a file.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.15
@copyright :  GPLv2
"""
import sys
import os
import os.path
import logging
import subprocess

import sx
import sx.plugins
from sx.logwriter import LogWriter
from sx.reports.sosreport import Sosreport
from sx.reports.sysreport import Sysreport
from sx.tools import FileUtil

class Checksysreport(sx.plugins.PluginBase):
    """
    A class that can run checksysreport against a report and then
    write the checksysreport data to a file.

    @cvar CHECKSYSREPORT_LIBS: Location for the libraries for checksysreport.
    @type CHECKSYSREPORT_LIBS: String
    @cvar CHECKSYSREPORT_EXE: Location for the executable for checksysreport.
    @type CHECKSYSREPORT_EXE: String
    @cvar CHEKCSYSREPORT_CONFIG_FILE: This is path to the checksysreport config file.
    @type STRING
    """
    CHECKSYSREPORT_LIBS = "/usr/share/checksysreport"
    CHECKSYSREPORT_EXE = "/usr/bin/checksysreport"
    CHEKCSYSREPORT_CONFIG_FILE = os.environ['HOME']+"/.checksysreportrc"
    def __init__(self, pathToPluginReportDir="") :
        """
        This init takes the root path to where the reports will be
        written. The parent class will then create the correct
        directory structure for the plugin.

        @param pathToPluginReportDir: This is the root path to where
        the report files will be written.
        @type pathToPluginReportDir: String
        """
        sx.plugins.PluginBase.__init__(self, "Checksysreport",
                                       "This plugin creates a checksysreport based on each extracted sosreport/sysreport.",
                                       ["Sosreport", "Sysreport"], False, True, {"enable_binary":"Enables running of binary checksysreport command instead of native call(options: on/off). "}, pathToPluginReportDir)
        self.__chksysData = {}
        self.__installedRPMSPath = {}
        self.setOptionValue("enable_binary", "on");

    def __executeBinary(self, pathToDir) :
        """
        This function will use the native binary to call
        checksysreport. The "checksysreport" rpm will need to be
        installed.

        @return: Returns the output from running the command.
        @rtype: String

        @param pathToDir: The path to the directory that
        checksysreport will run against.
        @type pathToDir: String
        """
        message = "Executing binary call to checksysreport to gather data."
        logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
        if (not os.path.exists(Checksysreport.CHECKSYSREPORT_EXE)):
            message = "The checksysreport command is not installed: %s." %(Checksysreport.CHECKSYSREPORT_EXE)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return ""
        message = "Running checksysreport against the directory: %s" % (pathToDir)
        logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)

        command = [Checksysreport.CHECKSYSREPORT_EXE, "-h"]
        task = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = task.communicate()
        if (task.returncode == 0):
            command = [Checksysreport.CHECKSYSREPORT_EXE, "-s", pathToDir]
            message = "The checksysreport execute statement: %s %s %s" %(command[0], command[1], command[2])
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)

            task = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = task.communicate()
            return stdout
        else:
            message = "The checksysreport command exited with an error."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
        return ""

    def __executeNative(self, pathToDir) :
        """
        This function will call the native python files to execute the
        check of the report.

        @return: Returns a string that is the
        @rtype: String

        @param pathToDir: The path to the directory that will run
        checksysreport against it.
        @type pathToDir: String
        """
        message = "Executing python native call to checksysreport to gather data."
        logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
        if (os.path.exists(Checksysreport.CHECKSYSREPORT_LIBS)) :
            sys.path.append(Checksysreport.CHECKSYSREPORT_LIBS)
            try:
                import checksysreport_wrapper
            except ImportError:
                message = "The checksysreport library could not be imported."
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return ""
            message = "Running checksysreport against the directory: %s" % (pathToDir)
            logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
            chksys=checksysreport_wrapper.checksysreport_wrapper(pathToDir)
            data = chksys.generate_report()
            # Convert text format to utf8 to avoid unicode errors
            return data.encode("utf8")
        else:
            message = "The checksysreport library is not installed correctly: %s." %(Checksysreport.CHECKSYSREPORT_LIBS)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return ""

    def __stripDanglingNewLine(self, pathToFile):
        # Make sure there is no danglying newlines at end of the
        # file to avoid error genereated by checksysreport.
        tailOfFile = FileUtil.tail(pathToFile)
        if (not len(tailOfFile) > 0):
            return False
        elif (tailOfFile[0] == "\n"):
            import fileinput
            try:
                fileInput = fileinput.input(pathToFile, inplace=True)
                for line in fileInput:
                    if (line != '\n'):
                        print line,
                fileInput.close()
            except IOError:
                pass
        return True

    # #######################################################################
    # Overwriting function of parent
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
        pathToInstalledRPMSList = ["sos_commands/rpm/rpm_-qa_--qf_NAME_-_VERSION_-_RELEASE_-_ARCH_INSTALLTIME_date_.b",
                                   "sos_commands/rpm/rpm_-qa_--qf_NAME_-_VERSION_-_RELEASE_._ARCH_INSTALLTIME_date_.b",
                                   "sos_commands/rpm/rpm_-qa_--qf_NAME_-_VERSION_-_RELEASE_-_ARCH" ,
                                   "installed-rpms"]

        for report in reports:
            if (self.isValidReportType(report)) :
                (head, tail) = os.path.split(report.getPathToExtractedReport())
                self.__chksysData[report.getPathToExtractedReport()] =  ""
                # Find the installed rpm file that is required.
                for path in pathToInstalledRPMSList:
                    currentPath = report.getPathForFile(path)
                    if (len(currentPath) > 0):
                        self.__installedRPMSPath[report.getPathToExtractedReport()] =  currentPath
                        # Break since path was found.
                        break;
    def execute(self) :
        """
        This function will run checksysreport on all the
        reports. Since this is intenstive task it will execute in this
        function.

        The command is:
        "/usr/bin/checksysreport -s <reportdir> > <path to file>"

        This command uses the checksysreport file located in your home directory:
        "~/.checksysreportrc."
        """
        message = "Running execute for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
        if (not os.path.exists(Checksysreport.CHEKCSYSREPORT_CONFIG_FILE)):
            message = "There was no configuration file for checksysreport, please create the config file: %s." %(Checksysreport.CHEKCSYSREPORT_CONFIG_FILE)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return
        cKeys = self.__chksysData.keys()
        cKeys.sort()
        for key in cKeys:
            # Make sure there is no danglying newlines at end of the
            # file to avoid error genereated by checksysreport.
            checksysreportData = ""
            if (self.__stripDanglingNewLine(self.__installedRPMSPath.get(key))):
                # Check to see which way the checksysreport will be generated and
                # put the result in the checksysreportData variable.
                if ("on" == self.getOptionValue("enable_binary")) :
                    checksysreportData = self.__executeBinary(key).strip()
                else:
                    checksysreportData = self.__executeNative(key).strip()
                # Add the data to the map and check for errors. If error then add empty string.
                if (checksysreportData.startswith("Canot parse the following in installed-rpms")):
                    message = "There was an error parsing the installed-rpms file that is read by checksysreport."
                    logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                    checksysreportData = ""
                elif ((checksysreportData.startswith("no such file")) or (checksysreportData.startswith("Unable to detect base channel"))):
                    message = "The checksysreport file could not be generated because of checksysreport error."
                    logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                    checksysreportData = ""
            else:
                message = "There was an error parsing the installed-rpms file that is read by checksysreport."
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            self.__chksysData[key] = checksysreportData

    def report(self) :
        """
        This function will write the checksysreport data to a file.
        """
        message = "Generating report for plugin: %s" %(self.getName())
        logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
        if (len(self.__chksysData.keys()) > 0):
            # Since we are going to run the plugin and create files in
            # the plugins report directory then we will first remove
            # all the existing files.
            self.clean()

        for key in self.__chksysData.keys():
            if (len(self.__chksysData[key]) > 0):
                (head, tail) = os.path.split(key)
                # We will not append the data because we are only writing once.
                self.write("%s.txt" %(tail), self.__chksysData[key], False)

