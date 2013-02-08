#!/usr/bin/env python
"""
This is a collection of classes that contain data for files from a
sosreport in the directory:
var/log/*

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.14
@copyright :  GPLv2
"""
import re

class SysLogParser:
    def parseVarLogMessagesData(varLogMessagesData):
        """
        """
        parsedList = []
        if (varLogMessagesData == None):
            return parsedList
        monthsRegex = "january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|october|oct|november|nov|december|dec"
        monthsDayRegex = "3[01]|[0-2]{0,1}\d"
        timestamp = "(2[0-3]|[01]?[0-9]):([0-5]?[0-9]):([0-5]?[0-9])"
        hostname = "[a-zA-Z]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*"

        # The matches are case insenstive
        regexStanza = "(?i)(?P<month>%s) (?P<monthDay>%s) " %(monthsRegex, monthsDayRegex) + \
            "(?P<timestamp>%s) (?P<hostname>%s) " %(timestamp, hostname) + \
            "(?P<msg>.*)"

        remStanza = re.compile(regexStanza)
        for line in varLogMessagesData:
            mo = remStanza.match(line)
            if mo:
                month = mo.group("month").strip()
                monthDay = mo.group("monthDay").strip()
                timestamp = mo.group("timestamp").strip()
                hostname = mo.group("hostname").strip()
                msg = mo.group("msg")

                msgSplit = msg.split(":", 1)
                if (len(msgSplit) == 2):
                    messageSender = msgSplit[0].strip()
                    message = msgSplit[1].strip()
                    varLogMessages = VarLogMessages(line, month, monthDay,
                                                    timestamp, hostname,
                                                    messageSender, message)
                    parsedList.append(varLogMessages)
        return parsedList
    parseVarLogMessagesData = staticmethod(parseVarLogMessagesData)


class VarLogMessages:
    def __init__(self, orginalMessage, month, monthDay, timestamp, hostname, messageSender, message):
        self.__orginalMessage = orginalMessage
        self.__month = month
        self.__monthDay = monthDay
        self.__timestamp = timestamp
        self.__hostname = hostname
        self.__messageSender = messageSender
        self.__message = message

    def __str__(self):
        return "%s | %s | %s | %s | %s | %s" %(self.getMonth(), self.getMonthDay(), self.getTimestamp(),
                                               self.getHostname(), self.getMessageSender(), self.getMessage())

    def getOriginalMessage(self):
        return self.__orginalMessage

    def getMonth(self):
        return self.__month

    def getMonthDay(self):
        return self.__monthDay

    def getTimestamp(self):
        return self.__timestamp

    def getHostname(self):
        return self.__hostname

    def getMessageSender(self):
        return self.__messageSender

    def getMessage(self):
        return self.__message
