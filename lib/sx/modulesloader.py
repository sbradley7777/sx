#!/usr/bin/env python
"""
This file contains 4 classes. ModulesLoader is default loader for all
modules: reports, plugins, and extractors.

ReportsLoader is a child of the ModulesLoader class that loads report modules.
PluginsLoader is a child of the ModulesLoader class that loads plugin modules.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.15
@copyright :  GPLv2
"""
import os
import os.path
import logging
import sys
import re

import sx
from sx.logwriter import LogWriter

class ModulesLoader :
    """
    This is the base loader for loading reports, plugins, and
    extractors.
    """
    def __init__(self):
        pass

    def __validateModule(self, modulePath) :
        """
        This is not implmented yet, but should verify that this is a
        module for sx and is valid.

        @return: Returns True if this valid sx module.
        @rtype: Boolean

        @param modulePath: The path to the module.
        @type modulePath: String
        """
        return True

    def __importModule(self, pathToModuleFile, moduleClassName):
        """
        This function will return a new class object based on the path and
        class name. None is returned if there is an error.

        @return: Returns a new class object based on path and class
        name. None is returned if there is an error.
        @rtype: Class

        @param pathToModuleFile: This is the path to module file that is in
        the python path.
        @type pathToModuleFile: String
        @param moduleClassName: Name of the class that will be imported
        @type moduleClassName: String
        """
        try:
            module = __import__(pathToModuleFile, globals(), locals(), [moduleClassName])
            return getattr(module, moduleClassName)
        except ValueError:
            pass
        except ImportError,e:
            message ="Import module error occurred on importing the Class \"%s\" from import: %s" %(moduleClassName, pathToModuleFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            print e
        return None

    def getClasses(self, pathToModuleBaseDir, moduleImportBase):
        """
        This class will return a list of classes based on path
        information.

        @return: Returns a list of classes based on path information.
        @rtype: Array

        @param pathToModuleBaseDir: The path to the base directory
        that contains the modules.
        @type pathToModuleBaseDir: String
        @param moduleImportBase: The name of the modules base
        python import name.
        @type moduleImportBase: String
        """
        #message = "Getting the classes for the base %s from the path: %s." %(moduleImportBase, pathToModuleBaseDir)
        #logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        # List of modules
        loadedModuleClasses = []

        if ((not len(pathToModuleBaseDir) > 0) or (not len(moduleImportBase) > 0)):
                return loadedModuleClasses

        # Set path to root of modules import
        pathToClassesDir = ("%s/%s") %(pathToModuleBaseDir, moduleImportBase.replace(".", "/"))

        # If the directory does not exist then nothing to do
        if (not (os.path.isdir(pathToClassesDir))):
            return loadedModuleClasses

        # Add path to modules if it does not exist in python path
        if (not (pathToModuleBaseDir in sys.path)) :
            sys.path.append(pathToModuleBaseDir)

        # Get list of files and load the classes into an array if they
        # are valid modules
        filenames = os.listdir(pathToClassesDir)
        filenames.sort()
        # validate and load modules
        for filename in filenames:
            moduleFilename =  filename[:-3]
            if ((not filename[-3:] == ".py") or (moduleFilename == "__init__")):
                continue
            if (self.__validateModule(os.path.join(pathToClassesDir,filename))) :
                try:
                    # First letter of module filename's class has to be be capitalized.
                    moduleClass = self.__importModule("%s.%s" %(moduleImportBase, moduleFilename), str.capitalize(moduleFilename))
                    if (not moduleClass == None):
                        loadedModuleClasses.append(moduleClass)
                except AttributeError:
                    message = "The class module was not found for %s." %(moduleFilename)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
            else:
                message = ("Module %s does not validate, skipping.") % (filename)
                logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
                continue
        return loadedModuleClasses

    def load(self, pathToModuleBaseDir, moduleImportBase):
        """
        This class will return a list of loaded(instance) objects based on path
        information.

        @return: Returns a list of loaded(instance) objects based on
        path information.
        @rtype: Array

        @param pathToModuleBaseDir: The path to the base directory
        that contains the modules.
        @type pathToModuleBaseDir: String
        @param moduleImportBase: The name of the modules base
        python import name.
        @type moduleImportBase: String
        """
        loadedModuleClasses = self.getClasses(pathToModuleBaseDir, moduleImportBase)
        loadedModules = []
        for moduleClass in loadedModuleClasses:
            if (not moduleClass == None):
                moduleInstance = moduleClass()
                loadedModules.append(moduleInstance)
        return loadedModules

class ReportsLoader(ModulesLoader) :
    """
    This class will load or perform various operations on report
    objects.
    """
    def __init__(self):
        ModulesLoader.__init__(self)
        self.__pathToBaseDir = sx.SXImportPath.generateBaseImportPath()

        # The report classes
        self.__coreClasses = self.getClasses(self.__pathToBaseDir, sx.REPORT_CORE_IMPORT)
        self.__userClasses = self.getClasses(sx.SXConfigurationFiles.CONFIGURATION_DIR,
                                             sx.SXConfigurationFiles.REPORT_USER_IMPORT)
        # Build the regex for searching.
        self.__findRegexCore =self. __buildFindReportRegex(self.__coreClasses)
        self.__findRegexUser =self. __buildFindReportRegex(self.__userClasses)

        # Load up extractors
        self.__extractorsLoader = ExtractorsLoader()

    def __buildFindReportRegex(self, reportClasses) :
        """
        Returns a regex string based on type detection file
        in report classes.

        Do note that certain characters are not allowed in filename
        because of re rules. All whitespaces will be turned to
        underscores.

        @return: Returns a regex string based on type detection file
        in report classes.
        @rtype: Class

        """
        # Build the expression for all the different signature
        # files inside that report file.
        regex = ""
        for reportClass in reportClasses:
            # Escape out . with \.
            if (len(regex) > 0) :
                regex += "|"
            if (not reportClass == None) :
                regex += "(?P<%s>.*%s.*)" %(reportClass.REPORT_NAME.replace(" ", "_"), reportClass.TYPE_DETECTION_FILE.replace(".", "\."))
        return regex

    def __findReport(self, listOfFilenames, includeUserReports=True) :
        """
        Returns the class that matches the report file. None is
        returned if no report type is found. This function is for
        matching a file in list of filenames to a unique file that
        identiifes the that this list of files is a certain report.

        @return: Returns the class for that matches the report.
        @rtype: Class

        @param listOfFilenames: A list of filenames that will be
        searched.
        @type listOfFilenames: Array
        @param includeUserReports: If enable the user modules(reports) will
        be searched. Default is True
        @type includeUserReports: Boolean
        """

        if (len(listOfFilenames) > 0) :
            regex = self.__findRegexCore
            reportClasses = self.__coreClasses
            if (includeUserReports):
                regex = "%s|%s" %(self.__findRegexCore, self.__findRegexUser)
                reportClasses += self.__userClasses
            detectionFileMap = {}
            for reportClass in reportClasses:
                detectionFileMap[reportClass.REPORT_NAME.replace(" ", "_")] = reportClass
            #message = "The regular expression used for searching for report types:\n\t  %s." %(regex)
            #logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            rem = re.compile(regex)
            for line in listOfFilenames:
                mo = rem.match(line)
                if mo:
                    if (detectionFileMap.has_key(mo.lastgroup)):
                        reportClass = detectionFileMap.get(mo.lastgroup)
                        report = reportClass()
                        return report
        return None

    def getReportByName(self, reportName, includeUserReports=True):
        reportClasses = self.__coreClasses
        if (includeUserReports):
            reportClasses += self.__userClasses
        for reportClass in reportClasses:
            if (reportClass.REPORT_NAME == reportName):
                report = reportClass()
                return report
        return None

    def getReport(self, pathToFilename, includeUserReports=True):
        """
        If a path to dir, then it will just search to see if dir is
        signature of an extracted report. If file then it will see if
        extracted file contains a known report type.
        """
        # List of files that will be searched to see if they contain
        # report signatures.
        message = "Searching for a known report type from the path: %s." %(pathToFilename)
        logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        listOfFilenames = []
        if (os.path.isfile(pathToFilename)):
            # If file then i need to extract with extractor to get list of files.
            extractor = self.__extractorsLoader.getExtractor(pathToFilename, includeUserReports)
            if (not extractor == None):
                listOfFilenames = extractor.list()
        elif (os.path.isdir(pathToFilename)):
            # If dir i dont need to extract anything just search the dir
            listOfFilenames = []
            for root, dirs, files in os.walk(pathToFilename):
                for currentFilename in files:
                    listOfFilenames.append(os.path.join(root, currentFilename))
        report = self.__findReport(listOfFilenames, includeUserReports)
        if (report == None) :
            message = "The report type could not be determined for the filepath: %s." %(pathToFilename)
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        else:
            message = "The filepath is a known report type: %s." %(report.getName())
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        return report

    def getReportFromList(self, listOfFilenames, includeUserReports=True):
        """
        Return Report object by searching a list of filenames.
        """
        report = self.__findReport(listOfFilenames, includeUserReports)
        if (report == None) :
            message = "The report type could not be determined from the list of filenames."
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        return report

    def load(self,includeUserReports=True):
        """
        This class will return a list of loaded(instance) objects based on path
        information.

        @return: Returns a list of loaded reports.
        @rtype: Array

        @param includeUserReports: If enable the user modules(reports) will
        be loaded. Default is True
        @type includeUserReports: Boolean
        """
        loadedModules = ModulesLoader.load(self, self.__pathToBaseDir, sx.REPORT_CORE_IMPORT)
        if (includeUserReports):
            loadedModules += ModulesLoader.load(self, sx.SXConfigurationFiles.CONFIGURATION_DIR,
                                                sx.SXConfigurationFiles.REPORT_USER_IMPORT)
        return loadedModules


class PluginsLoader(ModulesLoader) :
    """
    This class will load plugins and do various operations on plugins.
    """

    def __init__(self):
        ModulesLoader.__init__(self)
        self.__pathToBaseDir = sx.SXImportPath.generateBaseImportPath()

    def load(self, pathToPluginReportDir, includeUserPlugins=True):
        """
        This class will return a list of loaded(instance) objects based on path
        information.

        @return: Returns a list of loaded(instance) objects based on
        path information.
        @rtype: Array

        @param pathToPluginReportDir: Root directory for the path for
        which plugin report will be written.
        @type pathToPluginReportDir: String
        @param includeUserPlugins: If enable the user modules(plugins) will
        be loaded. Default is True.
        @type includeUserPlugins: Boolean
        """
        mClasses = self.getClasses(self.__pathToBaseDir, sx.PLUGIN_CORE_IMPORT)
        if (includeUserPlugins):
            mClasses += self.getClasses(sx.SXConfigurationFiles.CONFIGURATION_DIR,
                                       sx.SXConfigurationFiles.PLUGIN_USER_IMPORT)
        loadedModules = []
        for mClass in mClasses:
            if (not mClass == None):
                loadedModule = mClass(pathToPluginReportDir)
                loadedModules.append(loadedModule)
        return loadedModules

class ExtractorsLoader(ModulesLoader) :
    """
    This class returns Extractor objects.
    """
    def __init__(self):
        ModulesLoader.__init__(self)
        self.__pathToBaseDir = sx.SXImportPath.generateBaseImportPath()
        self.__extractorsImport = "sx.extractors"

        # Going to try preloading the classes
        self.__classes = ModulesLoader.getClasses(self, self.__pathToBaseDir, self.__extractorsImport)

    def getExtractor(self, pathToFilename, includeUserExtractors=True):
        """
        This function will return an extractor based on the pathToFilename.

        @return: Returns an extractor based on file type if an
        extractor exists for it.
        @rtype: Extractor

        @param pathToFilename: A pathToFilename that will be used to match to an extractor.
        @type pathToFilename: String
        @param includeUserExtractors: This will enable user written
        extractors to be used. Currently there is no support for user
        written extractors.
        @type includeUserExtractors: Boolean
        """
        # Currently there are no user extractors, but code will eventually.
        for extractorClass in self.__classes:
            extractor = extractorClass(pathToFilename)
            if (extractor.isValidMimeType()):
                return extractor
        # If no extractor is found then return None.
        return None

    def getExtractors(self, listOfFilenames, includeUserExtractors=True) :
        """
        This function will return a list of Extractor objects that
        were found. An Extractor object will only be created if it is
        a known type. If it is not a known type then file will not be
        added.

        @return: An array of Extractor objects.
        @rtype: Array

        @param listOfFilenames: An array of paths to a file.
        @type listOfFilenames: String
        @param includeUserExtractors: This will enable user written
        extractors to be used. Currently there is no support for user
        written extractors.
        @type includeUserExtractors: Boolean
        """
        # Now just get a list of known report extractor types.
        listOfExtractors = []
        for pathToFilename in listOfFilenames:
            # Currently there are no user extractors, but code will eventually.
            extractor = self.getExtractor(pathToFilename, includeUserExtractors)
            if (not extractor == None):
                listOfExtractors.append(extractor)
        return listOfExtractors

