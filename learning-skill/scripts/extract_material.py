#!/usr/bin/env python3
"""Extract local DOCX/TXT/Markdown without uploading or altering the source."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TIME = re.compile(r"^(?:发言人[^\n]*?\s+)?((?:\d{1,2}:)?\d{1,2}:\d{2})\s*$")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(source):
    media = []
    if source.suffix.lower() == ".docx":
        with ZipFile(source) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
            paragraphs = []
            for index, para in enumerate(root.iter(W + "p"), 1):
                parts = []
                for node in para.iter():
                    if node.tag == W + "t":
                        parts.append(node.text or "")
                    elif node.tag == W + "tab":
                        parts.append("\t")
                    elif node.tag in {W + "br", W + "cr"}:
                        parts.append("\n")
                text = "".join(parts)
                if text.strip():
                    paragraphs.append({"id": f"P{index:04d}", "text": text})
            media = [{"name": item.filename, "bytes": item.file_size}
                     for item in archive.infolist()
                     if item.filename.startswith("word/media/") and not item.is_dir()]
    elif source.suffix.lower() in {".md", ".txt", ".markdown"}:
        paragraphs = [{"id": f"L{index:04d}", "text": line}
                      for index, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1)
                      if line.strip()]
    else:
        raise ValueError("支持 .docx、.md、.txt；视频、PDF 或网页需先用相应工具提取。")
    timestamp = None
    for paragraph in paragraphs:
        match = TIME.fullmatch(paragraph["text"].strip())
        if match:
            timestamp = match.group(1)
        paragraph["timestamp"] = timestamp
    return paragraphs, media


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    # Each run gets its own directory: never replace previous extraction evidence.
    out = args.out.resolve()
    if any((out / name).exists() for name in ("source.json", "source.md")):
        parser.error("输出已存在；请选新的运行目录，以保留之前的提取证据。")
    try:
        paragraphs, media = extract(source)
        if not paragraphs:
            parser.error("未提取到文字；可能需要 OCR 或其他工具，不能当作已读完整材料。")
    except (ValueError, ET.ParseError) as error:
        parser.error(str(error))
    data = {"schema_version": 1, "source_id": "source-1", "source": str(source),
            "sha256": digest(source), "paragraph_count": len(paragraphs),
            "character_count": sum(len(p["text"]) for p in paragraphs),
            "embedded_media": media, "coverage": "word/document.xml" if source.suffix.lower() == ".docx" else "all text lines",
            "limitations": "文稿文字不等于视频画面或图像文字已核对；Word 页眉页脚与批注未提取。",
            "paragraphs": paragraphs}
    out.mkdir(parents=True, exist_ok=True)
    (out / "source.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"# 原文提取 {source.name}", "", f"SHA-256：`{data['sha256']}`", ""]
    for paragraph in paragraphs:
        lines.extend([f"### {paragraph['id']}", "", f"时间：{paragraph['timestamp'] or '未标注'}", "", paragraph["text"], ""])
    (out / "source.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({key: data[key] for key in ("source", "sha256", "paragraph_count", "character_count")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
