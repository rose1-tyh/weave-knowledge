"""数据目录配置测试 —— WEAVE_DATA_DIR 环境变量优先，未设置时保持项目内 storage"""
import importlib
import os
import pytest

import config


@pytest.fixture
def clean_env(monkeypatch):
    """确保测试期间无 WEAVE_DATA_DIR 干扰，结束后恢复默认"""
    monkeypatch.delenv("WEAVE_DATA_DIR", raising=False)
    importlib.reload(config)
    yield
    monkeypatch.delenv("WEAVE_DATA_DIR", raising=False)
    importlib.reload(config)


def test_default_paths_unchanged(clean_env):
    """无 WEAVE_DATA_DIR 时保持项目内 storage（向后兼容）"""
    assert config.DATABASE_PATH.endswith(os.path.join("storage", "weave.db"))
    assert config.PAPER_STORAGE_DIR.endswith(os.path.join("storage", "papers"))


def test_weave_data_dir_overrides_paths(clean_env, monkeypatch):
    """设置 WEAVE_DATA_DIR 后数据库与论文目录指向新位置"""
    data_dir = os.path.join("C:\\Users\\test\\AppData\\Roaming", "织识")
    monkeypatch.setenv("WEAVE_DATA_DIR", data_dir)
    importlib.reload(config)
    assert config.DATABASE_PATH == os.path.join(data_dir, "weave.db")
    assert config.PAPER_STORAGE_DIR == os.path.join(data_dir, "papers")


def test_blank_weave_data_dir_falls_back(clean_env, monkeypatch):
    """空白 WEAVE_DATA_DIR 视为未设置（回退项目内 storage）"""
    monkeypatch.setenv("WEAVE_DATA_DIR", "   ")
    importlib.reload(config)
    assert config.DATABASE_PATH.endswith(os.path.join("storage", "weave.db"))
