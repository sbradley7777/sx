#!/usr/bin/env python
"""

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.08
@copyright :  GPLv2
"""
import logging

import sx
from sx.logwriter import LogWriter
from sx.plugins.lib.general.processparser import PS


class GlusterPeerNode:
    def __init__(self, distroRelease, date, uname_a, hostname,
                 uptime, networkMaps, chkConfigList, installedRPMS,
                 filesysMountsList, etcFstabList, processList,
                 gpnUUID, listOfPeerNodes):
        self.__distroRelease = distroRelease
        self.__date = date
        self.__uname_a = uname_a
        self.__hostname = hostname
        self.__uptime = uptime
        self.__networkMaps = networkMaps
        self.__chkConfigList = chkConfigList
        self.__installedRPMS = installedRPMS
        self.__filesysMountList = filesysMountsList
        self.__etcFstabList = etcFstabList
        self.__processList = processList
        self.__gpnUUID = gpnUUID
        self.__listOfPeerNodes = listOfPeerNodes

    def getDistroRelease(self) :
        return self.__distroRelease

    def getDate(self):
        return self.__date

    def getUnameA(self) :
        return self.__uname_a

    def getHostname(self) :
        return self.__hostname

    def getUptime(self) :
        return self.__uptime

    def getNetworkMaps(self) :
        return self.__networkMaps

    def getChkConfigList(self) :
        return self.__chkConfigList

    def getInstalledRPMS(self):
        return self.__installedRPMS

    def getFilesystemMountList(self):
        return self.__filesysMountList

    def getEtcFstabList(self):
        return self.__etcFstabList

    def getProcessList(self):
        return self.__processList

    def getUUID(self):
        return self.__gpnUUID

    def getPeerNodes(self):
        return self.__listOfPeerNodes

    # ###############################################################
    # Public Helper functions
    # ###############################################################
    def getGlusterProcesses(self):
        processList = []
        for process in self.getProcessList():
            if (process.getCommand().find("/usr/sbin/glusterfs") >= 0):
                processList.append(process)
        return processList
