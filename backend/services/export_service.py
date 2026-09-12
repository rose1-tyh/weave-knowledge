"""知识导出服务 —— JSON / Markdown / Anki 卡片包"""

import hashlib
import os
import re
import tempfile

import genanki

from database import get_db
from services.domain_constants import type_label

# genanki 要求模型/牌组 ID 稳定（同 ID 升级时 Anki 视为同一模板，不会产生重复牌组）
_ANKI_MODEL_ID = 1607392319
_ANKI_MODEL = genanki.Model(
    _ANKI_MODEL_ID,
    "织识概念卡",
    fields=[{"name": "Question"}, {"name": "Answer"}, {"name": "Extra"}],
    templates=[{
        "name": "概念卡",
        "qfmt": "<div class='q'>{{Question}}</div>",
        "afmt": "{{FrontSide}}<hr id=answer><div class='a'>{{Answer}}</div>"
                "<br><div class='extra'>{{Extra}}</div>",
    }],
    css=".card{font-family:-apple-system,'Segoe UI','Noto Sans SC',sans-serif;"
        "font-size:16px;line-height:1.6;color:#222;background:#faf7f2;padding:16px}"
        ".q{font-size:22px;font-weight:600}.a{margin-top:8px}"
        ".extra{font-size:13px;color:#8a7f70;margin-top:12px}hr#answer{border:none;"
        "border-top:1px dashed #d8cfc0;margin:14px 0}",
)


def _sanitize_filename(title: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", title).strip() or "weave-deck"


class ExportService:

    @staticmethod
    async def export_json(paper_id: str) -> dict:
        """导出完整知识图谱为结构化 JSON"""
        db = await get_db()
        paper = await db.execute_fetchall(
            "SELECT id, title, page_count, upload_time FROM papers WHERE id = ?", [paper_id])
        if not paper:
            return None
        p = dict(paper[0])
        c_rows = await db.execute_fetchall("SELECT * FROM concepts WHERE paper_id = ?", [paper_id])
        r_rows = await db.execute_fetchall("SELECT * FROM relations WHERE paper_id = ?", [paper_id])

        concepts = [dict(r) for r in c_rows]
        relations = [dict(r) for r in r_rows]
        # slug → 概念名（关系列存 slug，导出时转回可读名称）
        slug_to_name = {c["slug"]: c["name"] for c in concepts}

        return {
            "paper": {
                "id": p["id"],
                "title": p["title"],
                "page_count": p["page_count"],
                "upload_time": p["upload_time"],
            },
            "concepts": [
                {"name": c["name"], "definition": c["definition"], "type": c["type"], "page": c["page"]}
                for c in concepts
            ],
            "relations": [
                {"source": slug_to_name.get(r["source_slug"], r["source_slug"]),
                 "target": slug_to_name.get(r["target_slug"], r["target_slug"]),
                 "type": r["type"], "evidence": r["evidence"]}
                for r in relations
            ],
        }

    @staticmethod
    async def export_markdown(paper_id: str) -> str:
        """导出知识摘要为 Markdown"""
        data = await ExportService.export_json(paper_id)
        if not data:
            return ""

        lines = [
            f"# {data['paper']['title']}",
            "",
            "> 由「织识」知识重构引擎自动生成",
            "",
            "## 核心概念",
            "",
        ]
        for c in data["concepts"]:
            lines.append(f"- **{c['name']}** [{c['type']}] — {c['definition']} _(第{c['page']}页)_")

        lines.extend(["", "## 概念关系", ""])
        for r in data["relations"]:
            lines.append(f"- **{r['source']}** → **{r['target']}** ({r['type']})")
            if r["evidence"]:
                lines.append(f"  > {r['evidence']}")

        return "\n".join(lines)

    @staticmethod
    async def export_anki(paper_id: str) -> tuple[bytes, str] | None:
        """导出 Anki 卡片包（.apkg）。

        正面 = 概念名；背面 = 定义；Extra = 类型/页码/原文证据/关联关系。
        牌组 ID 由 paper_id 哈希派生（稳定），重复导出导入不会生成重复牌组。
        """
        db = await get_db()
        paper = await db.execute_fetchall("SELECT id, title FROM papers WHERE id = ?", [paper_id])
        if not paper:
            return None
        title = paper[0]["title"]
        concepts = [dict(r) for r in await db.execute_fetchall(
            "SELECT slug, name, definition, type, page, evidence FROM concepts WHERE paper_id = ?",
            [paper_id])]
        if not concepts:
            return None
        relations = [dict(r) for r in await db.execute_fetchall(
            "SELECT source_slug, target_slug, type FROM relations WHERE paper_id = ?", [paper_id])]
        slug_to_name = {c["slug"]: c["name"] for c in concepts}
        rel_by_concept: dict[str, list] = {}
        for r in relations:
            src_name = slug_to_name.get(r["source_slug"], r["source_slug"])
            tgt_name = slug_to_name.get(r["target_slug"], r["target_slug"])
            rel_by_concept.setdefault(r["source_slug"], []).append((src_name, "→", tgt_name, r["type"]))
            rel_by_concept.setdefault(r["target_slug"], []).append((src_name, "←", tgt_name, r["type"]))

        deck = genanki.Deck(
            int(hashlib.md5(f"weave:{paper_id}".encode()).hexdigest()[:12], 16),
            f"织识::{title}",
        )
        for c in concepts:
            extra_parts = [f"类型：{type_label(c['type'])}"]
            if c["page"]:
                extra_parts.append(f"第 {c['page']} 页")
            if c["evidence"]:
                extra_parts.append(f"原文：{c['evidence']}")
            for src, arrow, tgt, rtype in rel_by_concept.get(c["slug"], [])[:5]:
                extra_parts.append(f"关联：{src} {arrow} {tgt}（{rtype}）")
            deck.add_note(genanki.Note(
                model=_ANKI_MODEL,
                fields=[c["name"], c["definition"] or "（暂无定义）", "<br>".join(extra_parts)],
                tags=[c["type"], "织识"],
            ))

        filename = f"{_sanitize_filename(title)}.apkg"
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "deck.apkg")
            genanki.Package(deck).write_to_file(path)
            with open(path, "rb") as f:
                return f.read(), filename
