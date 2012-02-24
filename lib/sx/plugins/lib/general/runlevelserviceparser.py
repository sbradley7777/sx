#!/usr/bin/env python
"""
This is a collection of classes that contain data for files from a
sosreport in the directory:
sos_commands/startup

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.09
@copyright :  GPLv2
"""
import re
import logging

import sx
from sx.logwriter import LogWriter

class RunLevelParser:
    def parseChkConfigData(chkConfigData) :
        parsedList = []
        if (chkConfigData == None):
            return parsedList
        if (not chkConfigData == None):
            regexStanza = "^(?P<name>%s)\s*[0-6].(?P<runlevel0>o[f|n][f]?)\s*"%("\w+") + \
                "[0-6].(?P<runlevel1>o[f|n][f]?)\s*[0-6].(?P<runlevel2>o[f|n][f]?)\s*" + \
                "[0-6].(?P<runlevel3>o[f|n][f]?)\s*[0-6].(?P<runlevel4>o[f|n][f]?)\s*" + \
                "[0-6].(?P<runlevel5>o[f|n][f]?)\s*[0-6].(?P<runlevel6>o[f|n][f]?).*$"
            remStanza = re.compile(regexStanza)
            for item in chkConfigData:
                mo = remStanza.match(item)
                if mo:
                    chkConfigServiceStatus = ChkConfigServiceStatus(mo.group("name"),
                                                                    mo.group("runlevel0"),
                                                                    mo.group("runlevel1"),
                                                                    mo.group("runlevel2"),
                                                                    mo.group("runlevel3"),
                                                                    mo.group("runlevel4"),
                                                                    mo.group("runlevel5"),
                                                                    mo.group("runlevel6"))
                    parsedList.append(chkConfigServiceStatus)
        return parsedList
    parseChkConfigData = staticmethod(parseChkConfigData)

class ChkConfigServiceStatus:
    """
    Container for data from chkconfig --list. On is True, off is
    False.
    """
    def __init__(self, name, rl0, rl1, rl2, rl3, rl4, rl5, rl6):
        self.__name = name
        self.__rl0 = self.__convertBooleanString(rl0)
        self.__rl1 = self.__convertBooleanString(rl1)
        self.__rl2 = self.__convertBooleanString(rl2)
        self.__rl3 = self.__convertBooleanString(rl3)
        self.__rl4 = self.__convertBooleanString(rl4)
        self.__rl5 = self.__convertBooleanString(rl5)
        self.__rl6 = self.__convertBooleanString(rl6)

        # The default will be zero can be specified later in set
        # method if needed.
        self.__startOrderNumber = 0
        self.__stopOrderNumber = 0

    def __str__(self):
        return "%s(%d/%d): 0:%s 1:%s 2:%s 3:%s 4:%s 5:%s 6:%s" %(self.getName(), self.getStartOrderNumber(),
                                                                 self.getStopOrderNumber(), str(self.isEnabledRunlevel0()),
                                                                 str(self.isEnabledRunlevel1()), str(self.isEnabledRunlevel2()),
                                                                 str(self.isEnabledRunlevel3()), str(self.isEnabledRunlevel4()),
                                                                 str(self.isEnabledRunlevel5()), str(self.isEnabledRunlevel6()))

    def __convertBooleanString(self, booleanString):
        """
        This function is for converting strings to boolean. For
        example the strings used in chkconfig data for "on" is True
        and "off" is False.
        """
        if (booleanString == "on"):
            return True
        return False

    def setStartOrderNumber(self, startOrderNumber):
        """
        Set the start order number. Can be used to set ordering for
        collection of services.

        @param startOrderNumber: A number that represents the start
        order for this service.
        @type startOrderNumber: Int
        """
        self.__startOrderNumber = startOrderNumber

    def setStopOrderNumber(self, stopOrderNumber):
        """
        Set the stop order number. Can be used to set ordering for
        collection of services.

        @param stopOrderNumber: A number that represents the stop
        order for this service.
        @type stopOrderNumber: Int
        """
        self.__stopOrderNumber = stopOrderNumber

    def getName(self):
        return self.__name

    def isEnabledRunlevel0(self):
        return self.__rl0

    def isEnabledRunlevel1(self):
        return self.__rl1

    def isEnabledRunlevel2(self):
        return self.__rl2

    def isEnabledRunlevel3(self):
        return self.__rl3

    def isEnabledRunlevel4(self):
        return self.__rl4

    def isEnabledRunlevel5(self):
        return self.__rl5

    def isEnabledRunlevel6(self):
        return self.__rl6

    def isEnabledOnAnyRunlevel(self):
        return (self.isEnabledRunlevel1() or self.isEnabledRunlevel2() or
                self.isEnabledRunlevel3() or self.isEnabledRunlevel4() or
                self.isEnabledRunlevel5() or self.isEnabledRunlevel6())

    def isDisabledOnAllRunlevels(self):
        return (not self.isEnabledRunlevel1() and not self.isEnabledRunlevel2() and
                not self.isEnabledRunlevel3() and not self.isEnabledRunlevel4() and
                not self.isEnabledRunlevel5() and not self.isEnabledRunlevel6())

    def getStartOrderNumber(self):
        return self.__startOrderNumber

    def getStopOrderNumber(self):
        return self.__stopOrderNumber

