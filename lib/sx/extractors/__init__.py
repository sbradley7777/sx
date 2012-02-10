#!/usr/bin/env python
"""
Performs operations on a tarball that is archived with tar and
compressed bzip2, gunzip, or xv. The GNU tar command is used to do all
the functions. In some instances "liblzma" will be needed to provide
support for tar.

Thread about native xz support:
http://bugs.python.org/issue6715

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.08
@copyright :  GPLv2
"""
import os
import os.path
import string
import logging
import mimetypes
import subprocess
import shutil
import time
import re

import sx
from sx.logwriter import LogWriter

class Extractor :
    """
    @cvar PATH_TO_TEMP_DIR: This is the path to directory that will
    @type PATH_TO_TEMP_DIR: String
    """
    PATH_TO_TEMP_DIR = "/tmp/sx-%s" %(time.strftime(sx.UID_TIMESTAMP))

    def __init__(self, name, pathToFile, pathToCommand):
        # Descriptive name of extractor
        self.__name = name
        self.__pathToFile = pathToFile
        self.__pathToCommand = pathToCommand

    def __str__(self):
        rstring = "%s: %s" %(self.getName(), self.getPathToFile())
        return rstring

    def getName(self):
        return self.__name

    def getPathToFile(self):
        return self.__pathToFile

    def getPathToCommand(self):
        return self.__pathToCommand

    def list(self) :
        commandOptions = self.getListArgs()
        if (commandOptions == None) :
            message =  "This file is unknown type and will not list the file contents: %s." %(self.getPathToFile())
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
        elif (not self.isCommandInstalled()):
            message = "The %s command does not appear to be installed or incorrect version." %(self.getPathToCommand())
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
        else:
            # Run the command to list the files in the files:
            command = [self.getPathToCommand(), commandOptions, self.getPathToFile()]
            task = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = task.communicate()
            if (not task.returncode  == 0):
                message = "There was an error listing the file contents: %s." % (self.getPathToFile())
                logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            else:
                return stdout.split()
        return []

    def clean() :
        """
        This function will remove any temporary files that were
        created. Returns True if the temporary directory no longer
        exists.

        @return: Returns True if the temporary directory no longer
        exists.
        @rtype: Boolean
        """
        if (os.path.isdir(Extractor.PATH_TO_TEMP_DIR)):
            try:
                # There might be a better way to handle this clean
                shutil.rmtree(Extractor.PATH_TO_TEMP_DIR)
            except (IOError, os.error):
                message = "Could not remove the temporary directory: %s" % (Extractor.PATH_TO_TEMP_DIR)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
        return (not os.path.isdir(Extractor.PATH_TO_TEMP_DIR))
    clean = staticmethod(clean)

    def isCommandInstalled(self) :
        return False

    def isValidMimeType(self):
        return False

    def getListArgs(self) :
        return None

    def getExtactArgs(self) :
        return None

    def getDataFromFile(self, pathToFileInExtractor) :
        return []

    def extract(self, extractDir, stripDirectoriesDepth=1) :
        return False

