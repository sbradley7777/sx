#!/usr/bin/env python
"""

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.14
@copyright :  GPLv2
"""
import re

class KernelParser:
    def parseUnameAData(unameAData):
        unameASplit = []
        if (unameAData == None) :
            return UnameA("", "", "", "", "", "", "")
        elif (len(unameAData) == 1):
            # RHEL 5
            unameASplit = unameAData[0].strip().split()
        elif (len(unameAData) == 2):
            if (unameAData[0].startswith("Linux")):
                # RHEL 6
                unameASplit = unameAData[0].strip().split()
            else:
                # RHEL 4
                unameASplit = unameAData[1].strip().split()
        if (len(unameASplit) == 15):
            kernelVersion = "%s %s %s %s %s %s %s %s" %(unameASplit[3], unameASplit[4],
                                                        unameASplit[5], unameASplit[6],
                                                        unameASplit[7], unameASplit[8],
                                                        unameASplit[9], unameASplit[10])
            return UnameA(unameASplit[0],
                          unameASplit[1],
                          unameASplit[2],
                          kernelVersion,
                          unameASplit[11],
                          unameASplit[12],
                          unameASplit[13],
                          unameASplit[14])
        return UnameA("", "", "", "", "", "", "", "")
    parseUnameAData = staticmethod(parseUnameAData)

class KernelRelease:
    def __init__(self, kernelRelease):
        self.__kernelRelease = kernelRelease
        regex = "^(?P<majorRelease>2\.[0-9]*.[0-9]*)-" + \
            "(?P<minorRelease>[0-9]*)" + \
            "(?P<patchRelease>.*)\." + \
            "(?P<distroRelease>fc[0-9]*|el4|el5|el6|el7)"


        rem = re.compile(regex)
        mo = rem.match(self.__kernelRelease.strip())
        self.__majorReleaseNumber = ""
        self.__minorReleaseNumber = ""
        self.__patchReleaseNumber = ""
        self.__distroRelease = ""
        if mo:
            self.__majorReleaseNumber = mo.group("majorRelease")
            self.__minorReleaseNumber = mo.group("minorRelease")
            self.__patchReleaseNumber = mo.group("patchRelease").strip(".")
            self.__distroRelease = mo.group("distroRelease")

    def __str__(self):
        return self.__kernelRelease

    def getMajorReleaseNumber(self):
        return self.__majorReleaseNumber

    def getMinorReleaseNumber(self):
        return self.__minorReleaseNumber

    def getPatchReleaseNumber(self):
        return self.__patchReleaseNumber

    def getDistroRelease(self):
        return self.__distroRelease

    #def compareGT(self, kernelReleaseString):
    #    pass

class UnameA:
    # Fix clusternodecompare.py and kmod-gfs2 module check.
    def __init__(self, kernelName, hostname, kernelRelease, kernelVersion, machineHardwareName, proccessorType, hardwarePlatform, osName):
        self.__kernelName = kernelName
        self.__hostname = hostname
        self.__kernelRelease = KernelRelease(kernelRelease)
        self.__kernelVersion = kernelVersion
        self.__machineHardwareName = machineHardwareName
        self.__proccessorType = proccessorType
        self.__hardwarePlatform = hardwarePlatform
        self.__osName = osName

    def __str__(self):
        return "%s %s %s %s %s %s %s %s" %(self.__kernelName, self.__hostname, self.__kernelRelease, self.__kernelVersion,
                                           self.__machineHardwareName, self.__proccessorType, self.__hardwarePlatform, self.__osName)

    def getKernelName(self):
        return self.__kernelName

    def getHostname(self):
        return self.__hostname

    def getKernelRelease(self):
        return self.__kernelRelease

    def getKernelVersion(self):
        return self.__kernelVersion

    def getMachineHardwareName(self):
        return self.__machineHardwareName

    def getProcessorType(self):
        return self.__proccessorType

    def getHardwarePlatform(self):
        return self.__hardwarePlatform

    def getOSName(self):
        return self.__osName

    def getCurrentDate(self):
        splitKV = self.__kernelVersion.split(" ", 2)
        splitKV.reverse()
        if (len(splitKV) > 0):
            return splitKV[0]
        return ""

