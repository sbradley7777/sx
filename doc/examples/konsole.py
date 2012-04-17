#!/usr/bin/env python
"""
This is a konsole plugin open up a tab in konsole session.

There is no way to know which session at this moment and just defaults
to sessoin 1, which is the var "self.__konsoleWindowNum."

The plugin can be placed in the directory: $HOME/.sx/sxplugins/
$ cp konsole.py $HOME/.sx/sxplugins/

It will need to be enabled.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.10
@copyright :  GPLv2
"""
import logging
import sys
import os.path
import dbus

import sx
import sx.plugins
from sx.logwriter import LogWriter

class Konsole(sx.plugins.PluginBase):
    """
    This is a konsole plugin open up a tab in konsole session.
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
        validReportTypes = ["Sosreport", "Sysreport"]
        sx.plugins.PluginBase.__init__(self,"Konsole",
                                       "This plugin opens new tab for each sysreport/sosreport to /var/log/messages.",
                                       ["Sosreport", "Sysreport"], False, True,
                                       {}, pathToPluginReportDir)

        self.__pathToReports = {}
        self.__konsoleWindowNum = 1
        self.__fileViewerCommand = "less"

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
        # Find window that is running "sxconsole"
        self.__konsoleWindowNum = 1

        for report in reports:
            if (self.isValidReportType(report)) :
                self.__pathToReports[report.getHostname()] = report.getPathToExtractedReport()

    def execute(self) :
        """
        This function should be overriden by the child if any
        intensive tasks needs be ran. This function should be used for
        writing to report files with write() functions or reporting
        any test results to console.
        """
        message = "Konsole will open tabs for each sosreport/sysreport /var/log/messages file."
        logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
        try :
            bus = dbus.SessionBus()
            for key in self.__pathToReports.keys():
                pathToReport = self.__pathToReports[key]
                if (os.path.exists(pathToReport)):
                    try:
                        # Create new tab
                        konsoleMainWindowObj = bus.get_object("org.kde.konsole","/konsole/MainWindow_%d" %(self.__konsoleWindowNum))
                        konsoleMainWindowInterface = dbus.Interface(konsoleMainWindowObj, "org.kde.KMainWindow")
                        konsoleMainWindowInterface.activateAction("new-tab")

                        # Set Window Title
                        konsoleMainWindowInterface = dbus.Interface(konsoleMainWindowObj, "com.trolltech.Qt.QWidget")
                        konsoleMainWindowInterface.setWindowTitle("%s" % (key))

                        # Get current session number
                        konsoleObj = bus.get_object("org.kde.konsole","/Konsole")
                        konsoleInterface = dbus.Interface(konsoleObj, "org.kde.konsole.Konsole")
                        currentSessionNum = konsoleInterface.currentSession()

                        # Run command in current session to cd to directory
                        currentSessionObj = bus.get_object("org.kde.konsole","/Sessions/%d" %(currentSessionNum))
                        currentSessionInterface = dbus.Interface(currentSessionObj, "org.kde.konsole.Session")
                        currentSessionInterface.sendText("cd %s\n" % (pathToReport))

                        # Run command in current session to open log file
                        pathToMessageFile = os.path.join(pathToReport, "var/log/messages")
                        if (os.path.exists(pathToMessageFile)):
                            currentSessionInterface.sendText("%s %s\n" % (self.__fileViewerCommand, pathToMessageFile))

                    except dbus.exceptions.DBusException, e:
                        message = "An error occurred trying to communicate with dbus to create/modify a session."
                        logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                        print e
                else:
                    message = "The report directory does not exist: %s" % (pathToReport)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
        except dbus.exceptions.DBusException:
            message = "An error occurred trying to communicate with dbus to get current session before adding sessions."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)


