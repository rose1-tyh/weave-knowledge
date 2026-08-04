from services.ai_service import AIService


def test_sanitize_missing_confidence_defaults_to_05():
    raw = {"concepts": [{"name": "概念", "definition": "d", "type": "finding", "page": 2}],
           "relations": [{"source": "概念", "target": "其他", "type": "cites", "evidence": "e"}]}
    out = AIService._sanitize_result(raw)
    assert out["concepts"][0]["confidence"] == 0.5
    assert out["concepts"][0]["evidence"] == ""
    assert out["relations"][0]["confidence"] == 0.5


def test_sanitize_clamps_out_of_range():
    raw = {"concepts": [{"name": "c", "confidence": 1.5}], "relations": []}
    assert AIService._sanitize_result(raw)["concepts"][0]["confidence"] == 1.0


def test_sanitize_handles_garbage_page():
    raw = {"concepts": [{"name": "c", "page": "abc"}], "relations": []}
    assert AIService._sanitize_result(raw)["concepts"][0]["page"] == 1
