import os
from pathlib import Path
import pytest
from pulse import config

@pytest.fixture
def mock_config_path(tmp_path, monkeypatch):
    """Mock the config path to use a temporary directory."""
    def mock_get_config_dir():
        return tmp_path
    
    def mock_get_config_path():
        return tmp_path / "config.toml"
        
    monkeypatch.setattr(config, "get_config_dir", mock_get_config_dir)
    monkeypatch.setattr(config, "get_config_path", mock_get_config_path)
    return tmp_path

def test_load_defaults(mock_config_path):
    """Test that defaults are loaded when no config file exists."""
    cfg = config.load_config()
    assert cfg["ui"]["theme"] == "nord"
    assert cfg["core"]["refresh_rate"] == 1.0
    # verify file was created
    assert (mock_config_path / "config.toml").exists()

def test_save_and_load(mock_config_path):
    """Test saving and then loading configuration."""
    cfg = {"ui": {"theme": "dracula"}, "core": {"refresh_rate": 0.5}}
    config.save_config(cfg)
    
    loaded = config.load_config()
    assert loaded["ui"]["theme"] == "dracula"
    assert loaded["core"]["refresh_rate"] == 0.5

def test_partial_config_merge(mock_config_path):
    """Test that a partial config file is merged with defaults."""
    # Create a partial config file
    partial = {"ui": {"theme": "monokai"}}
    config.save_config(partial)
    
    loaded = config.load_config()
    # Should have the saved value
    assert loaded["ui"]["theme"] == "monokai"
    # Should have the default value for the missing key
    assert loaded["core"]["refresh_rate"] == 1.0
