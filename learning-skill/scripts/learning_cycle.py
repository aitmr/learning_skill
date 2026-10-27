#!/usr/bin/env python3
"""Validate monthly learning evidence and render honest radar charts; standard library only."""
import argparse
import calendar
import html
import json
import math
import os
from datetime import date, timedelta
from pathlib import Path

TRACKS = ('foundational', 'frontier', 'career')
SUPPORTS = ('independent', 'hinted', 'reference', 'ai-assisted')
LABELS = ('概念基础', '理解辨析', '操作应用', '问题解决', '表达论证', '迁移整合')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def day(value):
    return date.fromisoformat(value)


def month_end(start):
    first = start.replace(day=1) + timedelta(days=32)
    boundary = first.replace(day=min(start.day, calendar.monthrange(first.year, first.month)[1]))
    return boundary - timedelta(days=1)


def calendar_days(start, anchor, track):
    end = month_end(start)
    return [{'date': (current := start + timedelta(days=i)).isoformat(),
             'cycle_day': i + 1, 'elapsed_day': (current - anchor).days + 1,
             'lesson_ids': [], 'objective': '', 'daily_test': True, 'radar': True,
             'refresh_required': track != 'foundational',
             'audio_interview_due': track == 'career' and ((current - anchor).days + 1) % 10 == 0}
            for i in range((end - start).days + 1)]


def initialize(topic, track, start, job_seeking=False):
    require(not job_seeking or track == 'career', '职业求职用途须使用 career 分类')
    return {'schema_version': 2, 'topic': topic, 'track': track,
            'job_seeking': job_seeking,
            'recording_started_on': start.isoformat(),
            'anchor_date': start.isoformat(),
            'cycle': {'start': start.isoformat(), 'end': month_end(start).isoformat(),
                      'plan_status': 'provisional', 'days': calendar_days(start, start, track)},
            'axes': [{'id': f'A{i + 1}', 'label': label,
                      'rubric': ['关键判断错误或不能完成', '术语或步骤有明显混淆',
                                 '主干正确但缺条件', '独立完成且关键条件正确', '能迁移并说明边界']}
                     for i, label in enumerate(LABELS)],
            'diagnosis': {'status': 'pending', 'rounds': []},
            'career_research': {'status': 'pending'} if job_seeking else None,
            'parts': [], 'lessons': [], 'stages': [], 'evidence': [],
            'daily': [], 'assessments': [], 'reviews': [], 'gaps': []}


def indexed(items, label):
    require(isinstance(items, list), f'{label} 必须是数组')
    result = {}
    for item in items:
        require(isinstance(item, dict) and isinstance(item.get('id'), str) and item['id'].strip(),
                f'{label} 需要非空 ID')
        require(item['id'] not in result, f'{label} ID 重复：{item["id"]}')
        result[item['id']] = item
    return result


def score(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 4


def note(root, value):
    require(isinstance(value, str) and value.strip(), '证据文件路径不能为空')
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()), '证据文件须在当前主题目录内')
    require(path.suffix.lower() == '.md' and path.is_file() and path.read_text(encoding='utf-8').strip(),
            f'需要已有、非空的 Markdown 记录：{value}')
    return path


def validate(data, root, as_of):
    require(data.get('schema_version') == 2, 'program schema_version 必须为 2')
    require(data.get('track') in TRACKS and str(data.get('topic', '')).strip(), '需要主题和有效学习分类')
    require(type(data.get('job_seeking', False)) is bool, 'job_seeking 须为布尔值')
    require(not data.get('job_seeking') or data['track'] == 'career', '职业求职用途须使用 career 分类')
    anchor = day(data['anchor_date'])
    recording_start = day(data.get('recording_started_on', data['anchor_date']))
    require(recording_start <= anchor, '记录开始日期不能晚于正式学习起点')
    cycle = data['cycle']
    start, end = day(cycle['start']), day(cycle['end'])
    require(anchor <= start <= end and end == month_end(start), '月周期边界不一致')
    require(cycle['plan_status'] in ('provisional', 'final'), '计划状态无效')
    expected = calendar_days(start, anchor, data['track'])
    require(len(cycle['days']) == len(expected), '月计划必须覆盖周期内每一天')
    for actual, planned in zip(cycle['days'], expected):
        for field in ('date', 'cycle_day', 'elapsed_day', 'refresh_required', 'audio_interview_due'):
            require(actual.get(field) == planned[field], f'日历字段不一致：{field}')
        require(actual.get('daily_test') is True and actual.get('radar') is True, '每日测试和雷达图须列入计划')
    axes = indexed(data['axes'], '维度')
    require(len(axes) == 6, '一个月内固定六个雷达维度')
    for axis in axes.values():
        require(isinstance(axis.get('label'), str) and axis['label'].strip() and
                len(axis.get('rubric', [])) == 5 and all(isinstance(x, str) and x.strip() for x in axis['rubric']),
                '每轴需要名称及 0–4 分锚点')
    evidence = indexed(data['evidence'], '证据')
    for item in evidence.values():
        require(recording_start <= day(item['date']) <= as_of, '证据日期不能在记录开始前或当前日期之后')
        note(root, item['answer_path']); note(root, item['feedback_path'])
        require(item.get('support') in SUPPORTS, '证据必须标明支持程度')
        require(isinstance(item.get('kind'), str) and item['kind'].strip(), '证据必须说明类型')
        require(item.get('score') is None or score(item['score']), '分数须为 0–4 或 null')
        require(isinstance(item.get('dimensions', {}), dict), 'dimensions 必须是字典')
        for key, value in item.get('dimensions', {}).items():
            require(key in axes and score(value), '雷达分数须关联既有维度且为 0–4')
        if item['kind'] == 'profile':
            require(item.get('score') is None and not item.get('dimensions'), '目标或条件回答不能当能力分')

    def refs(ids):
        require(isinstance(ids, list) and ids and len(ids) == len(set(ids)) and all(i in evidence for i in ids),
                '完成项必须关联真实且不重复的证据 ID')
        return [evidence[i] for i in ids]

    diagnosis = data['diagnosis']; rounds = diagnosis['rounds']
    require(isinstance(rounds, list) and len(rounds) <= 5, '诊断最多五轮')
    question_ids, finished = set(), True
    for number, current in enumerate(rounds, 1):
        require(finished and current['number'] == number, '前轮未答完或轮次顺序不一致')
        questions = current['questions']
        require(len(questions) == 4, '每轮恰好四题')
        finished = True
        for question in questions:
            require(question.get('id') and question['id'] not in question_ids and question.get('prompt'), '诊断题缺失或重复')
            question_ids.add(question['id'])
            require(question.get('kind') in ('profile', 'ability'), '诊断问题类型无效')
            eid = question.get('evidence_id')
            if eid is None:
                finished = False
            else:
                require(eid in evidence, '诊断回答必须关联证据')
                if question['kind'] == 'profile':
                    require(evidence[eid]['kind'] == 'profile', '条件问题须关联画像回答')
                else:
                    require(evidence[eid]['kind'] != 'profile' and evidence[eid].get('score') is not None,
                            '能力诊断需要实际评分的任务证据，不能用目标画像充数')
        if finished:
            require(current.get('summary'), '已完成的诊断轮需要反馈小结')
    complete = len(rounds) == 5 and finished
    require(diagnosis['status'] == ('complete' if complete else 'pending'), '诊断状态与真实回答不一致')
    require(cycle['plan_status'] != 'final' or complete, '五轮诊断未完成，只能标为暂定计划')
    if data.get('job_seeking') and cycle['plan_status'] == 'final':
        research = data.get('career_research')
        require(isinstance(research, dict) and research.get('status') == 'ready',
                '求职正式计划须先完成真实 JD 岗位调研；缺资料时保持暂定')
        require(isinstance(research.get('target_role'), str) and research['target_role'].strip(),
                '岗位调研需要明确目标职业')
        planned_on = day(cycle.get('planned_on', cycle['start']))
        require(day(research['researched_on']) <= planned_on <= as_of,
                '岗位调研须先于出计划，调研及计划日期不能在当前日期之后')
        note(root, research.get('report_path'))
        note(root, research.get('requirements_map_path'))
        channels = research.get('channels')
        require(isinstance(channels, dict) and all(
            channels.get(key) in ('read', 'partial', 'blocked', 'no-results')
            for key in ('boss', 'peer', 'official')),
            '求职计划须记录 BOSS、类似平台和大厂官网三渠道的实际尝试结果')
        require(any(channels[key] == 'read' for key in ('boss', 'peer', 'official')),
                '至少需有已完整阅读 JD 的渠道，摘要和官网首页不能充岗位证据')
        if any(channels[key] != 'read' for key in ('boss', 'peer', 'official')):
            require(isinstance(research.get('limitations'), str) and research['limitations'].strip(),
                    '岗位覆盖受限须说明未读渠道、目标范围和后续动作')
        job_ids = research.get('read_job_ids')
        require(isinstance(job_ids, list) and job_ids and
                all(isinstance(value, str) and value.strip() for value in job_ids) and
                len(job_ids) == len(set(job_ids)), '已读 JD 需要非空且去重的岗位 ID')
    used_answers = [q['evidence_id'] for r in rounds for q in r['questions'] if q.get('evidence_id')]
    require(len(used_answers) == len(set(used_answers)), '不能重复使用一份证据充多个诊断回答')
    stages = indexed(data['stages'], '阶段'); lessons = indexed(data['lessons'], '课程'); parts = indexed(data['parts'], '知识部分')
    for part in parts.values():
        require(part.get('stage_id') in stages, '知识部分需要所属阶段')
    for lesson in lessons.values():
        require(lesson.get('stage_id') in stages, '课程需要所属阶段')
        require(score(lesson.get('pass_score', 3)), '课程通过分无效')
        if cycle['plan_status'] == 'final':
            require(lesson.get('objective') and lesson.get('knowledge_point_ids') and lesson.get('practice') and
                    type(lesson.get('minutes')) is int and lesson['minutes'] > 0,
                    '正式课程需要目标、知识点、实践与时间预算')
    for planned in cycle['days']:
        require(all(i in lessons for i in planned['lesson_ids']), '日计划引用未知课程')
        if cycle['plan_status'] == 'final':
            require(planned['objective'].strip(), '正式月计划每天需要学习、复习或检验目标')
    completed = {}; daily_dates = set()
    for entry in data['daily']:
        date_str = entry['date']
        require(date_str not in daily_dates and anchor <= day(date_str) <= as_of, '日记录重复或日期无效')
        daily_dates.add(date_str)
        refresh = entry.get('refresh', {})
        if data['track'] == 'foundational':
            require(refresh.get('status') == 'not-required', '基础学科不做每日例行更新')
        elif entry.get('completed_lessons'):
            require(refresh.get('status') in ('complete', 'partial', 'failed'), '授新课前须有资料更新结果')
            note(root, refresh.get('web_log_path'))
            require(refresh.get('checked_on') == date_str, '资料更新须使用当天实际日期')
            if refresh['status'] == 'complete':
                require(refresh.get('doubao_status') == 'completed', '豆包未返回不能称更新流程全部完成')
                note(root, refresh.get('doubao_log_path'))
            else:
                require(refresh.get('reason'), '资料更新受限需要具体原因及可继续的稳定范围')
        for result in entry.get('completed_lessons', []):
            lid = result['lesson_id']
            require(lid in lessons and lid not in completed, '课程完成项重复或不存在')
            ev = refs(result['test_evidence_ids'])
            require(all(e['kind'] == 'daily-test' and e['date'] == date_str for e in ev), '课程完成需要当天日测证据')
            require(all(e['support'] == 'independent' and e.get('score') is not None and
                        e['score'] >= lessons[lid].get('pass_score', 3) for e in ev), '未独立通过日测不能记课程完成')
            completed[lid] = date_str
    assessments = indexed(data['assessments'], '检验')
    for item in assessments.values():
        require(item['type'] in ('interview', 'stage'), '检验类型无效')
        require(day(item['due_date']) >= anchor, '检验到期日不能早于学习开始')
        if item['type'] == 'interview':
            require((day(item['due_date']) - anchor).days % 10 == 9, '面试按实际开始日期每十天安排')
        require(item['status'] in ('planned', 'overdue', 'ready-for-voice', 'completed'), '检验状态无效')
        if item['status'] == 'completed':
            actual = item['actual_date']
            require(anchor <= day(actual) <= as_of, '检验实际日期无效')
            ev = refs(item['evidence_ids'])
            require(all(e['date'] == actual for e in ev), '检验证据日期不一致')
            note(root, item['retrospective_path'])
            if item['type'] == 'interview':
                require(day(actual) >= day(item['due_date']), '提前完成课程不能提前结清未来日历面试')
                require(item.get('mode') == 'audio' and item.get('voice_observed') is True and item.get('session_ref'),
                        '文字练习或未观察到双向语音不能完成音频面试')
                require(all(e['kind'] == 'interview' for e in ev), '音频面试需要对应面试证据')
            else:
                require(all(e['kind'] == 'stage-test' for e in ev), '阶段检验需要阶段试卷证据')
    for stage in stages.values():
        for lid in stage['lesson_ids']:
            require(lid in lessons and lessons[lid]['stage_id'] == stage['id'], '阶段课程关联错误')
        if stage.get('completed_on'):
            actual = stage['completed_on']
            require(anchor <= day(actual) <= as_of and all(lid in completed and completed[lid] <= actual for lid in stage['lesson_ids']),
                    '阶段不能早于必要课程完成')
            aid = stage.get('assessment_id'); assessment = assessments.get(aid, {})
            require(assessment.get('type') == 'stage' and assessment.get('status') == 'completed'
                    and assessment.get('actual_date') == actual, '阶段完成必须有当日整体检验与复盘')
    reviews = indexed(data['reviews'], '复习'); counts = {}; review_days = set()
    for item in sorted(reviews.values(), key=lambda x: (x['date'], x['id'])):
        pid = item['part_id']
        require(pid in parts and item['kind'] in ('routine', 'remedial'), '复习关联或类型错误')
        source_date = stages[parts[pid]['stage_id']].get('completed_on')
        require(source_date and day(source_date) < day(item['date']) <= as_of, '复习须在该部分初学完成之后')
        ev = refs(item['evidence_ids'])
        require(all(e['date'] == item['date'] and e['kind'] in ('review', 'remediation') for e in ev), '复习日期或证据类型不一致')
        if item['kind'] == 'routine':
            require((pid, item['date']) not in review_days, '同日同部分不能重复计常规复习')
            review_days.add((pid, item['date'])); counts[pid] = counts.get(pid, 0) + 1
            require(counts[pid] <= 3 and item['pass_number'] == counts[pid], '常规复习仅三遍且按顺序计数')
        else:
            require(item.get('trigger_gap_id'), '额外补缺需要关联已暴露缺口')
    gaps = indexed(data['gaps'], '缺口')
    for item in gaps.values():
        require(item['part_id'] in parts, '缺口需要关联既有知识部分')
        triggers = refs(item['trigger_evidence_ids'])
        require(item.get('reason') and item.get('supplement') and item.get('practice'), '复盘需要错因、补充内容与练习')
        require(item['status'] in ('open', 'resolved'), '缺口状态无效')
        if item['status'] == 'resolved':
            ev = refs(item['retest_evidence_ids'])
            require(all(e['kind'] == 'remediation' and e['support'] == 'independent' and
                        e.get('score') is not None and e['score'] >= 3 and
                        day(e['date']) >= max(day(t['date']) for t in triggers) for e in ev), '缺口未独立复测通过不能记解决')
    for item in reviews.values():
        if item['kind'] == 'remedial':
            require(item['trigger_gap_id'] in gaps and gaps[item['trigger_gap_id']]['part_id'] == item['part_id'], '补缺触发记录不一致')
    return {'valid': True, 'diagnosis_complete': complete, 'completed_lessons': len(completed),
            'routine_review_counts': counts, 'open_gaps': sum(g['status'] == 'open' for g in gaps.values())}


def radar_values(data, as_of):
    values = []
    for axis in data['axes']:
        matching = [e for e in data['evidence'] if e['support'] == 'independent' and
                    axis['id'] in e.get('dimensions', {}) and day(e['date']) <= as_of]
        latest = max((e['date'] for e in matching), default=None)
        records = [e for e in matching if e['date'] == latest] if latest else []
        values.append({'id': axis['id'], 'label': axis['label'], 'date': latest,
                       'value': sum(e['dimensions'][axis['id']] for e in records) / len(records) if records else None,
                       'evidence_ids': [e['id'] for e in records]})
    return values


def render_svg(values, title):
    cx, cy, radius = 350, 310, 155
    def xy(index, fraction):
        angle = -math.pi / 2 + index * math.tau / 6
        return (cx + radius * fraction * math.cos(angle), cy + radius * fraction * math.sin(angle))
    def points(items):
        return ' '.join(f'{x:.1f},{y:.1f}' for x, y in items)
    result = ['<svg xmlns="http://www.w3.org/2000/svg" width="700" height="620" viewBox="0 0 700 620" role="img">',
              f'<title>{html.escape(title)}</title>',
              '<rect width="700" height="620" rx="16" fill="#f8fafc"/>',
              '<g font-family="PingFang SC,Microsoft YaHei,sans-serif" font-size="15" fill="#0f172a">',
              f'<text x="350" y="36" text-anchor="middle" font-size="20">{html.escape(title)}</text>',
              '<text x="350" y="61" text-anchor="middle" fill="#64748b">0–4 分；灰色待测不等于零分</text>']
    for level in range(1, 5):
        result.append(f'<polygon points="{points(xy(i, level / 4) for i in range(6))}" fill="none" stroke="#cbd5e1"/>')
        result.append(f'<text x="{cx + 5}" y="{cy - radius * level / 4 - 3}" font-size="11" fill="#64748b">{level}</text>')
    for i, item in enumerate(values):
        x, y = xy(i, 1); lx, ly = xy(i, 1.32)
        result.append(f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="#cbd5e1"/>')
        value = '待测' if item['value'] is None else f'{item["value"]:.1f}'
        result.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle">{html.escape(item["label"])}</text>')
        result.append(f'<text x="{lx:.1f}" y="{ly + 21:.1f}" text-anchor="middle" fill="#64748b">{value}</text>')
    if all(v['value'] is not None for v in values):
        result.append(f'<polygon points="{points(xy(i, v["value"] / 4) for i, v in enumerate(values))}" fill="#2563eb" fill-opacity="0.14" stroke="#2563eb" stroke-width="2"/>')
    for i, item in enumerate(values):
        if item['value'] is not None:
            x, y = xy(i, item['value'] / 4)
            result.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#2563eb"/>')
    result.extend(['<text x="350" y="590" text-anchor="middle" fill="#64748b">分数取每轴最近一天的独立证据；详见同目录说明与原始回答</text>', '</g></svg>'])
    return '\n'.join(result)


def report(data, root, as_of, out):
    validate(data, root, as_of)
    require(not out.exists(), '报告目录已存在；请使用新的快照目录以保留历史')
    values = radar_values(data, as_of)
    title = f'{data["topic"]} · {as_of.isoformat()} 学习雷达'
    out.mkdir(parents=True)
    (out / '雷达图.svg').write_text(render_svg(values, title), encoding='utf-8')
    lines = [f'# {title}', '', '![学习雷达](雷达图.svg)', '',
             '分数为教学量表，来自每轴最近一天的独立表现。历史分保留原日期；未测不算零分。辅助表现单独记录，不抬高独立能力分。', '',
             '| 维度 | 分数 / 4 | 证据日期 | 独立证据 |', '|---|---|---|---|']
    evmap = indexed(data['evidence'], '证据')
    for item in values:
        value = '待测' if item['value'] is None else f'{item["value"]:.2f}'
        links = ', '.join(f'[{eid}]({os.path.relpath(root / evmap[eid]["answer_path"], out)})' for eid in item['evidence_ids']) or '无'
        lines.append(f'| {item["label"]} | {value} | {item["date"] or "—"} | {links} |')
    measured = sorted((v for v in values if v['value'] is not None), key=lambda x: x['value'])
    if len(measured) >= 2 and measured[0]['value'] < measured[-1]['value']:
        lines.extend(['', f'相对优势：{measured[-1]["label"]}。优先补强：{measured[0]["label"]}。只代表已测范围。'])
    else:
        lines.extend(['', '目前证据不足或各维度同分，暂不判定相对优势与劣势。'])
    missing = [v['label'] for v in values if v['value'] is None]
    if missing:
        lines.extend(['', '待补测：' + '、'.join(missing) + '。'])
    supported = [e['id'] for e in data['evidence'] if e['date'] == as_of.isoformat() and e['support'] != 'independent']
    lines.extend(['', '今日辅助练习：' + ('、'.join(supported) if supported else '无记录') + '。', '',
                  '下一步：教练依据薄弱轴、未测轴和开放缺口，写入当天学习笔记中的具体补练与复测，不仅罗列分数。'])
    (out / '雷达说明.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (out / '雷达数据.json').write_text(json.dumps(values, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'report': str(out / '雷达说明.md'), 'chart': str(out / '雷达图.svg')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    init = subs.add_parser('init')
    init.add_argument('--topic', required=True); init.add_argument('--track', choices=TRACKS, required=True)
    init.add_argument('--job-seeking', action='store_true', help='明确面向某职业求职时使用，须配合 --track career')
    init.add_argument('--date', required=True); init.add_argument('--out', type=Path, required=True)
    for name in ('validate', 'report'):
        sub = subs.add_parser(name); sub.add_argument('program', type=Path)
        sub.add_argument('--date', required=True, help='用户当地当前日期 YYYY-MM-DD')
        if name == 'report':
            sub.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'init':
            require(not args.out.exists(), '状态已存在，不能覆盖已有历史')
            data = initialize(args.topic, args.track, day(args.date), args.job_seeking)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x', encoding='utf-8') as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2); stream.write('\n')
            result = {'program': str(args.out), 'days': len(data['cycle']['days']), 'diagnosis': 'pending'}
        else:
            data = json.loads(args.program.read_text(encoding='utf-8'))
            root = args.program.resolve().parent
            result = validate(data, root, day(args.date)) if args.command == 'validate' else report(data, root, day(args.date), args.out)
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
