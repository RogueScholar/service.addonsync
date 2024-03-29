# -*- coding: utf-8; python-indent-offset: 2; python-guess-indent: nil; -*-
"""Apply include/exclude filters for installed add-ons if so configured.

This file is part of service.addonsync.

SPDX-FileCopyrightText: © 2016 Rob Webset
SPDX-FileCopyrightText:  2020-2021 Peter J. Mello <admin@petermello.net>

SPDX-License-Identifier: MPL-2.0

See LICENSES/MPL-2.0.txt for more information.
"""

from __future__ import absolute_import
import json
import xbmc
from xbmcaddon import Addon
import xbmcgui

# Import the common settings
from .settings import Settings, log

ADDON = Addon(id="service.addonsync")

if __name__ == "__main__":
  log(f"AddonFilter: Include / Exclude Filter "
      f"(version {ADDON.getAddonInfo('version')})")

  # Get the type of filter that is being applied
  FILTER_TYPE = Settings.get_filter_type()

  if FILTER_TYPE == Settings.FILTER_ALL:
    log("AddonFilter: Filter called when there is no filter required")
  else:
    # Make the call to find out all the add-ons that are installed
    JSON_QUERY = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "enabled": true, "properties": [ "broken", "name" ] }, "id": 1 }'  # noqa
        )
    json_response = json.loads(JSON_QUERY)

    addons = {}

    if ("result" in json_response) and (
        "addons" in json_response["result"]):
      # Check each of the screensavers that are installed on the system
      for addon_item in json_response["result"]["addons"]:
        addon_name = addon_item["addonid"]
        # Need to skip both built-in screensavers as they cannot be triggered
        # and are a bit dull, so shouldn't be in the mix
        if addon_name in [
            "screensaver.xbmc.builtin.black",
            "screensaver.xbmc.builtin.dim",
            "service.xbmc.versioncheck",
            ]:
          log(f"AddonFilter: Skipping built-in add-ons: {addon_name}")
          continue

        # Skip metadata add-ons
        if addon_name.startswith("metadata"):
          log(f"AddonFilter: Skipping metadata add-on: {addon_name}")
          continue
        # Skip localization add-ons
        if addon_name.startswith("resource.language"):
          log(f"AddonFilter: Skipping localization add-on: {addon_name}")
          continue
        # Skip add-on repositories
        if addon_name.startswith("repository"):
          log(f"AddonFilter: Skipping add-on repository: {addon_name}")
          continue
        # Skip skin add-ons
        if addon_name.startswith("skin"):
          log(f"AddonFilter: Skipping skin add-on: {addon_name}")
          continue

        # Skip ourself as we don't want to flip a slave into a master
        if addon_name in ["service.addonsync"]:
          log(f"AddonFilter: Detected ourself: {addon_name}")
          continue

        # Ensure we skip any add-ons that are flagged as broken
        if addon_item["broken"]:
          log(f"AddonFilter: Skipping broken addon: {addon_name}")
          continue

        # Now we are left with only the working add-ons
        log(f"AddonFilter: Detected Addon: {addon_name} ({addon_item['name']})")
        addons[addon_item["name"]] = addon_name

      if len(addons) < 1:
        log("AddonFilter: No Addons installed")
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001),
                            ADDON.getLocalizedString(32011))
      else:
        # Get the names of the addons and order them
        ADDON_NAMES = list(addons.keys())
        ADDON_NAMES.sort()
        SELECTION = None
        try:
          SELECTION = xbmcgui.Dialog().multiselect(
              ADDON.getLocalizedString(32001), ADDON_NAMES)
        except (ReferenceError, RuntimeError, TypeError):
          # Multi-select is only available for releases v16 onwards,
          # fall back to single select
          log("AddonFilter: Multiselect unsupported, using uniselect")
          TEMP_SELECTION = xbmcgui.Dialog().select(
              ADDON.getLocalizedString(32001), ADDON_NAMES)
          if TEMP_SELECTION > -1:
            SELECTION = []
            SELECTION.append(TEMP_SELECTION)

        # Check the cancel selection
        if SELECTION is not None:
          # Clear the previously saved values
          Settings.set_excluded_addons()
          Settings.set_included_addons()

          if len(SELECTION) > 0:
            ADDON_LIST = []
            for ADDON_SELECTION in SELECTION:
              addon_name = ADDON_NAMES[ADDON_SELECTION]
              log("AddonFilter: Selected addon %d (%s)"
                  % (ADDON_SELECTION, addon_name))
              ADDON_LIST.append(addons[addon_name])

            # Make a space separated string from the list
            ADDON_SPACE_LIST = " ".join(ADDON_LIST)

            if FILTER_TYPE == Settings.FILTER_EXCLUDE:
              Settings.set_excluded_addons(ADDON_SPACE_LIST)
            else:
              Settings.set_included_addons(ADDON_SPACE_LIST)
