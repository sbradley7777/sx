#!/usr/bin/env python
"""
This class does various operations on a /etc/cluster/cluster.conf file
that is in xml format.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.10
@copyright :  GPLv2
"""
import os.path
import re
import string
import logging
import fileinput
from xml.etree.ElementTree import XML, fromstring, tostring
from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import Element

import sx
from sx.tools import FileUtil
from sx.plugins.lib.storage.filesysparser import FilesysMount

class Quorumd:
    def __init__(self, quorumdAttributes):
        self.__quorumdAttributes = quorumdAttributes
        self.__quorumdHeuristics = []

    def __str__(self):
        rString = "Label: %s | min_score: %s \n" %(self.getLabel(), self.getMinScore())
        for heuristic in self.getHeuristics():
            rString += "\t%s\n" %(str(heuristic))
        return rString.rstrip()

    def addHeuristic(self, heuristic):
        if (len(heuristic.getProgram()) > 0):
            self.__quorumdHeuristics.append(heuristic)
            return True
        else:
            return False

    def getHeuristics(self):
        return self.__quorumdHeuristics

    def __getAttribute(self, name):
        if (self.__quorumdAttributes.has_key(name)):
            return self.__quorumdAttributes.get(name)
        else:
            return ""

    # Need to set defaults on some of these if empty string is returned.
    def getLabel(self):
        return self.__getAttribute("label")

    def getDevice(self):
        return self.__getAttribute("device")

    def getCmanLabel(self):
        return self.__getAttribute("cman_label")

    def getMinScore(self):
        return self.__getAttribute("min_score")

    def getUseUptime(self):
        return self.__getAttribute("use_uptime")

    def getPriority(self):
        return self.__getAttribute("priority")

    def getStatusFile(self):
        return self.__getAttribute("status_file")

    def getMasterWins(self):
        return self.__getAttribute("master_wins")

    def getAllowKill(self):
        return self.__getAttribute("allow_kill")

    def getReboot(self):
        return self.__getAttribute("reboot")

class QuorumdHeuristic:
    def __init__(self, heuristicAttributes):
        # If there is no program value then this should be invalid heuristic.
        self.__program = ""
        # The default interval is determined by the qdiskd timeout. Not sure how
        # to get that. By default I will set to -1.
        self.__interval = -1
        # Default is 1
        self.__score = 1
        # The default interval is determined by the qdiskd timeout. Not sure how
        # to get that. By default I will set to -1.
        self.__tko = -1
        if (heuristicAttributes.has_key("program")):
           self.__program = heuristicAttributes.get("program")
        if (heuristicAttributes.has_key("interval")):
            self.__interval = int(heuristicAttributes.get("interval"))
        if (heuristicAttributes.has_key("score")):
            self.__score = int(heuristicAttributes.get("score"))
        if (heuristicAttributes.has_key("tko")):
            self.__tko = int(heuristicAttributes.get("tko"))

    def __str__(self):
        rString = ""
        if (len(self.getProgram()) > 0):
            rString =  "program: %s" %(self.getProgram())
            if (self.getInterval() > 0):
                rString += " | interval: %d" %(self.getInterval())
            if (self.getScore() > 0):
                rString += " | score: %d" %(self.getScore())
            if (self.getTKO() > 0):
                rString += " | tko: %d" %(self.getTKO())
        return rString

    def getProgram(self):
        return self.__program

    def getInterval(self):
        return self.__interval

    def getScore(self):
        return self.__score

    def getTKO(self):
        return self.__tko

class ClusterConfMount(FilesysMount):
    def __init__(self, deviceName, mountPoint, fsType, mountOptions, resourceName, fsid):
        # /etc/fstab does not have attributes section so we just set to empty string.
        FilesysMount.__init__(self, deviceName, mountPoint, fsType, "", mountOptions)

        self.__resourceName = resourceName
        self.__fsid = fsid

    def getResourceName(self):
        return self.__resourceName

    def getFSID(self):
        return self.__fsid

class FailoverDomain:
    def __init__(self, name, isOrdered, isRestricted, failoverDomainMembersMap):
        self.__name = name
        self.__isOrdered = isOrdered
        self.__isRestricted = isRestricted
        self.__failoverDomainMembersMap = failoverDomainMembersMap

    def __str__(self):
        rString = "%s(ordered = %s | restricted = %s)\n" %(self.getName(), str(self.isOrdered()), str(self.isRestricted()))
        fdMap = self.getFailoverDomainMembersMap()
        keys = fdMap.keys()
        for key in keys:
            rString += "\t%s(priority: %s)\n" %(key, fdMap.get(key))
        return rString

    def getName(self):
        return self.__name

    def isOrdered(self):
        return (self.__isOrdered == "0")

    def isRestricted(self):
        return (self.__isRestricted == "0")

    def getFailoverDomainMembersMap(self):
        return self.__failoverDomainMembersMap

class ClusteredResource():
    def __init__(self, resourceType, resourceName, isPrivate, attributesMap):
        self.__resourceType = resourceType
        self.__resourceName = resourceName
        self.__isPrivate = isPrivate
        self.__attributesMap = attributesMap

    def __str__(self):
        return "%s(%s)" %(self.getName(), self.getType())

    def getType(self):
        return self.__resourceType

    def getName(self):
        return self.__resourceName

    def isPrivate(self):
        return self.__isPrivate

    def getAttributesMap(self):
        return self.__attributesMap

    def getAttributeNames(self):
        return self.__attributesMap.keys()

    def getAttribute(self, attributeName):
        if (self.__attributesMap.has_key(attributeName)):
            return self.__attributesMap.get(attributeName)
        return ""

class ClusteredResourceInService(ClusteredResource):
    def __init__(self, resourceType, resourceName, isPrivate, attributesMap, level, order):
        ClusteredResource.__init__(self, resourceType, resourceName, isPrivate, attributesMap)
        # The level is what level in the tree it is
        self.__level = level
        # The order is the order it was read in from the xml
        self.__order = order

        self.__childResources = []
    def __str__(self):
        return "%s(%s)" %(self.getName(), self.getType())

    def getLevel(self):
        return self.__level

    def getOrder(self):
        return self.__order

    def getChildResources(self):
        return self.__childResources

    def addChildResource(self, clusteredResource):
        self.__childResources.append(clusteredResource)

class ClusteredService():
    def __init__(self, serviceName, recoveryPolicy, failoverDomain, listOfClusteredResources, isVirtualMachineService=False):
        self.__serviceName = serviceName
        self.__recoveryPolicy = recoveryPolicy
        self.__failoverDomain = failoverDomain
        self.__listOfClusteredResources = listOfClusteredResources
        self.__isVirtualMachineService = isVirtualMachineService

    def __str__(self):
        rString = " %s(recovery policy: %s | failover domain: %s)\n     %s\n%s" %(self.getName(), self.getRecoveryPolicy(),
                                                                                  self.getFailoverDomain().getName(), self.getFailoverDomain(),
                                                                                  self.walkServiceToString())
        return rString

    def __walkServiceToStringHelper(self, resource):
        rString = ""
        for childResource in resource.getChildResources():
            spacer = "  " * childResource.getLevel()
            rString += "  %s%s\n%s" %(spacer, str(childResource), self.__walkServiceToStringHelper(childResource))
        return rString

    def walkServiceToString(self):
        rString = ""
        for resource in self.getListOfClusterResources():
            spacer = "  " * (resource.getLevel() - 1)
            rString +="     %s%s\n%s" %(spacer, str(resource), self.__walkServiceToStringHelper(resource))
        return rString

    def getName(self):
        return self.__serviceName

    def getRecoveryPolicy(self):
        return self.__recoveryPolicy

    def getFailoverDomain(self):
        return self.__failoverDomain

    def getListOfClusterResources(self):
        return self.__listOfClusteredResources

    def isVirtualMachineService(self):
        return self.__isVirtualMachineService

    def __getFlatListOfClusterResourcesHelper(self, resource):
        flatListOfClusteredResources = []
        for childResource in resource.getChildResources():
            flatListOfClusteredResources.append(childResource)
            flatListOfClusteredResources += self.__getFlatListOfClusterResourcesHelper(childResource)
        return flatListOfClusteredResources

    def getFlatListOfClusterResources(self):
        flatListOfClusteredResources = []
        for resource in self.getListOfClusterResources():
            flatListOfClusteredResources.append(resource)
            flatListOfClusteredResources += self.__getFlatListOfClusterResourcesHelper(resource)
        return flatListOfClusteredResources

class ClusterNodeProperties:
    def __init__(self, nodeName, nodeID, votes, multicastAddress, multicastInterface,
                 cmanMulticastAddress, fenceDevicesList) :
        """
        @param nodeName: The name of node.
        @type nodeName: String
        @param nodeID: The id of the node.
        @type nodeID: String
        @param votes: The votes for the node.
        @type votes: String
        @param multicastAddress: The multicast address of the node.
        @type multicastAddress: String
        @param multicastInterface: The multicast interface for the node.
        @type multicastInterface: String
        @param cmanMulticastAddress: The cman multicast address for the node.
        @type cmanMulticastAddress: String
        @param fenceDevicesList: A dictionary of fence devices.
        @type fenceDevicesList: Array
        """
        self.__nodeName = nodeName
        self.__nodeID = nodeID
        self.__votes = votes
        self.__multicastAddress = multicastAddress
        self.__multicastInterface = multicastInterface
        self.__cmanMulticastAddress = cmanMulticastAddress
        # List of dictionaries
        self.__fenceDevicesList = fenceDevicesList

    def __str__(self):
        rstring =  ""
        rstring += "%s\n" %(self.getNodeName())
        rstring += "\tClusternode ID:              %s\n" %(self.getNodeID())
        rstring += "\tClusternode Votes:           %s\n" %(self.getVotes())
        rstring += "\tClusternode MC Address:      %s\n" %(self.getMulticastAddress())
        rstring += "\tClusternode MC Interface:    %s\n" %(self.getMulticastInterface())
        rstring += "\tClusternode MC cman Address: %s\n" %(self.getCmanMulticastAddress())
        fenceDeviceString = ""
        for fd in self.getFenceDevicesList():
            fenceDeviceString += "\t\t%s\n" %(str(fd))
        if (len(fenceDeviceString) > 0):
            rstring += "\tFence Devices:\n%s" %(fenceDeviceString.rstrip())
        return rstring

    def getNodeName(self):
        """
        Returns the node name.

        @return: Returns the node name.
        @rtype: String
        """
        if (self.isEmpty()):
            return ""
        return self.__nodeName

    def getNodeID(self) :
        """
        Returns the nodeID.

        @return: Returns the nodeID.
        @rtype: String
        """
        if (self.isEmpty()):
            return "-1"
        return self.__nodeID

    def getVotes(self) :
        """
        Returns the votes for the node.

        @return: Returns the votes for the node.
        @rtype: String
        """
        if (self.isEmpty()):
            return ""
        return self.__votes

    def getMulticastAddress(self):
        """
        Returns the multicast address.

        @return: Returns the multicast address.
        @rtype: String
        """
        if (self.isEmpty()):
            return ""
        return self.__multicastAddress

    def getMulticastInterface(self):
        """
        Returns the multicast interface.

        @return: Returns the multicast interface.
        @rtype: String
        """
        if (self.isEmpty()):
            return ""
        return self.__multicastInterface

    def getCmanMulticastAddress(self):
        """
        Returns the cman multicast address.

        @return: Returns the cman multicast address.
        @rtype: String
        """
        if (self.isEmpty()):
            return ""
        return self.__cmanMulticastAddress

    def getFenceDevicesList(self) :
        """
        Returns the node name.

        @return: Returns the fence devices for the node.
        @rtype: Array
        """
        return self.__fenceDevicesList

    def isEmpty(self) :
        """
        If the nodeName is an empty string this object is considered
        empty. Returns True if nodeName is not empty.

        @return: Returns True if nodeName is not empty.
        @rtype: Boolean
        """
        # If node name is empty then considered data empty because data not associated with node name
        return (not len(self.__nodeName)> 0)

class FenceDevice:
    def __init__(self, name, agent, ipAddress=""):
        self.__name = name
        self.__agent = agent
        self.__ipAddress = ipAddress

    def getName(self):
        return self.__name

    def getAgent(self):
        return self.__agent

    def getIPAddress(self):
        return self.__ipAddress

class ClusterNadeFenceDevice(FenceDevice):
    def __init__(self, name, agent, ipAddress, methodName, methodOrder, methodFenceDeviceOrder):
        FenceDevice.__init__(self, name, agent, ipAddress)
        self.__methodName = methodName
        self.__methodOrder = methodOrder
        self.__methodFenceDeviceOrder = methodFenceDeviceOrder

    def __str__(self):
        if (len(self.getIPAddress()) > 0):
            return "%s(%s) %s | method: %s(%d|%d)" %(self.getName(), self.getAgent(),self.getIPAddress(),
                                                     self.getMethodName(), self.getMethodOrder(),
                                                     self.getMethodFenceDeviceOrder())
        else:
            return "%s(%s) | method: %s(%d|%d)" %(self.getName(), self.getAgent(), self.getMethodName(),
                                                  self.getMethodOrder(), self.getMethodFenceDeviceOrder())

    def getMethodName(self):
        return self.__methodName

    def getMethodOrder(self):
        """
        Returns the sequenctial order for the methods. The method order is
        determine by the sequential order of xml.

        The method order is the same as the fence level.

        @return: Returns the sequenctial order for the methods. The
        method order is determine by the sequential order of xml.
        @rtype: Int
        """
        return self.__methodOrder

    def getMethodFenceDeviceOrder(self):
        """
        Returns the sequenctial order for the fence devices under the
        method. The fence device order under each method is
        determine by the sequential order of xml.

        @return: Returns the sequenctial order for the fence devices
        under the method. The fence device order under each method is
        determine by the sequential order of xml.
        @rtype: Int
        """
        return self.__methodFenceDeviceOrder

class ClusterHAConfAnalyzer :
    """
    This class does various operations on a cluster.conf file that is
    in xml format.
    """
    def __init__(self, pathToClusterConf) :
        """
        Setups the cluster xml xpathcontext for the file. It will add
        in "" for password section if needed.

        @param pathToClusterConf: Path to the cluster.conf file that is an
        xml file.
        @type pathToClusterConf: String
        """
        # Ignore parser errors on cluster.conf files.
        #import warnings
        #warnings.filterwarnings("ignore", ": parser erwarror : ")

        self.__pathToClusterConf = pathToClusterConf
        self.__ccRootElement = None

        if (os.path.exists(self.__pathToClusterConf)) :
            clusterConfReadLines = []
            try:
                clusterConfFile = open(self.__pathToClusterConf, "r")
                clusterConfReadLines = clusterConfFile.readlines()
                clusterConfFile.close()
            except IOError:
                message = "There was an error reading the file: %s" %(self.__pathToClusterConf)
                logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            # Create the XML data string and replace/remove some text
            # in the XML file to make sure it parses with no errros.
            clusterConfString = ""
            for line in clusterConfReadLines:
                # Sometimes parser errors are thrown to console from
                # cluster.conf when parsing the file. Example:
                # parser warning : Unsupported version '1.1' <?xml version="1.1"?>
                # I will skip the header declaration to avoid these.
                if (not line.startswith("<?xml")):
                    if (line.find("=***") >= 0):
                        line = re.sub("=\*\*\*", "=\"***\"", line)
                    clusterConfString += line
            if (len(clusterConfString) > 0):
                # #######################################################################
                # Try to do xml parsing with elementtree instead of libxml2.
                # #######################################################################
                try:
                    self.__ccRootElement = fromstring(clusterConfString)
                except IOError:
                    message = "There was an XML parsing error on the file: %s." %(self.__pathToClusterConf)
                    logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
        else:
            message = "The cluster.conf file does not exist: %s" %(self.__pathToClusterConf)
            logging.getLogger(sx.MAIN_LOGGER_NAME).error(message)
            return

    # #######################################################################
    # Private IS Functions
    # #######################################################################
    def __isXMLValid(self) :
        """
        If there is parsing errors opening xml file up then file is
        invalid.

        @return: Returns False if the file contains parsing errors,
        otherwise returns True.
        @rtype: Boolean
        """
        return (not self.__ccRootElement == None)

    # #######################################################################
    # IS Functions
    # #######################################################################
    def isClusterConfFilesIdentical(self,listOfFiles) :
        if (not len(listOfFiles) > 1):
            return False
        return  FileUtil.isFilesIdentical(self.__pathToClusterConf, listOfFiles)

    def isQDiskEnabledWithHeurtistics(self):
        """
        Returns True if their quorumd is enable in their cluster.conf.

        @return: Returns True if their quorumd is enable in their
        cluster.conf.
        @rtype: Boolean
        """
        qdiskHeuristicsCount = len(self.__ccRootElement.findall("quorumd/"))
        return  (qdiskHeuristicsCount > 0)

    def isFencingEnabledOnAllNodes(self) :
        """
        Returns True if all clusternodes have fencing agent defined.

        @return: Trie of all clusternodes have fencing agent defined.
        @rtype: Boolean
        """
        for cnName in self.getClusterNodeNames():
            cnFenceDeviceList = self.getClusterNodeFenceDevicesList(cnName)
            if (not len(cnFenceDeviceList) > 0):
                return False
        return True

    def isFenceDeviceAgentEnabledOnClusterNode(self, clusternodeName, fenceDeviceAgentName):
        """
        Returns True if a particular fence device(agent) is enabled on
        a node under clusternodes stanza.  This is the name of the
        agent and not the name of the fence device.

        @return: Returns True if a particular fence device is enabled
        on a node under clusternodes stanza.
        @rtype: Boolean

        @param clusternodeName: The name of the node.
        @type clusternodeName: String
        @param fenceDeviceAgentName: The type of fenceDeviceAgentName that will be queried.
        @type fenceDeviceAgentName: String
        """
        fenceDeviceAgentName = fenceDeviceAgentName.strip()
        cnFenceDeviceList = self.getClusterNodeFenceDevicesList(clusternodeName)
        for fd in cnFenceDeviceList:
            if (fd.getAgent() == fenceDeviceAgentName):
                return True
        return False

    def isCleanStartEnabled(self) :
        """
        Returns True if the value is equal to 0, otherwise False.

        @return: Returns True if the value is equal to 0, otherwise False.
        @rtype: Boolean
        """
        fdElement = self.__ccRootElement.find("fence_daemon")
        try:
            return (not fdElement.attrib["clean_start"] == "0")
        except KeyError:
            # If attribute does not exist then return False
            return False
        except AttributeError:
            return False

    # #######################################################################
    # Get Functions
    # #######################################################################
    def getQuorumd(self):
        quorumdElement = self.__ccRootElement.find("quorumd")
        if (not quorumdElement == None):
            quorumd = Quorumd(quorumdElement.attrib)
            for heuristic in quorumdElement:
                quorumd.addHeuristic(QuorumdHeuristic(heuristic.attrib))
            return quorumd
        return None

    def getClusterName(self) :
        """
        Returns the name of the cluster.

        @return: Returns the name of the cluster.
        @rtype: String
        """
        if (self.__isXMLValid()):
            try:
                return self.__ccRootElement.attrib["name"]
            except KeyError:
                pass
            except AttributeError:
                pass
        return ""

    def getClusterNodeNames(self) :
        """
        Returns an array of strings for all the node names in
        cluster.conf.

        @return: Returns an array of strings for all the node names in
        cluster.conf.
        @rtype: Array
        """
        hostnames = []
        if (self.__isXMLValid()):
            for cnElement in self.__ccRootElement.findall("clusternodes/clusternode") :
                try:
                    hostnames.append(cnElement.attrib["name"])
                except KeyError:
                    pass
                except AttributeError:
                    pass

        return hostnames

    def getPostFailDelay(self) :
        """
        Returns the post_fail_delay value in fence_daemon
        properties. Empty String is returned if there was an error or
        no value.

        @return: The value of string post_join_delay in xml.
        @rtype: String
        """
        fdElement = self.__ccRootElement.find("fence_daemon")
        try:
            return fdElement.attrib["post_fail_delay"]
        except KeyError:
            return "0"
        except AttributeError:
            return "0"

    def getPostJoinDelay(self) :
        """
        Returns the post_join_delay value in fence_daemon
        properties. Empty String is returned if there was an error or
        no value.

        @return: The value of string post_join_delay in xml.
        @rtype: String
        """
        fdElement = self.__ccRootElement.find("fence_daemon")
        try:
            return fdElement.attrib["post_join_delay"]
        except KeyError:
            return "3"
        except AttributeError:
            return "3"

    def getCmanMulticastAddress(self) :
        """
        Returns the post_join_delay value in fence_daemon
        properties. Empty String is returned if there was an error or
        no value.

        @return: The value of string post_join_delay in xml.
        @rtype: String
        """
        fdElement = self.__ccRootElement.find("cman/multicast")
        try:
            return fdElement.attrib["addr"]
        except KeyError:
            return ""
        except AttributeError:
            return ""

    def getFenceDeviceList(self) :
        """
        This function will return an array of dictionaries for each
        fencedevice list.

        @return: Returns an array of dictionaries for each fencedevice
        list.
        @rtype: Array
        """
        # Get the names of all the fence devices
        fenceDeviceList = []
        for fdElement in self.__ccRootElement.findall("fencedevices/fencedevice") :
            try:
                name = fdElement.attrib["name"]
                agent = fdElement.attrib["agent"]
                ipAddress = ""
                try:
                    ipAddress = fdElement.attrib["ipaddr"]
                except KeyError:
                    pass
                except AttributeError:
                    pass
                try:
                    ipAddress = fdElement.attrib["hostname"]
                except KeyError:
                    pass
                except AttributeError:
                    pass
                fenceDeviceList.append(FenceDevice(name, agent, ipAddress))
            except KeyError:
                continue
            except AttributeError:
                continue
        return fenceDeviceList

    def getClusterNodeFenceDevicesList(self, clusternodeName) :
        cnFenceDevicesList = []
        # Get a list of all the fencing devices.
        fenceDeviceList = self.getFenceDeviceList()
        # Loop over each nodes fence devices
        for cnElement in self.__ccRootElement.findall("clusternodes/clusternode") :
            currentNodeName = ""
            try:
                currentNodeName = cnElement.attrib["name"]
            except KeyError:
                continue
            except AttributeError:
                continue
            if (currentNodeName == clusternodeName):
                cnMethodElements = cnElement.findall("fence/method")
                methodOrder = 1
                for cnMethodElement in cnMethodElements:
                   try:
                       methodName = cnMethodElement.attrib["name"]
                       methodFenceDeviceOrder = 1
                       for fdElement in cnMethodElement:
                           currentFDName = fdElement.attrib["name"]
                           for fd in fenceDeviceList:
                               if (fd.getName() == currentFDName):
                                   cnFenceDevicesList.append(ClusterNadeFenceDevice(fd.getName(), fd.getAgent(),
                                                                                    fd.getIPAddress(), methodName,
                                                                                    methodOrder, methodFenceDeviceOrder))
                                   methodFenceDeviceOrder = methodFenceDeviceOrder + 1
                                   break
                   except KeyError:
                       pass
                   except AttributeError:
                       pass
                   # Increment the method order
                   methodOrder = methodOrder + 1
        return cnFenceDevicesList

    def getClusterNodeProperties(self, clusternodeName) :
        """
        This function will return a dictionary of the properties in
        the clusternode section.

        @return: Returns a dictionary of the properties in the
        cluster.conf.
        @rtype: Dictionary
        """
        cmanMulticastAddress = self.getCmanMulticastAddress()
        cnFenceDevicesList = self.getClusterNodeFenceDevicesList(clusternodeName)
        # If there are no node ids set then we got to write them in
        # order they are traversed starting at 1.
        nodeIDFound = False
        for cnElement in self.__ccRootElement.findall("clusternodes/clusternode") :
                try:
                    nodeID = cnElement.attrib["nodeid"]
                    if (len(nodeID) > 0):
                        nodeIDFound = True
                except KeyError:
                    continue
        if (not nodeIDFound):
            message = "There was one or more nodes without a nodeid set in the /etc/cluster/cluster.conf."
            logging.getLogger(sx.MAIN_LOGGER_NAME).warning(message)
            message = "Will try to resolve this automatically so reporting will continue, please verify by reviewing the reports that contain the cluster.conf."
            logging.getLogger(sx.MAIN_LOGGER_NAME).info(message)

        # Loop over each node, and increment the currentNoNodeID
        # counter since we want it to start at 1, we will execute it
        # first and dont have to worry it erroring out. Since we
        # transvere in order of cluster.conf, we can assume they are
        # in order and start at node id 1.
        currentNoNodeID = 0
        for cnElement in self.__ccRootElement.findall("clusternodes/clusternode") :
            currentNoNodeID = currentNoNodeID + 1
            nodeName = ""
            nodeID = ""
            votes = ""
            multicastAddress = ""
            multicastInterface = ""
            try:
                nodeName = cnElement.attrib["name"]
            except KeyError:
                continue
            except AttributeError:
                continue
            if (nodeName == clusternodeName):
                try:
                    nodeID = cnElement.attrib["nodeid"]
                except KeyError:
                    nodeID = str(currentNoNodeID)
                except AttributeError:
                    nodeID = str(currentNoNodeID)
                try:
                    votes = cnElement.attrib["votes"]
                except KeyError:
                    votes = "1"
                except AttributeError:
                    votes = "1"

                for currentElement in cnElement:
                    if (currentElement.tag == "multicast"):
                        try:
                            multicastAddress = currentElement.attrib["addr"]
                            multicastInterface = currentElement.attrib["interface"]
                        except KeyError:
                            multicastAddress = ""
                            multicastInterface = ""
                        except AttributeError:
                            multicastAddress = ""
                            multicastInterface = ""
                message = "Found clusternode properties for: %s(%s)." %(clusternodeName, str(nodeID))
                logging.getLogger(sx.MAIN_LOGGER_NAME).debug(message)
                return ClusterNodeProperties(nodeName, nodeID, votes,
                                             multicastAddress, multicastInterface,
                                             cmanMulticastAddress, cnFenceDevicesList)
        return None

    def getClusterStorageFilesystemList(self):
        clusterStorageFilesystemList = []
        for cnResourceElement in self.__ccRootElement.findall("rm/resources/") :
            if (cnResourceElement.tag == "clusterfs"):
                name = ""
                device = ""
                mountPoint = ""
                fsType = ""
                mountOptions = ""
                fsid = ""
                try:
                    # These are required options
                    name = cnResourceElement.attrib["name"]
                    device = cnResourceElement.attrib["device"]
                    mountPoint = cnResourceElement.attrib["mountpoint"]
                    fsType = cnResourceElement.attrib["fstype"]
                    if (not ((fsType == "gfs") or (fsType == "gfs2"))):
                        continue
                except KeyError:
                    continue
                except AttributeError:
                    continue

                try:
                    mountOptions = cnResourceElement.attrib["options"]
                except KeyError:
                    pass
                except AttributeError:
                    pass
                try:
                    fsid= cnResourceElement.attrib["fsid"]
                except KeyError:
                    pass
                except AttributeError:
                    pass
                clusterStorageFilesystemList.append(ClusterConfMount(device, mountPoint, fsType, mountOptions, name, fsid))
        return clusterStorageFilesystemList

    # #######################################################################
    # Builds a view of the Resources and Services
    # #######################################################################
    def __getClusteredServiceResource(self, sharedResourcesList, resourceElement, level, order):
        try:
            name = resourceElement.attrib["ref"]
            for resource in sharedResourcesList:
                if (resource.getName() == name):
                    return ClusteredResourceInService(resource.getType(), resource.getName(), resource.isPrivate(), resource.getAttributesMap(), level, order)
        except KeyError:
            # This resource is not a reference but a private resource.
            resource = self.__getClusteredResource(resourceElement, True)
            if (not resource == None):
                return ClusteredResourceInService(resource.getType(), resource.getName(), resource.isPrivate(), resource.getAttributesMap(), level, order)
        return None

    def __getClusteredResource(self, resourceElement, isPrivate):
        resourceType = resourceElement.tag
        # This is a list of the attributes, with is a list of pairs. Where the
        # first item in list is attribute name and second item is attribute
        # value.
        # [('name', 'halvmVol1'), ('vg_name', 'VolGroupX'), ('lv_name', 'vol01')]
        attributesPairList = resourceElement.items()
        # Now will create a map of the attributes.
        attributesMap = {}
        for attributePair in attributesPairList:
            attributesMap[attributePair[0]] = attributePair[1]
        if (resourceType == "ip"):
            try:
                address = resourceElement.attrib["address"]
                return ClusteredResource(resourceType, address, False, attributesMap)
            except KeyError:
                return None
        else:
            try:
                name = resourceElement.attrib["name"]
                return ClusteredResource(resourceType, name, False, attributesMap)
            except KeyError:
                return None
        return None

    def __walkClusteredServiceResource(self, sharedResourcesList, resourceElement, level, order):
        clusteredResource = self.__getClusteredServiceResource(sharedResourcesList, resourceElement, level, order)
        if (not clusteredResource == None):
            level = level + 1
            order = 1
            for childResourceElement in resourceElement:
                childClusteredResource = self.__walkClusteredServiceResource(sharedResourcesList, childResourceElement, level, order)
                order = order + 1
                if (not childClusteredResource == None):
                    clusteredResource.addChildResource(childClusteredResource)
        return clusteredResource

    def __getFailoverDomain(self, failoverDomainsList, serviceElement):
        try:
            fdName = serviceElement.attrib["domain"]
            for fd in failoverDomainsList:
                if (fd.getName() == fdName):
                    return fd
        except KeyError:
            for fd in failoverDomainsList:
                    return fd
        return FailoverDomain("ERROR FINDING FAILOVERDOMAIN", 0, 0, {})

    def getFailoverDomains(self):
        failoverDomainsList = []
        # Add the default failover domain in, need to add in all the members
        clusternodeNames = self.getClusterNodeNames()
        defaultFailoverDomain = {}
        for clusternodeName in clusternodeNames:
            defaultFailoverDomain[clusternodeName] = "1"
        failoverDomainsList.append(FailoverDomain("Default Failover Domain", 0, 0, defaultFailoverDomain))
        for fdElement in self.__ccRootElement.findall("rm/failoverdomains/failoverdomain"):
            try:
                fdMembersMap = {}
                for childElement in fdElement:
                    try:
                        fdMembersMap[childElement.attrib["name"]] = childElement.attrib["priority"]
                    except KeyError:
                        pass
                    ordered = "0"
                    try:
                        ordered = fdElement.attrib["ordered"]
                    except KeyError:
                        pass
                    restricted = "0"
                    try:
                        ordered = fdElement.attrib["restricted"]
                    except KeyError:
                        pass
                failoverDomainsList.append(FailoverDomain(fdElement.attrib["name"],
                                                          ordered, restricted,
                                                          fdMembersMap))
            except KeyError:
                continue
        return failoverDomainsList

    def getSharedClusterResources(self):
        sharedResourceMap = {}
        for resourceElement in self.__ccRootElement.findall("rm/resources/"):
            clusteredResource = self.__getClusteredResource(resourceElement, False)
            if (not clusteredResource == None):
                key = "%s-%s" %(clusteredResource.getType(), clusteredResource.getName())
                if (not sharedResourceMap.has_key(key)):
                    sharedResourceMap[key] = clusteredResource
        return sharedResourceMap.values()

    def getClusteredServices(self) :
        failoverDomainsList = self.getFailoverDomains()
        sharedResourcesList = self.getSharedClusterResources()
        servicesMap={}
        for rmElement in self.__ccRootElement.findall("rm/"):
            if (rmElement.tag == "service"):
                try:
                    name = rmElement.attrib["name"]
                    # Get the Failover Domain for the service.
                    failoverDomain = self.__getFailoverDomain(failoverDomainsList, rmElement)
                    # Default recovery policy
                    recovery = "restart"
                    try:
                        recovery = rmElement.attrib["recovery"]
                    except KeyError:
                        pass
                    # Build the Service.
                    if (not servicesMap.has_key(name)):
                        level = 1
                        order = 1
                        listOfClusteredResourcesinService = []
                        for resourceElement in rmElement:
                            clusterResource = self.__walkClusteredServiceResource(sharedResourcesList,
                                                                                  resourceElement, level, order)
                            order = order + 1
                            if (not clusterResource == None):
                                listOfClusteredResourcesinService.append(clusterResource)
                        servicesMap[name] = ClusteredService(name, recovery,
                                                             failoverDomain, listOfClusteredResourcesinService)
                except KeyError:
                    continue
            elif (rmElement.tag == "vm"):
                name = rmElement.attrib["name"]
                # Get the Failover Domain for the service.
                failoverDomain = self.__getFailoverDomain(failoverDomainsList, rmElement)
                recovery = ""
                try:
                    recovery = rmElement.attrib["recovery"]
                except KeyError:
                    pass
                servicesMap[name] = ClusteredService(name, recovery, failoverDomain, [], True)
        return servicesMap.values()

    def getQuorumdSummary(self):
        quorumd = self.getQuorumd()
        if (not quorumd == None):
            return str(quorumd)
        else:
            return ""

