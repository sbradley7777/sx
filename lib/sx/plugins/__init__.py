#!/usr/bin/env python
"""
This class will be used to pull in all the plugins and will be
inherited by all the plugins.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.14
@copyright :  GPLv2
"""
import time
import os
import os.path
import logging

import sx
from sx.logwriter import LogWriter
from sx.modulesloader import PluginsLoader
from sx.tools import ConsoleUtil

class PluginsHelper:
    def printPluginsList(self, includeUserPlugins=True):
        # Load up all plugins and pass the directory to write reports
        pluginLoader = PluginsLoader()
        loadedPlugins = pluginLoader.load("", includeUserPlugins)
        if (not len(loadedPlugins) > 0):
            logging.getLogger(sx.MAIN_LOGGER_NAME).error("There were no plugins found.")
        else:
            enabledMessage = "The following plugins are currently enabled by default:\n"
            disabledMessage = "The following plugins are currently disabled by default:\n"
            for plugin in loadedPlugins:
                if plugin.isEnabled():
                    enabledMessage = "%s%s: %s\n" %(enabledMessage,
                                                    ConsoleUtil.colorText(str(plugin.getName()),"red"),
                                                    plugin.getDescription())
                else:
                    disabledMessage = "%s%s: %s\n" %(disabledMessage,
                                                     ConsoleUtil.colorText(str(plugin.getName()),"red"),
                                                     plugin.getDescription())
            if (not len(enabledMessage) > 0):
                enabledMessage = "There was no plugins enabled."
            if (not len(disabledMessage) > 0):
                disabledMessage = "There was no plugins disabled."
            print  "\n%s\n%s" %(enabledMessage, disabledMessage)

            print "The list of available options for plugins:"
            for plugin in loadedPlugins:
                optionNames = plugin.getOptions()
                if (len(optionNames) > 0):
                    for optionName in optionNames :
                        optionDescription = plugin.getOptionDescription(optionName)
                        print "%s.%s: %s" %(ConsoleUtil.colorText(str(plugin.getName()),"red"),
                                            ConsoleUtil.colorText(optionName,"red"),
                                            optionDescription)

    def getEnabledPluginsList(self, pathToPluginReportDir, enableAllPlugins, disableAllPlugins,
                              listOfEnabledPlugins, listOfDisabledPlugins, pluginsOptionsMap,
                              includeUserPlugins=True):
        # Load up all plugins and pass the directory to write reports
        pluginLoader = PluginsLoader()
        loadedPlugins = pluginLoader.load(pathToPluginReportDir, includeUserPlugins)

        # Enable/Disable all
        if (enableAllPlugins) :
            for plugin in loadedPlugins:
                plugin.setEnabled(True)
        elif (disableAllPlugins) :
            for plugin in loadedPlugins:
                plugin.setEnabled(False)

        # Enable singletons
        if (len(listOfEnabledPlugins) > 0):
            for ePlug in listOfEnabledPlugins:
                for lPlug in loadedPlugins:
                    if (lPlug.isNamed(str(ePlug))):
                        lPlug.setEnabled(True)
                        break;

        # Disable Singletons
        if (len(listOfDisabledPlugins) > 0):
            for dPlug in listOfDisabledPlugins:
                for lPlug in loadedPlugins:
                    if (lPlug.isNamed(str(dPlug))):
                        lPlug.setEnabled(False)
                        break;
        # #######################################################################
        # Get a list of only the enabled plugins and set the options for
        # each. Will add options later on in another iterations.
        # #######################################################################
        enabledPlugins = []
        for plugin in loadedPlugins:
            if (plugin.isEnabled()):
                enabledPlugins.append(plugin)
                # ###############################################################
                # Set the plugin options for each plugin.
                # Example map:
                #   {'cluster': {'locks_check': 'on'}, 'Opensosreport': {'filebrowser': 'konqueror', 'browser': 'firefox'}}
                # ###############################################################
                # Map the options on the enabled plugins
                pluginName = plugin.getName().lower()
                if (pluginsOptionsMap.has_key(pluginName)):
                    # Get a dictionary from a dictionary key whose
                    # value is a dictionary.
                    optionsMap = pluginsOptionsMap.get(pluginName)
                    for optionName in optionsMap.keys():
                        plugin.setOptionValue(optionName, optionsMap.get(optionName))
                        # Found the correct plugin so need to keep searching
                        continue
        # Return the list of enabled plugins.
        return enabledPlugins

    def generatePluginReports(self, listOfReports, listOfEnabledPlugins):
        # Setup: gather files needed from each report
        for plugin in listOfEnabledPlugins:
            if ((plugin.isReportsRequired()) and (len(listOfReports) > 0)):
                plugin.setup(listOfReports)

        # Execute: run some intense operation that could be used in report/action
        for plugin in listOfEnabledPlugins:
            if ((plugin.isReportsRequired()) and (len(listOfReports) > 0)):
                plugin.execute()

        # Reports: write a report to console or file for each plugin
        for plugin in listOfEnabledPlugins:
            if ((plugin.isReportsRequired()) and (len(listOfReports) > 0)):
                plugin.report()

        # Actions: does something that is outside of sx such as opening a
        # browser, filemanager, etc.
        for plugin in listOfEnabledPlugins:
            if ((plugin.isReportsRequired()) and (len(listOfReports) > 0)):
                plugin.action()

        # Generate a map of all the files created by the plugins
        mapOfPluginReportPaths = {}
        for plugin in listOfEnabledPlugins:
            listOfFiles = plugin.getFileList()
            if (len(listOfFiles) > 0) :
                for filename in listOfFiles:
                    if (not mapOfPluginReportPaths.has_key(plugin.getName())):
                        mapOfPluginReportPaths[plugin.getName()] = [filename]
                    else:
                        mapOfPluginReportPaths[plugin.getName()].append(filename)
        return mapOfPluginReportPaths

class PluginBase:
    """
    This is the base class for all plugins.
    """
    def __init__(self,
                 name,
                 description,
                 validReportTypes,
                 enabled,
                 requireReports,
                 options,
                 pathToPluginReportDir="") :
        """
        This is the default initialized function for a plugin. The
        options dictionary will contain keys and values. The keys is
        the name of the option and value is the description of the
        option.

        The pathToPluginReportDir is not required because it may not
        be known when plugin was created, but can be set later on. If
        it is not set then default directory will be used.

        @param  name: The name of the plugin.
        @type name: String
        @param description: A description of the plugin.
        @type description: String
        @param validReportTypes: This is list of class names that are
        valid report types.
        @type validReportTypes: Array
        @param enabled: If true the plugin is enabled and
        can be used on reports.
        @type enabled: boolean
        @param requireReports : If True then plugin needs reports to run.
        By default it is True.
        @type requireReports: Boolean
        @param options: Dictionary of valid options for plugin,
        this is the option name and description of the option.
        @type options: Dictionary
        @param pathToPluginReportDir: Path to location where the reports
        will be written.
        @type pathToPluginReportDir: String
        """
        self.__name = name
        self.__description = description
        self.__enabled = enabled
        self.__requireReports = requireReports

        # Array of valid report types that plugin supports
        self.__validReportTypes = validReportTypes

        # This is a dictionary of options for the plugin
        self.__optionDescriptions = options
        # Initialize the possible options that can have values
        self.__optionValues = {}
        # The option values and description should have same set of
        # keys. Note new options cannot be added outside on __init__
        # or descriptions changed.
        for key in self.__optionDescriptions.keys():
            # Empty String is for no default value. Defaults can be
            # added in the __init__ of the plugin.
            self.__optionValues[key] = ""

        # #######################################################################
        # Set path to plugin report directory. If the
        # pathToPluginReportDir is empty string then create a
        # temporary directory to hold all the reports that are
        # generated.
        # #######################################################################
        self.__pathToPluginReportDir = ""
        if (not len(pathToPluginReportDir) > 0):
            uid = time.strftime("%Y-%m-%d_%H%M%S")
            self.__pathToPluginReportDir =  "/tmp/sxconsole-%s/reports/%s" %(uid, self.__class__.__name__.lower())

        else:
            self.__pathToPluginReportDir = os.path.join(os.path.join(pathToPluginReportDir, "reports"),
                                                        self.__class__.__name__.lower())

    def __str__(self) :
        """
        Returns a string that is composed of the name and description.

        @return: Returns a string that is composed of the name and
        description.
        @rtype: String
        """
        message =  "%s: %s" %(self.__name, self.__description)
        return message

    def isEnabled(self) :
        """
        Returns True is plugin in enabled. Returns False if plugin is
        disabled.

        @return: Returns True is plugin in enabled. Returns False if
        iqt is disabled.
        @rtype: Boolean
        """
        return self.__enabled

    def isReportsRequired(self) :
        """
        Returns True if reports are required to run this plugin.

        @return: Returns True if reports are required to run this
        plugin.
        @rtype: Boolean
        """
        return self.__requireReports

    def getName(self):
        """
        Returns the name of the plugin.

        @return: Returns the name of the plugin.
        @rtype: String
        """
        return self.__name

    def getDescription(self) :
        """
        Returns the description of the plugin.

        @return: Returns the description of the plugin.
        @rtype: String
        """
        return self.__description

    def getPathToPluginReportDir(self) :
        """
        Returns the path to the plugin report directory, where all the
        reports for the plugin will be located. If path is not set
        then will default to /tmp directory.

        @return: Returns the path to the plugin report directory,
        where all the reports for the plugin will be located.
        @rtype: String
        """
        return self.__pathToPluginReportDir

    def getReportTypes(self) :
        """
        Returns an array of valid report types.

        @return: Array of valid report types.
        @rtype: Array
        """
        return self.__validReportTypes

    def getOptions(self) :
        """
        Returns a list of keys for the options description Dict.

        @return: Returns a list of keys for the options description
        Dict.
        @rtype: Array
        """
        return self.__optionDescriptions.keys()

    def getOptionDescription(self, optionName):
        """
        This funciton will return the description of the plugin option.

        @return: This funciton will return the description of the
        plugin option.  None is returned if optionName does not exist.
        @rtype: String
        """
        if self.__optionDescriptions.has_key(optionName):
            return self.__optionDescriptions[optionName]
        return None

    def getOptionValue(self, optionName):
        """
        This function will return the value of the plugin option.

        @return: This function will return the value of the plugin
        option. None is returned if optionName does not exist.
        @rtype:String
        """
        if self.__optionValues.has_key(optionName):
            return self.__optionValues[optionName]
        return None

    def setOptionValue(self, optionName, value) :
        """
        This function will set a value for a plugin option if it
        exists. Returns True if plugin option was set. False if option
        was not set because plugin option does not existdoes not
        exist.

        @return: This function will set a value for a plugin option if
        it exists. Returns True if plugin option was set. False if
        option was not set because plugin option does not existdoes
        not exist.  Returns True if value was assigned to existing
        optionName. If no optionName is found then false is returned.
        @rtype:Boolean

        @param optionName: The optionName is the name of a plugin option.
        @type optionName: String
        @param value: The value of the plugin option that will
        be set.
        @type value: String
        """
        if (self.__optionValues.has_key(optionName)) :
            self.__optionValues[optionName] = value
            return True
        return False

    def setEnabled(self, enabled) :
        """
        This function will set the enabled status of the plugin. True
        is enabled and False is disabled.

        @param enabled: This is the boolean status of the plugin that
        will be set.
        @type enabled: boolean
        """
        self.__enabled = enabled

    def isValidReportType(self, report) :
        """
        Returns True if the plugin supports the type of report.

        @return: Returns True if the plugin supports the type of report.
        @rtype: Boolean

        @param report: A Report object that will be checked to see if
        the plugin supports.
        @type report: Report
        """
        for rType in self.getReportTypes() :
            if (rType.lower() == report.getType().lower()) :
                return True
        return False

    def isNamed(self, name) :
        """
        Returns True if the name that is given is same as self.__name
        or self.__class__.__name__. It compares all names via lower
        cases. This is not case senstive.

        @return: Returns True if the name that is given is same as self.__name
        or self.__class__.__name__. It compares all names via lower
        cases. This is not case senstive.
        @rtype: Boolean

        @param name: The name that will be compared.
        @type name: String
        """
        # The name of the plugin and the class name can be different.
        if ((name.lower() == self.getName().lower()) or
            (name.lower() == self.__class__.__name__.lower())):
            return True
        return False

    # #######################################################################
    # Functions to get listing of files and removal of files.
    # #######################################################################
    def getFileList(self) :
        listOfFiles = []
        try:
            if os.access(self.getPathToPluginReportDir(), os.F_OK):
                for root, dirs, files in os.walk(self.getPathToPluginReportDir()):
                    for currentFilename in files:
                        listOfFiles.append(os.path.join(root, currentFilename))
        except (IOError, os.error):
            pass
        listOfFiles.sort()
        return listOfFiles

    def clean(self):
        """
        This command will remove all the files that are in the plugins
        report directory where all the files for this plugin are
        written.
        """
        listOfFiles = self.getFileList()
        for pathToFile in listOfFiles:
            if (os.path.isfile(pathToFile)) :
                try:
                    os.remove(pathToFile)
                except:
                    message = "There was an error trying to remove the file: %s" %(pathToFile)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
    # #######################################################################
    # Functions for writing to a file
    # #######################################################################
    def writeSeperator(self, filename, header="", appendToFile=True) :
        """
        A helper function for writing to a file. It will write a
        string that represents a seperator or header.

        @param filename: Name of file that will be written to.
        @type filename: String
        @param header: The string that will be written which is
        optional.
        @type header: String
        @param appendToFile: This will append the string to the file
        if True. If False then string will override the contents of
        the file.
        @type appendToFile: Boolean
        """
        if (len(header) > 0):
            #dashHeaderString = "------------------------------------------------------------------"
            dashHeaderString = "-------------------------------------------------------------------------------------------------"
            self.write(filename, "%s\n%s:" %(dashHeaderString, header), appendToFile)
            if (not appendToFile):
                appendToFile = False
        self.write(filename, "%s\n" %(dashHeaderString))

    def write(self, filename, data, appendToFile=True):
        """
        This function will write the data to the filename. The
        filename is a relative path. The function will append the
        plugin report directory path to the start of the filename to
        create the fullpath.

        @param filename: The filename is a relative path. The function
        will append the plugin report directory path to the start of
        the filename to create the fullpath.
        @type filename: String
        @param data: The string data that will be written to  the
        file.
        @type data: String
        @param appendToFile: This will append the string to the file
        if True. If False then string will override the contents of
        the file.
        @type appendToFile: Boolean
        """
        try:
            if not os.access(self.getPathToPluginReportDir(), os.F_OK):
                os.makedirs(self.getPathToPluginReportDir())
        except (IOError, os.error):
            if (not len(self.getPathToPluginReportDir()) > 0):
                message =  "The base directory for plugin reports was empty or not set before running report function. The directory cannot be created."
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            else:
                message =  "Cannot create directory: %s" %(self.getPathToPluginReportDir())
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return
        try:
            pathToFilename = os.path.join(self.getPathToPluginReportDir(),filename)
            filemode = "w"
            if (appendToFile):
                filemode = "a"
            fout = open(pathToFilename, filemode)
            fout.write(data + "\n")
            fout.close()
        except UnicodeEncodeError, e:
            # Python 2.6 has "as", 2.5 does not  except UnicodeEncodeError as e:
            message = "There was a unicode encode error on file: %s." %(filename)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            print e
        except IOError:
            message = "There was an error writing the file: %s." %(filename)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)

    def writeTestResult(self, filename, message, result) :
        """
        This function will writes the message to the filename. The
        filename is a relative path. The function will append the
        plugin report directory path to the start of the filename to
        create the fullpath.

        This function is really for test results.The boolean result to
        be written to the filename.  The boolean result should be
        either True or False. If True then "PASSED" will be appended
        to start of the message string. If False then "Failed" will be
        appended to start of the message string.

        For example a typical message that is written is:
        "FAILED: * Node names are in /etc/hosts."

        @param filename: The filename is a relative path. The function
        will append the plugin report directory path to the start of
        the filename to create the fullpath.
        @type filename: String
        @param message: The string data that will be written to  the
        file.
        @type message: String
        @param result: The boolean result to be written to the
        filename.  The boolean result should be either True or
        False. If True then "PASSED" will be appended to start of the
        message string. If False then "Failed" will be appended to
        start of the message string.
        """
        if result:
            data = "PASSED:   %s" %(message)
            self.write(filename, data)
        else:
            data = "FAILED: * %s" %(message)
            self.write(filename, data)

    def writeEnabledResult(self, filename, message, result) :
        """
        This function will writes the message to the filename. The
        filename is a relative path. The function will append the
        plugin report directory path to the start of the filename to
        create the fullpath.

        This function is really for writing the result of testing the
        state of something when it is tested.The boolean result to be
        written to the filename.  The boolean result should be either
        True or False. If True then "ENABLED" will be appended to start
        of the message string. If False then "DISABLED" will be appended
        to start of the message string.

        For example a typical message that is written is:
        DISABLED: * Testing if the service "modclusterd" is enabled for runlevels 3-5.

        @param filename: The filename is a relative path. The function
        will append the plugin report directory path to the start of
        the filename to create the fullpath.
        @type filename: String
        @param message: The string data that will be written to  the
        file.
        @type message: String
        @param result: The boolean result to be written to the
        filename.  The boolean result should be either True or
        False. If True then "ENABLED" will be appended to start of the
        message string. If False then "DISABLED" will be appended to
        start of the message string.
        """
        if result:
            data = "ENABLED:   %s" %(message)
            self.write(filename, data)
        else:
            data = "DISABLED:* %s" %(message)
            self.write(filename, data)

    # #######################################################################
    # Functions that should be overwritten in the plugin
    # #######################################################################
    def setup(self, reports) :
        """
        This function should be overridden by the child. The child
        should call this method first to set the variable for the
        location where the write() will write all the files.

        This function should extract all the files that will be
        accessed from the Report Objects, since the Report Objects
        should not be refrenced after this function exits.

        @param reports: This is the list of Report Objects.
        @type reports: Array
        """
        pass

    def execute(self) :
        """
        This function should be overriden by the child if any
        intensive tasks needs be ran. This function should be used for
        writing to report files with write() functions or reporting
        any test results to console.
        """
        pass

    def report(self) :
        """
        This function is where the reporting is done to console or to
        report files via the write() function.
        """
        pass

    def action(self) :
        """
        This function is for doing an action outside of sx such as
        opening a filemanager, web browser, etc.
        """
        pass
