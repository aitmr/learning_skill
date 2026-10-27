#!/usr/bin/env python3
"""Store real learning evidence and export flashcards; Python standard library only."""

import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

INTERVALS = (1, 3, 7, 14, 30)
KINDS = ("diagnostic", "recall", "explanation", "application", "map")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def card_hash(cards):
    value = json.dumps(cards, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def validate_cards(cards, source=None):
    if not isinstance(cards, list) or not cards:
        raise ValueError("cards 必须是非空数组。")
    ids = set()
    paragraph_map = {p["id"]: p for p in source["paragraphs"]} if source else None
    for card in cards:
        for field in ("id", "concept", "question", "answer"):
            if not isinstance(card.get(field), str) or not card[field].strip():
                raise ValueError(f"卡片缺少非空字段 {field}。")
        if card["id"] in ids:
            raise ValueError(f"卡片 ID 重复：{card['id']}")
        ids.add(card["id"])
        if card.get("origin") not in {"material", "supplement", "design"}:
            raise ValueError(f"{card['id']} 需要 origin：material、supplement 或 design。")
        if not isinstance(card.get("tags", []), list) or not all(isinstance(t, str) for t in card.get("tags", [])):
            raise ValueError("tags 必须是字符串数组。")
        if card["origin"] == "material" and not card.get("source_refs"):
            raise ValueError(f"{card['id']} 的原文知识需要 source_refs。")
        for ref in card.get("source_refs", []):
            if not isinstance(ref, dict) or not ref.get("paragraph_id"):
                raise ValueError(f"{card['id']} 的来源引用格式错误。")
            if paragraph_map is not None:
                para = paragraph_map.get(ref["paragraph_id"])
                if para is None:
                    raise ValueError(f"无效段落引用：{ref['paragraph_id']}")
                if ref.get("timestamp") != para.get("timestamp"):
                    raise ValueError(f"{ref['paragraph_id']} 的时间戳与原文不符。")


def verify_state(state, cards):
    if state.get("schema_version") != 1 or state.get("cards_sha256") != card_hash(cards):
        raise ValueError("状态版本或题库不匹配；请保留旧记录，为新题库另建状态。")
    if set(state.get("cards", {})) != {c["id"] for c in cards}:
        raise ValueError("状态中的题目与题库不一致。")


def initialize(args, cards):
    if args.state.exists():
        raise ValueError("状态文件已存在；请续用记录或选择新的路径，不能覆盖成绩。")
    today = date.fromisoformat(args.date)
    data = {"schema_version": 1, "topic": args.topic, "goal": args.goal,
            "started_on": today.isoformat(), "cards_sha256": card_hash(cards),
            "learner_level": "unknown", "diagnosis_status": "pending",
            "review_policy": args.review_policy or "legacy-intervals",
            "next_action": args.next_action,
            "cards": {c["id"]: {"status": "untested", "success_streak": 0,
                                    "next_due": None, "attempts": []} for c in cards}}
    write_json(args.state, data)
    return {"state": str(args.state), "cards": len(cards), "attempts": 0, "learner_level": "unknown"}


def record(args, cards):
    state = read_json(args.state)
    verify_state(state, cards)
    if args.card not in state["cards"]:
        raise ValueError("card 不在当前题库中。")
    answer = args.answer_file.read_text(encoding="utf-8").strip()
    feedback = args.feedback_file.read_text(encoding="utf-8").strip()
    if not answer or not feedback:
        raise ValueError("回答和反馈都需要实际内容；不能保存空白或未作答记录。")
    today = date.fromisoformat(args.date)
    card = state["cards"][args.card]
    dates = [state["started_on"]] + [x["date"] for x in card["attempts"]]
    if today < date.fromisoformat(max(dates)):
        raise ValueError("作答日期不能早于学习开始或这道题已有的作答。")
    policy = args.review_policy or state.get("review_policy", "legacy-intervals")
    if state.get("review_policy", "legacy-intervals") != policy:
        if policy != "stage-three":
            raise ValueError("月度阶段复习不能自动切回旧间隔；请保留历史并明确迁移。")
        state.setdefault("review_policy_history", []).append({
            "changed_on": today.isoformat(), "from": state.get("review_policy", "legacy-intervals"),
            "to": policy, "previous_due": {key: value.get("next_due") for key, value in state["cards"].items()}})
        for progress in state["cards"].values():
            progress["next_due"] = None
    state["review_policy"] = policy
    # Multiple attempts on one day do not count as spaced-repetition successes.
    already_passed_today = any(a["date"] == today.isoformat() and a["score"] >= 3
                               and a["support"] == "independent" for a in card["attempts"])
    if args.score < 3:
        card["success_streak"] = 0
        card["status"] = "needs_review"
        delay = INTERVALS[0]
    elif args.support != "independent":
        card["status"] = "practiced_with_support"
        delay = INTERVALS[0]
    else:
        if not already_passed_today or card["success_streak"] == 0:
            card["success_streak"] += 1
        passed_application = args.kind == "application" or any(
            a["score"] >= 3 and a["kind"] == "application" and a["support"] == "independent"
            for a in card["attempts"])
        card["status"] = "application_evidence" if passed_application else "recalled"
        delay = INTERVALS[min(card["success_streak"] - 1, len(INTERVALS) - 1)]
    card["next_due"] = (today + timedelta(days=delay)).isoformat() if policy == "legacy-intervals" else None
    card["attempts"].append({"date": today.isoformat(), "kind": args.kind, "score": args.score,
                             "answer": answer, "feedback": feedback,
                             "support": args.support, "evidence_file": str(args.answer_file.resolve())})
    state["next_action"] = (f"复习 {args.card}，计划日期 {card['next_due']}；结合本次反馈决定下一项练习。"
                            if policy == "legacy-intervals" else
                            f"{args.card} 的真实证据已保存；按 program.json 的阶段三遍复习和缺口队列续学。")
    write_json(args.state, state)
    return {"card": args.card, "status": card["status"], "next_due": card["next_due"],
            "note": "题目证据已保存；整体能力级别需教练另行诊断。"}


def export(args, cards):
    state = read_json(args.state)
    verify_state(state, cards)
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "flashcards.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        for card in cards:
            tags = [tag.replace(" ", "_") for tag in card.get("tags", [])]
            writer.writerow([card["question"], card["answer"], " ".join(tags)])
    with (args.out / "review_schedule.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["card_id", "concept", "status", "next_due", "attempts"])
        for card in cards:
            progress = state["cards"][card["id"]]
            writer.writerow([card["id"], card["concept"], progress["status"],
                             progress["next_due"] or "", len(progress["attempts"])])
    return {"flashcards": str(args.out / "flashcards.csv"),
            "schedule": str(args.out / "review_schedule.csv"),
            "untested": sum(c["status"] == "untested" for c in state["cards"].values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "init", "record", "export"):
        sub = subs.add_parser(command)
        sub.add_argument("--cards", type=Path, required=True)
        if command == "validate":
            sub.add_argument("--source", type=Path)
        else:
            sub.add_argument("--state", type=Path, required=True)
        if command == "init":
            sub.add_argument("--topic", required=True)
            sub.add_argument("--goal", required=True)
            sub.add_argument("--date", required=True, help="用户当地日期 YYYY-MM-DD")
            sub.add_argument("--next-action", default="开始第一轮四道诊断题，等待用户回答。")
            sub.add_argument("--review-policy", choices=("legacy-intervals", "stage-three"))
        elif command == "record":
            sub.add_argument("--review-policy", choices=("legacy-intervals", "stage-three"))
            sub.add_argument("--card", required=True)
            sub.add_argument("--date", required=True)
            sub.add_argument("--score", type=int, choices=range(5), required=True)
            sub.add_argument("--kind", choices=KINDS, required=True)
            sub.add_argument("--support", choices=("independent", "hinted", "reference", "ai-assisted"), required=True)
            sub.add_argument("--answer-file", type=Path, required=True)
            sub.add_argument("--feedback-file", type=Path, required=True)
        elif command == "export":
            sub.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        cards = read_json(args.cards)
        source = read_json(args.source) if args.command == "validate" and args.source else None
        validate_cards(cards, source)
        if args.command == "validate":
            result = {"valid": True, "cards": len(cards), "source_checked": source is not None}
        else:
            result = {"init": initialize, "record": record, "export": export}[args.command](args, cards)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
