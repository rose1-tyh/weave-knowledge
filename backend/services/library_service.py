"""知识库论文管理服务"""

from datetime import datetime
from database import get_db


class LibraryService:

    @staticmethod
    async def list_papers(search: str = "", sort: str = "upload_time", page: int = 1, size: int = 50) -> dict:
        db = await get_db()
        where = ""
        params = []
        if search:
            where = "WHERE title LIKE ?"
            params.append(f"%{search}%")
        order = "ORDER BY upload_time DESC" if sort == "upload_time" else "ORDER BY title ASC"
        offset = (page - 1) * size

        rows = await db.execute_fetchall(
            f"SELECT * FROM papers {where} {order} LIMIT ? OFFSET ?",
            params + [size, offset]
        )
        papers = [dict(r) for r in rows]

        # 统计
        total_row = await db.execute_fetchall(f"SELECT COUNT(*) as cnt FROM papers {where}", params)
        total = total_row[0]["cnt"] if total_row else 0

        return {"papers": papers, "total": total}

    @staticmethod
    async def get_paper(paper_id: str) -> dict | None:
        db = await get_db()
        row = await db.execute_fetchall("SELECT * FROM papers WHERE id = ?", [paper_id])
        if not row:
            return None
        paper = dict(row[0])
        # 统计概念/关系数
        c = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM concepts WHERE paper_id = ?", [paper_id])
        r = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM relations WHERE paper_id = ?", [paper_id])
        paper["concept_count"] = c[0]["cnt"] if c else 0
        paper["relation_count"] = r[0]["cnt"] if r else 0
        return paper

    @staticmethod
    async def update_paper(paper_id: str, data: dict):
        db = await get_db()
        updates = []
        params = []
        for key in ["title", "tags", "notes"]:
            if key in data:
                updates.append(f"{key} = ?")
                params.append(data[key])
        if updates:
            params.append(paper_id)
            await db.execute(f"UPDATE papers SET {', '.join(updates)} WHERE id = ?", params)
            await db.commit()

    @staticmethod
    async def delete_paper(paper_id: str):
        db = await get_db()
        await db.execute("DELETE FROM relations WHERE paper_id = ?", [paper_id])
        await db.execute("DELETE FROM concepts WHERE paper_id = ?", [paper_id])
        await db.execute("DELETE FROM papers WHERE id = ?", [paper_id])
        await db.commit()

    @staticmethod
    async def create_paper(paper_id: str, title: str, filename: str, page_count: int, text_length: int):
        db = await get_db()
        now = datetime.now().isoformat()
        await db.execute(
            "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            [paper_id, title, filename, page_count, text_length, now]
        )
        await db.commit()

    @staticmethod
    async def update_extract_status(paper_id: str, status: str, concept_count: int = 0, relation_count: int = 0):
        db = await get_db()
        now = datetime.now().isoformat()
        await db.execute(
            "UPDATE papers SET extract_status = ?, extract_time = ?, concept_count = ?, relation_count = ? WHERE id = ?",
            [status, now, concept_count, relation_count, paper_id]
        )
        await db.commit()

    @staticmethod
    async def get_stats() -> dict:
        db = await get_db()
        pc = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM papers", [])
        cc = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM concepts", [])
        rc = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM relations", [])
        return {
            "paperCount": pc[0]["cnt"] if pc else 0,
            "conceptCount": cc[0]["cnt"] if cc else 0,
            "relationCount": rc[0]["cnt"] if rc else 0,
        }

    @staticmethod
    async def save_concepts(paper_id: str, concepts: list[dict]):
        db = await get_db()
        now = datetime.now().isoformat()
        for c in concepts:
            await db.execute(
                "INSERT OR REPLACE INTO concepts "
                "(paper_id, slug, name, definition, type, page, evidence, confidence, confidence_ai, status, created_by, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ai', ?, ?)",
                [paper_id, c["id"], c["name"], c["definition"], c["type"], c["page"],
                 c.get("evidence", ""), c.get("confidence", 0.5), c.get("confidence_ai"),
                 c.get("status", "pending"), now, now]
            )
        await db.commit()

    @staticmethod
    async def save_relations(paper_id: str, relations: list[dict]):
        db = await get_db()
        now = datetime.now().isoformat()
        for r in relations:
            await db.execute(
                "INSERT INTO relations "
                "(paper_id, source_slug, target_slug, type, evidence, page, confidence, confidence_ai, status, created_by, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ai', ?, ?)",
                [paper_id, r["source"], r["target"], r["type"], r.get("evidence", ""),
                 r.get("page"), r.get("confidence", 0.5), r.get("confidence_ai"),
                 r.get("status", "pending"), now, now]
            )
        await db.commit()

    @staticmethod
    async def update_paper_text(paper_id: str, text: str):
        db = await get_db()
        await db.execute("UPDATE papers SET text = ? WHERE id = ?", [text, paper_id])
        await db.commit()

    @staticmethod
    async def get_graph_data(paper_id: str) -> dict | None:
        db = await get_db()
        paper = await LibraryService.get_paper(paper_id)
        if not paper:
            return None
        c_rows = await db.execute_fetchall("SELECT * FROM concepts WHERE paper_id = ?", [paper_id])
        r_rows = await db.execute_fetchall("SELECT * FROM relations WHERE paper_id = ?", [paper_id])

        type_colors = {
            "method": "#e8453c", "theory": "#8b5cf6", "dataset": "#10b981",
            "finding": "#f59e0b", "tool": "#00d4ff",
        }
        rel_colors = {
            "supports": "#10b981", "contradicts": "#e8453c", "extends": "#f59e0b",
            "cites": "#6b7280", "uses": "#00d4ff",
        }

        concepts = [dict(r) for r in c_rows]
        relations = [dict(r) for r in r_rows]

        # name → slug 映射
        name_to_slug = {c["name"]: c["slug"] for c in concepts}

        nodes = [{
            "id": c["slug"],
            "name": c["name"],
            "definition": c["definition"],
            "type": c["type"],
            "color": type_colors.get(c["type"], "#6b7280"),
            "page": c["page"],
            "evidence": c.get("evidence", ""),
            "confidence": c.get("confidence", 0.5),
            "confidence_ai": c.get("confidence_ai"),
            "status": c.get("status", "pending"),
        } for c in concepts]

        links = [{
            "source": name_to_slug.get(r["source_slug"], r["source_slug"]),
            "target": name_to_slug.get(r["target_slug"], r["target_slug"]),
            "type": r["type"],
            "color": rel_colors.get(r["type"], "#6b7280"),
            "evidence": r["evidence"],
            "relId": r["id"],
            "confidence": r.get("confidence", 0.5),
            "confidence_ai": r.get("confidence_ai"),
            "status": r.get("status", "pending"),
            "page": r.get("page"),
        } for r in relations]

        return {
            "paperTitle": paper["title"],
            "nodes": nodes,
            "links": links,
        }
