import pytest
from services.confidence_service import (
    enrich,
    final_confidence,
    text_signal_for_concept,
    text_signal_for_relation,
)


def test_concept_signal_zero_when_absent():
    assert text_signal_for_concept("图谱", "本文主要讨论文本分析。") == 0.0


def test_concept_signal_saturates_with_frequency():
    text = "图谱 图谱 图谱 图谱 图谱 图谱"
    assert text_signal_for_concept("图谱", text) == pytest.approx(1.0, abs=0.01)


def test_concept_signal_position_bonus():
    # 概念在摘要/结论位置出现 → 信号高于只在正文中部出现
    key = "图谱 概念定义。\n\n" + ("正文内容。" * 100) + "\n\n图谱 结论。"
    mid = "正文内容。" * 50 + "图谱 图谱" + "正文内容。" * 50
    assert text_signal_for_concept("图谱", key) > text_signal_for_concept("图谱", mid)


def test_relation_signal_uses_evidence_locatability():
    text = "图谱 图谱 图谱 图谱 图谱 图谱"
    found = text_signal_for_relation("图谱 图谱", 1.0, 1.0, text)
    missing = text_signal_for_relation("不存在的证据串", 1.0, 1.0, text)
    assert found > missing


def test_final_confidence_geometric_mean():
    assert final_confidence(0.9, 0.4) == pytest.approx(0.6, abs=0.01)


def test_final_confidence_clamps():
    assert final_confidence(1.5, 0.5) <= 1.0
    assert final_confidence(-0.2, 0.5) >= 0.0


def test_final_confidence_falls_back_to_text_signal():
    assert final_confidence(None, 0.7) == pytest.approx(0.7, abs=0.01)


def test_enrich_adds_fields_and_preserves_input():
    raw = {
        "concepts": [{"name": "图谱", "definition": "d", "type": "finding", "page": 1, "confidence": 0.9}],
        "relations": [{"source": "图谱", "target": "文本", "type": "cites", "evidence": "x", "confidence": 0.8}],
    }
    original = raw["concepts"][0]["confidence"]
    out = enrich(raw, "图谱 图谱 图谱 文本 文本 文本")
    assert out["concepts"][0]["confidence_ai"] == 0.9
    # 概念"图谱"在开头出现 3 次 → text_signal=1.0，几何平均 sqrt(0.9×1.0)≈0.95，
    # 最终置信度应介于 AI 自评与文本信号之间（几何平均语义），而非被 ai_conf 上限截断。
    assert 0.9 <= out["concepts"][0]["confidence"] <= 1.0
    assert "text_signal" in out["concepts"][0]
    assert out["relations"][0]["confidence_ai"] == 0.8
    assert "text_signal" in out["relations"][0]
    assert raw["concepts"][0]["confidence"] == original  # 入参不被修改
