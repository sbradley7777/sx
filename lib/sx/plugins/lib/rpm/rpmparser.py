#!/usr/bin/env python
"""
This is a collection of classes that contain data for files from a
sosreport in the directory:
sos_commands/rpm

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.10
@copyright :  GPLv2
"""
import re
import logging

import sx
from sx.logwriter import LogWriter

class RPMSParser:
    def parseInstalledRPMSData(installedRPMSData):
        parsedList = []
        if (installedRPMSData == None):
            return parsedList
        # Compile the regex to start matching. I dont think I can ever
        # get this 100% accurate, but can get 99% accurate.
        """
        regex = "(?P<name>.*[a-zA-Z])" + \
            "-(?P<majorVersion>\d)" + \
            ".(?P<minorVersion>\d)" + \
            "-(?P<releaseVersion>\d.*)" + \
            ".(?P<distroVersion>el4|el5|el6)" + \
            ".(?P<arch>noarch|i386|i586|i686|ia64|ppc|s390|s390x|x86_64)"
        """
        # In distroVersion leave empty one for rpms with no distroVersion
        regex = "^(?P<name>[a-zA-Z_0-9+]*)-.*" + \
            "-(?P<majorVersion>[0-9.]*).*" + \
            ".(?P<distroVersion>fc[0-9]*|el4|el5|el6|)" + \
            ".(?P<arch>noarch|i386|i586|i686|ia64|ppc|s390|s390x|x86_64)"
        rem = re.compile(r"%s" %(regex))
        for line in installedRPMSData:
            packageFullName = line.split()[0].lower().strip()
            mo = rem.match(packageFullName)
            if mo:
                parsedList.append(packageFullName)
                #print mo.groupdict(), " ", packageFullName
                """
                installedRPMS = InstalledRPMS(packageFullName,
                                              mo.group("name"),
                                              mo.group("majorVersion"),
                                              mo.group("minorVersion"),
                                              mo.group("releaseVersion"),
                                              mo.group("distroVersion"),
                                              mo.group("arch"))
                parsedList.append(installedRPMS)
                """
            else:
                print packageFullName
        print "\nAre the counts the same? \n\tinstalledRPMSData: %d\n\tparsedList:        %d" %(len(installedRPMSData), len(parsedList))
        return parsedList
    parseInstalledRPMSData = staticmethod(parseInstalledRPMSData)

class InstalledRPMS:
    def __init__(self, packageFullName, packageName, majorVersion, minorVersion,
                 releaseVersion, distoVersion, arch):
        self.__packageFullName = packageFullName
        self.__packageName = packageName
        self.__majorVersion = majorVersion
        self.__minorVersion = minorVersion

        self.__distroVersion = distoVersion
        self.__arch = arch

    def __str__(self):
        return self.__packageFullName

    def getPackageFullName(self):
        return self.__packageFullName

    def getPackageName(self):
        return self.__packageName

    def getMajorVersion(self):
        return self.__majorVersion

    def getMinorVersion(self):
        return self.__minorVersion

    def getDistroVersion(self):
        return self.__distroVersion

    def getArch(self):
        return self.__arch
class RPMUtils:
    def getPackageVersion(installedRPMSData, packageList) :
        """
        Matches the package in packageList to an re.matchobject. If
        match is found then that item is added to the dictionary. The
        dictionary uses the array item as key and package that is
        found in installed-rpms file as the value.

        If the key has empty string as value then no package was
        found.

        All "-" will be replaced with "__" since "-" is not allowed in
        the variable name using the "?P<var>" regex.

        @return: Returns Dictionary of the matched packages.
        @rtype: Dictionary

        @param installedRPMSData: This is the list of rpms that are
        installed.
        @type installedRPMSData: Array
        @param packageList: An array of strings that will be
        searched for in installedrpms file.
        @type packageList: Array
        """
        packageVersionDict = {}
        if ((installedRPMSData == None) or (not len(packageList) > 0)):
            return packageVersionDict
        combindedRegex = ""
        # Build a regex for all packages so all packages are searched.
        for package in packageList:
            # Populate the dictionary with keys which is item in array
            packageVersionDict[package] = []
            # Build the regex
            if (not len(combindedRegex) == 0):
                combindedRegex += "|"
            # reencode the "-" to "__" so regex be happy
            combindedRegex += "(?P<%s>%s-\d.*)" %(package.replace("-","__"), package)

        # Compile the regex to start matching
        rem = re.compile(r"%s" % combindedRegex)
        # Now search the data
        for line in installedRPMSData :
            mo = rem.match(line)
            if mo:
                moDict = mo.groupdict()
                for key in moDict.keys():
                    if (not moDict[key] == None):
                        # Dont include the date of installed
                        packageVersionDict[key.replace("__", "-")].append(moDict[key].split(" ", 1)[0].strip())

        # Remove packages that have empty array which means package was not found.
        keys = packageVersionDict.keys()
        for key in keys:
            if (not len(packageVersionDict[key]) > 0):
                del packageVersionDict[key]
        return packageVersionDict
    getPackageVersion = staticmethod(getPackageVersion)


