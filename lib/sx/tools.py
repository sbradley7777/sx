#!/usr/bin/env python
"""
This class has a collection of various tools that are used with
sosreports/sysreports.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.11
@copyright :  GPLv2
"""
import sys
import os
import os.path
import string
import re
import logging
import shutil
import hashlib
import datetime
import textwrap

# Import sx first so we can spit out message
import sx
from sx.logwriter import LogWriter

class ConfigurationFileParser:
    """
    This class will validate a config file. If the config is not
    correct then it will be empty.

    This class assumes that all options will have a value and thus no
    option will be empty.
    """
    def __init__(self, configurationFileData, configOptionsMap, enforceEmptyValues=True) :

        self.__validConfiguration = False

        # This is the data from configuration file that is just an
        # array and each item was a line in the file.
        self.__configurationFileData = configurationFileData

        # Here is all the valid keys in configuration file
        self.__configOptionsMap = configOptionsMap

        # Will not parse file if enforceKeys is enabled if the keys
        # are not in configOptionsMap that was passed.
        self.__enforceKeys = True
        if (len(configOptionsMap.keys()) == 0):
            self.__enforceKeys = False

        # Will not parse file with empty values
        self.__enforceEmptyValues = enforceEmptyValues

        # parse the file so that map is populated.
        self.__validConfiguration = self.__parseConfigurationFile()


    def __parseConfigurationFile(self) :
        """
        This function will parse the file and populate the dictionary
        with the correct values. If the file does not exist or the
        config file is not valid then a sys.exit will be called thus
        the application will exit.
        """
        if (not len(self.__configurationFileData) > 0):
            message = "This is an empty configuration file and contains no data to parse."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        # These are all the compiled regular expressions for no
        # quotes, single quotes, and double quotes of the value in the
        # pair.
        res = re.compile("^(?P<key>\w+)=(?P<value>(\S+)?$|\'(\S+.*)\'.*|\"(\S+.*)\".*)")
        remComments = re.compile("^#")

        for line in self.__configurationFileData:
            # If the line is a comment then skip
            if ((not len(line) > 0) or (remComments.match(line.strip().rstrip()))):
                # Skip empty lines and comments
                continue
            # Split the lines if there is inline comments.
            item = line.split("#")[0].strip().rstrip()
            searchRes = res.search(item)
            if (searchRes):
                key = searchRes.group("key")
                value = searchRes.group("value").strip("\"").strip("\'")
                if ((value == None) and (not self.__enforceEmptyValues)):
                    value = ""
                elif ((not len(value) > 0) and (not self.__enforceEmptyValues)):
                    value = ""
                elif ((not key in self.__configOptionsMap.keys()) and (self.__enforceKeys)):
                    message = "This is not a valid configuration file because there was an invalid key \"%s\" found." %(key)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                    return False
                # Added this to remove comments after value and strip other characters.
                value = value.split("#")[0]
                self.__configOptionsMap[key] = value.strip().rstrip().rstrip("\"").rstrip("\'")
            else:
                message = "This is an invalid configuration option: %s" %(item)
                logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                continue
        return True

    def isValid(self):
        """
        Returns True if configuration file is valid with no errors.

        @return: Returns True if configuration file is valid with no
        errors.
        @rtype: Boolean
        """
        return self.__validConfiguration

    def get(self, optionName) :
        """
        This function returns a value for an option in the config
        file. If the option does not exist then "" is returned. Empty
        string is returned if not a valid configuration file.

        @return: Returns the value for the option.If the option does
        not exist then "" is returned.
        @rtype: String

        @param optionName: An option in the configuration file.
        @type optionName: String
        """
        if ((self.__configOptionsMap.has_key(optionName)) and (self.isValid())):
            return self.__configOptionsMap[optionName]
        return ""

    def getMap(self) :
        """
        Returns the map of configuration options to values. Empty
        dictionary is returned if configuriation file is not valid.

        @return: Returns the map of configuration options to values.
        @rtype: Dictionary
        """
        if (self.isValid()):
            return self.__configOptionsMap
        else:
            return {}

class ChecksysreportConfigurationFileParser(ConfigurationFileParser):
    def __init__(self) :
        """
        This class will contain the default configuration options for
        sx. The class can also create the default configuration
        directories for sx.

        Currently just using ~/.checksysreport configuration file
        since it already contains the information that is needed.
        """
        self.__pathToDefaultConfigFile = os.path.join(os.environ['HOME'], ".checksysreportrc")
        defaultConfigOptionMap = {"rhn_login":"", "rhn_password":"", "rhn_server":"",
                                  "sql_host":"", "sql_port":"", "sql_login":"", "sql_password":"", "sql_database":""}
        configFileData = []
        if (os.path.isfile(self.__pathToDefaultConfigFile)):
            try:
                fin = open(self.__pathToDefaultConfigFile, "r")
                configFileData = fin.readlines()
                fin.close()
            except (IOError, os.error):
                message = "An error occured reading the file: %s." %(self.__pathToDefaultConfigFile)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            fin.close()
        else:
            message = "The configuration file does not exists and should be created: %s." %(self.__pathToDefaultConfigFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
        ConfigurationFileParser.__init__(self, configFileData, defaultConfigOptionMap)

    def getConfigurationFile(self):
        return self.__pathToDefaultConfigFile

# ###############################################################################
# Console Utilities class
# ###############################################################################
class ConsoleUtil:
    def colorText(text, color):
        """
        Terminal text coloring function for a string.

        The following colors are valid:
        black, red, green, brown, blue, purple, cyan, lgray, gray, lred,
        lgreen, yellow, lblue, pink, lcyan, white.

        @return: Returns a string reprensentation of the string with
        color.
        @rtype: String

        @param text: The string that will be colorized.
        @type text: String
        @param color: The color that will be used to colorize the text.
        @type color: String
        """
        colors = {  "black":"30", "red":"31", "green":"32", "brown":"33", "blue":"34",
                    "purple":"35", "cyan":"36", "lgray":"37", "gray":"1;30", "lred":"1;31",
                    "lgreen":"1;32", "yellow":"1;33", "lblue":"1;34", "pink":"1;35",
                    "lcyan":"1;36", "white":"1;37" }
        if (not colors.has_key(color)) :
            return  text
        opencol = "\033["
        closecol = "m"
        clear = opencol + "0" + closecol
        f = opencol + colors[color] + closecol
        return "%s%s%s" % (f, text, clear)
    colorText = staticmethod(colorText)

    def askToContinue(prompt, retries=3):
        """
        This function will prompt a user a question. The answer is
        either yes, y, no, n. There is a default of 4 failed
        attempts. Any errors or exceeding the prompt retry could will
        return False.

        @return: Returns True if they select yes/y. False on
        everything else.
        @rtype: Boolean

        @param prompt: The question that will be sent to console for
        end user to retry.
        @type prompt: String
        @param retries: The number of retries at answering the
        question.
        @type retries: Int
        """
        while True:
            try:
                result = raw_input(prompt)
                result = result.lower()
                if result in ('y', 'ye', 'yes'):
                    return True
                elif result in ('n', 'no', 'nop', 'nope'):
                    return False
                retries = retries - 1
                if (retries <= 0):
                    message = "Too many failed retries. Application will exit."
                    logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                    return False
                message = "Please answer (y)es or (n)o."
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            except IOError:
                message = "There was an error that occurred and application will exit."
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return False
    askToContinue = staticmethod(askToContinue)

# ###############################################################################
# Class that contains various simple util functions.
# ###############################################################################
class SimpleUtil:
    def isAlphaNumericPlus(svar):
        """
        Returns False if the string contains letters other than:
        a-zA-Z0-9_.-

        @returns: Returns False if the string contains letters other
        than: a-zA-Z0-9_.-
        @rtype: Boolean

        @param svar: A string that will be tested to see if it only
        contains certain characters.
        @type svar: String
        """
        ALPHANUM=re.compile('^[a-zA-Z0-9_.-]+$')
        for s in svar:
            if (ALPHANUM.match(s) is None):
                return False
        return True
    isAlphaNumericPlus = staticmethod(isAlphaNumericPlus)

    def castInt(sVar):
        """
        Returns None if casting the string to an Int failed or string
        was not Int Representation. If casting was successfully an Int
        is returned.

        @return: Returns None if casting the string to an Int failed
        or string was not Int Representation. If casting was
        successfully an Int is returned.
        @rtype: Int

        @param sVar: A string that will be cast to an Int.
        @type sVar: String
        """
        cVar = None
        if (isinstance(sVar, int)):
            # If sVar is already an int then just return then int back.
            return sVar
        elif (sVar.isalnum()):
            try:
                cVar = int(sVar)
            except(ValueError):
                return None
        return cVar
    castInt = staticmethod(castInt)

    def castBoolean(sVar):
        """
        Returns None if casting the string to an Boolean failed or string
        was not Boolean Representation. If casting was successfully an Boolean
        is returned.

        @return: Returns None if casting the string to an Boolean
        failed or string was not Boolean Representation. If casting
        was successfully an Boolean is returned.
        @rtype: Boolean

        @param sVar: A string that will be cast to an Boolean.
        @type sVar: String
        """
        sVar = sVar.lower()
        if (sVar == "true"):
            return True
        elif (sVar == "false"):
            return False
        return None
    castBoolean = staticmethod(castBoolean)

# ###############################################################################
# File Utilities class
# ###############################################################################
class FileUtil:

    def convertBytesToString(bytesCount):
        bytesCount = float(bytesCount)
        if (bytesCount >= 1099511627776):
            terabytes = bytesCount / 1099511627776
            return "%.2fTB" % terabytes
        elif (bytesCount >= 1073741824):
            gigabytes = bytesCount / 1073741824
            return "%.2fGB" % gigabytes
        elif (bytesCount >= 1048576):
            megabytes = bytesCount / 1048576
            return "%.2fMB" % megabytes
        elif (bytesCount >= 1024):
            kilobytes = bytesCount / 1024
            #return "%.2fKB" % kilobytes
            return "%dKB" % int(kilobytes)
        else:
            #return "%.2fb" % bytesCount
            return "%db" % int(bytesCount)
    convertBytesToString = staticmethod(convertBytesToString)

    def tail(pathToFile, n=1, bs=1024):
        lines = ""
        if (pathToFile == None):
            return lines
        elif(not len(pathToFile) > 0):
            message = "There was no path given to a file to read."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return lines
        elif(not os.path.exists(pathToFile)):
            message = "The file does not exist with the path: %s." %(pathToFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return lines
        elif (not os.path.isfile(pathToFile)):
            message = "The path to the source file is not a regular file: %s." %(pathToFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return lines
        try:
            f = open(pathToFile)
            f.seek(-1,2)
            # If file doesn't end in \n, count it anyway.
            l = 1-f.read(1).count('\n')
            B = f.tell()
            while n >= l and B > 0:
                block = min(bs, B)
                B -= block
                f.seek(B, 0)
                l += f.read(block).count('\n')
            f.seek(B, 0)
            # Discard first (incomplete) line if l > n.
            l = min(l,n)
            lines = f.readlines()[-l:]
            f.close()
        except OSError:
            message = "Could not read the file: %s." %(pathToFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return lines
        except IOError:
            message = "Could not read the file: %s." %(pathToFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return lines
        return lines
    tail = staticmethod(tail)

    def dirFileCount(pathToDirectory, includeSubDirectories=False):
        fileCount = 0
        dirCount = 0
        for root, dirs, files in os.walk(pathToDirectory, topdown=False):
            for filename in files:
                if ((filename == ".") or (filename == "..")):
                    continue
                fileCount = fileCount + 1
            if (includeSubDirectories):
                for dirName in dirs:
                    if ((dirName == ".") or (dirName == "..")):
                        continue
                    dirCount = dirCount + 1
        if (includeSubDirectories):
            return (dirCount + fileCount)
        return fileCount
    dirFileCount = staticmethod(dirFileCount)

    def unlinkFile(pathToSrc):
        message = "Removing the file: %s." %(pathToSrc)
        logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        if (os.path.exists(pathToSrc)):
            try:
                # This will unlink symbolic links and remove regular
                # files.
                os.unlink(pathToSrc)
            except OSError:
                message = "There was error removing the file: %s." %(pathToSrc)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return False
        else:
            message = "The filepath does not exists: %s." %(pathToSrc)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        return (not os.path.exists(pathToSrc))
    unlinkFile = staticmethod(unlinkFile)

    def getFileCreateTimestamp(pathToFilename):
        """
        Returns a string date formated of the files creation
        timestamp. None will be returned if there is an error.

        @return: Returns a string date formated of the file's creation
        timestamp. None will be returned if there is an error.
        @rtype: String

        @param pathToFilename: Path to the file whose creation time
        will be turned into a string.
        @type pathToFilename: String
        """
        creationTimestamp = None
        try:
            ct = os.path.getctime(pathToFilename)
            creationTimestamp = datetime.datetime.fromtimestamp(ct)
        except OSError:
            message = "There was an error getting the creation time for the file:\n\t  %s." %(pathToFilename)
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
        return creationTimestamp
    getFileCreateTimestamp = staticmethod(getFileCreateTimestamp)

    def getFileModificationTimestamp(pathToFilename):
        modTimestamp = None
        try:
            mt = os.path.getmtime(pathToFilename)
            modTimestamp = datetime.datetime.fromtimestamp(mt)
        except OSError:
            message = "There was an error getting the modification time for the file:\n\t  %s." %(pathToFilename)
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)
        return modTimestamp
    getFileModificationTimestamp = staticmethod(getFileModificationTimestamp)

    def isFilesIdentical(pathToFilesList) :
        """
        This function uses md5sum to verify that all files in array
        have same md5sum as the base file. If all files have same
        md5sum then True is returned.

        If the file list does not contain 2 or more files then False
        is returned.

        @return: True if cluster.confs are same on ClusterNode's.
        @rtype: Boolean

        @param pathToFilesList: A list of files that will be
        compared. This can include the base file.
        @type pathToFilesList: Array
        """
        if (not len(pathToFilesList) > 1) :
            message = "There are not enough files to compare mdsum's. There must be 2 or more files."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        # This is the base value that all files compared against. This
        # will be set to the last item added.
        baseMD5Sum = ""
        # This is map of file paths to md5sum of the contents
        md5sumMap = dict.fromkeys(pathToFilesList)
        for key in md5sumMap.keys():
            # Read the file into a string
            fileContents  = ""
            try:
                f = open(key, "r")
                fileContents = string.rstrip(f.read())
                f.close()
            except (IOError, os.error):
                message = "An error occured reading the file: %s." %(key)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return False
            # Generate the md5sum
            try:
                md5sum = hashlib.md5()
                md5sum.update(fileContents)
                currentMD5Sum = md5sum.digest()
                md5sumMap[key] = currentMD5Sum
                # Just grab the last item that was set.
                baseMD5Sum = currentMD5Sum
            except (IOError, os.error):
                message = "There was an error generating the md5sum for file: %s." %(key)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return False

        for key in md5sumMap.keys():
            if (not md5sumMap.get(key) == baseMD5Sum):
                return False
        return True
    isFilesIdentical = staticmethod(isFilesIdentical)

    def mkdirs(pathToDSTDir):
        """
        This function will create all the directories in the path if
        they do not exists. Returns True if the dir was created or
        directory already exists.

        @return: Returns True if the dir was created or directory
        already exists.
        @rtype: Boolean

        @param pathToDSTDir: Path of the directory that will be
        created.
        @type pathToDSTDir: String
        """
        if (os.path.isdir(pathToDSTDir)):
            return True
        elif ((not os.access(pathToDSTDir, os.F_OK)) and (len(pathToDSTDir) > 0)):
            try:
                os.makedirs(pathToDSTDir)
            except (OSError, os.error):
                message = "Could not create the directory: %s." %(pathToDSTDir)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return False
            except (IOError, os.error):
                message = "Could not create the directory with the path: %s." %(pathToDSTDir)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return False
        return os.path.isdir(pathToDSTDir)
    mkdirs = staticmethod(mkdirs)

    def copyFile(pathToSrcFile, pathToDstFile):
        if(not os.path.exists(pathToSrcFile)):
            message = "The file does not exist with the path: %s." %(pathToSrcFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif (not os.path.isfile(pathToSrcFile)):
            message = "The path to the source file is not a regular file: %s." %(pathToSrcFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif (pathToSrcFile == pathToDstFile):
            message = "The path to the source file and path to destination file cannot be the same: %s." %(pathToDstFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        else:
            # Create the directory structure if it does not exist.
            (head, tail) = os.path.split(pathToDstFile)
            if (not FileUtil.mkdirs(head)) :
                # The path to the directory was not created so file
                # could not be copied.
                return False
            # Copy the file to the dst path.
            try:
                shutil.copy(pathToSrcFile, pathToDstFile)
            except OSError:
                message = "Cannot copy the file %s to %s." %(pathToSrcFile, pathToDstFile)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return False
            except IOError:
                message = "Cannot copy the file %s to %s." %(pathToSrcFile, pathToDstFile)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
                return False
        return (os.path.exists(pathToDstFile))
    copyFile = staticmethod(copyFile)

    def archiveFile(pathToSrcFile, pathToDstFile=""):
        """
        This command will make a backup copy of the existing file in
        the same directory as the file unless a dst file path is
        given.. The file will be moved to a new file and filename will
        have the ".org" appended to it.

        @return: Returns True if the file that was moved was
        successfully archived.
        @rtype: Boolean

        @param pathToSrcFile: The path for the src file.
        @type pathToSrcFile: String
        @param pathToDstFile: The path for the dst file.
        @type pathToDstFile: String
        """
        if(not os.path.exists(pathToSrcFile)):
            message = "The file does not exist with the path: %s." %(pathToSrcFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif (not os.path.isfile(pathToSrcFile)):
            message = "The path to the source file is not a regular file: %s." %(pathToSrcFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif (pathToSrcFile == pathToDstFile):
            message = "The path to the source file and path to destination file cannot be the same: %s." %(pathToDstFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        elif (not len(pathToDstFile) > 0):
            # If there is no pathToDstFile then copy to the same directory
            # as the orginal file.
            (head, tail) = os.path.split(pathToSrcFile)
            pathToDstFile = os.path.join(head, ".%s.org" %(tail))

        # Create the directory structure if it does not exist.
        (head, tail) = os.path.split(pathToDstFile)
        if (not FileUtil.mkdirs(head)) :
            # The path to the directory was not created so file
            # could not be copied.
            return False

        # Added a remove of dstfile if it exists because there can
        # be perm issues with python because it does some chmod
        # action on the file.
        if (os.path.isfile(pathToDstFile)):
            try:
                os.remove(pathToDstFile)
            except OSError:
                message = "Cannot remove the file %s." %(pathToDstFile)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        try:
            shutil.copy(pathToSrcFile, pathToDstFile)
        except OSError:
            message = "Cannot copy the file %s to %s." %(pathToSrcFile, pathToDstFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        except IOError:
            message = "Cannot copy the file %s to %s." %(pathToSrcFile, pathToDstFile)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False
        return (os.path.exists(pathToDstFile))
    archiveFile = staticmethod(archiveFile)

class StringUtil:

    def wrapParagraph(s, width=98, newline=True):
        rString = textwrap.fill(s, width=98).rstrip()
        if (newline):
            return "%s\n" %(rString)
        return rString
    wrapParagraph = staticmethod(wrapParagraph)

    def wrapParagraphURLs(s, urls, width=98, newline=True):
        rString = StringUtil.wrapParagraph(s, width, newline=False).rstrip()
        for url in urls:
            rString += "\n- %s" %(url)
        if (newline):
            return "%s\n" %(rString)
        return rString
    wrapParagraphURLs = staticmethod(wrapParagraphURLs)

    def formatBulletString(description, urls, tableOfStrings=None, indentChar="*", indentSize=3, width=98) :
        # Orginal width was 65.
        # Only the first character will be used for the bullet. If no
        # character is passed then a whitespace will be used.
        if (len(indentChar) > 1):
            indentChar = indentChar[:1]
        elif (len(indentChar) <= 0):
            indentChar = " "
        initIndent = indentChar
        # Add in the whitespaces that will finish the indents
        if (not len(initIndent) >= indentSize):
            initIndent += " " * (indentSize - len(initIndent))
        # Create the subsequent intent size which will be all
        # whitespaces.
        subIndent = " " * indentSize

        # Format the string with textwrap
        rstring = "\n".join(textwrap.wrap(description, width=width, initial_indent=initIndent, subsequent_indent=subIndent))
        rstring += "\n"
        # Append the urls to the return string
        for url in urls:
            rstring += "%s - %s\n" %(subIndent, url)
        rstring = rstring.strip("\n")
        rstring += "\n"
        # Add the table string if not None
        if (not tableOfStrings == None):
            rstring += "\n"
            for s in tableOfStrings:
                rstring += "%s%s\n" %(subIndent, s)
            rstring += "\n"
        return rstring
    formatBulletString = staticmethod(formatBulletString)

    # #######################################################################
    # Functions for creating a formatted table from lists of lists:
    # #######################################################################
    def __formatTableValue(self, tableValue):
        """
        Format a number or strings according to given places.
        Adds commas and will truncate floats into ints.

        If a string is the parameter then execption will be caught and
        string will be returned.

        @return: Returns a formatted string.
        @rtype: String

        @param tableValue: The value that will be formatted.
        @type tableValue: Int or String
        """
        import locale
        locale.setlocale(locale.LC_NUMERIC, "")

        try:
            inum = int(tableValue)
            return locale.format("%.*f", (0, inum), True)
        except (ValueError, TypeError):
            return str(tableValue)

    def __getMaxColumnWidth(self, table, index):
        """
        Get the maximum width of the given column index from the
        current table. If index is out of range then a -1 is returned.

        @return: Returns the max width for that index or column.
        @rtype: Int

        @param table: A array of arrays(Can be strings, ints, floats).
        @type table: Array
        @param index: The current index of what will be compared.
        @type index: Int
        """
        try:
            return max([len(self.__formatTableValue(row[index])) for row in table])
        except IndexError:
            return -1

    def toTableString(self, table, headerList=None):
        """
        This function will take an array of arrays and then output a
        single string that is a formatted table.

        An empty string will be returned if the column count is not the
        same for each row in the table.

        @return: Returns a formatted table string with correct spacing
        for each column.
        @rtype: String

        @param table: A array of arrays(Can be strings, ints, floats).
        @type table: Array
        @param headerList: A list of strings that will be the headers
        for each column in the table.
        @type headerList: Array
        """
        if (not len(table) > 0):
            return ""
        tString = ""
        tableStringsList = self.formatStringListsToTable(table, headerList)
        for tableStrings in tableStringsList:
            currentLine = ""
            for ts in tableStrings:
                currentLine += ts
            tString += "%s\n" %(currentLine)
        return tString.rstrip()

    def toTableStringsList(self, table, headerList=None):
        """
        This function will take an array of arrays and then output a
        single string that is a formatted table.

        An empty string will be returned if the column count is not the
        same for each row in the table.

        @return: Returns a formatted list of strings with correct spacing
        for each column.
        @rtype: String

        @param table: A array of arrays(Can be strings, ints, floats).
        @type table: Array
        @param headerList: A list of strings that will be the headers
        for each column in the table.
        @type headerList: Array
        """
        tableOfStrings = []
        tableStringsList = self.formatStringListsToTable(table, headerList)
        for tableStrings in tableStringsList:
            currentLine = ""
            for ts in tableStrings:
                currentLine += ts
            tableOfStrings.append(currentLine)
        return tableOfStrings

    def formatStringListsToTable(self, table, headerList=None):
        """
        This function will take an array of arrays and then output a
        single string that is a formatted table.

        An empty list will be returned if the column count is not the
        same for each row in the table.

        I got code from this url and modified it:
        http://ginstrom.com/scribbles/2.11/09/04/pretty-printing-a-table-in-python/

        Example(added spacing to make example clear):
        table = [["",       "names", "birthyear", "age"], ["NCuser", "bob",   1976,         35]]

        @return: Returns a list of strings(row of strings) that has
        the proper spacing in each column.
        @rtype: String

        @param table: A array of arrays(Can be strings, ints, floats).
        @type table: Array
        @param headerList: A list of strings that will be the headers
        for each column in the table.
        @type headerList: Array
        """
        # Copy the table so that we do not ref the orginal list and change it.
        copyOfTable = []
        for currentList in table:
            newList = []
            for item in currentList:
                newList.append(item)
            if (len(newList) > 0):
                copyOfTable.append(newList)

        # Return empty list and print error if all the rows in table
        # dont have same column count.
        if (len(copyOfTable) > 0):
            # Add header to the list if one was passed to it and table is not empty.
            if (not headerList == None):
                copyOfTable.insert(0, headerList)
            # Make sure that table and header contain the same number
            # of columns.
            colCount = len(copyOfTable[0])
            for currentRow in copyOfTable:
                currentColCount = len(currentRow)
                if (not (currentColCount == colCount)):
                    message = "The table continues columns with a different columns counts and will not be processed."
                    logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                    return []
        else:
            message = "The table continues no rows in the table and will not be processed."
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            return []
        # This function will append new rows if the item in the column
        # for a row is an array/list. If there is a None value or
        # empty string then replace with "-" for no value rep.
        currentRowIndex = 0
        for currentRow in copyOfTable:
            newRows = []
            currentColIndex = 0
            for currentCol in currentRow:
                if (currentCol == None):
                   currentRow[currentColIndex] = "-"
                elif (not (len(currentCol) > 0)):
                    currentRow[currentColIndex] = "-"
                elif (type(currentCol) == list):
                    currentColList = currentCol
                    if (len(currentCol) > 0):
                        currentRow[currentColIndex] = currentColList.pop(0)
                    for ccListIndex in range(0, len(currentColList)):
                        try:
                            newRows[ccListIndex][currentColIndex] = currentColList[ccListIndex]
                        except IndexError:
                            newRow = []
                            for i in range(len(currentRow)):
                                newRow[i] = ""
                            newRow[currentColIndex] = currentColList[ccListIndex]
                            newRows.append(newRow)
                currentColIndex = currentColIndex + 1
            for row in newRows:
                copyOfTable.insert(currentRowIndex + 1,row)
            currentRowIndex = currentRowIndex  + 1
        # Fix the max spacing for each column after iterating over
        # each row.
        tableStringsList = []
        col_paddings = []
        for i in range(len(copyOfTable[0])):
            maxColumnWidth = self.__getMaxColumnWidth(copyOfTable, i)
            if (maxColumnWidth >= 0):
                col_paddings.append(maxColumnWidth)
        # If header was given then use the max column size to build
        # the seperator.
        if (not headerList == None):
            headerSeperatorList = []
            for colMaxSize in col_paddings:
                currentHeaderSeperator = ""
                currentHeaderSeperator += "-" * colMaxSize
                headerSeperatorList.append(currentHeaderSeperator)
            copyOfTable.insert(1, headerSeperatorList)
        for row in copyOfTable:
            # Left col string has no spacing.
            tableStrings = []
            tableStrings.append( str(row[0].ljust(col_paddings[0] + 1)))
            # Add spacing to the rest of the columns.
            for i in range(1, len(row)):
                # Add spacing to to the right side with ljust.
                try:
                    tableStrings.append(str(self.__formatTableValue(row[i]).ljust(col_paddings[i] + 2)))
                except IndexError:
                    continue
            tableStringsList.append(tableStrings)
        return tableStringsList
