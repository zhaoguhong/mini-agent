import tempfile
import unittest
from pathlib import Path

from miniagent.config.loader import load_config


class ConfigTests(unittest.TestCase):
    def test_env_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            config = load_config(
                config_path=tmp_path / "missing.toml",
                env={
                    "MINIAGENT_API_KEY": "key",
                    "MINIAGENT_MODEL": "model",
                    "MINIAGENT_DEFAULT_LANGUAGE": "en",
                    "MINIAGENT_STREAM": "false",
                    "MINIAGENT_WORKSPACE": str(tmp_path),
                },
            )

            self.assertEqual(config.api_key, "key")
            self.assertEqual(config.model, "model")
            self.assertEqual(config.default_language, "en")
            self.assertFalse(config.stream)
            self.assertEqual(config.workspace_root, Path(tmp_path))

    def test_required_validation_reports_missing(self):
        config = load_config(config_path=Path("/tmp/missing-miniagent-config.toml"), env={})

        with self.assertRaises(ValueError) as raised:
            config.validate_required()
        self.assertIn("api_key", str(raised.exception))
        self.assertIn("model", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
