# -*- coding: utf-8; python-indent-offset: 2; python-guess-indent: nil; -*-
"""Provide startup service to run at Kodi launch if so configured.

This file is part of service.addonsync.

SPDX-FileCopyrightText: © 2016 Rob Webset
SPDX-FileCopyrightText: © 2019 Robert Hudson
SPDX-FileCopyrightText:  2020-2021 Peter J. Mello <admin@petermello.net>

SPDX-License-Identifier: MPL-2.0

See LICENSES/MPL-2.0.txt for more information.
"""

from xbmcaddon import Addon

from .core import AddonSync
from .settings import Settings, log

ADDON = Addon(id="service.addonsync")


if __name__ == "__main__":
  log(f"AddonSync: Service Started (version {ADDON.getAddonInfo('version')})")

  # Check if we should be running sync when the system starts
  if Settings.is_run_at_launch():
    ADDON_SYNC = AddonSync()
    ADDON_SYNC.start_sync()
    del ADDON_SYNC
  else:
    log("AddonSync: Not running at startup")

  log("AddonSync: Service Ended")
