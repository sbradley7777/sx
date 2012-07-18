#!/usr/bin/env python
"""
This class contains object for data that is contains in the files
sos_commands/cluster in a sosreport.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.11
@copyright :  GPLv2
"""
import re

class ClusterCommandsParser:
    def parseCmanToolStatusData(dataList):
        """
        Each line in the array will be a pair and look like this
        below: <label>: <value>.  For example:
        Cluster Name: rh5cluster
        """
        # This map contains the labels for each line in the
        # datalist. Might need to have value as an array if there is
        # different versions of line.
        cmanToolStatusLabelMap = { "version":"Version", "configVersion": "Config Version", "clusterName":"Cluster Name",
                                   "clusterID":"Cluster Id", "clusterMember":"Cluster Member", "clusterGeneration": "Cluster Generation",
                                   "membershipState":"Membership state", "nodes":"Nodes", "expectedVotes":"Expected votes",
                                   "totalVotes":"Total votes", "quorum":"Quorum", "activeSubsystems":"Active subsystems",
                                   "flags":"Flags", "portsBound":"Ports Bound", "nodeName":"Node name",
                                   "nodeID":"Node ID", "heartbeatAddresses":"Multicast addresses", "nodeAddresses":"Node addresses"}

        # This map is the values that are contained for each key in the datalist.
        cmanToolStatusValuesMap = {}

        # Find the regex for line and add to cmanToolStatusValuesMap
        # if match is found.
        regexStanza = "(?P<label>^.*):(?P<value>.*$)"
        remStanza = re.compile(regexStanza)
        for line in dataList:
            mo = remStanza.match(line)
            if mo:
                label = mo.group("label").strip()
                value = mo.group("value").strip()
                for key in cmanToolStatusLabelMap.keys():
                    if (cmanToolStatusLabelMap.get(key) == label):
                        cmanToolStatusValuesMap[key] = value

        if (len(cmanToolStatusLabelMap.keys()) == len(cmanToolStatusValuesMap)):
            return CmanToolStatusCommand(cmanToolStatusValuesMap.get("version"), cmanToolStatusValuesMap.get("configVersion"),
                                         cmanToolStatusValuesMap.get("clusterName"), cmanToolStatusValuesMap.get("clusterID"),
                                         cmanToolStatusValuesMap.get("clusterMember"), cmanToolStatusValuesMap.get("clusterGeneration"),
                                         cmanToolStatusValuesMap.get("membershipState"), cmanToolStatusValuesMap.get("nodes"),
                                         cmanToolStatusValuesMap.get("expectedVotes"), cmanToolStatusValuesMap.get("totalVotes"),
                                         cmanToolStatusValuesMap.get("quorum"), cmanToolStatusValuesMap.get("activeSubsystems"),
                                         cmanToolStatusValuesMap.get("flags"), cmanToolStatusValuesMap.get("portsBound"),
                                         cmanToolStatusValuesMap.get("nodeName"), cmanToolStatusValuesMap.get("nodeID"),
                                         cmanToolStatusValuesMap.get("heartbeatAddresses"), cmanToolStatusValuesMap.get("nodeAddresses"))
        else:
            return None
    parseCmanToolStatusData = staticmethod(parseCmanToolStatusData)

    def parseClustatData(dataList):
        memberIDMap = {}
        memberStatusMap = {}
        serviceOwnerMap = {}
        serviceStateMap = {}

        serviceStart = False

        # if not re.match('^[a-zA-Z]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$', hostname)
        # From clustat.c
        # member name: some string with no spaces
        # ID: id > -1
        # State Possible Values: Online Offline Local Estranged RG-Master rgmanager Quorum Disk
        regexMemberStanza = "(?P<memberName>.*).*(?P<id>[0-9]?[0-9]).*(?P<status>(Online|Offline)(, Local|, Estranged|, RG-Master|, rgmanager|, Quorum Disk).*)"
        remMemberStanza = re.compile(regexMemberStanza)
        # clulib/rg_strings.c
        # owners: list of owners found
        # State Possible Values: stopped starting started stopping failed uninitialized checking recoverable recovering disabled migrating
        regexServiceStanza = ""
        for line in dataList:
            line = line.strip().rstrip()
            mo = remMemberStanza.match(line)
            if mo:
                memberName = mo.group("memberName").strip().rstrip()
                memberIDMap[memberName] = mo.group("id").strip().rstrip()
                memberStatusMap[memberName] = mo.group("status").strip().rstrip()
            elif (line.startswith("Service Name")):
                members = memberIDMap.keys()
                membersString = ""
                for member in members:
                    if (not member.startswith("/")):
                        membersString += "%s|" %(member)
                membersString = membersString.rstrip("|")
                regexServiceStanza = "^(service|vm):(?P<serviceName>.*)(?P<owner>%s).*(?P<state>stopped|starting|started|stopping|failed|uninitialized|checking|recoverable|recovering|disabled|migrating)" %(membersString)
            elif (len(regexServiceStanza) > 0):
                remServiceStanza = re.compile(regexServiceStanza)
                mo = remServiceStanza.match(line)
                if mo:
                    serviceName = mo.group("serviceName").strip().rstrip()
                    serviceOwnerMap[mo.group("serviceName").strip().rstrip()] = mo.group("owner").strip().rstrip()
                    serviceStateMap[mo.group("serviceName").strip().rstrip()] = mo.group("state").strip().rstrip()
        # If no values found then object will be basically empty.
        return ClustatCommand(memberIDMap, memberStatusMap, serviceOwnerMap, serviceStateMap)
    parseClustatData = staticmethod(parseClustatData)

class ClustatCommand:
    def __init__(self, memberIDMap, memberStatusMap, serviceOwnerMap, serviceStateMap):
        # These two maps will have same keys.
        self.__memberIDMap = memberIDMap
        self.__memberStatusMap = memberStatusMap
        # These two maps will have same keys.
        self.__serviceOwnerMap = serviceOwnerMap
        self.__serviceStateMap = serviceStateMap

    def getMembers(self):
        return self.__memberIDMap.keys()

    def getServices(self):
        return self.__serviceOwnerMap.keys()

    def getMemberID(self, memberName):
        if (self.__memberIDMap.has_key(memberName)):
            return self.__memberIDMap.get(memberName)
        return ""

    def getMemberStatus(self, memberName):
        # Need a isOffline isOnline function
        if (self.__memberStatusMap.has_key(memberName)):
            return self.__memberStatusMap.get(memberName)
        return ""

    def isOwnerQuorumDisk(self, memberName):
        memberStatus = self.getMemberStatus(memberName)
        return (memberStatus.find("Quorum Disk") > 0)

    def findQuorumDisk(self):
        for member in self.__memberStatusMap.keys():
            if (self.isOwnerQuorumDisk(member)):
                return member
        return ""

    def getServiceOwner(self, serviceName):
        # Need to grep out last owner and no owner
        if (self.__serviceOwnerMap.has_key(serviceName)):
            return self.__serviceOwnerMap.get(serviceName)
        return ""

    def getServiceLastOwner(self, serviceName):
        # Need to grep out owner and no owner
        if (self.__serviceOwnerMap.has_key(serviceName)):
            return self.__serviceOwnerMap.get(serviceName)
        return ""

    def getServiceState(self, serviceName):
        if (self.__serviceStateMap.has_key(serviceName)):
            return self.__serviceStateMap.get(serviceName)
        return ""


class CmanToolStatusCommand:
    def __init__(self, version, configVersion, clusterName,
                 clusterID, clusterMember, clusterGeneration,
                 membershipState, nodes, expectedVotes,
                 totalVotes, quorum, activeSubsystems, flags,
                 portsBound, nodeName, nodeID,
                 heartbeatAddresses, nodeAddresses):

        self.__version = version
        self.__configVersion = configVersion
        self.__clusterName = clusterName
        self.__clusterID = clusterID
        if (clusterMember.lower() == "yes"):
            self.__clusterMember = True
        else:
            self.__clusterMember = False
        self.__clusterGeneration = clusterGeneration
        self.__membershipState = membershipState
        self.__nodes = nodes
        self.__expectedVotes = expectedVotes
        self.__totalVotes = totalVotes
        self.__quorum = quorum
        self.__activeSubsystems = activeSubsystems
        self.__flags = flags
        self.__portsBound = portsBound
        self.__nodeName = nodeName
        self.__nodeID = nodeID
        self.__heartbeatAddresses = heartbeatAddresses.split()
        self.__nodeAddresses = nodeAddresses.split()

    def isMulicastHeartbeat(self):
        """
        Use the ip address of heartbeat to find out
        """
        return False

    def isBroadcastHeartbeat(self):
        """
        Use the ip address of heartbeat to find out
        """
        return False

    def getVersion(self):
        return self.__version

    def getConfigVersion(self):
        return self.__configVersion

    def getClusterName(self):
        return self.__clusterName

    def getClusterID(self):
        return self.__clusterID

    def isClusterMember(self):
        return self.__clusterMember

    def getClusterGeneration(self):
        return self.__clusterGeneration

    def getMembershipState(self):
        return self.__membershipState

    def getNodes(self):
        return self.__nodes

    def getExpectedVotes(self):
        return self.__expectedVotes

    def getTotalVotes(self):
        return self.__totalVotes

    def getQuorum(self):
        return self.__quorum

    def getActiveSubsystems(self):
        return self.__activeSubsystems

    def getFlags(self):
        return self.__flags

    def getPortsBound(self):
        return self.__portsBound

    def getNodeName(self):
        return self.__nodeName

    def getHeartbeatAddresses(self):
        return self.__heartbeatAddresses

    def getNodeAddresses(self):
        return self.__nodeAddresses
