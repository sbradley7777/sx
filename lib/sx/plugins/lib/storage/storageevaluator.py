#!/usr/bin/env python
"""
This class will evalatuate a cluster and create a report that will
link in known issues with links to resolution.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.15
@copyright :  GPLv2
"""
import os.path
import logging

import sx
from sx.logwriter import LogWriter
from sx.tools import StringUtil

class StorageEvaluator():

    def __init__(self, storageData):
        self.__storageData = storageData

    def getStorageData(self):
        return self.__storageData

    def evaluate(self):
        rstring = ""
        storageData = self.getStorageData()
        bdt = storageData.getBlockDeviceTree()
        # ###################################################################
        # Find out if multipath bindging file is located on a fs /var.
        # ###################################################################
        fsVarExist = False
        # Find out if /var is its own filesystem
        for filesysMount in bdt.getFilesysMountList():
            if (filesysMount.getMountPoint() == "/var"):
                fsVarExist = True
                break;
        if (fsVarExist):
            for line in storageData.getMultipathConfData():
                lineSplit = line.strip().split()
                if (len(lineSplit) == 2):
                    if ((lineSplit[0].strip() == "bindings_file") and
                        (lineSplit[1].strip().startswith("/var"))):
                        description = "The binding file for multipath is located on /var."
                        urls = ["https://access.redhat.com/knowledge/solutions/17643"]
                        rstring += StringUtil.formatBulletString(description, urls)
                        break;
        # ###################################################################
        # Check if emc and dmm module are loaded at same time.
        # ###################################################################
        foundEMC = False
        foundDMMultipath = False
        for lsmod in storageData.getLSMod():
            if (lsmod.getModuleName() == "emcp"):
                foundEMC = True
            elif (lsmod.getModuleName() == "dm_multipath"):
                foundDMMultipath = True
        if (foundEMC and foundDMMultipath) :
            description = "The modules dm-emc and scsi_dh_emc should never be loaded at the same time. One of these packages should be remove: emc or device-mapper-multipath."
            urls = ["https://access.redhat.com/knowledge/solutions/45197"]
            rstring += StringUtil.formatBulletString(description, urls)

        # ###################################################################
        # Add newline to separate the node stanzas
        # ###################################################################
        if (len(rstring) > 0):
            rstring += "\n"
        # ###################################################################
        return rstring


