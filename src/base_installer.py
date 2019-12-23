#!/usr/bin/env python
#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: saurabh.wagh@nutanix.com (Saurabh Wagh)
#
# This method provides a basic implementation of the Linux installer.
# Implementations for specific distributions may override this in favor of
# distribution specific implementation.
#

import json
import logging
import os
import pwd
import shutil
import stat
import tarfile

from abc import ABCMeta, abstractmethod
from distutils.version import LooseVersion
from installer_utils import *

class LinuxInstaller(object):
  """
  This class provides basic implementation for Linux installer functionality.
  """
  __metaclass__ = ABCMeta

  # Component names
  NGT_PACKAGE_NAME = "ngt_guest_agent.tar.gz"
  NGT_DAEMON_NAME = "ngt_guest_agent"
  NGT_UNINSTALL_SCRIPT_NAME = "uninstall_ngt.py"
  NGT_MARKER_NAME = "ngt_marker"
  NGT_LICENCE_FILE = "License.txt"

  # Derive the source paths from the location of the installer script.
  NGT_SRC_SOURCE = os.path.dirname(os.path.realpath(__file__))
  NGT_SRC_LINUX = os.path.dirname(NGT_SRC_SOURCE)
  NGT_SRC_INSTALLER = os.path.dirname(NGT_SRC_LINUX)
  NGT_SRC_ROOT = os.path.dirname(NGT_SRC_INSTALLER)
  NGT_SRC_CONFIG = NGT_SRC_ROOT + "/config"
  NGT_SRC_PACKAGE_PATH = NGT_SRC_SOURCE + "/" + NGT_PACKAGE_NAME
  NGT_SRC_DAEMON_PATH = NGT_SRC_SOURCE + "/" + NGT_DAEMON_NAME
  NGT_SRC_UNINSTALL_SCRIPT_PATH = NGT_SRC_LINUX + "/" + NGT_UNINSTALL_SCRIPT_NAME
  NGT_SRC_LICENSE_FILE_PATH = NGT_SRC_LINUX + "/" + NGT_LICENCE_FILE 

  # Destination folders for NGT installer.
  NGT_ROOT = "/usr/local/nutanix"
  NGT_CONFIG = NGT_ROOT + "/config"
  NGT_LOGS = NGT_ROOT + "/logs"
  NGT_BIN = NGT_ROOT + "/bin"
  DAEMON_CONFIG_DIR = "/etc/init.d"
  NGT_DST_PACKAGE_PATH = NGT_ROOT + "/" + NGT_PACKAGE_NAME
  NGT_DST_DAEMON_PATH = DAEMON_CONFIG_DIR + "/" + NGT_DAEMON_NAME
  NGT_MARKER_PATH = NGT_CONFIG + "/" + NGT_MARKER_NAME

  def is_ngt_installed(self):
    """
    This function checks if NGT is already installed.
    """

    if os.path.exists(self.NGT_CONFIG + "/ngt_marker"):
      return True
    return False

  def _get_ngt_version(self, file):
    """
    This function returns the version of NGT from config data in file.
    """

    try:
      with open(file) as data_file:
        data = json.load(data_file)
      return data["ngt_version"]
    except Exception as e:
      logging.error("Error occured while reading config file %s." %(file))
      return None

  def check_installation_required(self):
    """
    This function checks if NGT installation is required by comparing the
    version of installed NGT to version of installer.
    """

    try:
      existing_ngt_version =\
        self._get_ngt_version(self.NGT_CONFIG + "/ngt_config.json")
      installer_ngt_version =\
        self._get_ngt_version(self.NGT_SRC_CONFIG + "/ngt_config.json")

      if not installer_ngt_version:
        logging.error("Unable to get current installer version. Exiting")
        exit_installer(1)
        return

      installation_required = True
      if existing_ngt_version:
        if existing_ngt_version == installer_ngt_version:
          installation_required = False
          logging.error("NGT version %s is already installed. Exiting."\
            %(existing_ngt_version))
        elif LooseVersion(existing_ngt_version) >\
               LooseVersion(installer_ngt_version):
          installation_required = False
          logging.error("Installed version %s is newer than version %s "\
            "being installed. Exiting." %(existing_ngt_version,\
              installer_ngt_version))
        else:
          logging.info("Detected existing NGT version %s. Upgrading to " \
            "version %s." %(existing_ngt_version, installer_ngt_version))
      return installation_required
    except Exception as e:
      print(e)
      logging.error(e)
      return True

  def do_validate(self):
    """
    This function ensures that pre-conditions required for a successful execution
    of this script are satisfied. The script execution terminates upon validation
    failure.
    """
    # Only allow execution of this script as root user.
    if os.geteuid() != 0:
      logging.error("Permission denied. Please rerun the installation "\
        "script as root.")
      return False

    # Ensure that python-setuptools are installed before proceeding.
    try:
      import setuptools
    except ImportError:
      logging.error("Unable to import python-setuptools that is needed by "\
        "NGT Guest Agent.")
      logging.error("Please install python-setuptools and retry installation.")
      return False

    # Ensure that 'dmidecode' command is present. It is used to get
    # 'system_uuid'
    if not subprocess.call("type dmidecode", shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE) == 0:
      logging.error("Required package dmidecode not installed. Please "\
        "install dmidecode and retry installation.")
      return False

    return True

  def do_pre_process(self):
    """
    This function sets up the required folders for NGT Guest Agent installation.
    """
    if not os.path.exists(self.NGT_ROOT):
      os.makedirs(self.NGT_ROOT)

    if not os.path.exists(self.NGT_CONFIG):
      os.makedirs(self.NGT_CONFIG)

    if not os.path.exists(self.NGT_LOGS):
      os.makedirs(self.NGT_LOGS)

  @abstractmethod
  def install_ngt_daemon(self):
    """
    This function installs the NGT Guest Agent as an init.d daemon. Note that
    the base class method just copies the config to the /etc/init.d folder.
    The specific implementations still need to register the config as a daemon.
    """
    logging.info("Installing Nutanix Guest Agent Service.")
    # Copy the daemon config file to the etc/init.d folder
    shutil.copy(self.NGT_SRC_DAEMON_PATH, self.DAEMON_CONFIG_DIR)

    # Make the daemon config executable.
    mode = os.stat(self.NGT_DST_DAEMON_PATH)
    os.chmod(self.NGT_DST_DAEMON_PATH, mode.st_mode | stat.S_IEXEC)

  @abstractmethod
  def uninstall_ngt_daemon(self):
    """
    This function stops the NGT Guest Agent daemon and removes it.
    """

  @abstractmethod
  def setup_mobility_drivers(self):
    """
    This function loads the VirtIO and mptsas drivers into the initramfs file for the
    current OS kernel.
    """

  def do_setup(self):
    """
    This function installs the NGT Guest Agent on this VM, sets it up as
    a init.d daemon and sets up the VM mobility drivers for this VM.
    """
    # Setup the VM mobility drivers.
    try:
      self.setup_mobility_drivers()
    except:
      logging.error("Failed to setup Nutanix Guest Tools - VM mobility "\
        "drivers.")
      raise

    shutil.copy(self.NGT_SRC_PACKAGE_PATH, self.NGT_ROOT)

    # Extract the contents of the NGT installer package in the NGT root folder.
    tar_file = tarfile.open(self.NGT_DST_PACKAGE_PATH, "r:gz")
    tar_file.extractall(self.NGT_ROOT)

    config_files = os.listdir(self.NGT_SRC_CONFIG)
    for file_name in config_files:
      file_path = os.path.join(self.NGT_SRC_CONFIG, file_name)
      if (os.path.isfile(file_path)):
        shutil.copy(file_path, self.NGT_CONFIG)

    # Install the NGT Guest Agent daemon.
    try:
      self.install_ngt_daemon()
    except:
      # raise an exception so that installer does cleanup.
      raise

  def set_file_permissions(self):
    """
    This method sets the permissions on contents of the /usr/local/nutanix folder
    as follows:
    - Owner of all files and folders is set as user:root group:root.
    - Root user and group is granted read and execute permission on all files.
    - No permission is granted to any user (or group) other than the root.
    - Write / execute permission is granted to the root for the logs folder.
    """
    root_uid = pwd.getpwnam('root').pw_uid
    root_gid = pwd.getpwnam('root').pw_gid

    # Change permissions of the root folder.
    os.chown(self.NGT_ROOT, root_uid, root_gid)
    os.chmod(self.NGT_ROOT, 0o550)

    # Change permissions of all folders under root recursively.
    for root, dirs, files in os.walk(self.NGT_ROOT):
      for dir in dirs:
        dir_path = os.path.join(root, dir)
        os.chown(dir_path, root_uid, root_gid)
        os.chmod(dir_path, 0o550)
      for file in files:
        file_path = os.path.join(root, file)
        os.chown(file_path, root_uid, root_gid)
        os.chmod(file_path, 0o550)

    # Set log folder path to read / write / execute for owner / group.
    os.chmod(self.NGT_LOGS, 0o770)

  def do_post_process(self):
    """
    This function runs after a successful installation of NGT Guest Agent. It
    starts the NGT Guest Agent daemon and cleans up any temporary state from
    the installation phase.
    """
    # Start the NGT Guest Agent daemon.
    try:
      run_shell_command([self.NGT_DST_DAEMON_PATH, "start"])
    except:
      log.error("Failed to start Nutanix Guest Agent Service.")
      raise

    # Copy installer utils.
    shutil.copy(self.NGT_SRC_SOURCE + "/installer_utils.py", self.NGT_BIN)

    # Copy the uninstall script from the iso to bin.
    shutil.copy(self.NGT_SRC_UNINSTALL_SCRIPT_PATH, self.NGT_BIN)

    # Copy License.txt from the iso to nutanix directory.
    shutil.copy(self.NGT_SRC_LICENSE_FILE_PATH, self.NGT_ROOT)

    # Remove the package as it is no longer needed.
    if os.path.exists(self.NGT_DST_PACKAGE_PATH):
      os.remove(self.NGT_DST_PACKAGE_PATH)

    self.set_file_permissions()

    # Write a marker file to indicate completion of installation steps.
    with open(self.NGT_MARKER_PATH, 'a'):
      os.utime(self.NGT_MARKER_PATH, None)

  def do_cleanup(self):
    """
    This function uninstalls the NGT Guest Agent daemon and removes any files and
    folders that were created during its setup.
    """
    # Uninstall the NGT Guest Agent daemon.
    try:
      self.uninstall_ngt_daemon()
    except:
      # Ignore exceptions during cleanup as we call cleanup in scenarios such
      # as first install as well - just in case some partial stat is left behind.
      pass

    # Remove NGT Guest Agent folder
    shutil.rmtree(self.NGT_ROOT, ignore_errors=True)

  def is_ngt_running(self):
    """
    This function checks if the NGT Guest Agent process is currently running.
    """
    command = ['pgrep', '-f', 'guest_agent_monitor_linux.py']
    try:
      run_shell_command(command)
      return True
    except:
      # pgrep fails if no match is found for the given patter. This indicates
      # that the NGT Guest Agent process is not currently running.
      return False
