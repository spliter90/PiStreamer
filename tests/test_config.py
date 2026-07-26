import tempfile
import unittest
from pathlib import Path

import yaml

from pistreamer import config as config_module


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "config.yaml"
        self.original_path = config_module.CONFIG_PATH
        config_module.CONFIG_PATH = self.path
        self.addCleanup(setattr, config_module, "CONFIG_PATH", self.original_path)

    def test_missing_sections_receive_defaults(self):
        self.path.write_text("stream:\n  platform: twitch\n", encoding="utf-8")
        config = config_module.load_config()
        self.assertEqual(config["stream"]["platform"], "twitch")
        self.assertEqual(config["stream"]["quality_profile"], "wifi_standard")
        self.assertEqual(config["recording"]["max_storage_gb"], 20)

    def test_save_is_valid_yaml(self):
        config = config_module.load_config()
        config["web"]["password"] = "changed"
        config_module.save_config(config)
        loaded = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["web"]["password"], "changed")

    def test_invalid_root_is_rejected(self):
        self.path.write_text("- invalid\n- root\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            config_module.load_config()


if __name__ == "__main__":
    unittest.main()
