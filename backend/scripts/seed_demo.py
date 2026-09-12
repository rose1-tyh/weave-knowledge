"""演示数据种子脚本 —— 一键灌入示例论文与知识图谱（离线，无需 AI Key）

用途：评委/新用户 clone 后快速获得可演示的完整数据（含跨论文同名概念，
可演示全局探索融合、混合检索与 PageRank 洞察）。

用法（仓库根目录）：
    cd backend && python scripts/seed_demo.py            # 跳过已存在的论文（幂等）
    cd backend && python scripts/seed_demo.py --force    # 清除同名演示论文后重灌
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import close_db, get_db, init_db
from services.library_service import LibraryService

DEMO_PAPERS = [
    {
        "id": "demo-attention",
        "title": "Attention Is All You Need（演示样本）",
        "filename": "attention-demo.txt",
        "page_count": 11,
        "tags": '["演示", "深度学习"]',
        "text": (
            "Transformer 架构完全基于注意力机制，摒弃循环与卷积。自注意力允许模型在处理每个词时"
            "关注输入序列中的其他词，捕捉长距离依赖。多头注意力将注意力计算扩展到多个子空间，"
            "并行捕捉不同类型的语义关系。位置编码为模型提供词序信息。缩放点积注意力通过除以"
            "根号维度防止点积过大导致梯度消失。编码器-解码器结构中，编码器将输入映射为连续表示，"
            "解码器自回归地生成输出。"
        ),
        "concepts": [
            {"id": "attn-self", "name": "自注意力", "definition": "序列内元素相互关注并加权聚合信息的机制，捕捉长距离依赖", "type": "method", "page": 3, "evidence": "自注意力允许模型在处理每个词时关注输入序列中的其他词", "confidence": 0.95, "confidence_ai": 0.93, "status": "confirmed"},
            {"id": "attn-multi", "name": "多头注意力", "definition": "将注意力计算并行扩展到多个子空间以捕捉不同类型关系", "type": "method", "page": 4, "evidence": "多头注意力将注意力计算扩展到多个子空间，并行捕捉不同类型的语义关系", "confidence": 0.93, "confidence_ai": 0.9, "status": "confirmed"},
            {"id": "attn-scaled", "name": "缩放点积注意力", "definition": "除以根号维度的点积注意力，防止梯度消失的核心计算单元", "type": "method", "page": 4, "evidence": "缩放点积注意力通过除以根号维度防止点积过大导致梯度消失", "confidence": 0.9, "confidence_ai": 0.88, "status": "pending"},
            {"id": "attn-pos", "name": "位置编码", "definition": "为自注意力注入词序信息的编码方式", "type": "theory", "page": 5, "evidence": "位置编码为模型提供词序信息", "confidence": 0.88, "confidence_ai": 0.86, "status": "pending"},
            {"id": "attn-encdec", "name": "编码器-解码器", "definition": "编码器映射输入为连续表示，解码器自回归生成输出的架构", "type": "theory", "page": 2, "evidence": "编码器将输入映射为连续表示，解码器自回归地生成输出", "confidence": 0.91, "confidence_ai": 0.89, "status": "confirmed"},
            {"id": "attn-trans", "name": "Transformer", "definition": "完全基于注意力机制的序列建模架构", "type": "tool", "page": 1, "evidence": "Transformer 架构完全基于注意力机制，摒弃循环与卷积", "confidence": 0.97, "confidence_ai": 0.96, "status": "confirmed"},
        ],
        "relations": [
            {"source": "attn-trans", "target": "attn-self", "type": "uses", "evidence": "Transformer 架构完全基于注意力机制", "page": 1, "confidence": 0.95, "confidence_ai": 0.94, "status": "confirmed"},
            {"source": "attn-self", "target": "attn-multi", "type": "extends", "evidence": "多头注意力将注意力计算扩展到多个子空间", "page": 4, "confidence": 0.92, "confidence_ai": 0.9, "status": "confirmed"},
            {"source": "attn-multi", "target": "attn-scaled", "type": "uses", "evidence": "每个注意力头内部采用缩放点积注意力", "page": 4, "confidence": 0.9, "confidence_ai": 0.87, "status": "pending"},
            {"source": "attn-pos", "target": "attn-self", "type": "supports", "evidence": "位置编码弥补自注意力对顺序不敏感的缺陷", "page": 5, "confidence": 0.88, "confidence_ai": 0.85, "status": "pending"},
            {"source": "attn-encdec", "target": "attn-self", "type": "uses", "evidence": "编码器与解码器均以自注意力为核心构建", "page": 2, "confidence": 0.9, "confidence_ai": 0.88, "status": "confirmed"},
            {"source": "attn-trans", "target": "attn-encdec", "type": "uses", "evidence": "Transformer 采用编码器-解码器结构", "page": 2, "confidence": 0.93, "confidence_ai": 0.91, "status": "confirmed"},
        ],
    },
    {
        "id": "demo-kg",
        "title": "知识图谱综述：构建、融合与推理（演示样本）",
        "filename": "kg-survey-demo.txt",
        "page_count": 24,
        "tags": '["演示", "知识图谱"]',
        "text": (
            "知识图谱以三元组（实体、关系、实体）组织知识，支持语义检索与推理。实体对齐致力于判定"
            "不同知识源中的实体是否指向同一现实对象，是跨源融合的关键步骤。本体为知识图谱提供"
            "模式层约束，限定实体类型与关系层级。知识推理从已有三元组推导新事实，包括基于规则与"
            "基于表示学习的两类方法。知识图谱补全针对图谱稀疏性，预测缺失的实体或关系。"
        ),
        "concepts": [
            {"id": "kg-triple", "name": "三元组", "definition": "以（实体、关系、实体）组织知识的基本单元", "type": "theory", "page": 1, "evidence": "知识图谱以三元组组织知识", "confidence": 0.96, "confidence_ai": 0.95, "status": "confirmed"},
            {"id": "kg-align", "name": "实体对齐", "definition": "判定不同知识源中的实体是否指向同一现实对象", "type": "method", "page": 8, "evidence": "实体对齐致力于判定不同知识源中的实体是否指向同一现实对象", "confidence": 0.92, "confidence_ai": 0.9, "status": "confirmed"},
            {"id": "kg-onto", "name": "本体", "definition": "为知识图谱提供模式层约束，限定实体类型与关系层级", "type": "theory", "page": 3, "evidence": "本体为知识图谱提供模式层约束", "confidence": 0.9, "confidence_ai": 0.88, "status": "pending"},
            {"id": "kg-reason", "name": "知识推理", "definition": "从已有三元组推导新事实，含规则与表示学习两类路径", "type": "method", "page": 15, "evidence": "知识推理从已有三元组推导新事实", "confidence": 0.91, "confidence_ai": 0.9, "status": "confirmed"},
            {"id": "kg-complete", "name": "知识图谱补全", "definition": "针对图谱稀疏性预测缺失实体或关系的任务", "type": "finding", "page": 17, "evidence": "知识图谱补全针对图谱稀疏性，预测缺失的实体或关系", "confidence": 0.87, "confidence_ai": 0.85, "status": "pending"},
            {"id": "kg-kg", "name": "知识图谱", "definition": "以图结构组织知识、支持语义检索与推理的知识库", "type": "tool", "page": 1, "evidence": "知识图谱以三元组组织知识，支持语义检索与推理", "confidence": 0.98, "confidence_ai": 0.97, "status": "confirmed"},
        ],
        "relations": [
            {"source": "kg-kg", "target": "kg-triple", "type": "uses", "evidence": "知识图谱以三元组组织知识", "page": 1, "confidence": 0.96, "confidence_ai": 0.94, "status": "confirmed"},
            {"source": "kg-onto", "target": "kg-kg", "type": "supports", "evidence": "本体为知识图谱提供模式层约束", "page": 3, "confidence": 0.9, "confidence_ai": 0.88, "status": "confirmed"},
            {"source": "kg-align", "target": "kg-kg", "type": "extends", "evidence": "实体对齐是跨源融合的关键步骤", "page": 8, "confidence": 0.92, "confidence_ai": 0.9, "status": "confirmed"},
            {"source": "kg-reason", "target": "kg-complete", "type": "uses", "evidence": "补全任务依赖知识推理方法预测缺失三元组", "page": 17, "confidence": 0.88, "confidence_ai": 0.86, "status": "pending"},
            {"source": "kg-align", "target": "kg-complete", "type": "supports", "evidence": "对齐为跨源补全提供参照", "page": 18, "confidence": 0.85, "confidence_ai": 0.82, "status": "pending"},
        ],
    },
    {
        "id": "demo-rag",
        "title": "检索增强生成（RAG）研究进展（演示样本）",
        "filename": "rag-demo.txt",
        "page_count": 16,
        "tags": '["演示", "RAG"]',
        "text": (
            "检索增强生成将参数化知识与外部知识库结合：模型生成答案前先从知识库检索相关文档片段，"
            "以向量检索实现语义级召回。重排序器对召回结果精细打分，提升顶部相关性。幻觉问题在"
            "引入外部证据后显著缓解。知识图谱可以作为结构化知识源接入 RAG，为多跳推理提供支持。"
        ),
        "concepts": [
            {"id": "rag-rag", "name": "检索增强生成", "definition": "生成前从外部知识库检索相关文档以增强语言模型的范式", "type": "method", "page": 1, "evidence": "检索增强生成将参数化知识与外部知识库结合", "confidence": 0.96, "confidence_ai": 0.95, "status": "confirmed"},
            {"id": "rag-vec", "name": "向量检索", "definition": "以向量相似度实现语义级文档召回的检索方式", "type": "method", "page": 4, "evidence": "以向量检索实现语义级召回", "confidence": 0.93, "confidence_ai": 0.92, "status": "confirmed"},
            {"id": "rag-rerank", "name": "重排序器", "definition": "对召回结果精细打分以提升顶部相关性的模型", "type": "tool", "page": 7, "evidence": "重排序器对召回结果精细打分，提升顶部相关性", "confidence": 0.9, "confidence_ai": 0.89, "status": "pending"},
            {"id": "rag-halluc", "name": "幻觉", "definition": "语言模型生成与事实不符内容的现象", "type": "finding", "page": 2, "evidence": "幻觉问题在引入外部证据后显著缓解", "confidence": 0.89, "confidence_ai": 0.87, "status": "confirmed"},
            {"id": "kg-kg-2", "name": "知识图谱", "definition": "以图结构组织知识的结构化知识源，可接入 RAG 支持多跳推理", "type": "tool", "page": 12, "evidence": "知识图谱可以作为结构化知识源接入 RAG", "confidence": 0.92, "confidence_ai": 0.9, "status": "pending"},
        ],
        "relations": [
            {"source": "rag-rag", "target": "rag-vec", "type": "uses", "evidence": "以向量检索实现语义级召回", "page": 4, "confidence": 0.94, "confidence_ai": 0.93, "status": "confirmed"},
            {"source": "rag-rerank", "target": "rag-vec", "type": "extends", "evidence": "重排序器对召回结果精细打分", "page": 7, "confidence": 0.9, "confidence_ai": 0.88, "status": "pending"},
            {"source": "rag-rag", "target": "rag-halluc", "type": "contradicts", "evidence": "引入外部证据后幻觉显著缓解", "page": 2, "confidence": 0.91, "confidence_ai": 0.9, "status": "confirmed"},
            {"source": "kg-kg-2", "target": "rag-rag", "type": "supports", "evidence": "知识图谱可作为结构化知识源接入 RAG", "page": 12, "confidence": 0.92, "confidence_ai": 0.9, "status": "pending"},
        ],
    },
]


async def seed(force: bool = False):
    from config import PAPER_STORAGE_DIR
    os.makedirs(PAPER_STORAGE_DIR, exist_ok=True)   # 数据目录不存在时先建（独立于服务启动）
    await init_db()
    db = await get_db()
    seeded = 0
    for paper in DEMO_PAPERS:
        exists = await db.execute_fetchall("SELECT id FROM papers WHERE id = ?", [paper["id"]])
        if exists:
            if force:
                await LibraryService.delete_paper(paper["id"])
                print(f"  [force] 已删除旧演示论文 {paper['id']}")
            else:
                print(f"  跳过（已存在）: {paper['title']}")
                continue

        await LibraryService.create_paper(
            paper_id=paper["id"], title=paper["title"], filename=paper["filename"],
            page_count=paper["page_count"], text_length=len(paper["text"]))
        await LibraryService.update_paper(paper["id"], {"tags": paper["tags"]})
        await LibraryService.update_paper_text(paper["id"], paper["text"])
        await LibraryService.save_concepts(paper["id"], paper["concepts"])
        await LibraryService.save_relations(paper["id"], paper["relations"])
        await LibraryService.update_extract_status(
            paper["id"], "done", len(paper["concepts"]), len(paper["relations"]))
        seeded += 1
        print(f"  已灌入: {paper['title']}（{len(paper['concepts'])} 概念 · {len(paper['relations'])} 关系）")

    print(f"\n完成：新灌入 {seeded} 篇演示论文。启动后端后即可演示融合/检索/洞察。")
    await close_db()


if __name__ == "__main__":
    asyncio.run(seed(force="--force" in sys.argv))
