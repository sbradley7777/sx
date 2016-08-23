#!/usr/bin/env python
"""
This is a collection of classes that contain data for files from a
sosreport in the directory:
sos_commands/startup

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""
import re

class RunLevelParser:
    def parseChkConfigData(chkConfigData) :
        parsedList = []
        if (chkConfigData == None):
            return parsedList
        if (not chkConfigData == None):
            #regexStanza = "^(?P<name>%s)\s*[0-6].(?P<runlevel0>o[f|n][f]?)\s*"%("\w+") + \
            #    "[0-6].(?P<runlevel1>o[f|n][f]?)\s*[0-6].(?P<runlevel2>o[f|n][f]?)\s*" + \
            #    "[0-6].(?P<runlevel3>o[f|n][f]?)\s*[0-6].(?P<runlevel4>o[f|n][f]?)\s*" + \
            #    "[0-6].(?P<runlevel5>o[f|n][f]?)\s*[0-6].(?P<runlevel6>o[f|n][f]?).*$"
            # Current working regex
            #regexStanza = "^(?P<name>\w+(-\w+)?)\s*[0-6].(?P<runlevel0>o[f|n][f]?)\s*" + \
            #    "[0-6].(?P<runlevel1>o[f|n][f]?)\s*[0-6].(?P<runlevel2>o[f|n][f]?)\s*" + \
            #    "[0-6].(?P<runlevel3>o[f|n][f]?)\s*[0-6].(?P<runlevel4>o[f|n][f]?)\s*" + \
            #    "[0-6].(?P<runlevel5>o[f|n][f]?)\s*[0-6].(?P<runlevel6>o[f|n][f]?).*$"

            regexStanza = "^(?P<name>\w+(-\w+)?)\s*[0-6].(?P<runlevel0>o[f|n][f]?|desactivado|activo)\s*" + \
                "[0-6].(?P<runlevel1>o[f|n][f]?|desactivado|activo)\s*[0-6].(?P<runlevel2>o[f|n][f]?|desactivado|activo)\s*" + \
                "[0-6].(?P<runlevel3>o[f|n][f]?|desactivado|activo)\s*[0-6].(?P<runlevel4>o[f|n][f]?|desactivado|activo)\s*" + \
                "[0-6].(?P<runlevel5>o[f|n][f]?|desactivado|activo)\s*[0-6].(?P<runlevel6>o[f|n][f]?|desactivado|activo).*$"

            remStanza = re.compile(regexStanza)
            for item in chkConfigData:
                mo = remStanza.match(item)
                if mo:
                    chkConfigServiceStatus = ChkConfigServiceStatus(mo.group("name"),
                                                                    item,
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
    def __init__(self, name, rawStatus, rl0, rl1, rl2, rl3, rl4, rl5, rl6):
        self.__name = name
        # The actual line of service
        self.__rawStatus = rawStatus.rstrip()
        self.__rl0 = self.__convertStringToBoolean(rl0.strip())
        self.__rl1 = self.__convertStringToBoolean(rl1.strip())
        self.__rl2 = self.__convertStringToBoolean(rl2.strip())
        self.__rl3 = self.__convertStringToBoolean(rl3.strip())
        self.__rl4 = self.__convertStringToBoolean(rl4.strip())
        self.__rl5 = self.__convertStringToBoolean(rl5.strip())
        self.__rl6 = self.__convertStringToBoolean(rl6.strip())

    def __str__(self):
        return "%s: 0:%s 1:%s 2:%s 3:%s 4:%s 5:%s 6:%s" %(self.getName(),
                                                          self.__convertBooleanToString(self.isEnabledRunlevel0()),
                                                          self.__convertBooleanToString(self.isEnabledRunlevel1()),
                                                          self.__convertBooleanToString(self.isEnabledRunlevel2()),
                                                          self.__convertBooleanToString(self.isEnabledRunlevel3()),
                                                          self.__convertBooleanToString(self.isEnabledRunlevel4()),
                                                          self.__convertBooleanToString(self.isEnabledRunlevel5()),
                                                          self.__convertBooleanToString(self.isEnabledRunlevel6()))


    def __convertBooleanToString(self, boolean):
        if (boolean):
            return "on"
        else:
            return "off"

    def __convertStringToBoolean(self, booleanString):
        """
        This function is for converting strings to boolean. For
        example the strings used in chkconfig data for "on" is True
        and "off" is False.
        """
        if (booleanString == "on"):
            return True
        elif (booleanString == "activo"):
            return True
        return False

    def getName(self):
        return self.__name

    def getRawStatus(self):
        return self.__rawStatus

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

    #def getStartOrderNumber(self):
    #    return self.__startOrderNumber

    #def getStopOrderNumber(self):
    #    return self.__stopOrderNumber

