"""图谱数据构建服务 —— 为前端 D3 渲染准备数据"""

import hashlib


class GraphService:
    """将 AI 提取的原始数据转为前端可渲染的图谱"""

    TYPE_COLORS = {
        "method": "#e8453c", "theory": "#8b5cf6", "dataset": "#10b981",
        "finding": "#f59e0b", "tool": "#00d4ff",
    }
    RELATION_COLORS = {
        "supports": "#10b981", "contradicts": "#e8453c", "extends": "#f59e0b",
        "cites": "#6b7280", "uses": "#00d4ff",
    }

    @classmethod
    def build_graph(cls, raw: dict, paper_title: str) -> "KnowledgeGraphData":
        """从 AI 返回的原始 dict 构建结构化数据"""
        concepts = []
        for i, c in enumerate(raw.get("concepts", [])):
            slug = cls._to_slug(c.get("name", f"concept-{i}"))
            concepts.append(ConceptData(
                id=slug,
                name=c.get("name", ""),
                definition=c.get("definition", ""),
                type=c.get("type", "finding"),
                page=c.get("page", 1),
                evidence=c.get("evidence", ""),
                confidence=c.get("confidence", 0.5),
                confidence_ai=c.get("confidence_ai"),
                status=c.get("status", "pending"),
            ))

        concept_names = {c.name for c in concepts}
        relations = []
        for r in raw.get("relations", []):
            src = r.get("source", "")
            tgt = r.get("target", "")
            if src in concept_names and tgt in concept_names:
                relations.append(RelationData(
                    source=src,
                    target=tgt,
                    type=r.get("type", "cites"),
                    evidence=r.get("evidence", ""),
                    confidence=r.get("confidence", 0.5),
                    confidence_ai=r.get("confidence_ai"),
                    status=r.get("status", "pending"),
                    page=r.get("page"),
                ))

        return KnowledgeGraphData(
            paper_title=paper_title,
            concepts=concepts,
            relations=relations,
        )

    @classmethod
    def to_d3_format(cls, graph: "KnowledgeGraphData") -> dict:
        """转为 D3 力导向图所需的 nodes/links 格式"""
        name_to_id = {c.name: c.id for c in graph.concepts}
        nodes = [{
            "id": c.id, "name": c.name, "definition": c.definition,
            "type": c.type, "color": cls.TYPE_COLORS.get(c.type, "#6b7280"), "page": c.page,
            "evidence": c.evidence, "confidence": c.confidence,
            "confidence_ai": c.confidence_ai, "status": c.status,
        } for c in graph.concepts]
        links = [{
            "source": name_to_id.get(r.source, r.source),
            "target": name_to_id.get(r.target, r.target),
            "type": r.type, "color": cls.RELATION_COLORS.get(r.type, "#6b7280"), "evidence": r.evidence,
            "confidence": r.confidence, "confidence_ai": r.confidence_ai,
            "status": r.status, "page": r.page,
        } for r in graph.relations]
        return {"paperTitle": graph.paper_title, "nodes": nodes, "links": links}

    @staticmethod
    def _to_slug(name: str) -> str:
        return hashlib.md5(name.encode()).hexdigest()[:8]


# 简单数据类（避免 Pydantic 模型依赖）
class ConceptData:
    def __init__(self, id, name, definition, type, page,
                 evidence="", confidence=0.5, confidence_ai=None, status="pending"):
        self.id = id
        self.name = name
        self.definition = definition
        self.type = type
        self.page = page
        self.evidence = evidence
        self.confidence = confidence
        self.confidence_ai = confidence_ai
        self.status = status

    def model_dump(self) -> dict:
        return {"id": self.id, "name": self.name, "definition": self.definition,
                "type": self.type, "page": self.page, "evidence": self.evidence,
                "confidence": self.confidence, "confidence_ai": self.confidence_ai,
                "status": self.status}


class RelationData:
    def __init__(self, source, target, type, evidence,
                 confidence=0.5, confidence_ai=None, status="pending", page=None):
        self.source = source
        self.target = target
        self.type = type
        self.evidence = evidence
        self.confidence = confidence
        self.confidence_ai = confidence_ai
        self.status = status
        self.page = page

    def model_dump(self) -> dict:
        return {"source": self.source, "target": self.target, "type": self.type,
                "evidence": self.evidence, "confidence": self.confidence,
                "confidence_ai": self.confidence_ai, "status": self.status, "page": self.page}


class KnowledgeGraphData:
    def __init__(self, paper_title: str, concepts: list, relations: list):
        self.paper_title = paper_title
        self.concepts = concepts
        self.relations = relations
