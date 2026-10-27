#!/usr/bin/env python3
"""Validate evidence/dependencies and export a learning handoff; does not search the web."""

import argparse
import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PRIMARY = {"official-docs", "original-paper", "primary-record", "textbook", "user-material"}
KINDS = PRIMARY | {"review", "tutorial", "secondary"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def items(value, name):
    require(isinstance(value, list), f"{name} 必须是数组。")
    return value


def index(packet, field):
    result = {}
    for row in items(packet.get(field), field):
        require(isinstance(row, dict) and nonempty(row.get("id")), f"{field} 缺少 ID。")
        require(row["id"] not in result, f"{field} ID 重复：{row['id']}")
        result[row["id"]] = row
    return result


def canonical_url(url):
    require(nonempty(url), "来源 URL 不能为空。")
    parts = urlsplit(url)
    require(parts.scheme in {"http", "https"} and parts.netloc and not parts.username,
            f"来源 URL 格式无效：{url}")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/",
                       urlencode(sorted(query)), ""))


def validate(packet, base):
    require(isinstance(packet, dict) and packet.get("schema_version") == 1, "知识包版本应为 1。")
    topic = packet.get("topic", {})
    for field in ("keyword", "resolved_topic", "scope", "as_of"):
        require(nonempty(topic.get(field)), f"topic 缺少 {field}。")
    as_of = date.fromisoformat(topic["as_of"])
    for field in ("assumptions", "excluded"):
        require(all(nonempty(v) for v in items(topic.get(field), field)), f"{field} 含空项。")
    sources, claims, points = (index(packet, f) for f in ("sources", "claims", "knowledge_points"))
    queries, gaps = (index(packet, f) for f in ("queries", "gaps"))
    require(sources and claims and points, "来源、事实和知识点都不能是空的。")
    urls = set()
    for sid, source in sources.items():
        for field in ("title", "publisher", "origin_family", "reading_scope", "notes_path"):
            require(nonempty(source.get(field)), f"{sid} 缺少 {field}。")
        url = canonical_url(source.get("url"))
        require(url not in urls, f"重复来源（参数或锚点不能增加来源数）：{sid}")
        urls.add(url)
        require(source.get("kind") in KINDS, f"{sid} 的来源类型无效。")
        require(source.get("read_status") in {"read", "partial", "unread", "failed"}, f"{sid} 读取状态无效。")
        accessed = date.fromisoformat(source["accessed_on"])
        require(accessed <= as_of, f"{sid} 查阅日期不能晚于知识包日期。")
        if source.get("published_on") is not None:
            date.fromisoformat(source["published_on"])
        locators = items(source.get("covered_locators"), "covered_locators")
        require(all(nonempty(v) for v in locators), f"{sid} 的定位包含空项。")
        if source["read_status"] in {"read", "partial"}:
            require(locators, f"{sid} 已读取但没有记录覆盖范围。")
        relative = Path(source["notes_path"])
        note = (base / relative).resolve()
        require(not relative.is_absolute() and note.is_relative_to(base.resolve()), f"{sid} 笔记必须在知识包目录中。")
        require(note.is_file() and note.read_text(encoding="utf-8").strip(), f"{sid} 阅读笔记不存在或为空。")
    for qid, query in queries.items():
        require(nonempty(query.get("query")) and nonempty(query.get("purpose")), f"{qid} 查询内容不完整。")
        require(query.get("status") in {"executed", "no-results", "planned"}, f"{qid} 查询状态无效。")
        ids = items(query.get("source_ids"), "source_ids")
        require(all(s in sources for s in ids), f"{qid} 关联未知来源。")
        require(query["status"] == "executed" or not ids, f"{qid} 未获得结果却关联已选来源。")
    for cid, claim in claims.items():
        require(nonempty(claim.get("statement")), f"{cid} 陈述为空。")
        verification = claim.get("verification")
        require(verification in {"primary-source", "corroborated", "qualified", "pending"}, f"{cid} 核对状态无效。")
        evidence = items(claim.get("evidence"), "evidence")
        require(verification == "pending" or evidence, f"{cid} 已确认事实缺少证据。")
        families, kinds = set(), set()
        for ref in evidence:
            require(isinstance(ref, dict) and ref.get("source_id") in sources, f"{cid} 引用未知来源。")
            source = sources[ref["source_id"]]
            require(source["read_status"] in {"read", "partial"}, f"{cid} 使用未读取或失败来源。")
            require(ref.get("locator") in source["covered_locators"], f"{cid} 引用超出实际读取范围。")
            require(nonempty(ref.get("note")), f"{cid} 缺少证据说明。")
            families.add(source["origin_family"])
            kinds.add(source["kind"])
        if verification == "corroborated":
            require(len(families) >= 2, f"{cid} 同源转载不能算独立交叉证据。")
        if verification == "primary-source":
            require(kinds & PRIMARY, f"{cid} 缺少直接原始依据。")
    for kid, point in points.items():
        for field in ("title", "objective", "explanation", "example", "misconception", "boundary", "check_question"):
            require(nonempty(point.get(field)), f"{kid} 缺少 {field}。")
        require(point.get("status") in {"ready", "blocked"}, f"{kid} 状态无效。")
        require(point.get("priority") in {"core", "supporting", "later"}, f"{kid} 优先级无效。")
        criteria = items(point.get("answer_criteria"), "answer_criteria")
        require(criteria and all(nonempty(v) for v in criteria), f"{kid} 缺少回答检查要点。")
        deps, cids = (items(point.get(f), f) for f in ("prerequisites", "claim_ids"))
        require(all(d in points and d != kid for d in deps), f"{kid} 前置知识无效。")
        require(cids and all(c in claims for c in cids), f"{kid} 事实引用为空或不存在。")
        if point["status"] == "ready":
            require(all(claims[c]["verification"] != "pending" for c in cids), f"{kid} 未证实内容不能进入教学。")
            require(all(points[d]["status"] == "ready" for d in deps), f"{kid} 前置知识尚未可教。")
    visiting, visited = set(), set()

    def visit(kid):
        require(kid not in visiting, "知识点的前置关系存在循环。")
        if kid in visited:
            return
        visiting.add(kid)
        for dep in points[kid]["prerequisites"]:
            visit(dep)
        visiting.remove(kid)
        visited.add(kid)

    for kid in points:
        visit(kid)
    ready = {k for k, p in points.items() if p["status"] == "ready"}
    handoff = packet.get("handoff", {})
    order = items(handoff.get("teaching_order"), "teaching_order")
    require(len(order) == len(set(order)) and set(order) == ready, "教学顺序应包含且仅包含全部 ready 知识点。")
    seen = set()
    for kid in order:
        require(set(points[kid]["prerequisites"]) <= seen, f"{kid} 排在前置知识之前。")
        seen.add(kid)
    require(nonempty(handoff.get("first_diagnostic_question")), "缺少首道诊断题。")
    dimensions = set()
    for row in items(packet.get("coverage"), "coverage"):
        require(nonempty(row.get("dimension")) and row["dimension"] not in dimensions, "覆盖方向为空或重复。")
        dimensions.add(row["dimension"])
        require(row.get("status") in {"covered", "gap", "not-needed"}, "覆盖状态无效。")
        ids = items(row.get("knowledge_point_ids"), "knowledge_point_ids")
        require(all(k in points for k in ids), "覆盖地图引用未知知识点。")
        require(nonempty(row.get("reason")), "覆盖地图需说明范围或缺口。")
        if row["status"] == "covered":
            require(ids and set(ids) <= ready, "已覆盖方向必须关联可教知识点。")
    require(dimensions, "缺少覆盖地图。")
    for gid, gap in gaps.items():
        require(nonempty(gap.get("description")) and nonempty(gap.get("next_query")), f"{gid} 缺口说明不完整。")
        require(all(k in points for k in items(gap.get("affected_knowledge_point_ids"), "affected_knowledge_point_ids")), f"{gid} 引用未知知识点。")
    return {"valid_structure": True, "sources": len(sources), "claims": len(claims),
            "knowledge_points": len(points), "ready": len(ready), "blocked": len(points) - len(ready),
            "fact_check": "需人工核对陈述和证据；脚本不验证网页事实真伪。"}


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def export(packet, path, out):
    sources, claims, points = ({r["id"]: r for r in packet[f]} for f in ("sources", "claims", "knowledge_points"))
    order = packet["handoff"]["teaching_order"]
    require(order, "没有可教知识点；先交付待查事项，不能生成教学卡。")
    cards, detail = [], ["# 知识点明细", "", "包含回答要点，供教练按需读取。现场诊断先只呈现问题。", ""]
    for kid in order:
        p = points[kid]
        refs = [{"claim_id": cid, "source_id": e["source_id"], "url": sources[e["source_id"]]["url"], "locator": e["locator"]}
                for cid in p["claim_ids"] for e in claims[cid]["evidence"]]
        cards.append({"id": kid, "knowledge_point_id": kid, "concept": p["title"],
                      "question": p["check_question"], "answer": "；".join(p["answer_criteria"]),
                      "answer_criteria": p["answer_criteria"], "origin": "supplement", "source_refs": [],
                      "external_refs": refs, "tags": [packet["topic"]["keyword"], p["priority"]]})
        detail.extend([f"## {kid} {p['title']}", "", f"目标：{p['objective']}", "",
                       p["explanation"], "", f"前置：{', '.join(p['prerequisites']) or '无'}", "",
                       f"教学设计例子：{p['example']}", "", f"教学设计误区：{p['misconception']}", "",
                       f"边界：{p['boundary']}", "", f"检查问题：{p['check_question']}", "",
                       "回答要点：" + "；".join(p["answer_criteria"]), ""])
        for ref in refs:
            detail.append(f"依据 {ref['claim_id']}：[{sources[ref['source_id']]['title']}]({ref['url']})，{ref['locator']}。")
        detail.append("")
    out.mkdir(parents=True, exist_ok=True)
    card_file = out / "cards.json"
    if card_file.exists():
        require(json.loads(card_file.read_text(encoding="utf-8")) == cards,
                "已有题库内容不同；请另建 revision 目录，保留旧题库和作答历史。")
    catalog = ["# 资料索引", "", f"主题：{packet['topic']['resolved_topic']}；查阅截至 {packet['topic']['as_of']}。", ""]
    for source in sources.values():
        catalog.extend([f"## {source['id']} {source['title']}", "", f"[原始来源]({source['url']})", "",
                        f"发布者：{source['publisher']}；类型：{source['kind']}；出版日期：{source.get('published_on') or '未注明'}。", "",
                        f"已读范围：{source['reading_scope']}；状态：{source['read_status']}。", "",
                        f"证据分组：{source['origin_family']}；查阅：{source['accessed_on']}。", ""])
    graph = ["# 知识地图", "", f"范围：{packet['topic']['scope']}", "", "这是教学参考结构，用户掌握情况尚待诊断。", "",
             "| 顺序 | 知识点 | 优先级 | 前置 | 学习行为 |", "|---|---|---|---|---|"]
    for i, kid in enumerate(order, 1):
        p = points[kid]
        graph.append(f"| {i} | {kid} {p['title']} | {p['priority']} | {', '.join(p['prerequisites']) or '无'} | {p['objective']} |")
    graph.extend(["", "## 覆盖与待查", ""])
    for row in packet["coverage"]:
        graph.append(f"- {row['dimension']}：{row['status']}；{row['reason']}")
    for kid, p in points.items():
        if p["status"] == "blocked":
            graph.append(f"- {kid} {p['title']}：待核对，不进入当前教学。")
    gaps = ["# 待核对事项", "", "结构核对不能替代事实核对；未读内容和代码运行效果不视为已验证。", ""]
    for gap in packet["gaps"]:
        gaps.extend([f"## {gap['id']}", "", gap["description"], "", f"下一项查询：{gap['next_query']}", ""])
    if not packet["gaps"]:
        gaps.append("当前范围未记录未解决缺口；不代表整个领域没有未知部分。")
    handoff = {"schema_version": 1, "keyword": packet["topic"]["keyword"],
               "topic": packet["topic"]["resolved_topic"], "scope": packet["topic"]["scope"],
               "packet_path": str(path.resolve()), "cards_path": str(card_file.resolve()),
               "teaching_order": order, "first_diagnostic_question": packet["handoff"]["first_diagnostic_question"],
               "learner_level": "unknown", "diagnosis_status": "pending",
               "learning_protocol": {"diagnosis_rounds": 5, "questions_per_round": 4,
                                     "plan_period": "calendar-month", "routine_reviews_per_part": 3,
                                     "career_plan_requires_job_research": True},
               "gap_ids": [g["id"] for g in packet["gaps"]], "next_skill": "learning-skill"}
    files = {"资料索引.md": "\n".join(catalog), "知识地图.md": "\n".join(graph) + "\n",
             "知识点明细.md": "\n".join(detail), "待核对事项.md": "\n".join(gaps),
             "cards.json": json_text(cards), "handoff.json": json_text(handoff)}
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
    return {"files": len(files), "cards": len(cards), "handoff": str(out / "handoff.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "export"))
    parser.add_argument("packet", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
        result = validate(packet, args.packet.parent)
        if args.command == "export":
            require(args.out is not None, "export 需要 --out。")
            result.update(export(packet, args.packet, args.out))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
