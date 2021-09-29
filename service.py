# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: © 2016 Rob Webset
# SPDX-FileCopyrightText: © 2019 Robert Hudson
# SPDX-FileCopyrightText:  2020-2021 Peter J. Mello <admin@petermello.net>
#
# SPDX-License-Identifier: MPL-2.0

import xbmcaddon

from resources.lib.settings import log, Settings
from resources.lib.core import AddonSync

ADDON = xbmcaddon.Addon(id="service.addonsync")


if __name__ == "__main__":
    log("AddonSync: Service Started (version %s)" %
        ADDON.getAddonInfo('version'))

    # Check if we should be running sync when the system starts
    if Settings.isRunOnStartup():
        ADDON_SYNC = AddonSync()
        ADDON_SYNC.startSync()
        del ADDON_SYNC
    else:
        log("AddonSync: Not running at startup")

    log("AddonSync: Service Ended")
