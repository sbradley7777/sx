#!/usr/bin/env python
"""
This class contains object for data that is contains in the files
sos_commands/cluster in a sosreport.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.08
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




