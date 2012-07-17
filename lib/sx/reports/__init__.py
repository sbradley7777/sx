#!/usr/bin/env python
"""
This class is a container for different kind of reports. This is the
base class that all report types should inherit.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.10
@copyright :  GPLv2
"""
import os
import os.path
import shutil
import re
import logging

import sx
from sx.logwriter import LogWriter
from sx.tools import ConsoleUtil
from sx.modulesloader import ReportsLoader

class ReportsHelper:
    def printReportsList(self, includeUserReports=True):
        """
        Do a dry run on creating reports and plugins to print information
        to the console for the user. If includeUserReports is enabled
        then users custom reports will be included.

        param includeUserReports: If includeUserReports is enabled
        then users custom reports will be included. By default it
        is enabled.
        type includeUserReports: Boolean
        """
        # Load the reports
        reportsLoader = ReportsLoader()
        loadedReport = reportsLoader.load(includeUserReports)
        if (not len(loadedReport) > 0):
            logging.getLogger(sx.MAIN_LOGGER_NAME).error("There were no reports found.")
        else:
            print "List of installed report types:"
            for report in loadedReport:
                print "%s(%s):  %s" %(ConsoleUtil.colorText(report.getName(),"lblue"),
                                      report.TYPE_DETECTION_FILE,
                                      report.getDescription())


class Report:
    """
    This class is a container for different kind of reports. This is
    the base class that all report types should inherit.
    """
    def __init__(self, name, description, disableReadCopy=True, stripDirectoriesDepth=1) :
        """
        @param name: The name of the report.
        @type name: String
        @param description: A description of the report.
        @type description: String
        @param disableReadCopy: The boolean that if True will not copy a
        file to tmp location before reading it.
        @type disableReadCopy: Boolean
        @param stripDirectoriesDepth: This value will strip the root
        directories of the report to a depth that is given. Default is 1.
        @type stripDirectoriesDepth: Int
        """
        self.__name = name
        self.__description = description
        # The Default is 1 for how many directories need to be
        # removed.
        self.__stripDirectoriesDepth = stripDirectoriesDepth

        self.__pathToExtractedReport = ""
        self.__pathToTmpExtractedReport = ""

        # This option is for enabling/disabling copying a file to tmp
        # directory before reading it so that it is preserved.
        self.__disableReadCopy = disableReadCopy

    def __str__(self) :
        """
        Returns a formatted string of this object.

        @return: Returns a formatted string of this object.
        @rtype: String
        """
        return "%s: %s" %(self.getName(), self.getDescription())

    def getName(self) :
        """
        Returns name of the report.

        @return: Returns name of the report.
        @rtype: String
        """
        return self.__name

    def getDescription(self) :
        """
        Returns description of the report.

        @return: Returns description of the report.
        @rtype: String
        """
        return self.__description

    def getPathToExtractedReport(self) :
        """
        This function returns the path to the extracted report.

        @return: Returns the path to the extracted report.
        @rtype: String
        """
        return self.__pathToExtractedReport

    def getType(self) :
        """
        This function returns the class name of this report.

        @return: The class name of the report.
        @rtype: String
        """
        return self.__class__.__name__

    def setPathToExtractedReport(self, pathToExtractedReport):
        """
        This is helper function that will set the paths for
        extracted report path and temp extracted report path.

        @param pathToExtractedReport: Path to the extracted report.
        @type pathToExtractedReport: String
        """
        self.__pathToExtractedReport = pathToExtractedReport
        (head, tail) = os.path.split(self.__pathToExtractedReport)
        self.__pathToTmpExtractedReport = os.path.join(head, ".%s" %(tail))

    # ##########################################################################
    # Helper action functions
    # ##########################################################################
    def __copy(self, src, dst) :
        """
        Returns the path to the file that was copied from src to dst
        path. Empty string is returned if no file was copied because
        of an error.

        This function makes a temporary copy of the file, it does not
        return the actual path to the extracted report. This is an
        extact duplicate of the extracted report. The temporary
        directory of files is dynamically created as requests are
        made. If file is already copied then it does not create it
        again.

        @return: Returns the path to the file that was copied from
        src to dst path. Empty String is returned if copy was not completed.
        @rtype: String

        @param src: The path to the source file to copy.
        @type src: String
        @param dst: The path to the destination file to copy src file
        to.
        @type dst: String

        """
        if (os.path.isfile(src)) :
            pDir,filename = os.path.split(dst)
            try:
                if not os.access(pDir, os.F_OK):
                    os.makedirs(pDir)
            except (IOError, os.error):
                message =  "Cannot create directory: %s" % (pDir)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return ""
            try:
                # If file already exist then do not overwrite it, just
                # return the dst.
                if not (os.path.isfile(dst)) :
                    shutil.copyfile(src, dst)
                return dst
            except (IOError, os.error):
                message = "IOerror occured copying the file %s to destination \n\t%s" % (src, dst)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return ""
        elif (os.path.isdir(src)):
            try:
                if not os.access(dst, os.F_OK):
                    os.makedirs(dst)
            except (IOError, os.error):
                message =  "Cannot create directory: %s" %(pDir)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return ""
            for f in os.listdir(src):
                srcPath = os.path.join(src, f)
                dstPath = os.path.join(dst, f)
                self.__copy(srcPath, dstPath)
            return dst
        # Return empty string if file/dir does not exist
        return ""

    def clean(self) :
        """
        Remove the temporary location of files that were copied from
        extracted report.
        """
        if os.path.exists(self.__pathToTmpExtractedReport):
            try:
                shutil.rmtree(self.__pathToTmpExtractedReport)
            except OSError:
                message = "There was an error removing the directory: %s" %(self.__pathToTmpExtractedReport)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)

    # ##########################################################################
    # Extract File/Data from extracted sreports functions
    # ##########################################################################
    def includesOtherReports(self):
        """
        By default it will return False. If the other report contains
        other report types then set to True. The reason is that if
        True we can add the reports within the report to extraction
        process.

        @return: Returns True if there are other report types within
        this report that should be extracted.
        @rtype: Boolean
        """
        return False

    def getDataFromFile(self, pathToFile) :
        """
        This function will return the data in an array. Where each
        newline in file is a seperate item in the array. This should
        really just be used on relatively small files.

        None is returned if no file is found.

        @return: Returns an array of Strings, where each newline in
        file is an item in the array.
        @rtype: Array

        @param pathToFile: The path to the file, which is relative to
        the root report directory.
        @type pathToFile: String
        """
        pathToFile = self.getPathForFile(pathToFile)
        if (len(pathToFile) > 0) :
            try:
                fin = open(pathToFile, "r")
                data = fin.readlines()
                fin.close()
                return data
            except (IOError, os.error):
                message = "An error occured reading the file: %s." %(pathToFile)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            else:
                fin.close()
        return None

    def __getPathForDir(self, pathToDir):
        """
        This function will return the path to the directory. If
        the directory does not exist then empty string is returned.

        This function will not make a copy of the directory. Will only
        return a path to the orginal dir.

        @return: Returns the path to the directory. Empty string
        is returned if no directory is found.

        @param pathToDir: The path to the file, which is relative to
        the root report directory.
        @type pathToDir: String
        """
        if (len(pathToDir) > 0):
            src = os.path.join(self.__pathToExtractedReport, pathToDir).strip()
            if (os.path.isdir(src)):
                return src
        # This function will not make a copy of the directory.
        return ""

    def getDataFromDir(self, pathToDir):
        """
        This function will create a dictionary that contains all the
        data from every file in a directory. If the pathToDir is not a
        path to a directory then an empty dictionary is returned. This
        function will not read in any sub directories.

        This function will only go down 1 subdirectory and only return the files
        within that subdirectory.
        Example:
        sambaConfigMaps = report.getDataFromDir("etc/cluster/samba/*")

        @return: Returns a dictionary that contains the data for all
        files in that directory. The filename is the key and data is
        file is the value.
        @rtype: Dictionary

        @param pathToDir: The path to the directory, which is relative to
        the root report directory.
        @type pathToDir: String
        """
        fileDataMap = {}
        fullPathToDir = self.getPathForFile(pathToDir)
        # If a directory is requested with ending astericks then get all the
        # files in its subdirectories and root directory.
        if (pathToDir.endswith('/*')):
            # Strip the /* from the end of the path to get the root, so that we
            # can go 1 sub directory deep to get any files that exists in root
            # of the directory and in its sub directories.
            pathToDirMod = pathToDir.rstrip('/*')
            fullPathToDir = self.__getPathForDir(pathToDirMod)
            if (os.path.exists(fullPathToDir)):
                dirList = os.listdir(fullPathToDir)
                for currentFilename in dirList:
                    fullPathToCurrentFilename = os.path.join(fullPathToDir, currentFilename)
                    if (os.path.isdir(fullPathToCurrentFilename)):
                        subDirList = os.listdir(fullPathToCurrentFilename)
                        for subFilename in subDirList:
                            fullPathToSubFilename = os.path.join(fullPathToCurrentFilename, subFilename)
                            if (os.path.isfile(fullPathToSubFilename)):
                                splitPath = fullPathToSubFilename.split("%s/" %(self.__pathToExtractedReport))
                                if (len(splitPath) == 2):
                                    currentData = self.getDataFromFile(splitPath[1])
                                    if (not currentData == None):
                                        fileDataMap[splitPath[1]] = currentData
                    elif (os.path.exists(fullPathToCurrentFilename)):
                        splitPath = fullPathToCurrentFilename.split("%s/" %(self.__pathToExtractedReport))
                        if (len(splitPath) == 2):
                            currentData = self.getDataFromFile(splitPath[1])
                            if (not currentData == None):
                                fileDataMap[splitPath[1]] = currentData
        elif (os.path.isdir(fullPathToDir)):
            try:
                # Add all files in this directory to the list and sort later.
                dirList = os.listdir(fullPathToDir)
                for currentFilename in dirList:
                    # Skip directories
                    if (not os.path.isdir(os.path.join(fullPathToDir, currentFilename))):
                        currentData = self.getDataFromFile("%s/%s" %(pathToDir, currentFilename))
                        if (not currentData == None):
                            fileDataMap[currentFilename] = currentData
            except OSError:
                message = "There was an error getting a directory list for reports: %s." %(fullPathToDir)
                logging.getLogger(sx.MAIN_LOGGER_NAME).warn(message)
        return fileDataMap

    def getFileSize(self, pathToFile):
        """
        Returns the actual filesize of a file in bytes. -1 is returned
        if file does not exist.

        @return: Returns the actual filesize of a file in bytes. -1 is
        returned if file does not exist.
        @rtype: Long

        @param pathToFile: The path to the file which is not the full
        path but a subset of the path.
        @type pathToFile: String
        """
        # -1 means file does not exist.
        fileSize = -1
        if (len(pathToFile) > 0):
            src = os.path.join(self.__pathToExtractedReport, pathToFile)
            if (os.path.exists(src)):
                fileSize = os.path.getsize(src)
                return fileSize
        return fileSize

    def getPathForFile(self, pathToFile):
        """
        This function will return the path to the temporary file. If
        file does not exist then empty string is returned.

        @return: Returns the path to the temporary file. Empty string
        is returned if no file is found.

        @param pathToFile: The path to the file, which is relative to
        the root report directory.
        @type pathToFile: String
        """
        if (len(pathToFile) > 0):
            src = os.path.join(self.__pathToExtractedReport, pathToFile).strip()
            dst = os.path.join(self.__pathToTmpExtractedReport, pathToFile)
            # Cannot check if file cause we have symlinks in report
            if (os.path.exists(src)):
                if (self.__disableReadCopy):
                    return src
                else:
                    # A copy of the file will be made so that orginal file is
                    # preserved. After the copy function is complete the path
                    # of new file will be returned.
                    pathToSrcCopy = self.__copy(src,dst)
                    if (os.path.exists(pathToSrcCopy)):
                        return pathToSrcCopy
                    else:
                        message = "The path to the copied file does not exist: %s." %(pathToSrcCopy)
                        logging.getLogger(sx.MAIN_LOGGER_NAME).warn(message)
        return ""

    def extract(self, extractor, extractDir):
        """
        This function will extract the report to the extract
        dir.

        This function should be overwrriten with the specific report
        type extraction function. Returns True if there is not fatal
        errors.

        This function should be overridden by all report objects that
        inherit this class if they want the extraction directory to be
        called something other than what is contained in the report.

        @return: Returns True if there was no fatal errors. Tar
        errors are ignored because they should not be fatal, if they
        are the child should catch the errors since dir will not
        exist. If there are fatal errors, then False is returned.
        @rtype: boolean

        @param extractor: An extractor object that contains the path to the
        file that will be extracted.
        @type extractor: Extractor
        @param extractDir: The full path to directory for extraction.
        @type extractDir: String
        """
        message = "Extracting the %s: %s" %(self.getName(), extractor.getPathToFile())
        logging.getLogger(sx.MAIN_LOGGER_NAME).status(message)
        if (not len(extractDir) > 0):
            return False
        # Check for duplicate extraction point and rename if it exists.
        if os.path.exists(extractDir) :
            for i in range(1, 100) :
                (head, tail) = os.path.split(extractDir)
                duplicatePath = os.path.join(head, "%s-duplicate_%s" %(tail, str(i)))
                if (not os.path.exists(duplicatePath)) :
                    # Directory does not exist so we can extract to this path
                    extractDir = duplicatePath
                    break;
        # Set path to extraction point and temporary directory
        self.setPathToExtractedReport(extractDir)
        # Do the extraction of the file
        try:
            if not os.access(self.__pathToExtractedReport, os.F_OK):
                os.makedirs(self.__pathToExtractedReport)
        except (IOError, os.error):
            message =  "IO error occured on creating the directory: %s." %(self.__pathToExtractedReport)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        return extractor.extract(self.__pathToExtractedReport, self.__stripDirectoriesDepth)


