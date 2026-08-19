import json
import unittest
from dataclasses import FrozenInstanceError

from soc.models import (
    CorrelationV1, DetectionV1, EventQueryV1, HostProfileV1,
    InvestigationV1, SOCResponseV1,
)


class ResponseModelContractTests(unittest.TestCase):
    def test_envelope_has_stable_v1_shape_and_is_json_serializable(self):
        response = SOCResponseV1(data={"events": []}, metadata={"count": 0})
        payload = response.to_dict()
        self.assertEqual(list(payload), [
            "schema_version", "status", "data", "errors", "metadata"
        ])
        self.assertEqual(payload["schema_version"], "1.0")
        json.dumps(payload)

    def test_investigation_converts_internal_mappings_to_typed_models(self):
        profile = HostProfileV1.from_mapping({"hostname": "HOST", "total_events": 1})
        correlation = CorrelationV1.from_mapping({
            "hostname": "HOST", "parent_process": "a", "process_name": "b", "count": 1,
        })
        detection = DetectionV1.from_mapping({
            "rule_name": "r", "severity": "high", "reason": "why", "event": {"host": "HOST"},
        })
        result = SOCResponseV1(data=InvestigationV1(
            host_profile=profile, process_correlations=[correlation], detections=[detection]
        )).to_dict()
        self.assertEqual(result["data"]["host_profile"]["hostname"], "HOST")
        self.assertEqual(result["data"]["detections"][0]["rule_name"], "r")
        json.dumps(result)

    def test_query_models_are_immutable_contract_values(self):
        query = EventQueryV1(hostname="HOST", limit=5)
        with self.assertRaises(FrozenInstanceError):
            query.limit = 2


if __name__ == "__main__":
    unittest.main()
