import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SERVER_PATH = Path(__file__).resolve().parents[1] / "ai_supervisor_connector" / "rootfs" / "opt" / "ai_supervisor_connector" / "server.py"
UI_PATH = Path(__file__).resolve().parents[1] / "ai_supervisor_connector" / "rootfs" / "opt" / "ai_supervisor_connector" / "static" / "index.html"


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
        data = Path(self.temp.name) / "data"
        config = Path(self.temp.name) / "config"
        data.mkdir(); config.mkdir(); (config / "packages").mkdir()
        (data / "options.json").write_text(json.dumps({"allow_package_writes": False}), encoding="utf-8")
        self.mod = load_server(str(data), str(config))

    def tearDown(self):
        self.temp.cleanup()

    def test_version(self):
        self.assertEqual("5.0.0-alpha12", self.mod.APP_VERSION)

    def test_ui_does_not_claim_success_for_blocked_proposal(self):
        text = UI_PATH.read_text(encoding="utf-8")
        self.assertIn("Pasiūlymas užblokuotas", text)
        self.assertIn("Alpha12", text)

    def test_store_proposal_uses_higher_connector_risk(self):
        proposal = {
            "proposal_id": "abc",
            "risk_level": "low",
            "changes": [],
            "apply_ready": False,
            "review_only": True,
        }
        result = self.mod.store_proposal(proposal)
        self.assertEqual("medium", result["risk_level"])
        self.assertEqual("blocked", result["proposal_status"])


if __name__ == "__main__":
    unittest.main()
