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
    spec = importlib.util.spec_from_file_location("connector_alpha13_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class ConnectorAlpha13Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / "data"
        self.config = Path(self.temp.name) / "config"
        self.data.mkdir()
        self.config.mkdir()
        (self.config / "packages").mkdir()
        (self.data / "options.json").write_text(json.dumps({"allow_package_writes": True}), encoding="utf-8")
        self.mod = load_server(str(self.data), str(self.config))
        self.path = self.config / "packages" / "50_curtains.yaml"
        self.path.write_text("input_boolean:\n  test_flag:\n    name: Test\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def proposal(self, *, apply_ready: bool, review_only: bool):
        current = self.path.read_text(encoding="utf-8")
        return {
            "proposal_id": "12345678-aaaa-bbbb-cccc-123456789012",
            "summary": "Test",
            "risk_level": "medium",
            "changes": [{
                "path": "packages/50_curtains.yaml",
                "base_sha256": self.mod.sha256_text(current),
                "new_content": current.replace("Test", "Test 2"),
                "reason": "Test change",
                "diff": "--- a/packages/50_curtains.yaml\n+++ b/packages/50_curtains.yaml\n",
            }],
            "allowed_files": ["packages/50_curtains.yaml"],
            "apply_ready": apply_ready,
            "review_only": review_only,
        }

    def test_version(self):
        self.assertEqual("5.0.0-alpha13.1", self.mod.APP_VERSION)

    def test_review_only_proposal_is_valid_but_not_apply_allowed(self):
        validation = self.mod.validate_proposal(self.proposal(apply_ready=False, review_only=True))
        self.assertTrue(validation["valid"])
        self.assertFalse(validation["apply_allowed"])
        self.assertTrue(validation["review_only"])

    def test_apply_ready_proposal_requires_preflight(self):
        validation = self.mod.validate_proposal(self.proposal(apply_ready=True, review_only=False))
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["preflight_required"])
        self.assertFalse(validation["preflight_valid"])
        self.assertFalse(validation["apply_allowed"])

    def test_apply_rejects_review_only_before_backup(self):
        proposal = self.proposal(apply_ready=False, review_only=True)
        self.mod.write_json(self.mod.PROPOSALS_PATH, [proposal])
        with self.assertRaisesRegex(ValueError, "review-only"):
            self.mod.apply_proposal({
                "proposal_id": proposal["proposal_id"],
                "confirmation": "PATVIRTINU 12345678",
            })

    def test_ui_displays_diff_and_review_only_status(self):
        text = UI_PATH.read_text(encoding="utf-8")
        self.assertIn("c.diff || c.new_content", text)
        self.assertIn("Tik peržiūrai", text)
        self.assertIn("applyAllowed", text)


if __name__ == "__main__":
    unittest.main()
