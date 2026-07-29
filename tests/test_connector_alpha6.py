import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SERVER_PATH = Path(__file__).resolve().parents[1] / 'ai_supervisor_connector' / 'rootfs' / 'opt' / 'ai_supervisor_connector' / 'server.py'


def load_server(temp_dir: str):
    os.environ['DATA_DIR'] = temp_dir
    os.environ['SUPERVISOR_TOKEN'] = 'test-token'
    spec = importlib.util.spec_from_file_location('connector_alpha6_test', SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class ConnectorAlpha6Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.mod = load_server(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_device_compaction_omits_sensitive_identifiers(self):
        value = self.mod.compact_device_registry({
            'id': 'device1', 'name': 'Test', 'serial_number': 'secret',
            'identifiers': [['x', 'y']], 'connections': [['mac', 'AA:BB']],
        })
        self.assertEqual('device1', value['id'])
        self.assertNotIn('serial_number', value)
        self.assertNotIn('identifiers', value)
        self.assertNotIn('connections', value)

    def test_websocket_inventory_is_compacted_and_complete(self):
        ws_result = ({
            'states': [{'entity_id': 'cover.test', 'state': 'open', 'attributes': {'friendly_name': 'Test'}}],
            'config': {'version': '2026.7.0'},
            'entity_registry': [{'entity_id': 'cover.test', 'platform': 'demo', 'device_id': 'd1'}],
            'device_registry': [{'id': 'd1', 'name': 'Curtain'}],
            'area_registry': [{'area_id': 'living', 'name': 'Living'}],
        }, [])
        with patch.object(self.mod.HAWebSocketClient, 'call_many', return_value=ws_result):
            inventory = self.mod.collect_home_assistant_inventory()
        self.assertEqual('complete', inventory['entity_validation'])
        self.assertEqual(1, len(inventory['states']))
        self.assertEqual(1, len(inventory['entity_registry']))
        self.assertEqual(1, len(inventory['device_registry']))
        self.assertEqual(1, len(inventory['area_registry']))

    def test_file_kind_classifies_yaml_and_source(self):
        self.assertEqual('home_assistant_yaml', self.mod.file_kind(Path('packages/test.yaml')))
        self.assertEqual('source_code', self.mod.file_kind(Path('custom_components/x/client.py')))
        self.assertEqual('documentation', self.mod.file_kind(Path('README.md')))

    def test_component_catalog_maps_package_automation_script_and_helper(self):
        files = [{
            'path': 'packages/uzuolaidos.yaml',
            'kind': 'home_assistant_yaml',
            'content': """
input_boolean:
  uzuolaidos_automatika:
    name: Uzuolaidu automatika
script:
  uzuolaidos_vykdytojas:
    alias: Uzuolaidu vykdytojas
    sequence:
      - service: cover.set_cover_position
        target:
          entity_id: cover.miegamasis_curtain
automation:
  - id: uzuolaidos-centras
    alias: Uzuolaidu centras
    trigger:
      - platform: state
        entity_id: input_boolean.uzuolaidos_automatika
    action:
      - service: script.uzuolaidos_vykdytojas
""",
        }]
        components, warnings = self.mod.collect_component_catalog(files)
        self.assertEqual([], warnings)
        kinds = {item['kind'] for item in components}
        self.assertIn('automation', kinds)
        self.assertIn('script', kinds)
        self.assertIn('input_boolean', kinds)
        script = next(item for item in components if item['kind'] == 'script')
        self.assertIn('cover.miegamasis_curtain', script['control_targets'])

    def test_component_catalog_understands_root_list_automation_include(self):
        files = [{
            'path': 'automations/uzuolaidos.yaml',
            'kind': 'home_assistant_yaml',
            'content': """
- id: uzuolaidos-centras
  alias: Uzuolaidu centras
  triggers:
    - trigger: state
      entity_id: input_boolean.uzuolaidos_automatika
  actions:
    - action: script.uzuolaidos_vykdytojas
""",
        }]
        components, warnings = self.mod.collect_component_catalog(files)
        self.assertEqual([], warnings)
        self.assertEqual(1, len(components))
        self.assertEqual('automation', components[0]['kind'])
        self.assertIn('script.uzuolaidos_vykdytojas', components[0]['references'])

    def test_component_catalog_understands_root_mapping_script_include(self):
        files = [{
            'path': 'scripts/uzuolaidos.yaml',
            'kind': 'home_assistant_yaml',
            'content': """
uzuolaidos_vykdytojas:
  alias: Uzuolaidu vykdytojas
  sequence:
    - action: cover.set_cover_position
      target:
        entity_id: cover.svetaine_terasa_curtain
""",
        }]
        components, warnings = self.mod.collect_component_catalog(files)
        self.assertEqual([], warnings)
        self.assertEqual(1, len(components))
        self.assertEqual('script', components[0]['kind'])
        self.assertEqual('script.uzuolaidos_vykdytojas', components[0]['entity_id'])
        self.assertIn('cover.svetaine_terasa_curtain', components[0]['control_targets'])

    def test_dashboard_summary_extracts_views_and_entities(self):
        config = {
            'views': [{
                'title': 'Uzuolaidos', 'path': 'uzuolaidos',
                'cards': [{'type': 'entities', 'entities': ['cover.miegamasis_curtain', 'input_boolean.uzuolaidos_automatika']}],
            }]
        }
        result = self.mod.summarize_dashboard('alksniu-namas', 'Alksniu namas', config)
        self.assertEqual(1, result['view_count'])
        self.assertIn('cover.miegamasis_curtain', result['entity_ids'])
        self.assertEqual('uzuolaidos', result['views'][0]['path'])

    def test_config_check_normalises_empty_supervisor_data_as_valid(self):
        with patch.object(self.mod.SupervisorClient, 'request', return_value={}):
            result = self.mod.HAClient().check_config()
        self.assertEqual('valid', result['result'])
        self.assertEqual('supervisor/core/check', result['source'])


if __name__ == '__main__':
    unittest.main()
