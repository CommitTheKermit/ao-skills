#!/usr/bin/env python3
"""예약 시각과 실행 기록을 검사한다. 외부 서비스 완료의 진실성을 자동 판정하지 않는다."""
# usage-stats: harness scheduled-task-verification
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest
from zoneinfo import ZoneInfo

STAGES = {"registered":0, "started":1, "tool_succeeded":2, "service_completed":3}


def instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("시각에는 UTC offset이 필요합니다.")
    return result.astimezone(timezone.utc)


def dispatch_key(task, scheduled_for):
    return task, instant(scheduled_for).isoformat()


def inspect(records):
    occurrences, runs, errors = {}, {}, []
    for row in records:
        key = dispatch_key(row["task_id"], row["scheduled_for"])
        start, end, observed = instant(row["scheduled_for"]), instant(row["window_end"]), instant(row["observed_at"])
        if end <= start:
            raise ValueError("실행 구간 끝은 시작보다 뒤여야 합니다.")
        stage, run_id = row["stage"], row["run_id"]
        if stage not in {*STAGES, "failed"}:
            raise ValueError("알 수 없는 실행 단계입니다.")
        run_key = (*key, run_id)
        previous = runs.get(run_key)
        if previous and observed < previous["observed"]:
            errors.append("event_time_reversed")
        if stage == "started":
            if not start <= observed < end:
                errors.append("dispatch_outside_window")
            if key in occurrences:
                errors.append("duplicate_dispatch")
            occurrences[key] = run_id
        if stage != "failed":
            expected = STAGES[stage] - 1
            prior_stage = previous["stage"] if previous else None
            # 실행 기록은 started부터 제출할 수 있다. 등록 기록만으로 실행을 증명하지 않는다.
            valid_first = previous is None and stage in {"registered", "started"}
            if not valid_first and (prior_stage not in STAGES or STAGES[prior_stage] != expected):
                errors.append("invalid_stage_transition")
            if stage == "service_completed" and not str(row.get("evidence", "")).strip():
                errors.append("missing_service_evidence")
        runs[run_key] = {"stage":stage, "observed":observed, "evidence":row.get("evidence")}
    return {"valid":not errors, "errors":errors,
            "runs":[{"task_id":key[0], "scheduled_for_utc":key[1], "run_id":key[2],
                     "stage":value["stage"], "has_service_evidence":value["stage"] == "service_completed" and bool(str(value.get("evidence") or "").strip())}
                    for key, value in runs.items()]}


class ScheduleTest(unittest.TestCase):
    def row(self, stage="started", observed="2026-10-21T10:30:00+09:00", run_id="one", **extra):
        return dict(task_id="task",run_id=run_id,scheduled_for="2026-10-21T10:30:00+09:00",
                    window_end="2026-10-21T10:35:00+09:00",observed_at=observed,stage=stage,**extra)

    def test_utc_and_kst_same_occurrence(self):
        self.assertEqual(dispatch_key("task","2026-10-21T10:30:00+09:00"), dispatch_key("task","2026-10-21T01:30:00Z"))

    def test_window_boundaries(self):
        self.assertTrue(inspect([self.row()])["valid"])
        for time in ["2026-10-21T10:29:59+09:00", "2026-10-21T10:35:00+09:00"]:
            self.assertIn("dispatch_outside_window", inspect([self.row(observed=time)])["errors"])

    def test_duplicate_dispatch(self):
        self.assertIn("duplicate_dispatch",inspect([self.row(),self.row(run_id="two")])["errors"])

    def test_tool_success_does_not_mean_service_complete(self):
        result=inspect([self.row(),self.row(stage="tool_succeeded")])
        self.assertTrue(result["valid"])
        self.assertFalse(result["runs"][0]["has_service_evidence"])

    def test_service_receipt_required(self):
        rows=[self.row(),self.row(stage="tool_succeeded"),self.row(stage="service_completed")]
        self.assertIn("missing_service_evidence",inspect(rows)["errors"])
        rows[-1]["evidence"]="service record reference"
        self.assertTrue(inspect(rows)["valid"])

    def test_bad_order_and_time(self):
        self.assertIn("invalid_stage_transition",inspect([self.row(stage="service_completed",evidence="record")])["errors"])
        self.assertIn("event_time_reversed",inspect([self.row(),self.row(stage="tool_succeeded",observed="2026-10-21T10:29:00+09:00")])["errors"])

    def test_missing_timezone_and_invalid_window(self):
        with self.assertRaises(ValueError):
            instant("2026-10-21T10:30:00")
        row=self.row()
        row["window_end"]=row["scheduled_for"]
        with self.assertRaises(ValueError):
            inspect([row])

    def test_dst_offsets_distinguish_two_local_0130(self):
        zone=ZoneInfo("America/New_York")
        first=datetime(2026,11,1,1,30,tzinfo=zone,fold=0).isoformat()
        second=datetime(2026,11,1,1,30,tzinfo=zone,fold=1).isoformat()
        self.assertNotEqual(dispatch_key("task",first),dispatch_key("task",second))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,help="실행 이벤트 JSON 배열")
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(ScheduleTest))
        return 0 if result.wasSuccessful() else 1
    if not args.input:
        parser.error("--input 또는 --self-test가 필요합니다.")
    recorder=Path.home()/".agents/skills/usage-stats/scripts/usage_stats.py"
    if recorder.exists():
        subprocess.run([sys.executable,str(recorder),"record","harness","scheduled-task-verification"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    try:
        result=inspect(json.loads(args.input.read_text()))
    except (KeyError,TypeError,ValueError,OSError):
        result={"valid":False,"errors":["invalid_input"]}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    sys.exit(main())
