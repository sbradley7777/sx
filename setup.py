#!/usr/bin/python
from distutils.core import setup

# Additional Files in MANIFEST.in
# include LICENSE
# include AUTHORS
# include PKG-INFO
# include doc/README.txt
# include doc/examples/demo.py
# include doc/examples/demoreport.py
# include doc/examples/konsole.py

################################################################################
if __name__ == "__main__":
    setup(
        name="sx" ,
        version="2.09",
        author="Shane Bradley",
        author_email="sbradley@redhat.com",
        url="https://fedorahosted.org/sx",
        description="Tool to extract reports and run plug-ins against those extracted reports.",
        license="GPLv2",
        packages=["sx", "sx.plugins", "sx.plugins.lib",  "sx.reports", "sx.extractors",
                  "sx.plugins.lib.clusterha", "sx.plugins.lib.storage", "sx.plugins.lib.log",
                  "sx.plugins.lib.kernel", "sx.plugins.lib.networking", "sx.plugins.lib.general",
                  "sx.plugins.lib.rpm"],
        scripts=["sxconsole"],
        package_dir={"":"lib",}
    )
################################################################################

