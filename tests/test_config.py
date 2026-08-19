import os
import tempfile
import unittest
from pathlib import Path

from soc.config import SOCConfig
from soc.factory import build_components
from storage.event_reader import EventReader


class SOCConfigTests(unittest.TestCase):
    def test_paths_are_resolved_against_explicit_base_not_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            config = SOCConfig(base_dir=Path(directory), events_path="data/events.jsonl")
            self.assertEqual(config.events_path, Path(directory) / "data/events.jsonl")
            previous = Path.cwd()
            try:
                os.chdir(Path(directory).parent)
                self.assertEqual(EventReader().log_file.name, "events.jsonl")
                self.assertTrue(EventReader().log_file.is_absolute())
            finally:
                os.chdir(previous)

    def test_environment_and_explicit_overrides_are_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            config = SOCConfig.from_env({
                "SOC_BASE_DIR": directory,
                "SOC_EVENTS_PATH": "env/events.jsonl",
                "SOC_TIMELINE_LIMIT": "7",
            }, timeline_limit=3)
            self.assertEqual(config.events_path, Path(directory) / "env/events.jsonl")
            self.assertEqual(config.timeline_limit, 3)

    def test_factory_wires_shared_reader_without_global_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config = SOCConfig(base_dir=directory)
            first = build_components(config)
            second = build_components(config)
            self.assertIs(first.reader, first.search.reader)
            self.assertIs(first.reader, first.investigation.reader)
            self.assertIsNot(first.reader, second.reader)
            self.assertEqual(first.store.log_file, config.events_path)


if __name__ == "__main__":
    unittest.main()
