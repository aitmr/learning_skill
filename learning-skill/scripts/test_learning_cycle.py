#!/usr/bin/env python3
"""Behavioral checks use synthetic evidence in isolated temporary directories."""
import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from learning_cycle import initialize, validate, radar_values, render_svg, report, calendar_days, month_end


class CycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='月学习验证 空格-')
        self.root = Path(self.temp.name)
        self.state = initialize('隔离模拟主题', 'foundational', date(2026, 10, 23))
        self.as_of = date(2026, 12, 31)

    def tearDown(self):
        self.temp.cleanup()

    def evidence(self, eid, when='2026-10-23', kind='diagnostic', dimensions=None, score=3, support='independent'):
        for suffix in ('回答', '反馈'):
            (self.root / f'{eid}-{suffix}.md').write_text(f'# 隔离测试\n\n模拟{suffix}，不属于用户学习记录。\n', encoding='utf-8')
        self.state['evidence'].append({'id': eid, 'date': when, 'kind': kind, 'support': support,
                                       'score': score, 'answer_path': f'{eid}-回答.md',
                                       'feedback_path': f'{eid}-反馈.md', 'dimensions': dimensions or {}})
        return eid

    def full_diagnosis(self):
        for r in range(1, 6):
            questions = []
            for q in range(1, 5):
                eid = f'D{r}{q}'
                profile = r == 1
                self.evidence(eid, kind='profile' if profile else 'diagnostic', score=None if profile else 3)
                questions.append({'id': f'Q{r}{q}', 'prompt': '隔离测试问题',
                                  'kind': 'profile' if profile else 'ability', 'evidence_id': eid})
            self.state['diagnosis']['rounds'].append({'number': r, 'questions': questions, 'summary': '模拟反馈小结'})
        self.state['diagnosis']['status'] = 'complete'

    def completed_stage(self):
        self.state['lessons'] = [{'id': 'L1', 'stage_id': 'S1', 'pass_score': 3}]
        self.state['parts'] = [{'id': 'P1', 'stage_id': 'S1'}]
        self.state['stages'] = [{'id': 'S1', 'title': '隔离阶段', 'lesson_ids': ['L1'],
                                 'completed_on': '2026-10-23', 'assessment_id': 'AS1'}]
        self.evidence('T1', kind='daily-test')
        self.state['daily'] = [{'date': '2026-10-23', 'refresh': {'status': 'not-required'},
                                'completed_lessons': [{'lesson_id': 'L1', 'test_evidence_ids': ['T1']}]}]
        self.evidence('ST1', kind='stage-test')
        self.state['assessments'] = [{'id': 'AS1', 'type': 'stage', 'status': 'completed',
                                     'due_date': '2026-10-23', 'actual_date': '2026-10-23',
                                     'evidence_ids': ['ST1'], 'retrospective_path': 'ST1-反馈.md'}]

    def test_month_length_and_audio_calendar_do_not_follow_lesson_numbers(self):
        state = initialize('模拟', 'career', date(2026, 10, 23))
        self.assertEqual(len(state['cycle']['days']), 31)
        self.assertEqual([d['date'] for d in state['cycle']['days'] if d['audio_interview_due']],
                         ['2026-11-01', '2026-11-11', '2026-11-21'])
        self.assertEqual(month_end(date(2026, 1, 31)), date(2026, 2, 27))
        self.assertEqual(month_end(date(2024, 1, 31)), date(2024, 2, 28))
        next_month = calendar_days(date(2026, 11, 23), date(2026, 10, 23), 'career')
        self.assertEqual([d['elapsed_day'] for d in next_month if d['audio_interview_due']], [40, 50, 60])

    def test_empty_state_remains_pending_and_all_radar_axes_are_unknown(self):
        result = validate(self.state, self.root, self.as_of)
        self.assertFalse(result['diagnosis_complete'])
        values = radar_values(self.state, self.as_of)
        self.assertTrue(all(v['value'] is None for v in values))
        svg = render_svg(values, '<模拟> & 未测')
        ET.fromstring(svg)
        self.assertNotIn('fill-opacity=', svg)
        self.assertIn('待测', svg)

    def test_exactly_five_rounds_of_four_and_no_duplicate_answer_filler(self):
        self.full_diagnosis()
        self.assertTrue(validate(self.state, self.root, self.as_of)['diagnosis_complete'])
        self.state['diagnosis']['rounds'][-1]['questions'].pop()
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)
        self.state['diagnosis']['rounds'][-1]['questions'].append(copy.deepcopy(self.state['diagnosis']['rounds'][0]['questions'][0]))
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)

    def test_incomplete_round_cannot_open_next_or_finalize_plan(self):
        self.state['cycle']['plan_status'] = 'final'
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)
        self.state['cycle']['plan_status'] = 'provisional'
        self.state['diagnosis']['rounds'] = [
            {'number': n, 'questions': [{'id': f'Q{n}{i}', 'prompt': '模拟问题', 'kind': 'ability', 'evidence_id': None}
                                       for i in range(4)], 'summary': ''} for n in (1, 2)]
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)

    def career_plan_fixture(self):
        self.state['track'] = 'career'
        self.state['job_seeking'] = True
        self.state['cycle']['days'] = calendar_days(date(2026, 10, 23), date(2026, 10, 23), 'career')
        self.full_diagnosis()
        self.state['cycle'].update(plan_status='final', planned_on='2026-10-24')
        for entry in self.state['cycle']['days']:
            entry['objective'] = '隔离测试课程或复习目标'
        for name in ('岗位调研.md', '岗位能力映射.md'):
            (self.root / name).write_text('# 仅隔离测试\n模拟岗位证据，不是用户的调研。', encoding='utf-8')
        return {'status': 'ready', 'target_role': '隔离测试职业', 'researched_on': '2026-10-23',
                'report_path': '岗位调研.md', 'requirements_map_path': '岗位能力映射.md',
                'channels': {'boss': 'read', 'peer': 'read', 'official': 'read'},
                'read_job_ids': ['fixture-company:fixture-job-1'], 'limitations': ''}

    def test_career_final_plan_requires_original_job_research_and_mapping(self):
        research = self.career_plan_fixture()
        with self.assertRaisesRegex(ValueError, '岗位调研'):
            validate(self.state, self.root, self.as_of)
        self.state['career_research'] = research
        self.assertTrue(validate(self.state, self.root, self.as_of)['valid'])
        research['requirements_map_path'] = '不存在.md'
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)

    def test_career_research_precedes_plan_and_missing_channels_remain_explicit(self):
        research = self.career_plan_fixture()
        self.state['career_research'] = research
        research['researched_on'] = '2026-10-25'
        with self.assertRaisesRegex(ValueError, '先于出计划'):
            validate(self.state, self.root, self.as_of)
        research['researched_on'] = '2026-10-23'
        research['channels'].pop('boss')
        with self.assertRaisesRegex(ValueError, '三渠道'):
            validate(self.state, self.root, self.as_of)
        research['channels']['boss'] = 'blocked'
        with self.assertRaisesRegex(ValueError, '覆盖受限'):
            validate(self.state, self.root, self.as_of)
        research['limitations'] = '模拟 BOSS 登录限制；计划仅覆盖已读 JD 对应职业范围，稍后补查。'
        self.assertTrue(validate(self.state, self.root, self.as_of)['valid'])
        research['read_job_ids'].append(research['read_job_ids'][0])
        with self.assertRaisesRegex(ValueError, '去重'):
            validate(self.state, self.root, self.as_of)

    def test_job_research_gate_does_not_apply_to_subjects_or_erase_old_progress(self):
        self.full_diagnosis()
        self.state['cycle']['plan_status'] = 'final'
        for entry in self.state['cycle']['days']:
            entry['objective'] = '隔离学科测试目标'
        self.state.pop('career_research', None)
        before = copy.deepcopy(self.state['evidence'])
        self.assertTrue(validate(self.state, self.root, self.as_of)['valid'])
        self.assertEqual(before, self.state['evidence'])
        self.state['track'] = 'career'
        self.state['cycle']['days'] = calendar_days(date(2026, 10, 23), date(2026, 10, 23), 'career')
        for entry in self.state['cycle']['days']:
            entry['objective'] = '在职技能学习，未表达职业求职用途'
        self.assertTrue(validate(self.state, self.root, self.as_of)['valid'])
        self.state['job_seeking'] = True
        self.state['cycle'].update(plan_status='provisional', days=calendar_days(date(2026, 10, 23), date(2026, 10, 23), 'career'))
        self.assertTrue(validate(self.state, self.root, self.as_of)['valid'])
        self.assertEqual(before, self.state['evidence'])

    def test_same_day_acceleration_requires_separate_independent_daily_tests(self):
        self.completed_stage()
        self.state['lessons'].append({'id': 'L2', 'stage_id': 'S1'})
        self.state['stages'][0]['lesson_ids'].append('L2')
        self.evidence('T2', kind='daily-test', support='hinted')
        self.state['daily'][0]['completed_lessons'].append({'lesson_id': 'L2', 'test_evidence_ids': ['T2']})
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)
        self.state['evidence'][-1]['support'] = 'independent'
        self.assertEqual(validate(self.state, self.root, self.as_of)['completed_lessons'], 2)
        self.state['evidence'][-1]['date'] = '2026-10-24'
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)

    def test_frontier_refresh_records_actual_web_and_doubao_limits(self):
        self.completed_stage(); self.state['track'] = 'frontier'
        self.state['cycle']['days'] = calendar_days(date(2026, 10, 23), date(2026, 10, 23), 'frontier')
        self.state['daily'][0]['refresh'] = {'status': 'complete', 'checked_on': '2026-10-23',
                                            'web_log_path': 'T1-反馈.md', 'doubao_status': 'blocked-login'}
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)
        self.state['daily'][0]['refresh'].update(status='partial', reason='模拟登录阻碍；只继续稳定已核对内容')
        self.assertTrue(validate(self.state, self.root, self.as_of)['valid'])
        self.state['daily'][0]['refresh']['checked_on'] = '2026-10-22'
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)

    def test_written_interview_cannot_complete_audio_checkpoint(self):
        self.evidence('I1', when='2026-11-01', kind='interview')
        interview = {'id': 'I1', 'type': 'interview', 'due_date': '2026-11-01', 'actual_date': '2026-11-01',
                     'status': 'completed', 'mode': 'written', 'voice_observed': False,
                     'evidence_ids': ['I1'], 'retrospective_path': 'I1-反馈.md'}
        self.state['assessments'].append(interview)
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)
        interview.update(mode='audio', voice_observed=True, session_ref='isolated-test-only')
        self.assertTrue(validate(self.state, self.root, self.as_of)['valid'])
        interview['due_date'] = '2026-11-11'
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)

    def test_diagnosis_can_precede_formal_month_start_without_moving_evidence_dates(self):
        self.evidence('D1', when='2026-10-23')
        self.state['anchor_date'] = '2026-10-28'
        self.state['cycle'].update(start='2026-10-28', end='2026-11-27',
                                   days=calendar_days(date(2026, 10, 28), date(2026, 10, 28), 'foundational'))
        self.assertTrue(validate(self.state, self.root, self.as_of)['valid'])
        self.assertEqual(self.state['evidence'][0]['date'], '2026-10-23')

    def test_three_routine_reviews_then_targeted_remediation_preserve_count(self):
        self.completed_stage()
        for n, when in enumerate(('2026-10-24', '2026-10-28', '2026-11-02'), 1):
            eid = self.evidence(f'R{n}', when, kind='review')
            self.state['reviews'].append({'id': eid, 'part_id': 'P1', 'date': when, 'kind': 'routine',
                                         'pass_number': n, 'evidence_ids': [eid]})
        self.assertEqual(validate(self.state, self.root, self.as_of)['routine_review_counts']['P1'], 3)
        self.evidence('R4', '2026-11-03', kind='review')
        self.state['reviews'].append({'id': 'R4', 'part_id': 'P1', 'date': '2026-11-03', 'kind': 'routine',
                                     'pass_number': 4, 'evidence_ids': ['R4']})
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)
        self.state['reviews'].pop()
        self.evidence('M1', '2026-11-04', kind='remediation')
        self.state['gaps'] = [{'id': 'G1', 'part_id': 'P1', 'trigger_evidence_ids': ['R4'],
                               'reason': '模拟遗忘', 'supplement': '模拟补充', 'practice': '模拟变式任务',
                               'retest_evidence_ids': ['M1'], 'status': 'resolved'}]
        self.state['reviews'].append({'id': 'M1', 'part_id': 'P1', 'date': '2026-11-04', 'kind': 'remedial',
                                     'trigger_gap_id': 'G1', 'evidence_ids': ['M1']})
        result = validate(self.state, self.root, self.as_of)
        self.assertEqual(result['routine_review_counts']['P1'], 3)
        self.assertEqual(result['open_gaps'], 0)
        self.state['evidence'][-1]['score'] = 2
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)

    def test_radar_separates_supported_work_and_labels_old_independent_evidence(self):
        self.evidence('E1', dimensions={'A1': 2, 'A2': 3})
        self.evidence('E2', '2026-10-24', dimensions={'A1': 4}, support='ai-assisted')
        self.evidence('E3', '2026-10-25', dimensions={'A2': 1})
        values = radar_values(self.state, date(2026, 10, 25))
        self.assertEqual((values[0]['value'], values[0]['date']), (2, '2026-10-23'))
        self.assertEqual((values[1]['value'], values[1]['date']), (1, '2026-10-25'))
        self.assertIsNone(values[2]['value'])
        out = self.root / '报告'
        report(self.state, self.root, self.as_of, out)
        ET.parse(out / '雷达图.svg')
        self.assertIn('A', (out / '雷达数据.json').read_text())
        with self.assertRaises(ValueError):
            report(self.state, self.root, self.as_of, out)

    def test_missing_notes_future_evidence_and_unscored_profiles_cannot_fake_ability(self):
        self.evidence('P1', kind='profile', score=None)
        self.state['evidence'][0]['dimensions'] = {'A1': 4}
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)
        self.state['evidence'][0]['dimensions'] = {}
        (self.root / 'P1-回答.md').unlink()
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)
        (self.root / 'P1-回答.md').write_text('隔离测试')
        self.state['evidence'][0]['date'] = '2027-01-01'
        with self.assertRaises(ValueError):
            validate(self.state, self.root, self.as_of)


if __name__ == '__main__':
    unittest.main(verbosity=2)
