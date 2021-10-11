# -*- coding: utf-8; python-indent-offset: 2; python-guess-indent: nil; -*-
"""Invoke AddonSync as a Kodi Program add-on.

This file is part of service.addonsync.

SPDX-FileCopyrightText: © 2016 Rob Webset
SPDX-FileCopyrightText:  2020-2021 Peter J. Mello <admin@petermello.net>

SPDX-License-Identifier: MPL-2.0

See LICENSES/MPL-2.0.txt for more information.
"""

from __future__ import annotations, generator_stop
import xbmcgui
from xbmcaddon import Addon

from .core import AddonSync
from .settings import log

ADDON = Addon(id="service.addonsync")
ICON = ADDON.getAddonInfo("icon")
ADDONSYNC = AddonSync()


if __name__ == "__main__":
  log("AddonSync: Started Manually")

  # Print message that we have started
  xbmcgui.Dialog().notification(
    ADDON.getLocalizedString(32001),
    ADDON.getLocalizedString(32019),
    ICON,
    3000,
    False
    )

  COMPLETED = ADDONSYNC.start_sync()

  # Only show the complete message if we have not shown an error
  if COMPLETED:
    xbmcgui.Dialog().notification(
      ADDON.getLocalizedString(32001),
      ADDON.getLocalizedString(32020),
      ICON,
      3000,
      False,
      )
    del ADDONSYNC
    log("AddonSync: End Manual Running")
