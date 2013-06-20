#!/usr/bin/env python
"""
This is a collection of classes that contain data for files from a
sosreport in the directory:
var/log/*

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.15
@copyright :  GPLv2
"""

class VarLogMessagesMsg:
  def __init__(self, orginalMessage, timestamp, hostname, messageSender, pid, message):
    self.__orginalMessage = orginalMessage
    self.__timestamp = timestamp
    self.__hostname = hostname
    self.__messageSender = messageSender
    self.__pid = pid
    self.__message = message

  def __str__(self):
    #return "%s | %s | %s | %s | %s" %(self.getTimestamp(), self.getHostname(), self.getMessageSender(), self.getPid(), self.getMessage())
    return self.getOriginalMessage()

  def getOriginalMessage(self):
    return self.__orginalMessage

  def getTimestamp(self):
    return self.__timestamp

  def getHostname(self):
    return self.__hostname

  def getMessageSender(self):
    return self.__messageSender

  def getPid(self):
    return self.__pid

  def getMessage(self):
    return self.__message
