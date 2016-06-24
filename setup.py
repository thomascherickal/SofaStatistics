import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "sofastats",
    version = "1.5.0",
    author = "Grant Paton-Simpson",
    author_email = "grant@sofastatistics.com",
    description = ("Easy-to-use Statistics/Analysis/Reporting package"),
    license = "AGPL3",
    keywords = "statistics analysis reporting",
    url = "http://www.sofastatistics.com",
    packages=['sofastats', ],
    long_description=read('README'),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Scientific/Engineering :: Mathematics",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    ],
    include_package_data=True,
)

