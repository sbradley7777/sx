`sxconsole` is a tool used to extract various report types and then analyze those extracted reports with plugins. The tool also provides an archiving structure so that all the compressed and extracted reports are saved to a directory. This tool was developed for `sysreport`/`sosreports` but has been expanded to include any report that has a class defined.

`sxconsole` is the command-line interface to the `sx` library. The sx library contains the classes and functions to extract and then analyze the reports. The python script sxconsole takes a collection of "REPORTS" which are files and then will extract those reports to a unique directory. It will archive the compressed reports and the extracted reports. After the reports are extracted then all the enabled plugins will be ran against all the reports.

All the core files, reports, plugins are located in the python directory: `/usr/lib/python2.6/site-packages/sx/`.

The first time that sxconsole is ran a configuration directory will be created. A user can create their own "Report" types and "Plugins" and then place them in their user configuration directory located. Each directory needs to contain an empty file called `__init__.py` so that modules within can be loaded: `~/.sx/{sxreports, sxplugins}/`.

The python script sxconsole will extract different report types to an archived directory that the user specifies. The currently supported report types are:

- sosreport
- sysreport
- satellite-debug
- rhev log debugger

`sxconsole` can add non-report files to a archived ticket which means all the files can be kept in same location. After the reports are extracted, `sxconsole` can then run various plug-ins on those reports. For example the `clusterha` plugin does the following (against all the cluster nodes sosreports):

- Create a summary file that contains various information about cluster and nodes.
- Create a human readable report file about the clustered services and virtual machines.
- Create a report file that checks for configuration issues related to the cluster.
- Create a report file that compares various information in the sosreports against other sosreports.

#####What is the prerequisites for sx?
All these prereqs will be pulled in from your distro `yum` repo when installing the `sx` package. The package requires `python` >= 2.6.5.

#####How to install SX with the binary rpms?
Add later

##### How do you get the source code for this project?

$ mkdir ~/github; cd ~/github
$ git clone https://github.com/sbradley7777/sx.git
$ cd ~/github/sx
