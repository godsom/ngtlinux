#!/usr/bin/env python
#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: saurabh.wagh@nutanix.com (Saurabh Wagh)
#
# This method provides an implementation of the Linux installer for the SUSE
# distributions.
#

import os
import platform

from distutils.version import LooseVersion

from installer_utils import *
from base_installer import *

class SuseInstaller(LinuxInstaller):
  """
  Implementation of the Linux installer for SUSE distributions
  """
  SUSE_MIN_VERSION = "11"

  def do_validate(self):
    """
    This function ensures that pre-conditions required for a successful execution
    of this script on SUSE distributions are satisfied.
    """
    if not super(SuseInstaller, self).do_validate():
      return False

    version = platform.linux_distribution()[1]

    if LooseVersion(version) < LooseVersion(self.SUSE_MIN_VERSION):
      logging.error("Version %s is not supported. MinVersion %s." \
        %(version, self.SUSE_MIN_VERSION))
      return False

    return True

  def install_ngt_daemon(self):
    """
    This function installs the NGT Guest Agent as an init.d daemon.
    """
    super(SuseInstaller, self).install_ngt_daemon()

    # Add the daemon as a chkconfig service.
    try:
      run_shell_command(["/sbin/chkconfig", "--add", self.NGT_DAEMON_NAME])
    except:
      logging.error("Failed to add Nutanix Guest Agent Service to the " \
        "service configuration.")
      raise

    # Set daemon to autostart on boot.
    try:
      run_shell_command(["/sbin/chkconfig", self.NGT_DAEMON_NAME, "on"])
    except:
      logging.error("Failed to set Nutanix Guest Agent Service property " \
        "autostart on boot.")
      raise

    logging.info("Successfully installed Nutanix Guest Agent Service.")

  def uninstall_ngt_daemon(self):
    """
    This function stops the NGT Guest Agent daemon and removes it.
    """
    # Only attempt uninstall if the daemon was installed.
    if not os.path.exists(self.NGT_DST_DAEMON_PATH):
      return

    # Stop the daemon if currently running.
    try:
      run_shell_command([self.NGT_DST_DAEMON_PATH, "stop"])
    except:
      pass

    # Turn the autostart on boot to off.
    try:
      run_shell_command(["/sbin/chkconfig", self.NGT_DAEMON_NAME, "off"])
    except:
      pass

    # Remove the daemon from the chkconfig services list.
    try:
      run_shell_command(["/sbin/chkconfig", "--del", self.NGT_DAEMON_NAME])
    except:
      pass

    # Remove the daemon configuration from the init.d folder.
    os.remove(self.NGT_DST_DAEMON_PATH)

  def setup_mobility_drivers(self):
    """
    This function loads the VirtIO and mptsas drivers into the initramfs file
    for the current OS kernel.
    """
    logging.warning("Migration to AHV currently not supported for SUSE Guests.")
    logging.warning("Skipping installation of mobility drivers.")
