#!/usr/bin/env python
"""
This contains Global variables for sx.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""
import sys
import os.path
import logging
import datetime

from sx.logwriter import LogWriter
"""
@cvar MAIN_LOGGER_NAME: The name of the main logger
@type MAIN_LOGGER_NAME: String
@cvar MAIN_LOGGER_FORMAT: The format that log messages will be displayed.
@type MAIN_LOGGER_FORMAT: String
@cvar MAIN_LOGGER_TIMESTAMP_FORMAT: The format that log message will be
displayed with timestamp.
@type MAIN_LOGGER_TIMESTAMP_FORMAT: String
@cvar UID_TIMESTAMP: This is the time format for the unique directory id.
@type UID_TIMESTAMP: String
@cvar REPORT_CORE_IMPORT: The name of the core reports python library.
@type REPORT_CORE_IMPORT: String
@cvar PLUGIN_CORE_IMPORT: The name of the core plugin python library.
@type PLUGIN_CORE_IMPORT: String
"""
MAIN_LOGGER_NAME = "sx"
MAIN_LOGGER_FORMAT = "%(levelname)s %(message)s"
MAIN_LOGGER_TIMESTAMP_FORMAT = "%(asctime)s %(levelname)s %(message)s"
UID_TIMESTAMP = "%Y-%m-%d_%H%M%S"
REPORT_CORE_IMPORT="sx.reports"
PLUGIN_CORE_IMPORT="sx.plugins"

class SXImportPath:
    def generateBaseImportPath():
        pathToBaseDir = ""
        # #######################################################################
        # Search for user defined paths to modules such as for devel.
        # #######################################################################
        for path in sys.path:
            result = path.find("sx/lib")
            if (result >= 0) :
                # Found a user defined path for sx, so that is base
                # path that will be used.
                pathToBaseDir = path
                break;

        # #######################################################################
        # If no user path is defined for sx then the python paths will
        # be searched.
        # #######################################################################
        if (not len(pathToBaseDir) > 0):
            for path in sys.path :
                # Find the first occurance
                if (((path.strip()[-len("site-packages"):]) == "site-packages") and
                    (os.path.isdir(path + "/sx/reports") or
                     os.path.isdir(path + "/sx/plugins"))) :
                    pathToBaseDir = path
                    break;
        return pathToBaseDir
    generateBaseImportPath = staticmethod(generateBaseImportPath)

class ArchiveLayout:
    """
    This class will generate the paths based on a given archivePath
    and uid for all the directories that will be used by sx.

    Example of Layout:
    Compressed Reports Path:   ~/sxarchive/creports/15555553/2.17-04-18_123703
    Extracted Reports Path:    ~/sxarchive/ereports/15555553/2.17-04-18_123703
    Non-report Files Path:     ~/sxarchive/ereports/15555553/files
    """
    def __init__(self, archivePath, uid, timestamp=""):
        """
        @param archivePath: The root directory where all the files
        will be archived.
        @type archivePath: String
        @param uid: A unique identifer for the collection of files.
        @type uid: String
        @param timestamp: A string that represents a time stamp which
        is unique.
        @type timestamp: String
        """
        self.__archivePath = archivePath
        self.__uid = uid
        self.__timestamp = timestamp
        if (not len(timestamp) > 0):
            self.__timestamp = datetime.datetime.now().strftime(UID_TIMESTAMP)
        else:
            # Check to see if timestamp is valid and ValueError will be thrown
            # if invalid. This needs to be caught because the format would be
            # invalid.
            self.__timestamp = datetime.datetime.strptime(timestamp, UID_TIMESTAMP).strftime(UID_TIMESTAMP)

    def __str__(self) :
        """
        Returns a string that prints out the various variables.

        @return: Returns a string that prints out the various variables.
        @rtype: String
        """
        rstring  = "Archive Path:             %s\n" %(self.getPathToArchiveRoot())
        rstring += "UID:                      %s\n" %(self.getUID())
        rstring += "Timestamp:                %s\n" %(self.getTimestamp())
        rstring += "Extracted Report Path:    %s\n" %(self.getPathToExtractedReports())
        rstring += "Compressed Report Path:   %s\n" %(self.getPathToCompressedReports())
        rstring += "Non-Report Path:          %s\n" %(self.getPathToNonReportFiles())
        return rstring

    def getPathToArchiveRoot(self) :
        """
        Returns the archive path that is the root for all files.

        @return: Returns the archive path that is the root
        for all files.
        @rtype: String
        """
        return self.__archivePath

    def getUID(self) :
        """
        Returns the uid.

        @return: Returns the uid.
        @rtype: String
        """
        return self.__uid

    def getTimestamp(self):
        """
        Returns the timestamp that was generated.

        @return: Returns the timestamp that was generated.
        @rtype: String
        """
        return self.__timestamp

    def getPathToCompressedReports(self):
        """
        Returns the path to the compressed reports directory.

        @return: Returns the path to the compressed reports directory.
        @rtype: String
        """
        return  os.path.join(os.path.join(os.path.join(self.getPathToArchiveRoot(), "creports"), self.getUID()), self.getTimestamp())

    def getPathToExtractedReports(self):
        """
        Returns the path to the extracted reports directory.

        @return: Returns the path to the extracted reports directory.
        @rtype: String
        """
        return  os.path.join(os.path.join(os.path.join(self.getPathToArchiveRoot(), "ereports"), self.getUID()), self.getTimestamp())

    def getPathToNonReportFiles(self):
        """
        Returns the path to the non-reports directory

        @return: Returns the path to the non-reports directory.
        @rtype: String
        """
        return  os.path.join(os.path.join(os.path.join(self.getPathToArchiveRoot(), "ereports"), self.getUID()), "files")

class ArchivedLayout(ArchiveLayout):
    """
    This class takes an existing extracted reports path and creates
    the correct strings to the path of all directories for sx.

    Example of Layout:
    Compressed Reports Path:   ~/sxarchive/creports/15555553/2.17-04-18_123703
    Extracted Reports Path:    ~/sxarchive/ereports/15555553/2.17-04-18_123703
    Non-report Files Path:     ~/sxarchive/ereports/15555553/files
    """
    def __init__(self, pathToExistingArchive):
        """
        @param pathToExistingArchive: This is path to existing
        extracted report directory.
        @param pathToExistingArchive: String
        """
        pathToExistingArchive = pathToExistingArchive.rstrip("/")
        (head, tail) = os.path.split(pathToExistingArchive)
        timestamp = tail
        (head, tail) = os.path.split(head)
        uid = tail
        (head, tail) = os.path.split(head)
        archivePath = head
        ArchiveLayout.__init__(self, archivePath, uid, timestamp)

class ModifiedArchiveLayout(ArchiveLayout):
    """
    This class will generate the paths based on a given archivePath
    and uid for all the directories that will be used by sx.

    Example of Layout:
    Compressed Reports Path:   ~/sxarchive/15555553/2.17-04-18_122701/.creports
    Extracted Reports Path:    ~/sxarchive/15555553/2.17-04-18_122701
    Non-report Files Path:     ~/sxarchive/15555553/files
    """
    def __init__(self, archivePath, uid, timestamp=""):
        """
        @param archivePath: The root directory where all the files
        will be archived.
        @type archivePath: String
        @param uid: A unique identifer for the collection of files.
        @type uid: String
        @param timestamp: A string that represents a time stamp which
        is unique.
        @type timestamp: String
        """
        ArchiveLayout.__init__(self, archivePath, uid, timestamp)

    def getPathToCompressedReports(self):
        """
        Returns the path to the compressed reports directory.

        @return: Returns the path to the compressed reports directory.
        @rtype: String
        """
        return  os.path.join(self.getPathToExtractedReports(), ".creports")

    def getPathToExtractedReports(self):
        """
        Returns the path to the extracted reports directory.

        @return: Returns the path to the extracted reports directory.
        @rtype: String
        """
        return  os.path.join(os.path.join(self.getPathToArchiveRoot(), self.getUID()), self.getTimestamp())

    def getPathToNonReportFiles(self):
        """
        Returns the path to the non-reports directory

        @return: Returns the path to the non-reports directory.
        @rtype: String
        """
        return  os.path.join(os.path.join(self.getPathToArchiveRoot(), self.getUID()), "files")

class ModifiedArchivedLayout(ModifiedArchiveLayout):
    """
    This class takes an existing extracted reports path and creates
    the correct strings to the path of all directories for sx.

    Example of Layout:
    Compressed Reports Path:   ~/sxarchive/15555553/2.17-04-18_122701/.creports
    Extracted Reports Path:    ~/sxarchive/15555553/2.17-04-18_122701
    Non-report Files Path:     ~/sxarchive/15555553/files
    """
    def __init__(self, pathToExistingArchive):
        """
        @param pathToExistingArchive: This is path to existing
        extracted report directory.
        @param pathToExistingArchive: String
        """
        pathToExistingArchive = pathToExistingArchive.rstrip("/")
        (head, tail) = os.path.split(pathToExistingArchive)
        timestamp = tail
        (head, tail) = os.path.split(head)
        uid = tail
        archivePath = head
        ModifiedArchiveLayout.__init__(self, archivePath, uid, timestamp)

class SXConfigurationFiles:
    """
    This class will create the configuration directory structure for
    sxconsole.

    @cvar REPORT_USER_IMPORT: The name of the user reports python library.
    @type REPORT_USER_IMPORT: String
    @cvar PLUGIN_USER_IMPORT: The name of the user plugin python library.
    @type PLUGIN_USER_IMPORT: String
    @cvar CONFIGURATION_DIR: The path to default configuration directory.
    @type CONFIGURATION_DIR: String
    """
    REPORT_USER_IMPORT="sxreports"
    PLUGIN_USER_IMPORT="sxplugins"
    CONFIGURATION_DIR = os.path.join(os.environ['HOME'],".sx")

    def generateDefaultConfigurationDirectories(self):
        """
        This function will create a configuration directory for sxconsole.

        @return: Returns True if configuration files/directories were
        created correctly.
        @rtype: Boolean
        """
        # Create the user defined directories if needed
        for path in (os.path.join(SXConfigurationFiles.CONFIGURATION_DIR, SXConfigurationFiles.REPORT_USER_IMPORT),
                     os.path.join(SXConfigurationFiles.CONFIGURATION_DIR, SXConfigurationFiles.PLUGIN_USER_IMPORT)):
            if not os.access(path, os.F_OK):
                message = "Creating the configuration directory: %s" % (path)
                logging.getLogger(MAIN_LOGGER_NAME).status(message)
                try:
                    os.makedirs(path)
                except IOError:
                    message = "Could not create the directory: %s." % (path)
                    logging.getLogger(MAIN_LOGGER_NAME).error(message)
                    return False
                except OSError:
                    message = "Could not create the directory: %s." % (path)
                    logging.getLogger(MAIN_LOGGER_NAME).error(message)
                    return False

        # Create the python module __init_.py file so modules can be imported
        timestamp = datetime.datetime.now().strftime(UID_TIMESTAMP)
        for path in (os.path.join(os.path.join(SXConfigurationFiles.CONFIGURATION_DIR, SXConfigurationFiles.REPORT_USER_IMPORT), "__init__.py"),
                     os.path.join(os.path.join(SXConfigurationFiles.CONFIGURATION_DIR, SXConfigurationFiles.PLUGIN_USER_IMPORT), "__init__.py")) :
            if (not os.access(path, os.F_OK)) :
                try:
                    fout = open(path, "wb")
                    fout.write("# created by sxconsole: %s\n" %(timestamp))
                    fout.close()
                except IOError:
                    message = "There was an error writing the file: %s." %(path)
                    logging.getLogger(MAIN_LOGGER_NAME).error(message)
                    return False
                except OSError:
                    message = "Could not create the directory: %s." % (path)
                    logging.getLogger(MAIN_LOGGER_NAME).error(message)
                    return False
        return True



