#!/usr/bin/env python
"""
This is the main script that will extract reports and then run various
plugins on them.

All reports have to be a a compressed tarfile of type bzip2/gunzip.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""
import sys
import string
import os
import os.path
import shutil
import logging

import sx
from sx.logwriter import LogWriter
from sx.tools import FileUtil
from sx import SXConfigurationFiles

from sx import ArchiveLayout
from sx import ArchivedLayout
from sx import ModifiedArchiveLayout
from sx import ModifiedArchivedLayout
from sx.extractors import Extractor
from sx.reports import Report
from sx.plugins import PluginsHelper
from sx.modulesloader import ReportsLoader
from sx.modulesloader import ExtractorsLoader

from sx.analysisreport import AnalysisReport
from sx.analysisreport import ARSection
from sx.analysisreport import ARSectionItem

class SXConsole:
    def __init__(self, optionsMap, uid):
        self.__optionsMap = optionsMap
        self.__uid = uid
        lwObjSXC = LogWriter(sx.MAIN_LOGGER_NAME,
                             logging.INFO,
                             sx.MAIN_LOGGER_FORMAT,
                             disableConsoleLog=False)

        if (self.__optionsMap.get("enableDebugLogging")) :
            logging.getLogger(sx.MAIN_LOGGER_NAME).setLevel(logging.DEBUG)
            message = "Debugging has been enabled."
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)

        # Make sure that ~ is expanded on any path variable that is path to some
        # file or directory.
        if (self.__optionsMap.get("archivePath").startswith("~")):
            self.__optionsMap["archivePath"] = self.__optionsMap.get("archivePath").replace("~", os.path.expanduser("~"), 1)
        if (self.__optionsMap.get("reportPath").startswith("~")):
            self.__optionsMap["reportPath"] = self.__optionsMap.get("reportPath").replace("~", os.path.expanduser("~"), 1)
        listOfReports = self.__optionsMap.get("listOfReports")
        for i in range(0, len(listOfReports)):
            pathToReport = listOfReports[i]
            if (pathToReport.startswith("~")):
                listOfReports[i] = pathToReport.replace("~", os.path.expanduser("~"), 1)

        # #######################################################################
        # Create configuration directory if it does not exist and set debug
        # #######################################################################
        sxConfigFiles = SXConfigurationFiles()
        result = sxConfigFiles.generateDefaultConfigurationDirectories()
        if (not result):
            message = "There was an error creating the user configuration directory. sxconsole will proceed without it."
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)

        self.__al = None
        # Archive Layout
        if (self.__validateOptions(self.getUID(), self.__optionsMap.get("pathToExtractedReports"))):
            try:
                self.__al = self.__getArchiveLayout(self.getUID(), self.__optionsMap.get("archivePath"),
                                             self.__optionsMap.get("pathToExtractedReports"),
                                             self.__optionsMap.get("modifiedArchiveLayout"),
                                             self.__optionsMap.get("timestamp"))
            except ValueError:
                message = "The timestamp value (for the -t option) is using an incorrect format. See --help for the correct format to use with the -t option."
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)

    def getArchiveLayout(self):
        return self.__al

    def getUID(self):
        return self.__uid

    def __validateOptions(self, uid, pathToExtractedReports) :
        """
        This function validates that options that is given. It will exit
        if invalid args and return True if no errors.

        @return: Returns True if no validation errors on user options.
        @rtype: Boolean

        @param uid: The case number.
        @type uid: String
        @param pathToExtractedReports: Path to the root directory for an
        extracted reports.
        @type pathToExtractedReports: String
        """
        # #######################################################################
        # Validate that either a uid or extracted path was given.
        # #######################################################################
        if ((not len(uid) > 0) and (not len(pathToExtractedReports) > 0)):
            # No uid or path args are given
            message =  "No args given. A unique idenification number as an argument or a path to extracted reports with -p option is required."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif ((len(uid) > 0) and (len(pathToExtractedReports) > 0)):
            # Both options were given
            message =  "A uid and path (-p option) was given. Please choose only 1 option."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif ((len(pathToExtractedReports) > 0) and (not os.path.exists(pathToExtractedReports))):
            # If path has greater length than zero and path does not exist
            message = "The path passed with -p option is not a valid path of archived reports."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif (len(uid) > 0):
            if (not uid.isalnum()):
                # If no path was given and uid is greater than zero and is not alphanumeric uid
                message = "Only numeric ticket numbers  are valid."
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return False
        # Since we did not exit then can proceed to run.
        return True

    def __getArchiveLayout(self, uid, pathToArchiveDirectory, pathToExtractedReports,
                           isModifiedArchiveLayoutEnabled, timestamp="") :
        """
        This function is what will take the user options and do the action
        that user has specified.

        @return: Returns a ReportExtractor Object after the extraction or
        loading of reports.
        @rtype: ReportExtractor
        """
        # #######################################################################
        # Create the reportextractor class to begin extraction or loading
        # #######################################################################
        # The layout object
        al = None
        if (len(pathToExtractedReports) > 0) :
            # This will load an archive and not extracted the archive
            # since archive has already been extracted.
            al = ArchivedLayout(pathToExtractedReports)
            if (isModifiedArchiveLayoutEnabled):
                message = "The Modified Layout is ignored since archive layout is autodetected and cannot be modified once extracted."
                logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            if (not pathToExtractedReports.find("ereports") > 0):
                message = "Enabling the Modified Archive Layout since Default layout was not detected."
                logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                al = ModifiedArchivedLayout(pathToExtractedReports)
        else:
            # This will extracted a list of reports since they have not
            # been extracted.
            al = ArchiveLayout(pathToArchiveDirectory, uid, timestamp)
            if (isModifiedArchiveLayoutEnabled):
                message = "Enabling the Modified Archive Layout."
                logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                al = ModifiedArchiveLayout(pathToArchiveDirectory, uid, timestamp)
        return al

    def __getPluginOptions(self, cmdLineListOfPluginOptions) :
        """
        Check if plugin has an option in list of plugin options and if so enable
        it.Returns a dictionary of dictionaries.

        Example:
        {'cluster': {'locks_check': 'on'}, 'Opensosreport': {'filebrowser': 'konqueror', 'browser': 'firefox'}}

        @return: Returns a dictionary of dictionaries.
        @rtype: Dictionary

        @param cmdLineListOfPluginOptions: This is a list of options for various
        plugins.
        @type cmdLineListOfPluginOptions: Array
        """
        pluginOptionsMap = {}
        for option in cmdLineListOfPluginOptions :
            keyEqualSplit = option.split("=")
            peroidEqualSplit = option.split(".")
            if ((len(keyEqualSplit) == 2) and (len(peroidEqualSplit) == 2)) :
                pluginName = peroidEqualSplit[0].lower()
                pluginOptionName = keyEqualSplit[0].split(".")[1]
                pluginOptionValue = keyEqualSplit[1]
                if (pluginOptionsMap.has_key(pluginName)) :
                    optionMap = pluginOptionsMap.get(pluginName)
                    optionMap[pluginOptionName] = pluginOptionValue
                else:
                    pluginOptionsMap[pluginName] = {pluginOptionName:pluginOptionValue}
        return pluginOptionsMap

    def __initializeDirStructure(self, pathToCompressedReports, pathToExtractedReports):
        """
        Returns True if the directories created exists.
        """
        dirPaths = [pathToCompressedReports, pathToExtractedReports]
        for dirPath in dirPaths:
            if (not os.access(dirPath, os.F_OK)):
                try:
                    os.makedirs(dirPath)
                except OSError:
                    message = "Could not create the directory: %s." % (dirPath)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                    return False
                except IOError:
                    message = "Could not create the directory: %s." % (dirPath)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                    return False
                if (not os.access(dirPath, os.F_OK)):
                    message = "The directory does not exists after it was created: %s." % (dirPath)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                    return False
        return True

    def __extractReports(self, al, pathToExtractedReports, listOfReports,
                         pathToReportsDirectory, includeUserDefinedModules) :

        # Create the reporter object based on layout of the paths
        if (al == None):
            message = "The archive layout format could not be determine and application will exit."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            sys.exit(1)

        # Since layout was detected then we will proceed.
        if (not self.__initializeDirStructure(al.getPathToCompressedReports(), al.getPathToExtractedReports())):
            message = "The archive directories do not exist. The application will exit."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            sys.exit(1)
        # #######################################################################
        # Extract or load the reports
        # #######################################################################
        if (len(pathToExtractedReports) > 0) :
            # Load reports that were already extracted.
            reportsExtracted = self.__load(pathToExtractedReports, includeUserDefinedModules)
            message = "There was %d reports found and loaded." %(len(reportsExtracted))
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
        else:
            # Extract reports that have not been archived from the list of reports
            message = "The list of reports are being analyzed to verify that they are known report types."
            logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
            listOfReports = self.__getListOfReports(listOfReports, pathToReportsDirectory)
            message = "The reports will be extracted to the following directory: %s" %(al.getPathToExtractedReports())
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
            message = "Extracting %d reports."%(len(listOfReports))
            logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
            message = "This process could take a while on large reports."
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
            reportsExtracted = self.__extract(listOfReports, al.getPathToCompressedReports(),
                                              al.getPathToExtractedReports(), includeUserDefinedModules)
            message = "There was %d reports extracted to the directory: %s" %(len(reportsExtracted), al.getPathToExtractedReports())
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
        return reportsExtracted

    def __extract(self, listOfUnextractedReports, pathToCompressedReports,
                  pathToExtractedReports, includeUserDefinedModules) :
        """
        This function will extract all the reports in the array if
        they are a known type. It will return a list of report objects.

        This function also uses recursion in case a report contains
        other reports. For example a RHEV report contains
        sosreports. The sosreports that are in the RHEV report will be
        extracted as well.

        @return: Returns a list of all the report objects that were
        successfully extracted.
        @rtype: Array

        @param listOfUnextractedReports: An array of all the reports to attempt
        extract. If there is not a known type then the report will not
        be extracted and moved to archive location.
        @type listOfUnextractedReports: List
        @param includeUserDefinedModules: If True then user defined
        reports/plugins are enabled.
        @type includeUserDefinedModules: Boolean
        """
        # Zero out the list because this is new load of reports
        listOfReports = []
        # If the report contains reports then they need to be analyzed like a
        # RHEV report.
        reportsWithinReportList = []
        # Various loaders that are required.
        extractorsLoader = ExtractorsLoader()
        reportsLoader = ReportsLoader()

        for pathToFilename in listOfUnextractedReports:
            report = reportsLoader.getReport(pathToFilename, includeUserDefinedModules)
            if (not report == None):
                # The reason I have to find extractor again is because I moved
                # the file from orginal location so I dont want an extractor in
                # object if the file it extracts no longer exists.
                extractor = extractorsLoader.getExtractor(pathToFilename, includeUserDefinedModules)
                if (report.extract(extractor, pathToExtractedReports)):
                    # Add the report to the list of valid reports that were found.
                    listOfReports.append(report)
                    # Move the file if it was extracted correctly.
                    pathToNewFilename = os.path.join(pathToCompressedReports, os.path.basename(pathToFilename))
                    if (not self.__moveReport(pathToFilename, pathToNewFilename)):
                        message = "There was an error moving the file: %s\n\t  to %s." %(pathToFilename, pathToNewFilename)
                        logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                        # If the report contains or could contain other known
                        # report types then we will see if any of the files
                        # within that report can be added to the list of reports
                        # that need to be extracted.
                    if (report.includesOtherReports()):
                        pathToExtractedReport = report.getPathToExtractedReport()
                        # List of full path to files within the report that was
                        # extracted. Just top dir for now, will not goto deep it
                        # for now. I also moving these out which might be
                        # desired.
                        listOfFilesInExtractedReports = []
                        for currentFilename in os.listdir(pathToExtractedReport):
                            listOfFilesInExtractedReports.append(os.path.join(pathToExtractedReport, currentFilename))
                        if (len(listOfFilesInExtractedReports) > 0):
                            message =  "The %s report contains %d files and the %s report will be analyzed " %(report.getName(),
                                                                                                               len(listOfUnextractedReports),
                                                                                                               report.getName())
                            message += "to see if contain any other known report types."
                            logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
                            # Now do a little recursion
                            reportsWithinReportList += self.__extract(listOfFilesInExtractedReports, pathToCompressedReports,
                                                                      pathToExtractedReports, includeUserDefinedModules)
                else:
                    message = "There was an error extracting the report: %s." %(str(extractor))
                    logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
        # Add reports extracted that were in other reports
        listOfReports += reportsWithinReportList
        return listOfReports

    def __load(self, pathToExtractedReports, includeUserDefinedModules):
        """
        Returns the list of report paths that have already been
        extracted based on the path of pathToExtractedReports pass to
        init.

        @return: Returns the list of report paths that have already
        been extracted based on the path of pathToExtractedReports pass
        to init.
        @rtype: Array

        @param includeUserDefinedModules: If True then user defined
        reports/plugins are enabled.
        @type includeUserDefinedModules: Boolean
        """
        message = "Loading all the known report types for previously extracted reports."
        logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
        # Zero out the list because this is new load of reports
        listOfReports = []
        reportsLoader = ReportsLoader()
        for filename in os.listdir(pathToExtractedReports):
            if (filename == "reports"):
                continue
            elif (filename.startswith(".")):
                continue
            else:
                pathToFilename = os.path.join(pathToExtractedReports, filename)
                report = reportsLoader.getReport(pathToFilename, includeUserDefinedModules)
                if (not report == None) :
                    report.setPathToExtractedReport(pathToFilename)
                    listOfReports.append(report)
        return listOfReports

    # ##############################################################################
    # Helper functions for moving files to different location.
    # ##############################################################################
    def __moveReport(self, src, dst):
        """
        This function will move the file file that will be extracted
        to a new location. If there is a file that already exists for
        that path then then the file will not be moved or overwrite
        the existing file.

        @return: Returns True if a file exists for the provided dst
        path. Returns False if file does not exist.
        @rtype: String

        @param dst: Path to location where the extractor file will be
        moved to.
        @type dst: String
        """
        # The directories should be created before moving.
        if (not os.path.exists(src)):
            message = "The file does not exist: %s." %(src)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif (os.path.exists(dst)):
            message = "The file already exists and will not overwrite the existing file: %s." %(dst)
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        else:
            try:
                shutil.move(src, dst)
            except (IOError, os.error):
                message = "Cannot move the file %s to %s." %(src, dst)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
        # If the file exists then return True and set the new path to file.
        if (os.path.isfile(dst)):
            return True
        return False

    def __getListOfReports(self, cmdLineListOfReports, cmdLineReportPath):
        """
        This function returns a list of paths to reports based on
        arguments given. The function takes params that is a list of
        reports or path to where reports could be located to add to list.

        @return: Returns a list of paths to reports based on
        arguments given.

        @param cmdLineListOfReports: A list of paths to reports that will
        be extracted.
        @type cmdLineListOfReports: Array
        @param cmdLineReportPath: A path to a directory that contains
        reports.
        @type cmdLineReportPath: String
        """
        # Temporary list of reports that have not been validated
        listOfReports = []
        # Create a list of all possible reports.
        if (len (cmdLineListOfReports) > 0):
            for pathToFilename in cmdLineListOfReports:
                try:
                    if (not os.path.exists(pathToFilename)):
                        message = "The path to the report does not exist: %s" %(pathToFilename)
                        logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                    elif (os.path.isfile(pathToFilename)):
                        listOfReports.append(pathToFilename)
                    elif (os.path.isdir(pathToFilename)):
                        message = "The directory will be skipped: %s" %(pathToFilename)
                        logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                    else:
                        message = "The file will not be added: %s" %(pathToFilename)
                        logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                except OSError:
                    message = "There was an error evaluating the file: %s." %(pathToFilename)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).warn(message)
        elif (os.path.isdir(cmdLineReportPath)):
            try:
                # Add all files in this directory to the list and sort later.
                dirList = os.listdir(cmdLineReportPath)
                for filename in dirList:
                    pathToFilename = os.path.join(cmdLineReportPath, filename)
                    if (not os.path.exists(pathToFilename)):
                        message = "The path to the report does not exist: %s" %(pathToFilename)
                        logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                    elif (os.path.isfile(pathToFilename)):
                        listOfReports.append(pathToFilename)
                    elif (os.path.isdir(pathToFilename)):
                        message = "The directory will be skipped: %s" %(pathToFilename)
                        logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                    else:
                        message = "The file will not be added: %s" %(pathToFilename)
                        logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            except OSError:
                message = "There was an error getting a directory list for reports: %s." %(cmdLineReportPath)
                logging.getLogger(sx.MAIN_LOGGER_NAME).warn(message)
        return listOfReports


    def __cleanup(self, listOfReportsExtracted):
        # #######################################################################
        # Remove the compressed and extraction directory since nothing was
        # extracted and we do not want empty directories. This is ran after the
        # run() method is ran.
        # #######################################################################
        # Remove the compressed directory if it is empty.
        if ((os.path.exists(self.__al.getPathToCompressedReports())) and (not len(listOfReportsExtracted) > 0)):
            if (not FileUtil.dirFileCount(self.__al.getPathToCompressedReports()) > 0):
                try:
                    os.rmdir(self.__al.getPathToCompressedReports())
                except OSError:
                    message = "There was an error removing the non-empty directory: %s." %(self.__al.getPathToCompressedReports())
                    logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        # Remove the extraction directory if it is empty.
        if ((os.path.exists(self.__al.getPathToExtractedReports())) and (not len(listOfReportsExtracted) > 0)):
            if (not FileUtil.dirFileCount(self.__al.getPathToExtractedReports()) > 0):
                try:
                    os.rmdir(self.__al.getPathToExtractedReports())
                except OSError:
                    message = "There was an error removing the non-empty directory: %s." %(self.__al.getPathToExtractedReports())
                    logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        # #######################################################################
        # Remove all the temporary files created by the extraction. The
        # temporary directory created by Extraction classes, usually directory
        # /tmp/sx-*. All tarballs extract to here.
        # #######################################################################
        Extractor.clean()
        # #######################################################################
        # The plugins are done running and post-sxconsole action is done.
        # Remove tmp files since we are done with reportExtractor object
        # #######################################################################
        for report in listOfReportsExtracted:
            report.clean()


    # #######################################################################
    # The main functino to do the setup, extraction and analyzing.
    # #######################################################################
    def run(self):
        """
        This is main method that will start the extraction and analyzing then
        return a list of plugins that were ran.
        """
        # #######################################################################
        # Execute the main function to do the action if an ArchiveLayout object
        # created which means that all the information needed is valid.
        # #######################################################################
        listOfEnabledPlugins = []
        if (not self.__al == None):
            # #######################################################################
            # Get the list of extracted reports that were extracted or loaded.
            # #######################################################################
            listOfReportsExtracted = self.__extractReports(self.__al,
                                                           self.__optionsMap.get("pathToExtractedReports"),
                                                           self.__optionsMap.get("listOfReports"),
                                                           self.__optionsMap.get("reportPath"),
                                                           (not self.__optionsMap.get("disableUserDefinedModules")))

            # Set archive location if there was reports load/extracted.
            if (len(listOfReportsExtracted) > 0):
                # #######################################################################
                # Run the plugins on the extracted reports
                # #######################################################################
                # Get list of enabled plugins.
                pluginsHelper = PluginsHelper()
                # For now this map is empty
                listOfEnabledPlugins = pluginsHelper.getEnabledPluginsList(self.__al.getPathToExtractedReports(),
                                                                           self.__optionsMap.get("enableAllPlugins"),
                                                                           self.__optionsMap.get("disableAllPlugins"),
                                                                           self.__optionsMap.get("enablePlugins"),
                                                                           self.__optionsMap.get("disablePlugins"),
                                                                           self.__getPluginOptions(self.__optionsMap.get("pluginOptions")),
                                                                           (not self.__optionsMap.get("disableUserDefinedModules")))
                # Print a list of enabled plugins.
                if (len(listOfEnabledPlugins) > 0) :
                    message = "There was %d plugins enabled." %(len(listOfEnabledPlugins))
                    logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
                    # Generate map of all plugins reports that were created after they run.
                    pluginsHelper.generatePluginReports(listOfReportsExtracted, listOfEnabledPlugins)
                else:
                    logging.getLogger(sx.MAIN_LOGGER_NAME).info("Skipping plugins since there was no plugins enabled.")

                self.__cleanup(listOfReportsExtracted)
            return listOfEnabledPlugins


