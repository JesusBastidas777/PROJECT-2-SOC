import unittest

from soc.ui.app import SOCApplication
from soc.ui.state import UIState


class ServiceStub:
    def ingest_event(self): pass
    def command_center(self): pass
    def get_host_risk(self): pass
    def list_incidents(self): pass


class UIFailureIsolationTests(unittest.TestCase):
    def test_failed_refresh_preserves_then_recovers(self):
        app = SOCApplication(ServiceStub(), view="alerts")
        good = UIState("alerts", payload="last", updated_at="one")
        app.collect = lambda: (_ for _ in ()).throw(OSError("read failed"))
        stale = app.refresh(good, include_detail=True)
        self.assertEqual(stale.payload, "last")
        self.assertTrue(stale.stale)
        self.assertEqual(stale.status, "degraded")
        app.collect = lambda: UIState("alerts", payload="new", updated_at="two")
        recovered = app.refresh(stale)
        self.assertFalse(recovered.stale)
        self.assertEqual(recovered.payload, "new")


if __name__ == "__main__": unittest.main()
