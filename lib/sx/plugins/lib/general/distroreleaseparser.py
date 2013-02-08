#!/usr/bin/env python
"""
This is a collection of classes that contain data for files from a
sosreport in the directory:
etc/redhat-release

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.14
@copyright :  GPLv2
"""
import re

class DistroReleaseParser:
    def parseEtcRedHatReleaseRedhatReleaseData(etcRedHatReleaseData) :
        """
        Returns the release version from the release file(rhel:
        /etc/redhat-release).

        Example from /etc/redhat-release:
        "Red Hat Enterprise Linux AS release 4 (Nahant Update 6)"
        "Red Hat Enterprise Linux Server release 5.3 (Tikanga)"
        "Fedora release 10 (Cambridge)"

        @return: Returns a DistroRelease object that contains information
        about the Distrobution Release.
        @rtype: DistroRelease

        param etcRedHatReleaseData: This is the contents of the
        /etc/redhat-release file.
        type etcRedHatReleaseData: Array
        """
        if (etcRedHatReleaseData == None):
            return None
        elif (not len(etcRedHatReleaseData) > 0):
            return None
        else:
            regex = "^(?P<distroName>Red Hat Enterprise Linux|Fedora) " + \
                "(?P<distroType>AS|ES|WS|Server|\s)?\ ?" + \
                "release (?P<distroMajorVersion>\d{1,2})[\. ]?" + \
                "(?P<distroMinorVersion1>\d{1,})?\s*" + \
                "(?P<isbeta>Beta)?\s*" + \
                "\(\D*(?P<distroMinorVersion2>\d{1,})?\)"


            rem = re.compile(regex)
            mo = rem.match(etcRedHatReleaseData[0].strip())
            if mo:
                distroName = mo.group("distroName")
                distroType =  mo.group("distroType")
                distroMajorVersion = mo.group("distroMajorVersion")
                if (distroMajorVersion == None):
                    distroMajorVersion = 0
                distroMinorVersion =  mo.group("distroMinorVersion1")
                if (distroMinorVersion == None):
                    if (mo.group("distroMinorVersion2") == None):
                        distroMinorVersion = 0
                    else:
                        distroMinorVersion = mo.group("distroMinorVersion2")
                return DistroRelease(distroName, distroType, distroMajorVersion, distroMinorVersion)
            return None
    parseEtcRedHatReleaseRedhatReleaseData = staticmethod(parseEtcRedHatReleaseRedhatReleaseData)

    def findReleaseFromRPM(installedRPMSData):
        """
        This function will get the release information based on the
        redhat-release rpm that is installed.

        @return: Returns a DistroRelease object that contains information
        about the Distrobution Release.
        @rtype: DistroRelease

        @param installedRPMSData: List of installed rpms.
        @type installedRPMSData: Array
        """
        return None
    findReleaseFromRPM = staticmethod(findReleaseFromRPM)

class DistroRelease:
    """
    This is a container for the information that is in the
    /etc/redhat-release file.
    """
    def __init__(self, distroName, distroType, distroMajorVersion, distroMinorVersion):
        """
        @param distroName: The name of the distro.
        @type distroName: String
        @param distroType: The type of distro.
        @type distroType: String
        @param distroMajorVersion: The major version of the distro.
        @type distroMajorVersion: Int
        @param distroMinorVersion: The minor version of the distro.
        @type distroMinorVersion: Int
        """
        if (distroName == "Red Hat Enterprise Linux"):
            distroName = "RHEL"
        self.__distroName = distroName
        self.__distroType = distroType
        self.__distroMajorVersion = int(distroMajorVersion)
        self.__distroMinorVersion = int(distroMinorVersion)

    def __str__(self) :
        """
        This function returns a string reprenstation of the object.

        @return: Returns a string reprenstation of the object.
        @rtype: String
        """
        return "%s %s %s.%s" %(self.__distroName, self.__distroType, self.__distroMajorVersion, self.__distroMinorVersion)

    def getDistroName(self) :
        """
        Returns the name of the distro release.

        @return: Returns the name of the distro release.
        @rtype: String
        """
        return self.__distroName

    def getDistroType(self) :
        """
        Returns the type of the distro release.
        For example: AS,ES,WS,SERVER,etc.

        @return: Returns the type of the distro release.
        @rtype: String
        """
        return self.__distroType

    def getMajorVersion(self) :
        """
        Returns the major version of the distro release.

        @return: Returns the major version of the distro release.
        @rtype: String
        """
        return self.__distroMajorVersion

    def getMinorVersion(self) :
        """
        Returns the minor version of the distro release.

        @return: Returns the minor version of the distro release.
        @rtype: String
        """
        return self.__distroMinorVersion
