#!/usr/bin/env python3
"""Test evidence and handoff invariants with isolated synthetic fixtures."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from knowledge_packet import export, validate


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="知识包 测试-")
        self.root = Path(self.temp.name)
        (self.root / "sources").mkdir()
        (self.root / "sources/S1.md").write_text("测试夹具的阅读笔记，非实际研究。", encoding="utf-8")
        source = {"id": "S1", "title": "测试原始来源", "url": "https://example.org/docs",
                  "publisher": "测试", "kind": "official-docs", "origin_family": "origin-a",
                  "accessed_on": "2026-10-15", "published_on": None, "read_status": "partial",
                  "covered_locators": ["Overview"], "reading_scope": "仅测试 Overview",
                  "notes_path": "sources/S1.md"}
        claim = {"id": "CL1", "statement": "测试事实", "verification": "primary-source",
                 "evidence": [{"source_id": "S1", "locator": "Overview", "note": "测试依据"}]}
        point = {"id": "K1", "title": "测试概念", "objective": "解释概念", "explanation": "测试解释",
                 "claim_ids": ["CL1"], "prerequisites": [], "priority": "core", "status": "ready",
                 "example": "测试例子", "misconception": "测试误区", "boundary": "只用于测试",
                 "check_question": "测试问题？", "answer_criteria": ["测试要点"]}
        self.packet = {"schema_version": 1,
                       "topic": {"keyword": "测试", "resolved_topic": "测试", "scope": "测试", "as_of": "2026-10-15", "assumptions": [], "excluded": []},
                       "queries": [{"id": "Q1", "query": "测试查询", "purpose": "测试", "status": "executed", "source_ids": ["S1"]}],
                       "sources": [source], "claims": [claim], "knowledge_points": [point],
                       "coverage": [{"dimension": "定义", "status": "covered", "knowledge_point_ids": ["K1"], "reason": "测试依据"}],
                       "gaps": [], "handoff": {"teaching_order": ["K1"], "first_diagnostic_question": "测试诊断？"}}
        self.path = self.root / "knowledge-packet.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_partial_read_exports_traceable_cards_without_scores(self):
        self.assertEqual(validate(self.packet, self.root)["ready"], 1)
        out = self.root / "中文 导出"
        result = export(self.packet, self.path, out)
        self.assertEqual(result["cards"], 1)
        cards = json.loads((out / "cards.json").read_text())
        self.assertEqual(cards[0]["external_refs"][0]["locator"], "Overview")
        self.assertEqual(cards[0]["origin"], "supplement")
        handoff = json.loads((out / "handoff.json").read_text())
        self.assertEqual(handoff["learner_level"], "unknown")
        self.assertNotIn("attempts", handoff)
        self.assertIn("测试解释", (out / "知识点明细.md").read_text())

    def test_unread_or_outside_reading_scope_is_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["sources"][0]["read_status"] = "unread"
        with self.assertRaisesRegex(ValueError, "未读取"):
            validate(packet, self.root)
        packet = copy.deepcopy(self.packet)
        packet["claims"][0]["evidence"][0]["locator"] = "Methods"
        with self.assertRaisesRegex(ValueError, "读取范围"):
            validate(packet, self.root)

    def test_unknown_reference_and_missing_evidence_are_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["claims"][0]["evidence"][0]["source_id"] = "S404"
        with self.assertRaisesRegex(ValueError, "未知来源"):
            validate(packet, self.root)
        packet["claims"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "缺少证据"):
            validate(packet, self.root)

    def test_same_origin_cannot_be_presented_as_independent(self):
        packet = copy.deepcopy(self.packet)
        second = dict(packet["sources"][0], id="S2", url="https://mirror.example.org/docs")
        packet["sources"].append(second)
        packet["claims"][0]["verification"] = "corroborated"
        packet["claims"][0]["evidence"].append({"source_id": "S2", "locator": "Overview", "note": "转载"})
        with self.assertRaisesRegex(ValueError, "同源转载"):
            validate(packet, self.root)
        second["origin_family"] = "origin-b"
        self.assertTrue(validate(packet, self.root)["valid_structure"])

    def test_tracking_parameters_and_fragments_do_not_create_new_sources(self):
        packet = copy.deepcopy(self.packet)
        packet["sources"].append(dict(packet["sources"][0], id="S2", url="https://example.org/docs/?utm_source=test#part"))
        with self.assertRaisesRegex(ValueError, "重复来源"):
            validate(packet, self.root)

    def test_pending_fact_cannot_enter_teaching(self):
        packet = copy.deepcopy(self.packet)
        packet["claims"][0]["verification"] = "pending"
        with self.assertRaisesRegex(ValueError, "未证实"):
            validate(packet, self.root)

    def test_cycles_and_wrong_teaching_order_are_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["knowledge_points"].append(dict(packet["knowledge_points"][0], id="K2", prerequisites=["K1"]))
        packet["handoff"]["teaching_order"] = ["K2", "K1"]
        with self.assertRaisesRegex(ValueError, "前置知识之前"):
            validate(packet, self.root)
        packet["knowledge_points"][0]["prerequisites"] = ["K2"]
        with self.assertRaisesRegex(ValueError, "循环"):
            validate(packet, self.root)

    def test_missing_notes_and_future_access_dates_are_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["sources"][0]["notes_path"] = "sources/missing.md"
        with self.assertRaisesRegex(ValueError, "笔记不存在"):
            validate(packet, self.root)
        packet = copy.deepcopy(self.packet)
        packet["sources"][0]["accessed_on"] = "2026-10-16"
        with self.assertRaisesRegex(ValueError, "晚于知识包"):
            validate(packet, self.root)

    def test_changed_cards_preserve_old_export(self):
        out = self.root / "旧版本"
        export(self.packet, self.path, out)
        original = (out / "cards.json").read_bytes()
        changed = copy.deepcopy(self.packet)
        changed["knowledge_points"][0]["check_question"] = "改了题目？"
        with self.assertRaisesRegex(ValueError, "保留旧题库"):
            export(changed, self.path, out)
        self.assertEqual((out / "cards.json").read_bytes(), original)

    def test_exported_cards_work_with_learning_skill_and_preserve_real_evidence(self):
        out = self.root / "两个 skill 交接"
        export(self.packet, self.path, out)
        practice = Path(__file__).resolve().parents[2] / "learning-skill/scripts/practice.py"
        self.assertTrue(practice.is_file(), "交接测试需要同级 learning-skill。")
        cards, state = out / "cards.json", out / "state.json"

        def run(*args):
            result = subprocess.run([sys.executable, str(practice), *map(str, args)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

        run("validate", "--cards", cards)
        run("init", "--cards", cards, "--state", state, "--topic", "测试主题", "--goal", "测试目标", "--date", "2026-10-15")
        self.assertEqual(json.loads(state.read_text())["cards"]["K1"]["attempts"], [])
        (out / "answer.txt").write_text("独立临时测试回答，不是用户实际作答。", encoding="utf-8")
        (out / "feedback.txt").write_text("测试反馈。", encoding="utf-8")
        run("record", "--cards", cards, "--state", state, "--card", "K1", "--date", "2026-10-15", "--score", "2", "--kind", "recall", "--support", "independent", "--answer-file", out / "answer.txt", "--feedback-file", out / "feedback.txt")
        data = json.loads(state.read_text())
        self.assertEqual(data["learner_level"], "unknown")
        self.assertEqual(data["cards"]["K1"]["next_due"], "2026-10-16")
        run("export", "--cards", cards, "--state", state, "--out", out / "review")
        self.assertTrue((out / "review/flashcards.csv").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
