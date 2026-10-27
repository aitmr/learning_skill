#!/usr/bin/env python3
"""Behavior checks isolated from the learner's real records."""

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

SCRIPTS = Path(__file__).resolve().parent


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="learning-skill-测试 空格-")
        self.root = Path(self.temp.name)
        self.cards = self.root / "练习卡.json"
        self.state = self.root / "学习状态.json"
        self.card_data = [{"id": "C1", "concept": "测试", "question": "先测试, 再学习\n为什么？",
                           "answer": "定位起点。", "origin": "design", "tags": ["复习 练习"]}]
        self.cards.write_text(json.dumps(self.card_data, ensure_ascii=False), encoding="utf-8")
        self.answer = self.root / "回答.txt"
        self.feedback = self.root / "反馈.txt"
        self.answer.write_text("根据当前能力安排内容。", encoding="utf-8")
        self.feedback.write_text("解释了目的，还要补一个应用例子。", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, script, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stderr)
        return result

    def init(self):
        self.cli("practice.py", "init", "--cards", self.cards, "--state", self.state,
                 "--topic", "测试", "--goal", "能独立说明理由", "--date", "2026-10-14")

    def record(self, day, score, kind="recall", support="independent", ok=True):
        self.cli("practice.py", "record", "--cards", self.cards, "--state", self.state,
                 "--card", "C1", "--date", day, "--score", score, "--kind", kind,
                 "--support", support, "--answer-file", self.answer,
                 "--feedback-file", self.feedback, ok=ok)

    def progress(self):
        return json.loads(self.state.read_text())["cards"]["C1"]

    def test_docx_extract_keeps_ids_times_and_original(self):
        source = self.root / "原文 有空格.docx"
        xml = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
        <w:p><w:r><w:t>发言人   07:30</w:t></w:r></w:p><w:p/>
        <w:p><w:r><w:t>先测试</w:t><w:tab/><w:t>再学习</w:t></w:r></w:p>
        <w:tbl><w:tr><w:tc><w:p><w:r><w:t>表格信息</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
        </w:body></w:document>'''
        with ZipFile(source, "w") as archive:
            archive.writestr("word/document.xml", xml)
        original = source.read_bytes()
        out = self.root / "提取"
        self.cli("extract_material.py", source, "--out", out)
        data = json.loads((out / "source.json").read_text())
        self.assertEqual([p["id"] for p in data["paragraphs"]], ["P0001", "P0003", "P0004"])
        self.assertEqual(data["paragraphs"][1]["text"], "先测试\t再学习")
        self.assertEqual(data["paragraphs"][2]["timestamp"], "07:30")
        self.assertEqual(source.read_bytes(), original)
        before = (out / "source.json").read_bytes()
        self.cli("extract_material.py", source, "--out", out, ok=False)
        self.assertEqual((out / "source.json").read_bytes(), before)

    def test_initial_state_is_unassessed_and_cannot_be_overwritten(self):
        self.init()
        progress = self.progress()
        self.assertEqual(progress["attempts"], [])
        self.assertIsNone(progress["next_due"])
        self.assertEqual(json.loads(self.state.read_text())["learner_level"], "unknown")
        original = self.state.read_bytes()
        self.cli("practice.py", "init", "--cards", self.cards, "--state", self.state,
                 "--topic", "测试", "--goal", "测试", "--date", "2026-10-14", ok=False)
        self.assertEqual(self.state.read_bytes(), original)

    def test_real_evidence_and_review_dates_survive_restart(self):
        self.init()
        self.record("2026-10-14", 2)
        self.assertEqual(self.progress()["next_due"], "2026-10-15")
        self.record("2026-10-15", 3)
        self.record("2026-10-16", 4, "application")
        progress = self.progress()
        self.assertEqual(progress["next_due"], "2026-10-19")
        self.assertEqual(progress["status"], "application_evidence")
        self.assertEqual(progress["attempts"][0]["answer"], self.answer.read_text())
        self.assertEqual(len(progress["attempts"]), 3)
        self.record("2026-10-17", 1)
        self.assertEqual(self.progress()["next_due"], "2026-10-18")
        self.assertEqual(self.progress()["success_streak"], 0)

    def test_same_day_or_ai_help_does_not_advance_review_interval(self):
        self.init()
        self.record("2026-10-14", 4, "application", "ai-assisted")
        self.assertEqual(self.progress()["status"], "practiced_with_support")
        self.assertEqual(self.progress()["success_streak"], 0)
        self.record("2026-10-14", 3)
        self.record("2026-10-14", 4)
        self.assertEqual(self.progress()["success_streak"], 1)
        self.assertEqual(self.progress()["next_due"], "2026-10-15")

    def test_empty_or_backdated_answer_does_not_change_history(self):
        self.init()
        original = self.state.read_bytes()
        self.answer.write_text("  ", encoding="utf-8")
        self.record("2026-10-14", 3, ok=False)
        self.assertEqual(self.state.read_bytes(), original)
        self.answer.write_text("真实回答", encoding="utf-8")
        self.record("2026-10-13", 3, ok=False)
        self.assertEqual(self.state.read_bytes(), original)

    def test_csv_round_trip_and_untested_dates(self):
        self.init()
        out = self.root / "导出 卡片"
        self.cli("practice.py", "export", "--cards", self.cards, "--state", self.state, "--out", out)
        with (out / "flashcards.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[0][0], self.card_data[0]["question"])
        self.assertEqual(len(rows[0]), 3)
        with (out / "review_schedule.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]["next_due"], "")
        self.assertEqual(rows[0]["attempts"], "0")

    def test_source_references_must_exist_and_match_time(self):
        source = self.root / "source.json"
        source.write_text(json.dumps({"paragraphs": [{"id": "P0007", "text": "阶梯", "timestamp": "00:26"}]}))
        card = dict(self.card_data[0], origin="material", source_refs=[{"paragraph_id": "P0007", "timestamp": "00:26"}])
        self.cards.write_text(json.dumps([card]))
        self.cli("practice.py", "validate", "--cards", self.cards, "--source", source)
        card["source_refs"][0]["timestamp"] = "01:26"
        self.cards.write_text(json.dumps([card]))
        self.cli("practice.py", "validate", "--cards", self.cards, "--source", source, ok=False)
        card["source_refs"][0]["paragraph_id"] = "P9999"
        self.cards.write_text(json.dumps([card]))
        self.cli("practice.py", "validate", "--cards", self.cards, "--source", source, ok=False)

    def test_stage_policy_records_evidence_without_parallel_legacy_due_dates(self):
        self.cli("practice.py", "init", "--cards", self.cards, "--state", self.state,
                 "--topic", "隔离测试", "--goal", "测试证据", "--date", "2026-10-14",
                 "--review-policy", "stage-three")
        self.record("2026-10-14", 3)
        self.assertIsNone(self.progress()["next_due"])
        self.assertEqual(len(self.progress()["attempts"]), 1)
        self.assertEqual(json.loads(self.state.read_text())["review_policy"], "stage-three")

    def test_switching_old_policy_keeps_answers_and_archives_all_old_due_dates(self):
        self.init()
        self.record("2026-10-14", 3)
        old = json.loads(self.state.read_text())
        self.cli("practice.py", "record", "--cards", self.cards, "--state", self.state,
                 "--card", "C1", "--date", "2026-10-15", "--score", 3, "--kind", "recall",
                 "--support", "independent", "--answer-file", self.answer,
                 "--feedback-file", self.feedback, "--review-policy", "stage-three")
        new = json.loads(self.state.read_text())
        self.assertEqual(new["cards"]["C1"]["attempts"][0], old["cards"]["C1"]["attempts"][0])
        self.assertEqual(new["review_policy_history"][0]["previous_due"]["C1"], "2026-10-15")
        self.assertIsNone(new["cards"]["C1"]["next_due"])
        self.assertEqual(len(new["cards"]["C1"]["attempts"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
