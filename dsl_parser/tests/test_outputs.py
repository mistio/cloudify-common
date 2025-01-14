########
# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

from dsl_parser import exceptions
from dsl_parser import functions
from dsl_parser.tasks import prepare_deployment_plan
from dsl_parser.tests.abstract_test_parser import AbstractTestParser


class TestOutputs(AbstractTestParser):

    def test_outputs_definition(self):
        yaml = """
node_templates: {}
outputs: {}
"""
        parsed = self.parse(yaml)
        self.assertEqual(0, len(parsed['outputs']))

    def test_outputs_valid_output(self):
        yaml = """
node_templates: {}
outputs:
    port0:
        description: p0
        value: 1234
    port1:
        description: p1
        value: some_port
    port2:
        description: p2
        value: {}
    port3:
        description: p3
        value: []
    port4:
        value: false
"""
        parsed = self.parse(yaml)
        outputs = parsed['outputs']
        self.assertEqual(5, len(parsed['outputs']))
        self.assertEqual('p0', outputs['port0']['description'])
        self.assertEqual(1234, outputs['port0']['value'])
        self.assertEqual('p1', outputs['port1']['description'])
        self.assertEqual('some_port', outputs['port1']['value'])
        self.assertEqual('p2', outputs['port2']['description'])
        self.assertEqual({}, outputs['port2']['value'])
        self.assertEqual('p3', outputs['port3']['description'])
        self.assertEqual([], outputs['port3']['value'])
        self.assertNotIn('description', outputs['port4'])
        self.assertFalse(outputs['port4']['value'])
        prepared = prepare_deployment_plan(parsed)
        self.assertEqual(parsed['outputs'], prepared['outputs'])

    def test_invalid_outputs(self):
        yaml = """
node_templates: {}
outputs:
    port:
        description: p0
"""
        self.assertRaises(exceptions.DSLParsingFormatException,
                          self.parse, yaml)

    def test_valid_get_attribute(self):
        yaml = """
node_types:
    webserver_type: {}
node_templates:
    webserver:
        type: webserver_type
outputs:
    port:
        description: p0
        value: { get_attribute: [ webserver, port ] }
"""
        parsed = self.parse(yaml)
        outputs = parsed['outputs']
        func = functions.parse(outputs['port']['value'])
        self.assertTrue(isinstance(func, functions.GetAttribute))
        self.assertEqual('webserver', func.node_name)
        self.assertEqual('port', func.attribute_path[0])
        prepared = prepare_deployment_plan(parsed)
        self.assertEqual(parsed['outputs'], prepared['outputs'])

    def test_invalid_get_attribute(self):
        yaml = """
node_templates: {}
outputs:
    port:
        description: p0
        value: { get_attribute: [ webserver, port ] }
"""
        try:
            self.parse(yaml)
            self.fail('Expected exception.')
        except KeyError as e:
            self.assertTrue('does not exist' in str(e))
        yaml = """
node_templates: {}
outputs:
    port:
        description: p0
        value: { get_attribute: aaa }
"""
        try:
            self.parse(yaml)
            self.fail('Expected exception.')
        except ValueError as e:
            self.assertTrue('Illegal arguments passed' in str(e))

    def test_valid_get_secret(self):
        yaml = """
node_types:
    webserver_type: {}
node_templates:
    webserver:
        type: webserver_type
outputs:
    port:
        description: p0
        value: { get_secret: secret_key }
"""
        parsed = self.parse(yaml)
        outputs = parsed['outputs']
        func = functions.parse(outputs['port']['value'])
        self.assertTrue(isinstance(func, functions.GetSecret))
        self.assertEqual('secret_key', func.secret_id)
        storage = self.mock_evaluation_storage()
        prepared = prepare_deployment_plan(parsed, storage.get_secret)
        self.assertEqual(parsed['outputs'], prepared['outputs'])

    def test_invalid_nested_get_attribute(self):
        yaml = """
node_types:
    webserver_type: {}
node_templates:
    webserver:
        type: webserver_type
outputs:
    endpoint:
        description: p0
        value:
            ip: 10.0.0.1
            port: { get_attribute: [ aaa, port ] }
"""
        try:
            self.parse(yaml)
            self.fail('Expected exception.')
        except KeyError as e:
            self.assertTrue('does not exist' in str(e))

    def test_valid_evaluation(self):
        yaml = """
inputs:
    input:
        default: input_value
node_types:
    webserver_type:
        properties:
            property:
                default: property_value
node_templates:
    webserver:
        type: webserver_type
outputs:
    port:
        description: p0
        value: { get_attribute: [ webserver, port ] }
    endpoint:
        value:
            port: { get_attribute: [ webserver, port ] }
    concatenated:
        value: { concat: [one,
                          {get_property: [webserver, property]},
                          {get_attribute: [webserver, attribute]},
                          {get_input: input},
                          {get_secret: secret},
                          {get_capability: [ dep_1, cap_a ]},
                          six] }
"""

        def assertion(tested):
            self.assertEqual('one', tested[0])
            self.assertEqual('property_value', tested[1])
            self.assertEqual({'get_attribute': ['webserver', 'attribute']},
                             tested[2])
            self.assertEqual('input_value', tested[3])
            self.assertEqual({'get_secret': 'secret'}, tested[4])
            self.assertEqual({'get_capability': ['dep_1', 'cap_a']}, tested[5])
            self.assertEqual('six', tested[6])

        instances = [{
            'id': 'webserver1',
            'node_id': 'webserver',
            'runtime_properties': {
                'port': 8080,
                'attribute': 'attribute_value'
            }
        }]
        nodes = [{'id': 'webserver'}]
        storage = self.mock_evaluation_storage(
            instances, nodes, capabilities={'dep_1': {'cap_a': 'value_a_1'}})

        parsed = prepare_deployment_plan(self.parse_1_1(yaml),
                                         storage.get_secret)
        concatenated = parsed['outputs']['concatenated']['value']['concat']
        assertion(concatenated)

        outputs = functions.evaluate_outputs(parsed['outputs'], storage)
        self.assertEqual(8080, outputs['port'])
        self.assertEqual(8080, outputs['endpoint']['port'])
        self.assertEqual('oneproperty_valueattribute_'
                         'valueinput_valuesecret_valuevalue_a_1six',
                         outputs['concatenated'])

    def test_unknown_node_instance_evaluation(self):
        yaml = """
node_types:
    webserver_type: {}
node_templates:
    webserver:
        type: webserver_type
outputs:
    port:
        description: p0
        value: { get_attribute: [ webserver, port ] }
"""
        parsed = self.parse(yaml)

        outputs = functions.evaluate_outputs(
            parsed['outputs'], self.mock_evaluation_storage())
        self.assertIn('Node webserver has no instances', outputs['port'])
        self.assertIn('webserver', outputs['port'])

    def test_invalid_multi_instance_evaluation(self):
        yaml = """
node_types:
    webserver_type: {}
node_templates:
    webserver:
        type: webserver_type
outputs:
    port:
        description: p0
        value: { get_attribute: [ webserver, port ] }
"""
        parsed = self.parse(yaml)

        instance = {
            'id': 'webserver1',
            'node_id': 'webserver',
            'runtime_properties': {'port': 8080}
        }
        storage = self.mock_evaluation_storage(
            node_instances=[instance, instance],
            nodes=[{'id': 'webserver'}])
        outputs = functions.evaluate_outputs(parsed['outputs'], storage)
        self.assertIn('unambiguously', outputs['port'])
        self.assertIn('webserver', outputs['port'])

    def test_get_attribute_nested_property(self):
        yaml = """
node_types:
    webserver_type: {}
node_templates:
    webserver:
        type: webserver_type
outputs:
    port:
        value: { get_attribute: [ webserver, endpoint, port ] }
    protocol:
        value: { get_attribute: [ webserver, endpoint, url, protocol ] }
    none:
        value: { get_attribute: [ webserver, endpoint, url, none ] }
"""
        parsed = self.parse(yaml)

        node_instance = {
            'id': 'webserver1',
            'node_id': 'webserver',
            'runtime_properties': {
                'endpoint': {
                    'url': {
                        'protocol': 'http'
                    },
                    'port': 8080
                }
            }
        }
        storage = self.mock_evaluation_storage(
            node_instances=[node_instance], nodes=[{'id': 'webserver'}])
        outputs = functions.evaluate_outputs(parsed['outputs'], storage)
        self.assertEqual(8080, outputs['port'])
        self.assertEqual('http', outputs['protocol'])
        self.assertIsNone(outputs['none'])

    def test_only_one_unknown_node_instance(self):
        yaml = """
node_types:
    webserver_type: {}
    unknown_type: {}
node_templates:
    webserver:
        type: webserver_type
    unknown:
        type: unknown_type
        instances:
            deploy: 0
outputs:
    port:
        value: { get_attribute: [ webserver, endpoint, port ] }
    protocol:
        value: { get_attribute: [ webserver, endpoint, url, protocol ] }
    unknown:
        value: { get_attribute: [ unknown, endpoint ] }
"""
        parsed = self.parse(yaml)

        node_instance = {
            'id': 'webserver1',
            'node_id': 'webserver',
            'runtime_properties': {
                'endpoint': {
                    'url': {
                       'protocol': 'http'
                    },
                    'port': 8080
                }
            }
        }
        storage = self.mock_evaluation_storage(
            node_instances=[node_instance], nodes=[{'id': 'webserver'}])
        outputs = functions.evaluate_outputs(parsed['outputs'], storage)

        self.assertEqual(8080, outputs['port'])
        self.assertEqual('http', outputs['protocol'])
        self.assertIn('Node unknown has no instances', outputs['unknown'])
