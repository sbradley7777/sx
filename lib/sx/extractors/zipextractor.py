#!/usr/bin/env python
"""

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.10
@copyright :  GPLv2
"""
import os.path
import string
import logging
import mimetypes
import subprocess
import shutil
import time

import sx
from sx.logwriter import LogWriter
from sx.extractors import Extractor


class Zipextractor(Extractor) :
    def __init__(self, pathToFile):
        Extractor.__init__(self, "ZIPextractor", pathToFile, "/usr/bin/unzip")

    def isCommandInstalled(self) :
        command = [self.getPathToCommand(), "-v"]
        try: 
            unzipTask = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = unzipTask.communicate()
            if ((stdout.find("Info-ZIP") >= 0) or (unzipTask.returncode  == 0)):
                return True
            return False
        except OSError:
            message = "There was an error checking if the binary zip is installed."
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return False


    def isValidMimeType(self):
        mimetypes.init()
        mimetypes.encodings_map[".xz"] = "xz"

        # Returns a tuple of [type, encoding]: (index 0 = type), (index 1 = encoding)
        mimeType = mimetypes.guess_type(self.getPathToFile())
        if ((mimeType[0] == "application/zip") and (mimeType[1] == None)):
            return True
        return False

    def getListArgs(self) :
        # $ unzip -L LOG_2010_12_16_12_32_50.zip
        if (not self.isValidMimeType()):
            return None;
        return "-l"

    def getExtactArgs(self) :
        # There is no options needed, quiet and overwrite files
        # options will be added.

        # $ unzip LOG_2010_12_16_12_32_50.zip -d somedir
        if (not self.isValidMimeType()):
            return None;
        return "-qo"

    # ###########################################################################
    # Extract, getDataFromFile functions
    # ###########################################################################
    def getDataFromFile(self, pathToFileInExtractor) :
        # unzip RHEV-log.zip RhevManager.exe.config -d test/
        fullPathToFile = pathToFileInExtractor
        fileList =  self.list()
        fullPathToFile = ""
        for item in fileList:
            # No stripping required on zip files.
            if (item == pathToFileInExtractor):
                fullPathToFile = item
                break;
        # Get the options to extract
        commandOptions = self.getExtactArgs()
        if (commandOptions == None) :
            message =  "This file is unknown type and will not be extracted: %s." %(self.getPathToFile())
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        elif (not len(fullPathToFile) > 0):
            message = "The path to the file does not exist: %s" %(pathToFileInExtractor)
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        else:
            # ###################################################################
            # Create a tmp directory to extract the file
            # ###################################################################
            if (not os.access(Extractor.PATH_TO_TEMP_DIR, os.F_OK)):
                try:
                    os.makedirs(Extractor.PATH_TO_TEMP_DIR)
                except (IOError, os.error):
                    message = "Could not create the directory to extract file to: %s" % (Extractor.PATH_TO_TEMP_DIR)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)

            command = [self.getPathToCommand(), commandOptions, self.getPathToFile(), fullPathToFile, "-d", Extractor.PATH_TO_TEMP_DIR]
            task = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = task.communicate()
            if (not task.returncode  == 0):
                message = "There was an error extracting a file from the file: %s." % (self.getPathToFile())
                logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            else:
                fileExtractedContents = []
                pathToExtractedFile = os.path.join(Extractor.PATH_TO_TEMP_DIR, fullPathToFile)
                # Extract the contents of the file to an array
                if (os.path.isfile(pathToExtractedFile)):
                    try:
                        fout = open(pathToExtractedFile, "r")
                        fileExtractedContents = fout.readlines()
                        fout.close
                    except (IOError, os.error, KeyError):
                        message = "There was a problem reading a file that was extracted from a tarfile: %s" %(pathToExtractedFile)
                        logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                return fileExtractedContents
        return []

    def extract(self, extractDir, stripDirectoriesDepth=1) :
        commandOptions = self.getExtactArgs()
        if (commandOptions == None) :
            message =  "This file is unknown type and will not be extracted: %s." %(self.getPathToFile())
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        elif (not self.isCommandInstalled()):
            message = "The %s command does not appear to be installed or incorrect version." %(self.getPathToCommand())
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        else:
            command = [self.getPathToCommand(), commandOptions, self.getPathToFile(), "-d", extractDir]
            task = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = task.communicate()
            if (not task.returncode  == 0):
                message = "There was an error extracting the file: %s." % (self.getPathToFile())
                logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            else:
                return os.path.isdir(extractDir)
        return False
