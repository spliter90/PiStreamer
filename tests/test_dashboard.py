import unittest

from pistreamer.app import app
import pistreamer.metrics  # noqa: F401


class DashboardApiTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_dashboard_requires_authentication(self):
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 401)

    def test_dashboard_returns_consolidated_status(self):
        with self.client.session_transaction() as session:
            session["authenticated"] = True

        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("system", payload)
        self.assertIn("stream", payload)
        self.assertIn("network", payload)
        self.assertIn("logs", payload)
        self.assertIn("hostname", payload["system"])
        self.assertIn("ffmpeg_speed", payload["stream"])
        self.assertIn("history", payload["network"])


if __name__ == "__main__":
    unittest.main()
