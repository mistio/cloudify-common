########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

from mock import Mock

from dsl_parser import functions
from dsl_parser import exceptions
from dsl_parser.tasks import prepare_deployment_plan
from dsl_parser.tests.abstract_test_parser import AbstractTestParser


class TestGetSecret(AbstractTestParser):
    secrets_yaml = """
data_types:
    agent_config_type:
        properties:
            user:
                type: string
                required: false
            key:
                type: string
                required: false
relationships:
    cloudify.relationships.contained_in: {}
plugins:
    p:
        executor: central_deployment_agent
        install: false
node_types:
    webserver_type:
        properties:
            ip:
                default: ''
            agent_config:
                type: agent_config_type
node_templates:
    node:
        type: webserver_type
    webserver:
        type: webserver_type
        properties:
            ip: { get_secret: ip }
            agent_config:
                key: { get_secret: agent_key }
                user: { get_secret: user }
        interfaces:
            test:
                op_with_no_get_secret:
                    implementation: p.p
                    inputs:
                        a: 1
                op_with_get_secret:
                    implementation: p.p
                    inputs:
                        a: { get_secret: node_template_secret_id }
        relationships:
            -   type: cloudify.relationships.contained_in
                target: node
                source_interfaces:
                    test:
                        op_with_no_get_secret:
                            implementation: p.p
                            inputs:
                                a: 1
                        op_with_get_secret:
                            implementation: p.p
                            inputs:
                                a: { get_secret: source_op_secret_id }
                target_interfaces:
                    test:
                        op_with_no_get_secret:
                            implementation: p.p
                            inputs:
                                a: 1
                        op_with_get_secret:
                            implementation: p.p
                            inputs:
                                a: { get_secret: target_op_secret_id }
outputs:
    webserver_url:
        description: Web server url
        value: { concat: ['http://', { get_secret: ip }, ':',
        { get_secret: webserver_port }] }
"""

    def test_has_intrinsic_functions_property(self):
        yaml = """
relationships:
    cloudify.relationships.contained_in: {}
plugins:
    p:
        executor: central_deployment_agent
        install: false
node_types:
    webserver_type: {}
node_templates:
    node:
        type: webserver_type
    webserver:
        type: webserver_type
        interfaces:
            test:
                op_with_no_get_secret:
                    implementation: p.p
                    inputs:
                        a: 1
                op_with_get_secret:
                    implementation: p.p
                    inputs:
                        a: { get_secret: node_template_secret_id }
        relationships:
            -   type: cloudify.relationships.contained_in
                target: node
                source_interfaces:
                    test:
                        op_with_no_get_secret:
                            implementation: p.p
                            inputs:
                                a: 1
                        op_with_get_secret:
                            implementation: p.p
                            inputs:
                                a: { get_secret: source_op_secret_id }
                target_interfaces:
                    test:
                        op_with_no_get_secret:
                            implementation: p.p
                            inputs:
                                a: 1
                        op_with_get_secret:
                            implementation: p.p
                            inputs:
                                a: { get_secret: target_op_secret_id }
"""
        parsed = prepare_deployment_plan(self.parse(yaml), self.get_secret)
        webserver_node = None
        for node in parsed.node_templates:
            if node['id'] == 'webserver':
                webserver_node = node
                break
        self.assertIsNotNone(webserver_node)

        def assertion(operations):
            op = operations['test.op_with_no_get_secret']
            self.assertIs(False, op.get('has_intrinsic_functions'))
            op = operations['test.op_with_get_secret']
            self.assertIs(True, op.get('has_intrinsic_functions'))

        assertion(webserver_node['operations'])
        assertion(webserver_node['relationships'][0]['source_operations'])
        assertion(webserver_node['relationships'][0]['target_operations'])

    def test_validate_secrets_all_valid(self):
        get_secret_mock = Mock(return_value='secret_value')
        parsed = prepare_deployment_plan(self.parse_1_3(self.secrets_yaml),
                                         get_secret_mock)
        self.assertTrue(get_secret_mock.called)
        self.assertFalse(hasattr(parsed, 'secrets'))

    def test_validate_secrets_all_invalid(self):
        # regex-OR all the possible secret names and require {7} of them,
        # because the ordering isn't guaranteed
        expected_message = (
            r"Required secrets: \[((target_op_secret_id|"
            r"node_template_secret_id|ip|agent_key|user|webserver_port|"
            r"source_op_secret_id),? ?){7}\] don't exist in this tenant"
        )

        get_secret_not_found = Mock(side_effect=NotFoundException)
        self.assertRaisesRegex(exceptions.UnknownSecretError,
                               expected_message,
                               prepare_deployment_plan,
                               self.parse_1_3(self.secrets_yaml),
                               get_secret_not_found)

    def test_validate_secrets_unexpected_exception(self):
        get_secret_exception = Mock(side_effect=TypeError)
        self.assertRaisesRegex(TypeError,
                               '',
                               prepare_deployment_plan,
                               self.parse_1_3(self.secrets_yaml),
                               get_secret_exception)

    def test_validate_secrets_some_invalid(self):
        expected_message = (
            r"Required secrets: \[((ip|source_op_secret_id),? ?){2}\] "
            r"don't exist in this tenant"
        )

        def fake_get_secret(name):
            if name in ['ip', 'source_op_secret_id']:
                raise NotFoundException()

        self.assertRaisesRegex(exceptions.UnknownSecretError,
                               expected_message,
                               prepare_deployment_plan,
                               self.parse_1_3(self.secrets_yaml),
                               fake_get_secret)

    def test_validate_secrets_without_secrets(self):
        no_secrets_yaml = """
relationships:
    cloudify.relationships.contained_in: {}
plugins:
    p:
        executor: central_deployment_agent
        install: false
node_types:
    webserver_type: {}
node_templates:
    node:
        type: webserver_type
    webserver:
        type: webserver_type
        interfaces:
            test:
                op_with_no_get_secret:
                    implementation: p.p
                    inputs:
                        a: 1
        relationships:
            -   type: cloudify.relationships.contained_in
                target: node
                source_interfaces:
                    test:
                        op_with_no_get_secret:
                            implementation: p.p
                            inputs:
                                a: 1
                target_interfaces:
                    test:
                        op_with_no_get_secret:
                            implementation: p.p
                            inputs:
                                a: 1
"""
        get_secret_mock = Mock(return_value='secret_value')
        parsed = prepare_deployment_plan(self.parse_1_3(no_secrets_yaml),
                                         get_secret_mock)
        self.assertFalse(get_secret_mock.called)
        self.assertFalse(hasattr(parsed, 'secrets'))


class NotFoundException(Exception):
    status_code = 404


class TestEvaluateFunctions(AbstractTestParser):
    def test_evaluate_functions(self):

        payload = {
            'a': {'get_secret': 'id_a'},
            'b': {'get_secret': 'id_b'},
            'c': {'get_secret': 'id_c'},
            'd': {'get_secret': 'id_d'},
            'f': {'concat': [
                {'get_secret': 'id_a'},
                {'get_secret': 'id_b'},
                {'get_secret': 'id_c'},
                {'get_secret': 'id_d'}
            ]}
        }

        functions.evaluate_functions(
            payload, {}, self.mock_evaluation_storage())

        self.assertEqual(payload['a'], 'id_a_value')
        self.assertEqual(payload['b'], 'id_b_value')
        self.assertEqual(payload['c'], 'id_c_value')
        self.assertEqual(payload['d'], 'id_d_value')
        self.assertEqual(payload['f'], 'id_a_valueid_b_value'
                                       'id_c_valueid_d_value')

    def test_node_template_properties_simple(self):
        yaml = """
node_types:
    type:
        properties:
            property: {}
node_templates:
    node:
        type: type
        properties:
            property: { get_secret: secret }
"""
        parsed = prepare_deployment_plan(self.parse_1_3(yaml),
                                         self.get_secret)
        node = self.get_node_by_name(parsed, 'node')
        self.assertEqual({'get_secret': 'secret'},
                         node['properties']['property'])

        functions.evaluate_functions(
            parsed, {}, self.mock_evaluation_storage())
        self.assertEqual(node['properties']['property'], 'secret_value')


class TestNestedGetSecret(AbstractTestParser):
    def setUp(self):
        super(TestNestedGetSecret, self).setUp()
        self.mock_storage = self.mock_evaluation_storage(
            secrets={
                'no_parse_secret': '}',
                'hello_secret': '{"hello": "test"}',
                'soft_secret': '["say", "wave"]',
                'big_secret': '{"something": [{"like": ["this", "that"]}]}',
            },
        )

    def test_get_secret_empty_list(self):
        yaml = """
outputs:
  secret:
    value: { get_secret: [] }
"""
        with self.assertRaisesRegex(exceptions.FunctionValidationError,
                                    ".*2 elements.*"):
            self.parse_1_3(yaml)

    def test_get_secret_list_with_1_element(self):
        yaml = """
outputs:
  secret:
    value: { get_secret: [my_secret] }
"""
        with self.assertRaisesRegex(exceptions.FunctionValidationError,
                                    ".*2 elements.*"):
            self.parse_1_3(yaml)

    def test_get_secret_list_secret_does_not_exist(self):
        yaml = """
outputs:
  secret:
    value: { get_secret: [missing_secret, test] }
"""
        parsed = self.parse_1_3(yaml)
        get_secret_not_found = Mock(side_effect=NotFoundException)
        with self.assertRaisesRegex(exceptions.UnknownSecretError,
                                    "Required secret.*missing_secret.*"):
            prepare_deployment_plan(parsed, get_secret_not_found)

    def test_get_secret_not_json_parseable(self):
        payload = {
            'a': {'get_secret': ['no_parse_secret', 'test']},
        }
        with self.assertRaisesRegex(exceptions.FunctionEvaluationError,
                                    '.*not parse.*no_parse_secret.*'):
            functions.evaluate_functions(
                payload, {}, self.mock_storage)

    def test_get_secret_wrong_key_name(self):
        payload = {
            'a': {'get_secret': ['hello_secret', 'test']},
        }
        with self.assertRaisesRegex(exceptions.FunctionEvaluationError,
                                    '.*not find.*test.*hello_secret.*'):
            functions.evaluate_functions(
                payload, {}, self.mock_storage)

    def test_get_secret_list_bad_index(self):
        payload = {
            'a': {'get_secret': ['soft_secret', 'somestring']},
        }
        with self.assertRaisesRegex(exceptions.FunctionEvaluationError,
                                    '.*not find.*somestring.*soft_secret.*'):
            functions.evaluate_functions(
                payload, {}, self.mock_storage)

    def test_get_secret_list_index_out_of_bounds(self):
        payload = {
            'a': {'get_secret': ['soft_secret', 3]},
        }
        with self.assertRaisesRegex(exceptions.FunctionEvaluationError,
                                    '.*not find.*3.*soft_secret.*'):
            functions.evaluate_functions(
                payload, {}, self.mock_storage)

    def test_get_secret_bad_key_mid_list(self):
        payload = {
            'a': {'get_secret': ['big_secret', 'something', 0, 'lkie', 1]},
        }
        with self.assertRaisesRegex(exceptions.FunctionEvaluationError,
                                    '.*not find.*lkie.*big_secret.*'):
            functions.evaluate_functions(
                payload, {}, self.mock_storage)

    def test_get_nested_secret_from_dict(self):
        payload = {
            'a': {'get_secret': ['hello_secret', 'hello']},
        }
        functions.evaluate_functions(
            payload, {}, self.mock_storage)
        self.assertEqual(payload['a'], 'test')

    def test_get_nested_secret_from_list(self):
        payload = {
            'a': {'get_secret': ['soft_secret', 1]},
        }
        functions.evaluate_functions(
            payload, {}, self.mock_storage)
        self.assertEqual(payload['a'], 'wave')

    def test_get_deeply_nested_secret(self):
        payload = {
            'a': {'get_secret': ['big_secret', 'something', 0, 'like', 1]},
        }
        functions.evaluate_functions(payload, {}, self.mock_storage)
        self.assertEqual(payload['a'], 'that')
