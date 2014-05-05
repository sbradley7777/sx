#!/usr/bin/env python
"""
This is a collection of classes that contain data for files from a
sosreport in the directory:
sos_commands/kernel/

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""

class ModulesParser:
    def parseEtcModprobeConf(etcModprobeConfData):
        modprobeConfCommands = []
        if (etcModprobeConfData == None):
            return modprobeConfCommands
        for item in etcModprobeConfData:
            if ((not item.strip().startswith("#")) and (len(item) > 0)):
                modprobeConfCommands.append(ModprobeConfCommand(item))
        return modprobeConfCommands
    parseEtcModprobeConf = staticmethod(parseEtcModprobeConf)

    def parseLSModData(lsModData):
        """
        Example:
        dm_mirror              54737  0
        dm_log                 44993  3 dm_raid45,dm_region_hash,dm_mirror
        """
        parsedList = []
        if (lsModData == None):
            return parsedList
        for line in lsModData:
            lineSplit = line.split()
            if (len(lineSplit) > 0):
                moduleUsedBy = []
                if (len(lineSplit) == 4):
                    moduleUsedBy = lineSplit[3].strip().split(",")
                parsedList.append(LSMod(lineSplit[0].strip(),
                                        lineSplit[1].strip(),
                                        lineSplit[2].strip(),
                                        moduleUsedBy))
        return parsedList
    parseLSModData = staticmethod(parseLSModData)

class ModprobeConfCommand:
    def __init__(self, commandLine):
        """
        How to create the object is based on the way the modprobe.conf
        is structured:

        alias     wildcard   modulename
        options   modulename option ...
        install   modulename command ...
        remove    modulename command ...
        include   filename
        blacklist modulename
        """
        # Set the vars because not all will have values.
        self.__command = ""
        self.__moduleName = ""
        self.__wildCard  = ""
        self.__moduleOptions = ""
        self.__moduleCommands = ""
        self.__filename = ""

        self.__commandLine = commandLine
        splitCommandLine = self.__commandLine.split()
        if (len(splitCommandLine) > 0):
            self.__command = splitCommandLine.pop(0).strip()
            if ((len(splitCommandLine) > 0) and (self.__command == "include")):
                self.__filename = splitCommandLine.pop(0).strip()
            elif ((len(splitCommandLine) > 0) and (self.__command == "blacklist")):
                self.__blacklist = splitCommandLine.pop(0).strip()
            elif ((len(splitCommandLine) > 0) and (self.__command == "alias")):
                if (len(splitCommandLine) == 2):
                    self.__wildCard = splitCommandLine.pop(0).strip()
                self.__moduleName = splitCommandLine.pop(0).strip()
            elif ((len(splitCommandLine) > 0) and (self.__command == "options")):
                self.__moduleName = splitCommandLine.pop(0).strip()
                self.__moduleOptions = splitCommandLine
            elif ((len(splitCommandLine) > 0) and (self.__command == "install")):
                self.__moduleName = splitCommandLine.pop(0).strip()
                self.__moduleCommands = splitCommandLine
            elif ((len(splitCommandLine) > 0) and (self.__command == "remove")):
                self.__moduleName = splitCommandLine.pop(0).strip()
                self.__moduleCommands = splitCommandLine

    def getCommandLine(self):
        return self.__commandLine

    def getCommand(self):
        return self.__command

    def getModuleName(self):
        return self.__moduleName

    def getWildCard(self):
        return self.__wildCard

    def getModuleOptions(self):
        return self.__moduleOptions

    def getModuleCommands(self):
        return self.__moduleCommands

    def getFilename(self):
        return self.__filename

class LSMod:
    def __init__(self, moduleName, moduleSize, moduleUsedCount, moduleUsedBy):
        self.__moduleName = moduleName
        self.__moduleSize = moduleSize
        self.__moduleUsedCount = moduleUsedCount
        self.__moduleUsedBy = moduleUsedBy

    def getModuleName(self):
        return self.__moduleName

    def getModuleSize(self):
        return self.__moduleSize

    def getModuleUsedCount(self):
        return self.__moduleUsedCount

    def getModuleUsedBy(self):
        return self.__moduleUsedBy
