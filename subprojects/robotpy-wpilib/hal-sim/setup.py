#!/usr/bin/env python3

from os.path import dirname, exists, join
import sys, subprocess
from setuptools import setup

setup_dir = dirname(__file__)
base_package = 'hal_impl'
version_file = join(setup_dir, base_package, 'version.py')

# Automatically generate a version.py based on the git version
if exists(join(setup_dir, '..', '.git')):
    p = subprocess.Popen(["git", "describe", "--tags", "--long"],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    # Make sure the git version has at least one tag
    if err:
        print("Error: You need to create a tag for this repo to use the builder")
        sys.exit(1)

    # Convert git version to PEP440 compliant version
    # - Older versions of pip choke on local identifiers, so we can't include the git commit
    v, commits, local = out.decode('utf-8').rstrip().split('-', 2)
    if commits != '0':
        v = '%s.post0.dev%s' % (v, commits)

    # Create the version.py file
    with open(join(setup_dir, base_package, 'version.py'), 'w') as fp:
        fp.write("# Autogenerated by setup.py\n__version__ = '{0}'".format(v))

if exists(version_file):
    with open(version_file, 'r') as fp:
        exec(fp.read(), globals())
else:
    __version__ = "master"

with open(join(setup_dir, 'README.rst'), 'r') as readme_file:
    long_description = readme_file.read()

setup(
    name='robotpy-hal-sim',
    version=__version__,
    description='WPILib HAL layer for simulations',
    long_description=long_description,
    author='Peter Johnson, Dustin Spicuzza',
    author_email='robotpy@googlegroups.com',
    url='https://github.com/robotpy/robotpy-wpilib',
    keywords='frc first robotics hal can',
    packages=['hal_impl'],
    install_requires='robotpy-hal-base==' + __version__, # is this a bad idea?
    license="BSD License",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.4",
        "Topic :: Scientific/Engineering"
    ]
    )
