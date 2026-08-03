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
        self.target = self.config / "packages" / "90_diagnostics.yaml"
        self.target.write_text("input_boolean:\n  alpha13_test:\n    name: Alpha13 test\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def proposal(self):
        current = self.target.read_text(encoding="utf-8")
        return {
            "proposal_id": "abcdef12-aaaa-bbbb-cccc-123456789012",
            "summary": "Low-risk diagnostic change",
            "risk_level": "low",
            "changes": [{
                "path": "packages/90_diagnostics.yaml",
                "base_sha256": self.mod.sha256_text(current),
                "new_content": current.replace("Alpha13 test", "Alpha13 preflight test"),
                "reason": "Rename a diagnostic helper",
                "diff": "--- a/packages/90_diagnostics.yaml\n+++ b/packages/90_diagnostics.yaml\n",
                "operation_count": 1,
                "component_kind": "root",
                "component_id": "",
            }],
            "allowed_files": ["packages/90_diagnostics.yaml"],
            "apply_ready": True,
            "review_only": False,
        }

    def test_version(self):
        self.assertEqual("5.0.0b1", self.mod.APP_VERSION)

    def test_apply_ready_proposal_is_gated_until_preflight(self):
        validation = self.mod.validate_proposal(self.proposal())
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["preflight_required"])
        self.assertFalse(validation["preflight_valid"])
        self.assertFalse(validation["apply_allowed"])

    def test_successful_preflight_stages_files_without_modifying_home_assistant(self):
        proposal = self.mod.store_proposal(self.proposal())
        original = self.target.read_text(encoding="utf-8")
        self.mod.HAClient.check_config = lambda _self: {
            "result": "valid",
            "source": "test",
            "message": "valid",
        }
        result = self.mod.preflight_proposal({"proposal_id": proposal["proposal_id"]})
        self.assertEqual("passed", result["status"])
        self.assertTrue(result["connector_validation"]["preflight_valid"])
        self.assertTrue(result["connector_validation"]["apply_allowed"])
        self.assertEqual(original, self.target.read_text(encoding="utf-8"))
        stage_dir = Path(result["stage_directory"])
        self.assertTrue((stage_dir / "current" / "packages" / "90_diagnostics.yaml").exists())
        self.assertTrue((stage_dir / "proposed" / "packages" / "90_diagnostics.yaml").exists())

    def test_file_change_after_preflight_invalidates_gate(self):
        proposal = self.mod.store_proposal(self.proposal())
        self.mod.HAClient.check_config = lambda _self: {"result": "valid"}
        self.mod.preflight_proposal({"proposal_id": proposal["proposal_id"]})
        self.target.write_text("input_boolean:\n  changed_elsewhere:\n    name: Changed\n", encoding="utf-8")
        stored = self.mod.find_proposal(proposal["proposal_id"])
        validation = self.mod.validate_proposal(stored)
        self.assertFalse(validation["valid"])
        self.assertFalse(validation["preflight_valid"])
        self.assertFalse(validation["apply_allowed"])

    def test_apply_without_preflight_is_rejected_before_backup(self):
        proposal = self.proposal()
        self.mod.write_json(self.mod.PROPOSALS_PATH, [proposal])
        called = []
        self.mod.SupervisorClient.backup = lambda *_args, **_kwargs: called.append(True)
        with self.assertRaisesRegex(ValueError, "preflight"):
            self.mod.apply_proposal({
                "proposal_id": proposal["proposal_id"],
                "confirmation": "PATVIRTINU ABCDEF12",
            })
        self.assertEqual([], called)

    def test_ui_requires_preflight_before_apply_button(self):
        text = UI_PATH.read_text(encoding="utf-8")
        self.assertIn("Patikrinti prieš įrašymą", text)
        self.assertIn("preflightProposal", text)
        self.assertIn("applyAllowed", text)
        self.assertIn("Beta1 plano ir operacijų diagnostika", text)


if __name__ == "__main__":
    unittest.main()
