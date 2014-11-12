#!/usr/bin/env python
"""

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""

class SystemdParser:
    def parseSystemdServicesState(systemdServicesStateData) :
        # sos_commands/systemd/systemctl_list-unit-files
        parsedList = []
        if (not systemdServicesStateData == None):
            for item in systemdServicesStateData:
                item = item.strip().rstrip()
                if ((not (item.lower().find("unit file") >= 0)) and (len(item) > 0)):
                    itemSplit = item.split(" ", 1)
                    if (len(itemSplit) == 2):
                        systemdUnitState = SystemdUnitState(itemSplit[0].strip().rstrip(), itemSplit[1].strip().rstrip())
                        parsedList.append(systemdUnitState)
        return parsedList
    parseSystemdServicesState = staticmethod(parseSystemdServicesState)

class SystemdUnitState:
    def __init__(self, unitName, state):
        # See man page for systemctl for information about state descriptions under "is-enabled".
        self.__unitName = unitName
        self.__name = self.__unitName.split(".", 1)[0]
        self.__type = self.__unitName.split(".", 1)[1]
        self.__state = state

        # The default will be zero can be specified later in set
        # method if needed.
        self.__startOrderNumber = 0
        self.__stopOrderNumber = 0

    def __str__(self):
        return "%s(%s)" %(self.getUnitName(), self.getState())

    def getUnitName(self):
        return self.__unitName

    def getName(self):
        return self.__name

    def getType(self):
        return self.__type

    def getState(self):
        return self.__state

    def isEnabled(self):
        return ((self.__state.lower() == "enabled") or (self.__state.lower() == "enabled-runtime"))

    def isDisabled(self):
        return (self.__state.lower() == "disabled")

    def isStatic(self):
        return (self.__state.lower() == "static")

    def isLinked(self):
        return ((self.__state.lower() == "linked") or (self.__state.lower() == "linked-runtime"))

    def isMasked(self):
        return ((self.__state.lower() == "masked") or (self.__state.lower() == "masked-runtime"))

    def getStartOrderNumber(self):
        return self.__startOrderNumber

    def getStopOrderNumber(self):
        return self.__stopOrderNumber

    def setStartOrderNumber(self, startOrderNumber):
        self.__startOrderNumber = startOrderNumber

    def setStopOrderNumber(self, stopOrderNumber):
        self.__stopOrderNumber = stopOrderNumber

