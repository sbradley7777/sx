#!/usr/bin/env python
"""
This class will evalatuate a cluster and create a report that will
link in known issues with links to resolution.

This plugin is documented here:
- https://fedorahosted.org/sx/wiki/SX_clusterplugin

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.15
@copyright :  GPLv2
"""
from copy import deepcopy
import operator

from sx.plugins.lib.clusterha.clusternode import ClusterNode
from sx.tools import StringUtil

class CompareData:
    def __init__(self, title, description):
        self.__title = title
        self.__description = description
        # The key is a string that will be some value that is found in
        # the report. The value of key will be the name of the report.

        # The key with least number of items will be considered the
        # key that is incorrect or we shall say it will be the one
        # outside the norm cause who is stay which is correct.
        self.__compareMap = {}

    def __str__(self):
        return "%s: %s"%(self.__title, self.__description)

    def getTitle(self):
        return self.__title

    def getDescription(self):
        return self.__description

    def getCompareMap(self):
        return self.__compareMap

    def isIdentical(self):
        # If all the reports had the same size then the size of the
        # map should be 1. Else there was no reports compared or there
        # was a mismatch so multiple keys created.
        return (len(self.__compareMap.keys()) == 1)

    def __getCompareValueCountTuples(self, compareMap):
        # Get the items that are not equal to the majority of
        # items. There could be instances where there is multiple keys
        # with same value count that is the highest and there is no
        # way to tell which is diff so none of those returned.
        compareValueCountMap = {}
        for key in compareMap.keys():
            compareValueCountMap[key] = len(compareMap.get(key))
        sortedTuples = sorted(compareValueCountMap.iteritems(), key=operator.itemgetter(1))
        return sortedTuples

    def getNonBaseCompareMap(self):
        # Get a map with least number of reports.
        compareValueCountTuples = self.__getCompareValueCountTuples(self.__compareMap)
        compareValueCountTuples.reverse()
        rMap = {}
        if (len(compareValueCountTuples) > 0):
            maxCountValue = compareValueCountTuples[0][1]
            for cTuple in compareValueCountTuples:
                currentCountKey = cTuple[0]
                currentCountValue = cTuple[1]
                if (currentCountValue < maxCountValue):
                    valueCopy = deepcopy(self.__compareMap.get(currentCountKey))
                    if (rMap.has_key(currentCountKey)):
                        rMap[currentCountKey].append(valueCopy)
                    else:
                        rMap[currentCountKey] = valueCopy
        return rMap

    def getBaseCompareMap(self):
        # Get a map with most number of reports.
        compareValueCountTuples = self.__getCompareValueCountTuples(self.__compareMap)
        compareValueCountTuples.reverse()
        rMap = {}
        maxCountValue = compareValueCountTuples[0][1]
        for cTuple in compareValueCountTuples:
            currentCountKey = cTuple[0]
            currentCountValue = cTuple[1]
            if (currentCountValue >= maxCountValue):
                valueCopy = deepcopy(self.__compareMap.get(currentCountKey))
                if (rMap.has_key(currentCountKey)):
                    rMap[currentCountKey].append(valueCopy)
                else:
                    rMap[currentCountKey] = valueCopy
            # I could break if the if is false, but we let it cycle
            # through cause should be quick loop.
        return rMap

    def add(self, compareString, reportName):
        if ((len(compareString) > 0) and (len(reportName) > 0)):
            if (self.__compareMap.has_key(compareString)):
                self.__compareMap[compareString].append(reportName)
            else:
                self.__compareMap[compareString] = [reportName]

class ComparePackages:
    def __init__(self, title, description):
        self.__title = title
        self.__description = description
        # The key is a string that will be some value that is found in
        # the report. The value of key will be the name of the report.

        # The key with least number of items will be considered the
        # key that is incorrect or we shall say it will be the one
        # outside the norm cause who is stay which is correct.
        self.__compareMap = {}

        # list of all the reportNames added.
        self.__listOfReportNames = []

    def __str__(self):
        return "%s: %s"%(self.__title, self.__description)

    def getTitle(self):
        return self.__title

    def getDescription(self):
        return self.__description

    def getCompareMap(self):
        return self.__compareMap

    def __getCompareValueCountTuples(self, compareMap):
        # Get the items that are not equal to the majority of
        # items. There could be instances where there is multiple keys
        # with same value count that is the highest and there is no
        # way to tell which is diff so none of those returned.
        compareValueCountMap = {}
        for key in compareMap.keys():
            compareValueCountMap[key] = len(compareMap.get(key))
        sortedTuples = sorted(compareValueCountMap.iteritems(), key=operator.itemgetter(1))
        return sortedTuples

    def isIdentical(self):
        numberOfReports = len(self.__listOfReportNames)
        for packageName in self.__compareMap.keys():
            packageMap = self.__compareMap.get(packageName)
            if (len(packageMap.keys()) == 1):
                if (not len(packageMap.items()[0][1]) == numberOfReports):
                    # If there is only 1 package version found and if
                    # all the reports are not listed here then one of
                    # the reports does not have package installed.
                    return False
            else:
                # There was another version of a package installed.
                return False
        return True

    def getMissingPackagesMap(self):
        compareMap = {}
        for packageName in self.__compareMap.keys():
            packageMap = self.__compareMap.get(packageName)
            currentReports = []
            for key in packageMap.keys():
                currentReports += packageMap.get(key)
            diffList = list(set(self.__listOfReportNames).difference(set(currentReports)))
            if (len(diffList) > 0):
                compareMap[packageName] = diffList
        return compareMap

    def getDiffernetPackagesVersionMap(self):
        compareMap = {}
        for packageName in self.__compareMap.keys():
            packageMap = self.__compareMap.get(packageName)
            currentReports = []
            compareValueCountTuples = self.__getCompareValueCountTuples(packageMap)
            compareValueCountTuples.reverse()
            maxCountValue = compareValueCountTuples[0][1]
            for cTuple in compareValueCountTuples:
                currentCountKey = cTuple[0]
                currentCountValue = cTuple[1]
                if (currentCountValue < maxCountValue):
                    valueCopy = deepcopy(packageMap.get(currentCountKey))
                    if (compareMap.has_key(currentCountKey)):
                        compareMap[currentCountKey].append(valueCopy)
                    else:
                        compareMap[currentCountKey] = valueCopy
        return compareMap

    def add(self, installedRPMSMap, reportName):
        # Example:
        # openais -> {'openais-0.80.6-28.el5.x86_64': ['rh5node1.examplerh.com', 'rh5node2.examplerh.com', 'rh5node3.examplerh.com']}
        if ((len(installedRPMSMap.keys()) > 0) and (len(reportName) > 0) and
            (not reportName in self.__listOfReportNames)):
            # Add the report name in so no duplicates and keep track
            # of the number of package lists we are comparing.
            self.__listOfReportNames.append(reportName)
            for packageName in installedRPMSMap.keys():
                fullPackageName = installedRPMSMap.get(packageName)[0]
                if (not self.__compareMap.has_key(packageName)):
                    self.__compareMap[packageName] = {}
                packageMap = self.__compareMap.get(packageName)
                if (packageMap.has_key(fullPackageName)):
                    packageMap.get(fullPackageName).append(reportName)
                else:
                    packageMap[fullPackageName] = [reportName]

class ClusternodeCompare():
    def __init__(self, cnc):
        self.__cnc = cnc
        # Seperator between sections:
        self.__seperator = "-------------------------------------------------------------------------------------------------"

    def getClusterNodes(self):
        return self.__cnc

    # #######################################################################
    # Evaluate Function
    # #######################################################################
    def __compareDataToString(self, compareData):
        stringUtil = StringUtil()
        rString = ""
        nonBaseCompareMap = compareData.getNonBaseCompareMap()
        if (not len(nonBaseCompareMap.keys()) > 0):
            return rString
        description = "The following hosts had similar compared values:"
        baseCompareMap = compareData.getBaseCompareMap()
        keys = baseCompareMap.keys()
        keys.sort()
        compareTable = []
        for key in keys:
            reportNames = baseCompareMap.get(key)
            reportNames.sort()
            currentHostnames = ""
            for reportName in reportNames:
                currentHostnames += "%s " %(reportName)
            compareTable.append([key, currentHostnames])
        tableHeader = ["Compared String", "Hostname(s)"]
        tableOfStrings = stringUtil.toTableStringsList(compareTable, tableHeader)
        rString += StringUtil.formatBulletString(description, [], tableOfStrings)

        description = "The following hosts had different compared values than the above compared values:"
        keys = nonBaseCompareMap.keys()
        keys.sort()
        compareTable = []
        for key in keys:
            reportNames = nonBaseCompareMap.get(key)
            reportNames.sort()
            currentHostnames = ""
            for reportName in reportNames:
                currentHostnames += "%s " %(reportName)
            compareTable.append([key, currentHostnames])
        tableHeader = ["Compared String", "Hostname(s)"]
        tableOfStrings = stringUtil.toTableStringsList(compareTable, tableHeader)
        rString += StringUtil.formatBulletString(description, [], tableOfStrings)

        if (len(rString) > 0):
            rString = "%s\n%s" %(compareData, rString)
        return rString

    def __comparePackagesToString(self, comparePackages):
        stringUtil = StringUtil()
        rString = ""
        missingPackagesMap = comparePackages.getMissingPackagesMap()
        if (len(missingPackagesMap.keys()) > 0):
            description = "The following hosts did not have certain cluster packages installed(whereas other hosts did have the packages installed):"
            keys = missingPackagesMap.keys()
            keys.sort()
            missingPackagesTable = []
            for key in keys:
                reportNames = missingPackagesMap.get(key)
                reportNames.sort()
                if (len(reportNames) > 0):
                    currentHostnames = ""
                    for reportName in reportNames:
                        currentHostnames += "%s " %(reportName)
                    missingPackagesTable.append([key, currentHostnames])
            tableHeader = ["Package Name", "Hostname(s)"]
            tableOfStrings = stringUtil.toTableStringsList(missingPackagesTable, tableHeader)
            rString += StringUtil.formatBulletString(description, [], tableOfStrings)

        differentPackagesVersionMap = comparePackages.getDiffernetPackagesVersionMap()
        if (len(differentPackagesVersionMap.keys()) > 0):
            description = "The following hosts had a different package version installed:"
            keys = differentPackagesVersionMap.keys()
            keys.sort()
            differentPackageVersionsTable = []
            for key in keys:
                reportNames = differentPackagesVersionMap.get(key)
                reportNames.sort()
                if (len(reportNames) > 0):
                    currentHostnames = ""
                    for reportName in reportNames:
                        currentHostnames += "%s " %(reportName)
                    differentPackageVersionsTable.append([key, currentHostnames])
            tableHeader = ["Package Name", "Hostname(s)"]
            tableOfStrings = stringUtil.toTableStringsList(differentPackageVersionsTable, tableHeader)
            rString += StringUtil.formatBulletString(description, [], tableOfStrings)
        if (len(rString) > 0):
            rString = "%s\n%s" %(comparePackages, rString)
        return rString

    def compare(self):
        rString = ""
        clusternodeCount = self.__cnc.count()
        if (not clusternodeCount > 1):
            return rString
        # Compare various aspects of the all clusternodes.
        compareKernelVersion = CompareData("Compare Kernel Version", "Compares the kernel version from the uname output.")
        compareArchVersion = CompareData("Compare Kernel Arch Version", "Compares the kernel arch version from the uname output.")
        compareDistroReleaseVersion = CompareData("Compare Red Hat Release", "Compares the Red Hat release file.")
        comparePackagesVersion = ComparePackages("Compare Cluster Packages Installed", "Compares the cluster packages installed.")
        for clusternode in self.__cnc.getClusterNodes():
            unameA = clusternode.getUnameA()
            compareKernelVersion.add(str(unameA), clusternode.getClusterNodeName())
            compareArchVersion.add(unameA.getProcessorType(), clusternode.getClusterNodeName())
            compareDistroReleaseVersion.add(str(clusternode.getDistroRelease()), clusternode.getClusterNodeName())
            comparePackagesVersion.add(clusternode.getClusterPackagesVersion(), clusternode.getClusterNodeName())
        if (not compareKernelVersion.isIdentical()):
            rString += "%s" %(self.__compareDataToString(compareKernelVersion))
        if (not compareArchVersion.isIdentical()):
            rString += "%s" %(self.__compareDataToString(compareArchVersion))
        if (not compareDistroReleaseVersion.isIdentical()):
            rString += "%s" %(self.__compareDataToString(compareDistroReleaseVersion))
        if (not comparePackagesVersion.isIdentical()):
            rString += "%s" %(self.__comparePackagesToString(comparePackagesVersion))
        return rString
