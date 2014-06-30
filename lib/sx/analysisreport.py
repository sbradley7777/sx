#!/usr/bin/env python
"""
Classes used to create a container for analysis and summary output of the
plugins ran against the reports. The AR stands for Analysis Reports.

The ARSection will only be 1 deep ns AnalysisReport will contain a 1 deep list
of ARSections.


@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.17
@copyright :  GPLv2
"""
class AnalysisReport:
    """
    This class is a container for the analysis report for plugins to save the
    their output.
    """
    def __init__(self, name, description):
        # The name is the unique id for this analysis report and description contains text that will be printed.
        self.__name = name.strip().rstrip()
        self.__description = description.strip().rstrip()
        self.__sections = []

    def __str__(self):
        rstring = ""
        for section in self.getSections():
            if (len(rstring) > 0):
                rstring += "\n\n%s" %(str(section))
            else:
                rstring += "\n%s" %(str(section))
        return rstring

    def getName(self):
        return self.__name

    def getDescription(self):
        return self.__description

    def getSections(self):
        return self.__sections

    def addSection(self, section):
        self.__sections.append(section)

class ARSection:
    """
    This class is a container for a group of items within the AnalysisReport.
    """
    def __init__(self, name, description, separator="-------------------------------------------------------------------------------------------------"):
        # The name is the unique id for this section and description contains text that will be printed.
        self.__name = name.strip().rstrip()
        self.__description = description.strip().rstrip()
        self.__items = []
        self.__separator = separator

    def __str__(self):
        rstring = ""
        rstring += "%s\n%s\n%s" %(self.__separator, self.getDescription(), self.__separator)
        for item in self.getItems():
            rstring += "\n%s\n" %(item)
        rstring = rstring.strip().rstrip()
        return "%s" %(rstring)

    def getName(self):
        return self.__name

    def getDescription(self):
        return self.__description

    def getItems(self):
        return self.__items

    def addItem(self, sectionItem):
        self.__items.append(sectionItem)

class ARSectionItem:
    def __init__(self, name, description):
        # The name is the unique id for this item and description contains text that will be printed.
        # TODO: Need bullets that can be enabled.
        self.__name = name.strip().rstrip()
        self.__description = description.strip().rstrip()

    def __str__(self):
        rstring = ""
        rstring += "%s" %(self.getDescription())
        return rstring

    def getName(self):
        return self.__name

    def getDescription(self):
        return self.__description

    def setDecription(self, description):
        self.__description = description

class ARSectionItemWithUrls(ARSectionItem):
    def __init__(self, name, description, urls):
        ARSubSectionItem.__init__(self, name, description)
        self.__urls = urls

    def __str__(self):
        rstring = ""
        rstring += "%s" %(self.getDescription())
        return rstring

    def getUrls(self):
        return self__urls

