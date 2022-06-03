sxconsole is a tool used to extract various report types and then
analyze those extracted reports with plugins. The tool also provides
an archiving structure so that all the compressed and extracted
reports are saved to a directory. This tool was developed for
sysreport/sosreports but has been expaned to include any report that
has a class defined.

sxconsole is the commadline interface to the "sx" library. The "sx"
library contains the classes and functions to extract and then analyze
the reports. The tool sxconsole takes a collection of "REPORTS" which
are files and then will extract those reports to a unique
directory. It will archive the compressed reports and the extracted
reports. After the reports are extracted then all the enabled plugins
will be ran against all the reports.

All the core files, reports, plugins are located in the python
directory: /usr/lib/python2.6/site-packages/sx/

The first time that sxconsole is ran a configuration directory will be
created. A user can create their own "Report" types and "Plugins" and
then place them in their user configuration directory located. Each
directory needs to contain an empty file called __init__.py so that
modules within can be loaded:
  ~/.sx/sxreports/
  ~/.sx/sxplugins/

Example:
  There are 3 sosreports that are created. Each report is from a
  different clusternode which will be analyzed by the cluster plugin
  and checksysreport plugin. After the reports are extracted then
  sxconsole will run the cluster plugin which will analyze them from a
  cluster perspective(analyze all reports as a single collection) and
  then analyze each report from the node. The reports will also have
  the checksysreport plugin gather information about those reports as
  well.

---------------------------------------------------------------------------------
What are REPORTS?
---------------------------------------------------------------------------------
The "Report" class defines how to extract the files with the
compressed report file such as sosreport/sysreport file. The class
defines how to validate if it is a known report and what kind of
report the file is.

The default "Report" types are located in the default python directory:
/usr/lib/python2.6/site-packages/sx/reports/

The currently supported report types are:
  * sosreport
  * sysreport
  * satellite-debug

---------------------------------------------------------------------------------
What are PLUGINS?
---------------------------------------------------------------------------------
The "Plugins" class defines how to gather the files needed to then
analyze/report on information contained in the collection of reports.

The default "Plugins" are located in the default python directory:
/usr/lib/python2.6/site-packages/sx/plugins/

The currenlty supported plugins are:
  * checksysreport
  * cluster
  * opensosreport
  * satellitedebug
  * yakuake

To get a better description of what each REPORT/PLUGINS does then run:
$ sxconsole -l

---------------------------------------------------------------------------------
How do you write a custom REPORT class?
---------------------------------------------------------------------------------
All custom written report classes will go into the directory:
  ~/.sx/sxreports/

They will be loaded up automatically if not disabled with -U
options. Report types cannot be disabled unlike plugins which can be
enabled/disabled.

A Report class needs to inherit the "Report" class then pass the
required args to the parent class.

Each Report class needs to define the following:
  * TYPE_DETECTION_FILE (Global Variable in the class)
  * extract()

The global variable are used to identify the Report class which is a
unique file in the report.

The extract() function is what is used to extract the report. Most of
the work of the extraction can be passed to the parent class. The main
purpose of this function is for you to define how your extraction
should be handled. For instance what should the name of the root
extraction folder should be or if we should skip a few directories
down in the compressed report.

The sysreport/sosreport is good example of how this works.

Do note that there is no mechanism for checking for duplicate types of
reports. When a file is scanned to see it is a known report type then
the first one wins.

---------------------------------------------------------------------------------
Do you have an example of a REPORT class?
---------------------------------------------------------------------------------
The demoreport.py example is a good place to start. It is a working example
report:
This command will create configuration directory.
$ sxconsole -l

This command will copy the file to the user configuration directory.
$ cp /usr/share/doc/sx*/examples/demoreport.py ~/.sx/sxreports/demoreport.py

---------------------------------------------------------------------------------
How do you write a custom PLUGIN class?
---------------------------------------------------------------------------------
All custom written plugin classes will go into the directory:
  ~/.sx/sxplugins/

They will be loaded up automatically if not disabled with -U options
and are enabled.

The plugin needs to inherit "PluginBase" class then in the __init__
pass the required args that are required to the parent class.

The new plugin class then will need to override any functions that
this plugin will perform and these functions are called in the below
order. If the plugin does not define that function then it will be
skipped since the parent just calls "pass."
  * setup()
  * execute()
  * report()
  * action()

The setup() will extract all the data and filepaths that are needed
for the plugin to function.

The execute() function is for intenstive task that is used to gather
data for the reporting. For example running checksysreport against the
report directory.

The report() function is where the report is generated and either
written to a file or to console.

The action() function is performing an action outside of the plugin
such as opening a directory with file viewer.

---------------------------------------------------------------------------------
Do you have an example of a PLUGIN class?
---------------------------------------------------------------------------------
The demo.py example is a good place to start. It is a working example
plugin that prints information to console and writes to a file. This
plugin has been well documented and should work against
sosreports/sysreports.

This command will create configuration directory.
$ sxconsole -l

This command will copy the file to the user configuration directory.
$ cp /usr/share/doc/sx*/examples/demo.py ~/.sx/sxplugins/demo.py
