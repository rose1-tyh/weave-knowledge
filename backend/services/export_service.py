"""知识导出服务"""

from database import get_db


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
