#!/usr/bin/env python
"""

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.16
@copyright :  GPLv2
"""
from sx.tools import StringUtil

class ProcessParser:
    def parsePSData(psData):
        psList = []
        if (psData == None):
            return psList
        else:
            for process in psData:
                process = process.rstrip()
                if (not process.startswith("USER")):
                    processSplit = process.split(None, 10)
                    if (len(processSplit) == 11):
                        psList.append(PS(processSplit[0], processSplit[1], processSplit[2],
                                         processSplit[3], processSplit[4], processSplit[5],
                                         processSplit[6], processSplit[7], processSplit[8],
                                         processSplit[9], processSplit[10]))
        return psList
    parsePSData = staticmethod(parsePSData)


class PS:
    def __init__(self, user, pid, cpuPercentage, memoryPercentage, vsz,
                 rss, tty, stat, start, time, command):
        self.__user = user
        self.__pid = pid
        self.__cpuPercentage = cpuPercentage
        self.__memoryPercentage = memoryPercentage
        self.__vsz = vsz
        self.__rss = rss
        self.__tty = tty
        self.__stat = stat
        self.__start = start
        self.__time = time
        self.__command = command

    def __str__(self):
        rString = "%s: CPU %s | MEM %s | %s" %(self.getPID(), self.getCPUPercentage(),
                                               self.getMemoryPercentage(), self.getCommand())
        return rString

    def getUser(self):
        return self.__user

    def getPID(self):
        return self.__pid

    def getCPUPercentage(self):
        return self.__cpuPercentage

    def getMemoryPercentage(self):
        return self.__memoryPercentage

    def getVSZ(self):
        return self.__vsz

    def getRSS(self):
        return self.__rss

    def getTTY(self):
        return self.__tty

    def getStat(self):
        return self.__stat

    def getStart(self):
        return self.__start

    def getTime(self):
        return self.__time

    def getCommand(self):
        return self.__command
