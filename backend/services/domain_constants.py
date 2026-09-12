"""领域展示元数据 —— 概念类型/关系类型的色板与中文标签（后端单一来源）

图谱着色、搜索徽标、分析图表共用此映射；前端 design tokens 与此对应。
"""

TYPE_COLORS = {
    "method": "#e8453c",
    "theory": "#8b5cf6",
    "dataset": "#10b981",
    "finding": "#f59e0b",
    "tool": "#00d4ff",
}

TYPE_LABELS = {
    "method": "研究方法",
    "theory": "理论基础",
    "dataset": "数据集",
    "finding": "研究发现",
    "tool": "工具/系统",
}

REL_COLORS = {
    "supports": "#10b981",
    "contradicts": "#e8453c",
    "extends": "#f59e0b",
    "cites": "#6b7280",
    "uses": "#00d4ff",
}

REL_LABELS = {
    "supports": "支撑/验证",
    "contradicts": "矛盾/质疑",
    "extends": "扩展/改进",
    "cites": "引用",
    "uses": "使用",
}

FALLBACK_COLOR = "#6b7280"


def type_color(t: str) -> str:
    return TYPE_COLORS.get(t, FALLBACK_COLOR)


def rel_color(t: str) -> str:
    return REL_COLORS.get(t, FALLBACK_COLOR)


def type_label(t: str) -> str:
    return TYPE_LABELS.get(t, t)


def rel_label(t: str) -> str:
    return REL_LABELS.get(t, t)
