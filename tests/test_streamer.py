import tempfile
import time
import unittest

from pistreamer.config import DEFAULT_CONFIG, _merge_dict
from pistreamer.streamer import StreamManager


class StreamManagerTests(unittest.TestCase):
    def config(self):
        config = _merge_dict(DEFAULT_CONFIG, {})
        config["stream"]["stream_key"] = "secret"
        return config

    def test_recording_aborts_when_network_output_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.config()
            config["recording"].update({"enabled": True, "path": directory})
            manager = StreamManager(config)
            args = manager._output_args("rtmp://example/live/key")
            tee = args[-1]
            self.assertIn("[f=flv:onfail=abort]", tee)
            self.assertIn("onfail=ignore", tee)

    def test_recent_failures_expire(self):
        manager = StreamManager(self.config())
        now = time.monotonic()
        manager._failure_times.extend([now - 121, now - 5])
        self.assertEqual(manager.recent_failures, 1)

    def test_stats_parser_updates_speed_and_drops(self):
        manager = StreamManager(self.config())
        manager._parse_stats("frame= 10 drop= 2 speed=1.01x")
        self.assertEqual(manager.dropped_frames, 2)
        self.assertEqual(manager.ffmpeg_speed, 1.01)

    def test_target_requires_stream_key(self):
        config = self.config()
        config["stream"]["stream_key"] = ""
        with self.assertRaises(ValueError):
            StreamManager(config)._stream_target(config["stream"])


if __name__ == "__main__":
    unittest.main()
