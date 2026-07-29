import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SERVER_PATH = Path(__file__).resolve().parents[1] / 'ai_supervisor_connector' / 'rootfs' / 'opt' / 'ai_supervisor_connector' / 'server.py'


def load_server(data_dir: str, config_dir: str):
    os.environ['DATA_DIR'] = data_dir
    os.environ['HOMEASSISTANT_CONFIG_DIR'] = config_dir
    os.environ['SUPERVISOR_TOKEN'] = 'test-token'
    spec = importlib.util.spec_from_file_location('connector_alpha9_test', SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class ConnectorAlpha9HotfixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / 'data'
        self.config = Path(self.temp.name) / 'config'
        self.data.mkdir()
        self.config.mkdir()
        (self.data / 'options.json').write_text(json.dumps({
            'max_snapshot_mb': 2,
            'engine_url': '',
            'engine_token': '',
            'allow_package_writes': False,
        }), encoding='utf-8')
        self.mod = load_server(str(self.data), str(self.config))

    def tearDown(self):
        self.temp.cleanup()

    def test_status_uses_engine_health_without_name_error(self):
        (self.data / 'v5_settings.json').write_text(json.dumps({
            'engine_url': 'http://192.168.1.50:8765',
            'engine_token': 'token-value',
        }), encoding='utf-8')
        self.mod.engine_health = lambda: {'ok': True, 'version': '5.0.0-alpha8'}
        result = self.mod.status()
        self.assertTrue(result['ok'])
        self.assertTrue(result['engine']['ok'])
        self.assertEqual('5.0.0-alpha9', result['connector_version'])

    def test_pair_engine_restored_and_persists_token(self):
        calls = []

        class FakeEngineClient:
            def request(self, method, path, payload=None, **kwargs):
                calls.append((method, path, payload, kwargs))
                return {
                    'token': 'x' * 32,
                    'engine_name': 'Test Engine',
                }

        self.mod.EngineClient = FakeEngineClient
        result = self.mod.pair_engine({
            'engine_url': 'http://192.168.1.50:8765',
            'pairing_code': '123456',
        })
        saved = json.loads((self.data / 'v5_settings.json').read_text(encoding='utf-8'))
        self.assertTrue(result['ok'])
        self.assertEqual('http://192.168.1.50:8765', saved['engine_url'])
        self.assertEqual('x' * 32, saved['engine_token'])
        self.assertEqual('POST', calls[0][0])
        self.assertEqual('/v1/pair', calls[0][1])
        self.assertFalse(calls[0][3]['auth'])


if __name__ == '__main__':
    unittest.main()
