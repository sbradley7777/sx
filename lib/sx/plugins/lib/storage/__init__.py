#!/usr/bin/env python
"""
@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.11
@copyright :  GPLv2
"""
import logging

import sx
from sx.plugins.lib.general.distroreleaseparser import DistroReleaseParser
from sx.plugins.lib.general.distroreleaseparser import DistroRelease
from sx.plugins.lib.storage.blockdevicetree import BlockDeviceTree
from sx.plugins.lib.storage.procparser import ProcParser
from sx.plugins.lib.storage.procparser import ProcPartitions
from sx.plugins.lib.storage.procparser import ProcFilesystems
from sx.plugins.lib.storage.procparser import ProcMounts
from sx.plugins.lib.storage.procparser import ProcDevices
from sx.plugins.lib.storage.procparser import ProcScsiScsi
from sx.plugins.lib.kernel.modulesparser import ModulesParser
from sx.plugins.lib.kernel.modulesparser import LSMod
from sx.plugins.lib.storage.filesysparser import FilesysParser
from sx.plugins.lib.storage.filesysparser import FilesysMount
from sx.plugins.lib.log.syslogparser import SysLogParser
from sx.plugins.lib.log.syslogparser import VarLogMessages


class StorageData:
    def __init__(self, hostname, uptime, distroRelease, uname,
                 lsMod, multipathConf, dmCommandsMap, varLogMessages,
                 blockDeviceTree):
        """
        These are all the files that we know will be present.
        """
        self.__hostname = hostname
        self.__uptime = uptime
        self.__distroRelease = distroRelease
        self.__uname = uname

        # These vars we can set after inital object is created with
        # set functions

        self.__lsMod = lsMod

        self.__multipathConfData = []
        if (not multipathConf == None):
            self.__multipathConfData = multipathConf

        self.__dmCommandsMap = {}
        if (not dmCommandsMap == None):
            self.__dmCommandsMap = dmCommandsMap

        self.__varLogMessages = varLogMessages
        self.__blockDeviceTree = blockDeviceTree

    # #######################################################################
    # Get functions
    # #######################################################################
    def getHostname(self):
        """
        Returns the hostname.

        @return: Returns the hostname.
        @rtype: String
        """
        return self.__hostname

    def getUptime(self):
        """
        Returns the uptime for the cluster node.
        @return: Returns the uptime for the cluster node.
        @rtype: String
        """
        return self.__uptime

    def getDistroRelease(self):
        """
        Returns the DistroRelease Object for this node.

        @return: Returns the DistroRelease Object for this node.
        @rtype: DistroRelease
        """
        return self.__distroRelease

    def getUname(self):
        """
        Returns the data from the uname_a file.

        @return: Returns the data from the uname_a file.
        @rtype: String
        """
        return self.__uname

    def getLSMod(self):
        """
        Returns the data that was in the file "sos_commands/kernel/lsmod" as
        object array.

        @return: Returns the data that was in the file "sos_commands/kernel/lsmod" as
        object array.
        @rtype: Array
        """
        return self.__lsMod

    def getMultipathConfData(self):
        """
        Returns the data from the file /etc/multipath.conf as an array of strings.

        @return: Returns the data from the file /etc/multipath.conf as
        an array of strings.
        @rtype: Array
        """
        multipathConfDataNoComments = []
        for line in self.__multipathConfData:
            # Do not include comments and empty lines.
            if ((not line.strip().startswith("#")) and (len(line.strip()) > 0)):
                multipathConfDataNoComments.append(line.rstrip())
        return multipathConfDataNoComments

    def getDMCommandsMap(self):
        """
        This functions returns the dictionary for dmCommandsMap which is the
        mapping of all the data in the directory
        "sos_commands/devicemapper" contain in a sosreport.

        The key is the filename of the file in that directory and the
        value is data within that file.

        @return: This functions returns the dictionary for
        dmCommandsMap which is the mapping of all the data in the
        directory "sos_commands/devicemapper" contain in a sosreport.
        @rtype: Dictionary
        """
        return self.__dmCommandsMap

    def getVarLogMessages(self):
        """
        Returns the data that was in the file "/var/log/messages" as
        object array.

        @return: Returns the data that was in the file "/var/log/messages" as
        object array.
        @rtype: Array
        """
        return self.__varLogMessages

    def getBlockDeviceTree(self):
        return self.__blockDeviceTree

    # #######################################################################
    # Helper functions
    # #######################################################################
    def getSummary(self) :
        """
        Returns a string that contain basic information within this object.

        @return: Returns a string that contain basic information
        within this object.
        @rtype: String
        """
        unameASplit = self.getUname().split()
        unameA = ""
        for i in range (0, len(unameASplit)):
            if (i == 5) :
                unameA += "\n\t      "
            unameA += "%s " %(unameASplit[i])
            i = i + 1
        summary = ""
        summary += "Hostname:     %s" %(self.getHostname())
        summary += "\nRH Release:   %s" %(self.getDistroRelease())
        summary += "\nUptime:       %s" %(self.getUptime())
        summary += "\nUname -a:     %s" %(unameA)
        return summary

class StorageDataGenerator:
    def __init__(self):
        # The max size of the /var/log/messages file that can be
        # parsed in megabytes. If the file is to large then it will
        # take to long to parse the data and will appear hung.
        # TODO: Add override option in the future.
        self.__varLogMessagesSizeMax = 5

    def generate(self, report) :
        """
        This function will setup data structure to hold any data/path
        to files that are needed to use in this plugin.

        @param reports: This is the list of Report Objects.
        @type reports: Array
        """
        storageData = None
        varLogMessagesList = []
        varLogMessagesSize = (report.getFileSize("var/log/messages")/(1024*1024.0))
        if (int(varLogMessagesSize) < self.__varLogMessagesSizeMax):
            # Add in the data since it is smaller than max size.
            message = "The size of the messages log is %s MBs. If may take a few minutes to process the file." %(str(varLogMessagesSize))
            logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
            varLogMessagesList = SysLogParser.parseVarLogMessagesData(report.getDataFromFile("var/log/messages"))
        else:
            message = "The size of the messages log is %s MBs which is larger than the max file size that can be parsed which is %s MBs." %(str(varLogMessagesSize), str(self.__varLogMessagesSizeMax))
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)
        distroRelease = DistroReleaseParser.parseEtcRedHatReleaseRedhatReleaseData(report.getDataFromFile("etc/redhat-release"))
        procFilesystemsList = ProcParser.parseProcFilesystemsData(report.getDataFromFile("proc/filesystems"))
        fsTypes = []
        for procFilesystem in procFilesystemsList:
            fsTypes.append(procFilesystem.getFSType())
        mountData = report.getDataFromFile("mount")
        if (mountData == None):
            mountData = report.getDataFromFile("sos_commands/filesys/mount_-l")
        filesysMountsList = FilesysParser.parseFilesysMountData(mountData, fsTypes)

        dmCommandsMap = report.getDataFromDir("sos_commands/devicemapper")
        blockDeviceTree = BlockDeviceTree(ProcParser.parseProcPartitionsData(report.getDataFromFile("proc/partitions")),
                                          procFilesystemsList,
                                          ProcParser.parseProcDevicesData(report.getDataFromFile("proc/devices")),
                                          ProcParser.parseProcScsiScsiData(report.getDataFromFile("proc/scsi/scsi")),
                                          filesysMountsList,
                                          dmCommandsMap.get("dmsetup_info_-c"),
                                          dmCommandsMap.get("dmsetup_table"))

        storageData = StorageData(report.getHostname(),
                                  report.getUptime(),
                                  distroRelease,
                                  report.getUname(),
                                  ModulesParser.parseLSModData(report.getDataFromFile("sos_commands/kernel/lsmod")),
                                  report.getDataFromFile("etc/multipath.conf"),
                                  report.getDataFromDir("sos_commands/devicemapper"),
                                  varLogMessagesList,
                                  blockDeviceTree)

        return storageData
