# -*- coding: utf-8; python-indent-offset: 2; python-guess-indent: nil; -*-
"""Read and store add-on configuration under userdata.

This file is part of service.addonsync.

SPDX-FileCopyrightText: © 2016 Rob Webset
SPDX-FileCopyrightText:  2020-2021 Peter J. Mello <admin@petermello.net>

SPDX-License-Identifier: MPL-2.0

See LICENSES/MPL-2.0.txt for more information.
"""

from __future__ import annotations, generator_stop
import os
import xbmc
import xbmcvfs
from xbmcaddon import Addon

ADDON = Addon(id="service.addonsync")
ADDON_ID = ADDON.getAddonInfo("id")


def log(txt, loglevel=xbmc.LOGDEBUG):
  """Control logging AddonSync messages to the Kodi system log."""
  if (ADDON.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
    message = f"{ADDON_ID}: {txt}"
    xbmc.log(msg=message, level=loglevel)


def dir_exists(dir_path):
  """Check if a directory exists."""
  # There is an issue with password protected SMB/CIFS shares, in that they
  # seem to always return false for a directory exists call, so if we have an
  # SMB/CIFS share with a password and user name, then we return true
  if "@" in dir_path:
    return True

  # The xbmcvfs exists interface require that directories end in a slash
  if (not dir_path.endswith("/")) and (not dir_path.endswith("\\")):
    dir_sep = "/"
    if "\\" in dir_path:
      dir_sep = "\\"
    dir_path = f"{dir_path}{dir_sep}"
  return xbmcvfs.exists(dir_path)


def os_path_join(folder, file):
  """Construct canonical filepaths from directory tree file lists."""
  # Check if it ends in a slash
  if folder.endswith("/") or folder.endswith("\\"):
    # Remove the slash character
    folder = folder[:-1]
  return os.path.join(folder, file)


def nested_copy(root_src_dir, root_target_dir):
  """Perform a nested (recursive) copy of one directory tree to another."""
  log(f"nested_copy: Copy {root_src_dir} to {root_target_dir}")

  # Make sure the target directory exists
  xbmcvfs.mkdirs(root_target_dir)

  dirs, files = xbmcvfs.listdir(root_src_dir)

  for file in files:
    src_file = f"{root_src_dir}{file}"
    target_file = "{root_target_dir}{file}"
    log(f"nested_copy: Copy file {src_file} to {target_file}")
    xbmcvfs.copy(src_file, target_file)

  for adir in dirs:
    src_dir = f"{root_src_dir}{adir}/"
    target_dir = f"{root_target_dir}{adir}/"
    log(f"nested_copy: Copy directory {src_dir} to {target_dir}")
    nested_copy(src_dir, target_dir)


def nested_delete(root_dir):
  """Remove a directory recursively if it is no longer needed."""
  if dir_exists(root_dir):
    dirs, files = xbmcvfs.listdir(root_dir)
    # Remove nested directories first
    for ao_dir in dirs:
      nested_delete(os_path_join(root_dir, ao_dir))
    # If there are any nested files remove them
    for ao_file in files:
      xbmcvfs.delete(os_path_join(root_dir, ao_file))
    # Now remove the actual directory
    xbmcvfs.rmdir(root_dir)
  else:
    log(f"nested_delete: Directory {root_dir} does not exist")


class Settings:
  """Map names and store config variables from settings.xml to Python."""

  FILTER_ALL = 0
  FILTER_INCLUDE = 1
  FILTER_EXCLUDE = 2

  @staticmethod
  def is_first_use():
    """Remember if AddonSync has created the central store already."""
    return ADDON.getSetting("isFirstUse") == "true"

  @staticmethod
  def set_first_use(use_value="false"):
    """Set to true on installation to trigger central store creation."""
    ADDON.setSetting("isFirstUse", use_value)

  @staticmethod
  def get_central_store_loc():
    """Read filepath of the central store."""
    central_store_loc = ADDON.getSetting("centralStoreLocation")
    # Make sure the location ends with a slash
    if ("/" in central_store_loc) and (not central_store_loc.endswith("/")):
      central_store_loc = f"{central_store_loc}/"
    elif ("\\" in central_store_loc) and (not central_store_loc.endswith("\\")):
      central_store_loc = f"{central_store_loc}\\"
    return central_store_loc

  @staticmethod
  def is_master():
    """Check whether we are running as a Master or Slave instance."""
    # Safer to check for slave type, as master will not overwrite
    if int(ADDON.getSetting("installationType")) == 1:
      return False
    return True

  @staticmethod
  def is_run_at_launch():
    """Check for 'service' config (run whenever Kodi is launched)."""
    return ADDON.getSetting("runOnStartup") == "true"

  @staticmethod
  def get_sync_interval():
    """Get the scheduled interval at which to synchronize add-ons."""
    # If we do not want to run on startup, then the interval is
    # just the once
    if not Settings.is_run_at_launch():
      return 0
    return int(float(ADDON.getSetting("checkInterval")))

  @staticmethod
  def is_restart_synced_services():
    """Check if we need to restart service add-ons following syncs."""
    return ADDON.getSetting("restartUpdatedServiceAddons") == "true"

  @staticmethod
  def is_force_version_match():
    """Check if we only sync when add-ons have matching versions."""
    return ADDON.getSetting("forceVersionMatch") == "true"

  @staticmethod
  def get_filter_type():
    """Check if filtering is enabled and if it's inclusive or exclusive."""
    index = int(ADDON.getSetting("filterType"))
    filter_type = Settings.FILTER_ALL
    if index == 1:
      filter_type = Settings.FILTER_INCLUDE
    elif index == 2:
      filter_type = Settings.FILTER_EXCLUDE

    return filter_type

  @staticmethod
  def get_excluded_addons():
    """Return id strings of any add-ons to exclude from syncs."""
    return ADDON.getSetting("excludedAddons")

  @staticmethod
  def get_included_addons():
    """Get id strings of the only add-ons we are supposed to sync."""
    return ADDON.getSetting("includedAddons")

  @staticmethod
  def set_excluded_addons(value=""):
    """Write the id strings of excluded add-ons to AddonSync config."""
    ADDON.setSetting("excludedAddons", value)

  @staticmethod
  def set_included_addons(value=""):
    """Write the id strings of the add-ons we restrict syncing to."""
    ADDON.setSetting("includedAddons", value)
