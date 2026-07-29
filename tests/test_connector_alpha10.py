import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SERVER_PATH = Path(__file__).resolve().parents[1] / "ai_supervisor_connector" / "rootfs" / "opt" / "ai_supervisor_connector" / "server.py"


def load_server(data_dir: str, config_dir: str):
    os.environ["DATA_DIR"] = data_dir
    os.environ["HOMEASSISTANT_CONFIG_DIR"] = config_dir
    os.environ["SUPERVISOR_TOKEN"] = "test-token"
    spec = importlib.util.spec_from_file_location("connector_alpha12_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class ConnectorAlpha12Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / "data"
        self.config = Path(self.temp.name) / "config"
        self.data.mkdir()
        self.config.mkdir()
        (self.data / "options.json").write_text(json.dumps({"max_snapshot_mb": 2}), encoding="utf-8")
        self.mod = load_server(str(self.data), str(self.config))

    def tearDown(self):
        self.temp.cleanup()

    def test_raw_component_keeps_direct_script_call_as_dependency(self):
        block = """
    alias: Užuolaidų centras
    action:
      - action: script.uzuolaidos_vykdytojas
      - action: cover.close_cover
        target:
          entity_id: cover.svetaine_terasa_curtain
"""
        component = self.mod._raw_component_record(
            "automation", "uzuolaidos-centras", block, "packages/50_curtains.yaml", 1, 8
        )
        self.assertIn("script.uzuolaidos_vykdytojas", component["references"])
        self.assertNotIn("cover.close_cover", component["references"])
        self.assertIn("cover.close_cover", component["services"])

    def test_connector_version_is_alpha12(self):
        self.assertEqual("5.0.0-alpha12", self.mod.APP_VERSION)


if __name__ == "__main__":
    unittest.main()
