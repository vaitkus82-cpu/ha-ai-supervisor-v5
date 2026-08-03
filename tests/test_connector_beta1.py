import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

SERVER_PATH = Path(__file__).resolve().parents[1] / "ai_supervisor_connector" / "rootfs" / "opt" / "ai_supervisor_connector" / "server.py"
UI_PATH = Path(__file__).resolve().parents[1] / "ai_supervisor_connector" / "rootfs" / "opt" / "ai_supervisor_connector" / "static" / "index.html"


def load_server(data_dir: str, config_dir: str):
    os.environ["DATA_DIR"] = data_dir
    os.environ["HOMEASSISTANT_CONFIG_DIR"] = config_dir
    os.environ["SUPERVISOR_TOKEN"] = "test-token"
    spec = importlib.util.spec_from_file_location("connector_beta1_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class ConnectorBeta1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        data = Path(self.temp.name) / "data"
        config = Path(self.temp.name) / "config"
        data.mkdir(); config.mkdir(); (config / "packages").mkdir()
        (data / "options.json").write_text(json.dumps({"allow_package_writes": False}), encoding="utf-8")
        self.mod = load_server(str(data), str(config))

    def tearDown(self):
        self.temp.cleanup()

    def test_background_job_completes_and_persists_result(self):
        self.mod.HAClient.check_config = lambda _self: {"result": "valid", "message": "ok"}
        started = self.mod.start_job({"action": "check_config", "payload": {}})
        for _ in range(100):
            job = self.mod.get_job(started["job_id"])
            if job["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)
        self.assertEqual("completed", job["status"])
        self.assertEqual("valid", job["result"]["result"])

    def test_ui_polls_background_jobs_for_long_operations(self):
        text = UI_PATH.read_text(encoding="utf-8")
        self.assertIn("runJob('preflight'", text)
        self.assertIn("api/jobs/start", text)
        self.assertIn("api/jobs/${encodeURIComponent(jobId)}", text)

    def test_incident_report_uses_selflab_endpoint(self):
        calls = []
        original = self.mod.EngineClient.request
        try:
            self.mod.EngineClient.request = lambda _self, method, path, payload=None, **kwargs: calls.append((method, path, payload)) or {"accepted": True}
            self.mod.report_engine_incident("test", "failure", {"a": 1})
        finally:
            self.mod.EngineClient.request = original
        self.assertEqual("/v1/selflab/incidents", calls[0][1])
        self.assertEqual("failure", calls[0][2]["message"])


if __name__ == "__main__":
    unittest.main()
