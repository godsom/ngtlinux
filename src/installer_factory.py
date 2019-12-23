#!/usr/bin/env python
#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: saurabh.wagh@nutanix.com
#
# This file provides factory methods that return objects for platform
# dependant implementations of several classes.
#

import logging
import platform
import sys

from installer_utils import *

def get_linux_installer():
  """
  Get implementation of the NGT linux installer for the current Linux
  distribution.
  """

  os_type = platform.system().lower()
  if os_type != 'linux':
    logging.error("Unsupported platform : " + os_type)
    exit_installer(1)
    return

  distribution = platform.linux_distribution()[0].lower()
  if ("centos" in distribution or
      "oracle linux server" in distribution or
      "red hat" in distribution):
    # CentOS and Oracle Linux derive from the Red Hat Enterprise Linux
    # and hence the same installer works for them. For Oracle Linux, the
    # distribution string may the same as that for Red Hat in some cases.
    from redhat_installer import RedhatInstaller as LinuxInstaller

  elif "ubuntu" in distribution:
    from ubuntu_installer import UbuntuInstaller as LinuxInstaller

  elif "suse" in distribution:
    from suse_installer import SuseInstaller as LinuxInstaller

  else:
    logging.error("Unsupported distribution : " + distribution)
    exit_installer(1)
    return

  logging.info("Using Linux Installer for " + distribution +\
    " linux distribution.")
  return LinuxInstaller()
