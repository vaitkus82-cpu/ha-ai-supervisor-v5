import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

SERVER_PATH = Path(__file__).resolve().parents[1] / 'ai_supervisor_connector' / 'rootfs' / 'opt' / 'ai_supervisor_connector' / 'server.py'


def load_server(temp_dir: str):
    os.environ['DATA_DIR'] = temp_dir
    os.environ['SUPERVISOR_TOKEN'] = 'test-token'
    spec = importlib.util.spec_from_file_location('connector_alpha8_test', SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class ConnectorAlpha8Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.mod = load_server(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def package_text(self):
        return '''
input_boolean:
  uzuolaidos_rankinis:
    name: Užuolaidų rankinis režimas
input_datetime:
  uzuolaidos_rankinis_iki:
    name: Užuolaidų rankinis iki
script:
  uzuolaidos_vykdytojas:
    alias: Užuolaidų vykdytojas
    sequence:
      - variables:
          cover_entity: cover.svetaine_terasa_curtain
          source_cover: cover.miegamasis_curtain
      - condition: template
        value_template: "{{ states('cover.svetaine_terasa_curtain') not in ['unknown', 'unavailable'] }}"
      - action: cover.set_cover_position
        target:
          entity_id: "{{ cover_entity }}"
        data:
          position: 50
automation:
  - id: uzuolaidos-centras
    alias: Užuolaidų centras
    trigger:
      - platform: state
        entity_id: input_boolean.uzuolaidos_rankinis
    action:
      - variables:
          source_cover: cover.svetaine_kaire_curtain
      - condition: template
        value_template: "{{ state_attr('cover.miegamasis_curtain', 'current_position') is not none }}"
      - action: script.uzuolaidos_vykdytojas
'''

    def test_package_jinja_and_custom_fields_are_catalogued(self):
        files = [{
            'path': 'packages/50_curtains.yaml',
            'kind': 'home_assistant_yaml',
            'content': self.package_text(),
        }]
        components, warnings = self.mod.collect_component_catalog(files)
        self.assertEqual([], warnings)
        kinds = {item['kind'] for item in components}
        self.assertTrue({'automation', 'script', 'input_boolean', 'input_datetime'} <= kinds)
        refs = {entity for item in components for entity in item.get('references', [])}
        self.assertIn('cover.svetaine_terasa_curtain', refs)
        self.assertIn('cover.svetaine_kaire_curtain', refs)
        self.assertIn('cover.miegamasis_curtain', refs)
        raw_or_merged = [item for item in components if item.get('catalog_source') in {'raw_yaml_text', 'parsed_plus_raw'}]
        self.assertTrue(raw_or_merged)

    def test_raw_text_fallback_survives_parser_failure(self):
        text = self.package_text() + '\ninput_boolean:\n  duplicate_key:\n    name: duplicate\n'
        files = [{'path': 'packages/50_curtains.yaml', 'kind': 'home_assistant_yaml', 'content': text}]
        components, warnings = self.mod.collect_component_catalog(files)
        self.assertTrue(warnings)
        self.assertTrue(any(item['kind'] == 'automation' for item in components))
        self.assertTrue(any(item['kind'] == 'script' for item in components))
        refs = {entity for item in components for entity in item.get('references', [])}
        self.assertIn('cover.svetaine_terasa_curtain', refs)


if __name__ == '__main__':
    unittest.main()
