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
    spec = importlib.util.spec_from_file_location('connector_alpha8_test', SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class ConnectorAlpha8Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / 'data'
        self.config = Path(self.temp.name) / 'config'
        self.data.mkdir()
        self.config.mkdir()
        (self.data / 'options.json').write_text(json.dumps({'max_snapshot_mb': 2}), encoding='utf-8')
        self.mod = load_server(str(self.data), str(self.config))
        self.mod.collect_home_assistant_inventory = lambda: {
            'states': [], 'config': {}, 'entity_registry': [], 'device_registry': [],
            'area_registry': [], 'inventory_status': {}, 'entity_validation': 'unavailable', 'warnings': [],
        }
        self.mod.collect_lovelace_inventory = lambda: ([], [])

    def tearDown(self):
        self.temp.cleanup()

    def test_packages_yaml_is_prioritised_over_large_source_tree(self):
        source = self.config / 'custom_components' / 'example'
        source.mkdir(parents=True)
        for index in range(18):
            (source / f'module_{index:02d}.py').write_text('x = "' + ('a' * 180000) + '"\n', encoding='utf-8')
        packages = self.config / 'packages'
        packages.mkdir()
        (packages / '50_curtains.yaml').write_text(
            'automation:\n  - id: curtains\n    alias: Užuolaidos\n    trigger: []\n    action:\n      - action: cover.close_cover\n        target:\n          entity_id: cover.svetaine_terasa_curtain\n',
            encoding='utf-8',
        )
        (self.config / 'configuration.yaml').write_text('homeassistant:\n  packages: !include_dir_named packages\n', encoding='utf-8')

        snapshot = self.mod.build_snapshot()
        paths = {item.get('path') for item in snapshot['files']}
        self.assertIn('packages/50_curtains.yaml', paths)
        self.assertIn('configuration.yaml', paths)
        self.assertGreaterEqual(snapshot['snapshot_scope']['included_package_yaml_files'], 1)
        self.assertEqual('root-and-packages-yaml-first', snapshot['snapshot_scope']['priority_policy'])
        self.assertGreater(snapshot['snapshot_scope']['omitted_by_budget'], 0)


if __name__ == '__main__':
    unittest.main()
