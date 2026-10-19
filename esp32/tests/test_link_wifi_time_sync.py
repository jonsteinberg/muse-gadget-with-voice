# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Wall-clock time syncs once Wi-Fi has an address (wifi_mgr.c): TLS
certificate validation (HTTPS APIs, OTA) fails without it, since the
chip boots with no usable time."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIFI_MGR_C = ROOT / "main" / "wifi_mgr.c"


class LinkWifiTimeSyncTest(unittest.TestCase):
    def test_sntp_starts_on_got_ip(self) -> None:
        source = WIFI_MGR_C.read_text()
        self.assertIn('#include "esp_netif_sntp.h"', source)
        self.assertIn("sntp_start_once();", source)
        # Once per boot; reconnects must not re-init the client.
        self.assertIn("static bool s_sntp_started = false;", source)
        self.assertIn("ESP_NETIF_SNTP_DEFAULT_CONFIG(", source)


if __name__ == "__main__":
    unittest.main()
