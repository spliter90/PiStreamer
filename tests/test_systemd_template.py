import unittest
from pathlib import Path


class SystemdTemplateTests(unittest.TestCase):
    def test_execstart_can_be_verified_before_current_symlink_exists(self):
        service = Path("systemd/pistreamer.service").read_text(encoding="utf-8")
        self.assertIn(
            "ExecStart=/usr/bin/env /opt/pistreamer/current/.venv/bin/python "
            "/opt/pistreamer/current/run.py",
            service,
        )


if __name__ == "__main__":
    unittest.main()
