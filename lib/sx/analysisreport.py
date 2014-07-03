#!/usr/bin/env python
"""
Classes used to create a container for analysis and summary output of the
plugins ran against the reports. The AR stands for Analysis Reports.

The ARSection will only be 1 deep ns AnalysisReport will contain a 1 deep list
of ARSections.

TODO:
* ARSectionItem: Need bullets that can be enabled.


@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""
class AR:
    """
    A parent class that contains the minimual attributes and functions needed
    for report, sections, and items.
    """
    def __init__(self, name, description):
        # The name is the unique id for this analysis report and description
        # contains text that will be printed.
        self.__name = name.strip().rstrip()
        self.__description = description.strip().rstrip()

        self.__container = []

    def getName(self):
        return self.__name

    def getDescription(self):
        return self.__description

    def setDecription(self, description):
        self.__description = description

    def list(self):
        return self.__container

    def add(self, object):
        foundDuplicate = False
        for item in self.list():
            if (item.getName() == object.getName()):
                foundDuplicate = False
        if (not foundDuplicate):
            self.__container.append(object)
            return True
        return False

class AnalysisReport(AR):
    """
    This class is a container for the analysis report for plugins to save the
    their output.
    """
    def __init__(self, name, description):
        AR.__init__(self, name, description)
        self.__sections = []

    def __str__(self):
        rstring = ""
        for section in self.list():
            if (len(rstring) > 0):
                rstring += "\n\n%s" %(str(section))
            else:
                rstring += "\n%s" %(str(section))
        return rstring

class ARSection(AR):
    """
    This class is a container for a group of items within the AnalysisReport.
    """
    def __init__(self, name, description, separator="-------------------------------------------------------------------------------------------------"):
        AR.__init__(self, name, description)
        # The name is the unique id for this section and description contains text that will be printed.
        self.__items = []
        self.__separator = separator

    def __str__(self):
        rstring = ""
        rstring += "%s\n%s\n%s" %(self.__separator, self.getDescription(), self.__separator)
        for item in self.list():
            rstring += "\n%s\n" %(item)
        rstring = rstring.strip().rstrip()
        return "%s" %(rstring)

class ARSectionItem(AR):
    """
    An item that goes into the section.
    """
    def __init__(self, name, description):
        AR.__init__(self, name, description)
        self.__name = name.strip().rstrip()
        self.__description = description.strip().rstrip()

    def __str__(self):
        rstring = ""
        rstring += "%s" %(self.getDescription())
        return rstring

class ARSectionItemWithUrls(ARSectionItem):
    def __init__(self, name, description, urls):
        ASectionItem.__init__(self, name, description)
        self.__urls = urls

    def __str__(self):
        rstring = ""
        rstring += "%s" %(self.getDescription())
        return rstring

    def getUrls(self):
        return self__urls

