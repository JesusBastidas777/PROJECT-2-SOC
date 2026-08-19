"""Explainable grouping of related alerts without mutating them."""

import hashlib
from collections import defaultdict

from detection.enrichment import RULE_CONTEXT
from inventory.host_catalog import host_key
from normalization.time_utils import parse_timestamp
from soc.errors import QueryError


PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}


class AlertGrouping:
    def __init__(self, alert_service, risk_service):
        self.alert_service = alert_service
        self.risk_service = risk_service

    @staticmethod
    def _category(alert):
        return RULE_CONTEXT.get(alert.rule_name, (alert.rule_name, "medium"))[0]

    @classmethod
    def _relationship(cls, left, right, window_seconds):
        if host_key(left.hostname) != host_key(right.hostname):
            return []
        left_time = parse_timestamp(left.created_at or left.timestamp)
        right_time = parse_timestamp(right.created_at or right.timestamp)
        if left_time is None or right_time is None:
            return []
        if abs((left_time - right_time).total_seconds()) > window_seconds:
            return []
        reasons = []
        if left.event_uid and left.event_uid == right.event_uid:
            reasons.append("same_event_uid")
        left_processes = {
            value for value in (
                left.event.get("process_name"), left.event.get("parent_process")
            ) if value
        }
        right_processes = {
            value for value in (
                right.event.get("process_name"), right.event.get("parent_process")
            ) if value
        }
        if {str(value).casefold() for value in left_processes} & {
            str(value).casefold() for value in right_processes
        }:
            reasons.append("related_process")
        if cls._category(left) == cls._category(right):
            reasons.append("same_detection_category")
        return reasons

    def correlate(self, *, hostname=None, window_minutes=30,
                  include_singletons=True):
        if not isinstance(window_minutes, (int, float)) or window_minutes <= 0:
            raise QueryError("window_minutes must be positive")
        alerts = []
        for status in ("open", "acknowledged"):
            alerts.extend(self.alert_service.search(hostname=hostname, status=status))
        alerts.sort(key=lambda item: item.alert_id)
        parent = list(range(len(alerts)))
        pair_reasons = defaultdict(set)

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left, right):
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for left in range(len(alerts)):
            for right in range(left + 1, len(alerts)):
                reasons = self._relationship(
                    alerts[left], alerts[right], window_minutes * 60
                )
                if reasons:
                    union(left, right)
                    pair_reasons[left].update(reasons)
                    pair_reasons[right].update(reasons)

        grouped = defaultdict(list)
        for index in range(len(alerts)):
            grouped[find(index)].append(index)
        results = []
        for indexes in grouped.values():
            if len(indexes) == 1 and not include_singletons:
                continue
            members = [alerts[index] for index in indexes]
            ids = sorted(item.alert_id for item in members)
            group_id = "grp-" + hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()[:20]
            timestamps = [
                item.created_at or item.timestamp for item in members
                if parse_timestamp(item.created_at or item.timestamp) is not None
            ]
            reasons = sorted(set().union(*(pair_reasons[index] for index in indexes)))
            if len(indexes) == 1:
                reasons = ["singleton"]
            hostname_value = members[0].hostname
            results.append({
                "group_id": group_id,
                "hostname": hostname_value,
                "time_range": {
                    "start": min(timestamps, key=parse_timestamp) if timestamps else None,
                    "end": max(timestamps, key=parse_timestamp) if timestamps else None,
                },
                "alerts": members,
                "alert_ids": ids,
                "priority": min(
                    (item.priority for item in members),
                    key=lambda value: PRIORITY_ORDER.get(value, 99),
                ),
                "reasons": reasons,
                "host_risk": self.risk_service.calculate(hostname_value),
            })
        return sorted(results, key=lambda item: (
            PRIORITY_ORDER.get(item["priority"], 99), item["group_id"]
        ))

    def get(self, group_id, **options):
        return next(
            (item for item in self.correlate(**options) if item["group_id"] == group_id),
            None,
        )
