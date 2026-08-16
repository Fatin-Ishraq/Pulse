import copy

import pytest

from pulse import config


@pytest.fixture
def mock_config_path(tmp_path, monkeypatch):
    """Point the config helpers at a temporary directory."""
    monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path)
    monkeypatch.setattr(config, "get_config_path", lambda: tmp_path / "config.toml")
    return tmp_path


class TestLoadSave:
    def test_load_defaults(self, mock_config_path):
        cfg = config.load_config()
        assert cfg["ui"]["theme"] == "nord"
        assert cfg["core"]["refresh_rate"] == 1.0
        assert (mock_config_path / "config.toml").exists()

    def test_save_and_load(self, mock_config_path):
        config.save_config({"ui": {"theme": "dracula"}, "core": {"refresh_rate": 0.5}})

        loaded = config.load_config()
        assert loaded["ui"]["theme"] == "dracula"
        assert loaded["core"]["refresh_rate"] == 0.5

    def test_partial_config_merge(self, mock_config_path):
        config.save_config({"ui": {"theme": "monokai"}})

        loaded = config.load_config()
        assert loaded["ui"]["theme"] == "monokai"
        assert loaded["core"]["refresh_rate"] == 1.0

    def test_corrupt_file_falls_back_to_defaults(self, mock_config_path):
        (mock_config_path / "config.toml").write_text("this is not = valid = toml [[[")

        loaded = config.load_config()
        assert loaded["ui"]["theme"] == "nord"

    def test_save_reports_failure(self, mock_config_path, monkeypatch):
        def refuse(*args, **kwargs):
            raise OSError("read-only filesystem")

        monkeypatch.setattr("builtins.open", refuse)
        assert config.save_config({"ui": {}}) is False


class TestDefaultsAreNotShared:
    def test_load_does_not_hand_out_the_module_defaults(self, mock_config_path):
        """Regression: the app mutated DEFAULT_CONFIG through the returned dict."""
        pristine = copy.deepcopy(config.DEFAULT_CONFIG)

        cfg = config.load_config()
        cfg["ui"]["theme"] = "gruvbox"

        assert config.DEFAULT_CONFIG == pristine
        assert config.load_config()["ui"]["theme"] != "gruvbox"

    def test_each_call_returns_an_independent_copy(self, mock_config_path):
        first = config.load_config()
        second = config.load_config()
        first["core"]["refresh_rate"] = 42.0
        assert second["core"]["refresh_rate"] == 1.0

    def test_default_config_helper_copies(self):
        first = config.default_config()
        first["ui"]["theme"] = "monokai"
        assert config.default_config()["ui"]["theme"] == "nord"


class TestValidation:
    @pytest.mark.parametrize("value", [0, -1, "fast", None, [], float("nan")])
    def test_bad_refresh_rates_fall_back_into_range(self, value):
        rate = config.validate_refresh_rate(value)
        assert config.MIN_REFRESH_RATE <= rate <= config.MAX_REFRESH_RATE

    def test_refresh_rate_is_clamped_not_rejected(self):
        assert config.validate_refresh_rate(0.001) == config.MIN_REFRESH_RATE
        assert config.validate_refresh_rate(9999) == config.MAX_REFRESH_RATE

    def test_valid_refresh_rate_passes_through(self):
        assert config.validate_refresh_rate(2.5) == 2.5

    def test_unknown_theme_falls_back(self):
        assert config.validate_theme("hot-pink") == config.DEFAULT_THEME
        assert config.validate_theme(None) == config.DEFAULT_THEME
        assert config.validate_theme(42) == config.DEFAULT_THEME

    def test_known_theme_passes_through(self):
        assert config.validate_theme("gruvbox") == "gruvbox"

    def test_loaded_config_is_validated(self, mock_config_path):
        config.save_config({"ui": {"theme": "nonsense"}, "core": {"refresh_rate": -5}})

        loaded = config.load_config()
        assert loaded["ui"]["theme"] == config.DEFAULT_THEME
        assert loaded["core"]["refresh_rate"] >= config.MIN_REFRESH_RATE

    def test_non_dict_sections_are_repaired(self):
        cfg = config.validate_config({"ui": "not a dict", "core": 7})
        assert cfg["ui"]["theme"] == config.DEFAULT_THEME
        assert cfg["core"]["refresh_rate"] == config.DEFAULT_REFRESH_RATE


class TestConfigLocation:
    def test_windows_uses_appdata(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config.sys, "platform", "win32")
        monkeypatch.setenv("APPDATA", str(tmp_path))

        path = config.get_config_dir()
        assert path == tmp_path / "pulse"
        assert path.is_dir()

    def test_windows_falls_back_when_appdata_is_unset(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config.sys, "platform", "win32")
        monkeypatch.delenv("APPDATA", raising=False)
        monkeypatch.setattr(config.Path, "home", staticmethod(lambda: tmp_path))

        assert config.get_config_dir() == tmp_path / "AppData" / "Roaming" / "pulse"

    def test_posix_respects_xdg_config_home(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config.sys, "platform", "linux")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        assert config.get_config_dir() == tmp_path / "pulse"

    def test_posix_defaults_to_dot_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config.sys, "platform", "linux")
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setattr(config.Path, "home", staticmethod(lambda: tmp_path))

        assert config.get_config_dir() == tmp_path / ".config" / "pulse"

    def test_config_path_sits_in_the_config_dir(self, mock_config_path):
        assert config.get_config_path().parent == mock_config_path


class TestThemeListsMatch:
    def test_app_themes_match_validated_themes(self):
        from pulse.app import THEMES
        assert THEMES == list(config.VALID_THEMES)
