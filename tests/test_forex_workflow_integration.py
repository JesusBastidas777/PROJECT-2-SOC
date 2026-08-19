import tempfile
import unittest

from soc import FOREXWorkflow, SOCConfig, SOCService


class FOREXWorkflowIntegrationTests(unittest.TestCase):
    def test_empty_global_and_legacy_retry_are_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SOCService(SOCConfig(base_dir=directory))
            workflow = FOREXWorkflow(service)
            empty = workflow.security_posture().data["posture"]
            event = {"forex_event_id": "legacy-1", "terminal_id": "FX-1", "type": "legacy"}
            first = workflow.ingest_and_assess(event)
            second = workflow.ingest_and_assess(event)
        self.assertEqual(empty["scope"], "global")
        self.assertFalse(empty["attention_required"])
        self.assertTrue(first.metadata["stored"])
        self.assertTrue(second.metadata["duplicate"])


if __name__ == "__main__":
    unittest.main()
