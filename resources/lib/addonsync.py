# -*- coding: utf-8; python-indent-offset: 2; python-guess-indent: nil; -*-
"""Invoke AddonSync as a Kodi Program add-on.

This file is part of service.addonsync.

SPDX-FileCopyrightText: © 2016 Rob Webset
SPDX-FileCopyrightText:  2020-2021 Peter J. Mello <admin@petermello.net>

SPDX-License-Identifier: MPL-2.0

See LICENSES/MPL-2.0.txt for more information.
"""

import xbmcgui
from xbmcaddon import Addon

from .core import AddonSync
from .settings import log

ADDON = Addon(id="service.addonsync")


if __name__ == "__main__":
  log("AddonSync: Started Manually")

  # Print message that we have started
  xbmcgui.Dialog().notification(ADDON.getLocalizedString(32001),
                                ADDON.getLocalizedString(32019),
                                ADDON.getAddonInfo("icon"), 3000, False)

  COMPLETED = AddonSync().start_sync()

  # Only show the complete message if we have not shown an error
  if COMPLETED:
    xbmcgui.Dialog().notification(ADDON.getLocalizedString(32001),
                                  ADDON.getLocalizedString(32020),
                                  ADDON.getAddonInfo("icon"), 3000, False)
    log("AddonSync: Completed manual add-on settings sync successfully.")
