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

"""Spoken replies go through ElevenLabs (muse_chat_session.cpp): the request
shape, and the fallbacks that keep text captions working. Voice notes still
ask Muse for text; TTS is a separate fetch per reply message."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SESSION_CPP = ROOT / "components" / "muse" / "muse_chat_session.cpp"
PRIV_H = ROOT / "components" / "muse" / "muse_chat_priv.h"
KCONFIG = ROOT / "components" / "muse" / "Kconfig"


def _function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : i]
    raise AssertionError(f"could not find end of {signature}")


class TtsContractTest(unittest.TestCase):
    def test_fetch_posts_text_to_elevenlabs(self) -> None:
        source = SESSION_CPP.read_text()
        # Endpoint, voice and an MP3 the minimp3 path decodes.
        self.assertIn("https://api.elevenlabs.io/v1/text-to-speech/%s", source)
        self.assertIn("output_format=mp3_", source)
        fetch = _function_body(source, "static bool tts_fetch(")
        self.assertIn('esp_http_client_set_header(c, "xi-api-key", key)', fetch)
        self.assertIn('cJSON_AddStringToObject(body, "text", text)', fetch)
        self.assertIn('cJSON_AddStringToObject(body, "model_id"', fetch)
        self.assertIn("esp_http_client_set_post_field", fetch)
        self.assertIn("esp_http_client_perform(c)", fetch)
        # Only HTTP 200 bytes reach the decoder; anything else falls back.
        self.assertIn("status == 200", fetch)
        self.assertIn("tts_data(mp3, r.len)", fetch)
        self.assertIn("ok = true", fetch)

    def test_tls_uses_pinned_gts_root(self) -> None:
        # The default bundle's lookup can't follow ElevenLabs' cross-signed
        # chain top, so the client pins GTS Root R1 directly.
        source = SESSION_CPP.read_text()
        self.assertIn("_binary_elevenlabs_roots_pem_start", source)
        self.assertIn("cfg.cert_pem = elevenlabs_roots_pem_start", source)
        roots = (ROOT / "components" / "muse" / "elevenlabs_roots.pem").read_text()
        self.assertEqual(roots.count("BEGIN CERTIFICATE"), 1)

    def test_fetch_needs_a_key_and_never_logs_it(self) -> None:
        fetch = _function_body(SESSION_CPP.read_text(), "static bool tts_fetch(")
        self.assertIn("CONFIG_MUSE_TTS_API_KEY", fetch)
        self.assertIn("if (!key[0])", fetch)
        for line in fetch.splitlines():
            if "ESP_LOG" in line:
                # The key variable must never reach a log; "API key" words are fine.
                self.assertNotIn("key", line.replace("API key", ""))

    def test_start_tts_speaks_only_with_text_and_speaker(self) -> None:
        start = _function_body(SESSION_CPP.read_text(), "static void start_tts(void)")
        self.assertIn("s_turn.texts && muse_settings_speaker_on()", start)
        self.assertIn("tts_fetch(text)", start)
        # Failure restores the silent caption path instead of playing half audio.
        self.assertIn("s_turn.silent = true", start)
        self.assertIn("show_reply_start(m)", start)

    def test_voice_notes_still_ask_muse_for_text(self) -> None:
        # Server contract (see "Request text replies" in history): the note
        # envelope stays text modality; TTS is fetched separately per message.
        head = PRIV_H.read_text()
        self.assertIn('\\"output_modality\\":\\"text\\"', head)

    def test_kconfig_defaults(self) -> None:
        kconfig = KCONFIG.read_text()
        self.assertIn("config MUSE_TTS_ELEVENLABS", kconfig)
        self.assertIn('default "JBFqnCBsd6RMkjVDRZzb"', kconfig)
        self.assertIn('default "eleven_flash_v2_5"', kconfig)


if __name__ == "__main__":
    unittest.main()
