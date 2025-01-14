########
# Copyright (c) 2013-2019 Cloudify Platform Ltd. All rights reserved
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

import os
import yaml as yml

from dsl_parser._compat import pathname2url
from dsl_parser.constants import TYPE_HIERARCHY
from dsl_parser.parser import (parse as dsl_parse,
                               parse_from_path)
from dsl_parser.tests.abstract_test_parser import AbstractTestParser
from dsl_parser import (models,
                        version,
                        exceptions,
                        constants)


def op_struct(plugin_name,
              mapping,
              inputs=None,
              executor=None,
              max_retries=None,
              retry_interval=None,
              timeout=None,
              timeout_recoverable=None):
    if not inputs:
        inputs = {}
    result = {
        'plugin': plugin_name,
        'operation': mapping,
        'inputs': inputs,
        'executor': executor,
        'has_intrinsic_functions': False,
        'max_retries': max_retries,
        'retry_interval': retry_interval,
        'timeout': timeout,
        'timeout_recoverable': timeout_recoverable
    }
    return result


def workflow_op_struct(plugin_name,
                       mapping,
                       parameters=None,
                       is_cascading=False):

    if not parameters:
        parameters = {}
    return {
        'plugin': plugin_name,
        'operation': mapping,
        'parameters': parameters,
        'is_cascading': is_cascading
    }


class BaseParserApiTest(AbstractTestParser):
    def _assert_blueprint(self, result):
        node = result['nodes'][0]
        self.assertEqual('test_type', node['type'])
        plugin_props = [p for p in node['plugins']
                        if p['name'] == 'test_plugin'][0]
        self.assertEqual(11, len(plugin_props))
        self.assertEqual('test_plugin',
                         plugin_props[constants.PLUGIN_NAME_KEY])
        operations = node['operations']
        self.assertEqual(op_struct('test_plugin', 'install',
                                   executor='central_deployment_agent'),
                         operations['install'])
        self.assertEqual(op_struct('test_plugin', 'install',
                                   executor='central_deployment_agent'),
                         operations['test_interface1.install'])
        self.assertEqual(op_struct('test_plugin', 'terminate',
                                   executor='central_deployment_agent'),
                         operations['terminate'])
        self.assertEqual(op_struct('test_plugin', 'terminate',
                                   executor='central_deployment_agent'),
                         operations['test_interface1.terminate'])

    def _assert_minimal_blueprint(self, result, expected_type='test_type'):
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_node', node['name'])
        self.assertEqual(expected_type, node['type'])
        self.assertEqual('val', node['properties']['key'])


class TestParserApi(BaseParserApiTest):
    def test_empty_blueprint_with_dsl_version(self):
        self.parse('')

    def test_minimal_blueprint(self):
        result = self.parse(self.MINIMAL_BLUEPRINT)
        self._assert_minimal_blueprint(result)

    def test_import_from_path(self):
        yaml = self.create_yaml_with_imports([self.MINIMAL_BLUEPRINT])
        result = self.parse(yaml)
        self._assert_minimal_blueprint(result)

    def test_type_with_single_explicit_interface_and_plugin(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + self.BASIC_PLUGIN + """
node_types:
    test_type:
        interfaces:
            test_interface1:
                install:
                    implementation: test_plugin.install
                    inputs: {}
                terminate:
                    implementation: test_plugin.terminate
                    inputs: {}
                start:
                    implementation: test_plugin.start
                    inputs: {}
        properties:
            install_agent:
                default: false
            key: {}
            number:
                default: 80
            boolean:
                default: false
            complex:
                default:
                    key1: value1
                    key2: value2
            """

        result = self.parse(yaml)
        self._assert_blueprint(result)

    def test_type_with_interfaces_and_basic_plugin(self):
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS
        result = self.parse(yaml)
        self._assert_blueprint(result)
        first_node = result['nodes'][0]
        parsed_plugins = first_node['plugins']
        expected_plugins = [{
            constants.PLUGIN_NAME_KEY: 'test_plugin',
            constants.PLUGIN_SOURCE_KEY: 'dummy',
            constants.PLUGIN_INSTALL_KEY: True,
            constants.PLUGIN_EXECUTOR_KEY: constants.CENTRAL_DEPLOYMENT_AGENT,
            constants.PLUGIN_INSTALL_ARGUMENTS_KEY: None,
            constants.PLUGIN_PACKAGE_NAME: None,
            constants.PLUGIN_PACKAGE_VERSION: None,
            constants.PLUGIN_SUPPORTED_PLATFORM: None,
            constants.PLUGIN_DISTRIBUTION: None,
            constants.PLUGIN_DISTRIBUTION_VERSION: None,
            constants.PLUGIN_DISTRIBUTION_RELEASE: None
        }]
        self.assertEqual(parsed_plugins, expected_plugins)

    def test_type_with_interface_and_plugin_with_install_args(self):
        yaml = self.PLUGIN_WITH_INTERFACES_AND_PLUGINS_WITH_INSTALL_ARGS
        result = self.parse(yaml,
                            dsl_version=self.BASIC_VERSION_SECTION_DSL_1_1)
        self._assert_blueprint(result)
        first_node = result['nodes'][0]
        parsed_plugins = first_node['plugins']
        expected_plugins = [{
            constants.PLUGIN_NAME_KEY: 'test_plugin',
            constants.PLUGIN_SOURCE_KEY: 'dummy',
            constants.PLUGIN_INSTALL_KEY: True,
            constants.PLUGIN_EXECUTOR_KEY: constants.CENTRAL_DEPLOYMENT_AGENT,
            constants.PLUGIN_INSTALL_ARGUMENTS_KEY: '-r requirements.txt',
            constants.PLUGIN_PACKAGE_NAME: None,
            constants.PLUGIN_PACKAGE_VERSION: None,
            constants.PLUGIN_SUPPORTED_PLATFORM: None,
            constants.PLUGIN_DISTRIBUTION: None,
            constants.PLUGIN_DISTRIBUTION_VERSION: None,
            constants.PLUGIN_DISTRIBUTION_RELEASE: None
        }]
        self.assertEqual(parsed_plugins, expected_plugins)

    def test_dsl_with_type_with_operation_mappings(self):
        yaml = self.create_yaml_with_imports(
            [self.BASIC_NODE_TEMPLATES_SECTION, self.BASIC_PLUGIN]) + """
node_types:
    test_type:
        properties:
            key: {}
        interfaces:
            test_interface1:
                install:
                    implementation: test_plugin.install
                    inputs: {}
                terminate:
                    implementation: test_plugin.terminate
                    inputs: {}
            test_interface2:
                start:
                    implementation: other_test_plugin.start
                    inputs: {}
                shutdown:
                    implementation: other_test_plugin.shutdown
                    inputs: {}

plugins:
    other_test_plugin:
        executor: central_deployment_agent
        source: dummy
"""
        result = self.parse(yaml)
        node = result['nodes'][0]
        self._assert_blueprint(result)

        operations = node['operations']
        self.assertEqual(op_struct('other_test_plugin', 'start',
                                   executor='central_deployment_agent'),
                         operations['start'])
        self.assertEqual(op_struct('other_test_plugin', 'start',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.start'])
        self.assertEqual(op_struct('other_test_plugin', 'shutdown',
                                   executor='central_deployment_agent'),
                         operations['shutdown'])
        self.assertEqual(op_struct('other_test_plugin', 'shutdown',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.shutdown'])

    def test_recursive_imports(self):
        bottom_level_yaml = self.BASIC_TYPE
        bottom_file_name = self.make_yaml_file(bottom_level_yaml)

        mid_level_yaml = self.BASIC_PLUGIN + """
imports:
    -   {0}""".format(bottom_file_name)
        mid_file_name = self.make_yaml_file(mid_level_yaml)

        top_level_yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
imports:
    -   {0}""".format(mid_file_name)

        result = self.parse(top_level_yaml)
        self._assert_blueprint(result)

    def test_parse_dsl_from_file(self):
        filename = self.make_yaml_file(self.BASIC_VERSION_SECTION_DSL_1_0 +
                                       self.MINIMAL_BLUEPRINT)
        result = parse_from_path(filename)
        self._assert_minimal_blueprint(result)

    def test_import_empty_list(self):
        yaml = self.MINIMAL_BLUEPRINT + """
imports: []
        """
        result = self.parse(yaml)
        self._assert_minimal_blueprint(result)

    def test_blueprint_description_field(self):
        yaml = self.MINIMAL_BLUEPRINT + self.BASIC_VERSION_SECTION_DSL_1_2 +\
            """
description: sample description
        """
        result = self.parse(yaml)
        self._assert_minimal_blueprint(result)
        self.assertIn('description', result)
        self.assertEqual('sample description', result['description'])

    def test_blueprint_description_field_omitted(self):
        yaml = self.MINIMAL_BLUEPRINT + self.BASIC_VERSION_SECTION_DSL_1_2
        result = self.parse(yaml)
        self._assert_minimal_blueprint(result)
        self.assertIn('description', result)
        self.assertEqual(None, result['description'])

    def test_diamond_imports(self):
        bottom_level_yaml = self.BASIC_TYPE
        bottom_file_name = self.make_yaml_file(bottom_level_yaml)

        mid_level_yaml = self.BASIC_PLUGIN + """
imports:
    -   {0}""".format(bottom_file_name)
        mid_file_name = self.make_yaml_file(mid_level_yaml)

        mid_level_yaml2 = """
imports:
    -   {0}""".format(bottom_file_name)
        mid_file_name2 = self.make_yaml_file(mid_level_yaml2)

        top_level_yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
imports:
    -   {0}
    -   {1}""".format(mid_file_name, mid_file_name2)
        result = self.parse(top_level_yaml)
        self._assert_blueprint(result)

    def _create_importable_yaml_for_version_1_3_and_above(self, importable):
        imported_yaml = self.make_yaml_file(
            self.BASIC_TYPE +
            self.BASIC_PLUGIN +
            importable)
        main_yaml = """
imports:
    -   {0}""".format(imported_yaml) + \
            self.BASIC_NODE_TEMPLATES_SECTION + \
            self.BASIC_INPUTS + \
            self.BASIC_OUTPUTS

        return main_yaml

    def _verify_1_2_and_below_non_mergeable_imports(self,
                                                    importable,
                                                    import_type):
        main_yaml = self._create_importable_yaml_for_version_1_3_and_above(
            importable)
        with self.assertRaises(exceptions.DSLParsingLogicException) as cm:
            self.parse_1_2(main_yaml)
        self.assertIn("Import failed: non-mergeable field: '{0}'".format(
            import_type), str(cm.exception))

    def _verify_1_3_and_above_mergeable_imports(self, importable):
        main_yaml = self._create_importable_yaml_for_version_1_3_and_above(
            importable)
        result = self.parse_1_3(main_yaml)
        self._assert_blueprint(result)

    def test_version_1_2_and_above_input_imports(self):
        importable = """
inputs:
    test_input2:
        default: value
"""
        self._verify_1_2_and_below_non_mergeable_imports(
            importable, 'inputs')
        self._verify_1_3_and_above_mergeable_imports(importable)

    def test_version_1_2_and_above_node_template_imports(self):
        importable = """
node_templates:
    test_node2:
        type: test_type
        properties:
            key: "val"
"""
        self._verify_1_2_and_below_non_mergeable_imports(
            importable, 'node_templates')
        self._verify_1_3_and_above_mergeable_imports(importable)

    def test_version_1_2_and_above_output_imports(self):
        importable = """
outputs:
    test_output2:
        value: value
"""
        self._verify_1_2_and_below_non_mergeable_imports(
            importable, 'outputs')
        self._verify_1_3_and_above_mergeable_imports(importable)

    def test_node_get_type_properties_including_overriding_properties(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
node_types:
    test_type:
        properties:
            key:
                default: "not_val"
            key2:
                default: "val2"
    """
        result = self.parse(yaml)
        # this will also check property "key" = "val"
        self._assert_minimal_blueprint(result)
        node = result['nodes'][0]
        self.assertEqual('val2', node['properties']['key2'])

    def test_type_properties_empty_properties(self):
        yaml = """
node_templates:
    test_node:
        type: test_type
node_types:
    test_type:
        properties: {}
"""
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_node', node['name'])
        self.assertEqual('test_type', node['type'])

    def test_type_properties_empty_property(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
node_types:
    test_type:
        properties:
            key: {}
"""
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_node', node['name'])
        self.assertEqual('test_type', node['type'])
        self.assertEqual('val', node['properties']['key'])
        # TODO: assert node-type's default and description values once
        # 'node_types' is part of the parser's output

    def test_type_properties_property_with_description_only(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
node_types:
    test_type:
        properties:
            key:
                description: property_desc
"""
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_node', node['name'])
        self.assertEqual('test_type', node['type'])
        self.assertEqual('val', node['properties']['key'])
        # TODO: assert type's default and description values once 'type' is
        # part of the parser's output

    def test_type_properties_standard_property(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
node_types:
    test_type:
        properties:
            key:
                default: val
                description: property_desc
                type: string
"""
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_node', node['name'])
        self.assertEqual('test_type', node['type'])
        self.assertEqual('val', node['properties']['key'])
        # TODO: assert type's default and description values once 'type' is
        # part of the parser's output

    def test_type_properties_derivation(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
node_types:
    test_type:
        properties:
            key:
                default: "not_val"
            key2:
                default: "val2"
        derived_from: "test_type_parent"

    test_type_parent:
        properties:
            key:
                default: "val1_parent"
            key2:
                default: "val2_parent"
            key3:
                default: "val3_parent"
    """
        result = self.parse(yaml)
        # this will also check property "key" = "val"
        self._assert_minimal_blueprint(result)
        node = result['nodes'][0]
        self.assertEqual('val2', node['properties']['key2'])
        self.assertEqual('val3_parent', node['properties']['key3'])

    def test_empty_types_hierarchy_in_node(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
node_types:
    test_type:
        properties:
            key:
                default: "not_val"
            key2:
                default: "val2"
    """
        result = self.parse(yaml)
        node = result['nodes'][0]
        self.assertEqual(1, len(node[TYPE_HIERARCHY]))
        self.assertEqual('test_type', node[TYPE_HIERARCHY][0])

    def test_types_hierarchy_in_node(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
node_types:
    test_type:
        derived_from: "test_type_parent"
        properties:
            key:
                default: "not_val"
            key2:
                default: "val2"
    test_type_parent: {}
    """
        result = self.parse(yaml)
        node = result['nodes'][0]
        self.assertEqual(2, len(node[TYPE_HIERARCHY]))
        self.assertEqual('test_type_parent', node[TYPE_HIERARCHY][0])
        self.assertEqual('test_type', node[TYPE_HIERARCHY][1])

    def test_types_hierarchy_order_in_node(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
node_types:
    test_type:
        derived_from: "test_type_parent"
        properties:
            key:
                default: "not_val"
            key2:
                default: "val2"
    test_type_parent:
        derived_from: "parent_type"

    parent_type: {}
    """
        result = self.parse(yaml)
        node = result['nodes'][0]
        self.assertEqual(3, len(node[TYPE_HIERARCHY]))
        self.assertEqual('parent_type', node[TYPE_HIERARCHY][0])
        self.assertEqual('test_type_parent', node[TYPE_HIERARCHY][1])
        self.assertEqual('test_type', node[TYPE_HIERARCHY][2])

    def test_type_properties_recursive_derivation(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
node_types:
    test_type:
        properties:
            key:
                default: "not_val"
            key2:
                default: "val2"
        derived_from: "test_type_parent"

    test_type_parent:
        properties:
            key:
                default: "val_parent"
            key2:
                default: "val2_parent"
            key4:
                default: "val4_parent"
        derived_from: "test_type_grandparent"

    test_type_grandparent:
        properties:
            key:
                default: "val1_grandparent"
            key2:
                default: "val2_grandparent"
            key3:
                default: "val3_grandparent"
        derived_from: "test_type_grandgrandparent"

    test_type_grandgrandparent: {}
    """
        result = self.parse(yaml)
        # this will also check property "key" = "val"
        self._assert_minimal_blueprint(result)
        node = result['nodes'][0]
        self.assertEqual('val2', node['properties']['key2'])
        self.assertEqual('val3_grandparent', node['properties']['key3'])
        self.assertEqual('val4_parent', node['properties']['key4'])

    def test_type_interface_derivation(self):
        yaml = self.create_yaml_with_imports(
            [self.BASIC_NODE_TEMPLATES_SECTION, self.BASIC_PLUGIN]) + """
node_types:
    test_type:
        properties:
            key: {}
        interfaces:
            test_interface1:
                install:
                    implementation: test_plugin.install
                    inputs: {}
                terminate:
                    implementation: test_plugin.terminate
                    inputs: {}
            test_interface2:
                start:
                    implementation: test_plugin2.start
                    inputs: {}
                stop:
                    implementation: test_plugin2.stop
                    inputs: {}
            test_interface3:
                op1:
                    implementation: test_plugin3.op
                    inputs: {}
        derived_from: test_type_parent

    test_type_parent:
        interfaces:
            test_interface1:
                install:
                    implementation: nop_plugin.install
                    inputs: {}
                terminate:
                    implementation: nop_plugin.install
                    inputs: {}
            test_interface2:
                start:
                    implementation: test_plugin2.start
                    inputs: {}
                stop:
                    implementation: test_plugin2.stop
                    inputs: {}
            test_interface3:
                op1:
                    implementation: test_plugin3.op
                    inputs: {}
            test_interface4:
                op2:
                    implementation: test_plugin4.op2
                    inputs: {}

plugins:
    test_plugin2:
        executor: central_deployment_agent
        source: dummy
    test_plugin3:
        executor: central_deployment_agent
        source: dummy
    test_plugin4:
        executor: central_deployment_agent
        source: dummy
"""
        result = self.parse(yaml)
        self._assert_blueprint(result)
        node = result['nodes'][0]
        operations = node['operations']
        self.assertEqual(12, len(operations))
        self.assertEqual(op_struct('test_plugin2', 'start',
                                   executor='central_deployment_agent'),
                         operations['start'])
        self.assertEqual(op_struct('test_plugin2', 'start',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.start'])
        self.assertEqual(op_struct('test_plugin2', 'stop',
                                   executor='central_deployment_agent'),
                         operations['stop'])
        self.assertEqual(op_struct('test_plugin2', 'stop',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.stop'])
        self.assertEqual(op_struct('test_plugin3', 'op',
                                   executor='central_deployment_agent'),
                         operations['op1'])
        self.assertEqual(op_struct('test_plugin3', 'op',
                                   executor='central_deployment_agent'),
                         operations['test_interface3.op1'])
        self.assertEqual(op_struct('test_plugin4', 'op2',
                                   executor='central_deployment_agent'),
                         operations['op2'])
        self.assertEqual(op_struct('test_plugin4', 'op2',
                                   executor='central_deployment_agent'),
                         operations['test_interface4.op2'])
        self.assertEqual(4, len(node['plugins']))

    def test_type_interface_recursive_derivation(self):
        yaml = self.create_yaml_with_imports(
            [self.BASIC_NODE_TEMPLATES_SECTION, self.BASIC_PLUGIN]) + """
node_types:
    test_type:
        properties:
            key: {}
        interfaces:
            test_interface1:
                install:
                    implementation: test_plugin.install
                    inputs: {}
                terminate:
                    implementation: test_plugin.terminate
                    inputs: {}
        derived_from: test_type_parent

    test_type_parent:
        derived_from: test_type_grandparent

    test_type_grandparent:
        interfaces:
            test_interface1:
                install:
                    implementation: non_plugin.install
                    inputs: {}
                terminate:
                    implementation: non_plugin.terminate
                    inputs: {}
            test_interface2:
                start:
                    implementation: test_plugin2.start
                    inputs: {}
                stop:
                    implementation: test_plugin2.stop
                    inputs: {}

plugins:
    test_plugin2:
        executor: central_deployment_agent
        source: dummy
"""
        result = self.parse(yaml)
        self._assert_blueprint(result)
        node = result['nodes'][0]
        operations = node['operations']
        self.assertEqual(8, len(operations))
        self.assertEqual(op_struct('test_plugin2', 'start',
                                   executor='central_deployment_agent'),
                         operations['start'])
        self.assertEqual(op_struct('test_plugin2', 'start',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.start'])
        self.assertEqual(op_struct('test_plugin2', 'stop',
                                   executor='central_deployment_agent'),
                         operations['stop'])
        self.assertEqual(op_struct('test_plugin2', 'stop',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.stop'])
        self.assertEqual(2, len(node['plugins']))

    def test_two_explicit_interfaces_with_same_operation_name(self):
        yaml = self.create_yaml_with_imports(
            [self.BASIC_NODE_TEMPLATES_SECTION, self.BASIC_PLUGIN]) + """
node_types:
    test_type:
        properties:
            key: {}
        interfaces:
            test_interface1:
                install:
                    implementation: test_plugin.install
                    inputs: {}
                terminate:
                    implementation: test_plugin.terminate
                    inputs: {}
            test_interface2:
                install:
                    implementation: other_test_plugin.install
                    inputs: {}
                shutdown:
                    implementation: other_test_plugin.shutdown
                    inputs: {}
plugins:
    other_test_plugin:
        executor: central_deployment_agent
        source: dummy
"""
        result = self.parse(yaml)
        node = result['nodes'][0]
        self.assertEqual('test_type', node['type'])
        operations = node['operations']
        self.assertEqual(op_struct('test_plugin', 'install',
                                   executor='central_deployment_agent'),
                         operations['test_interface1.install'])
        self.assertEqual(op_struct('test_plugin', 'terminate',
                                   executor='central_deployment_agent'),
                         operations['terminate'])
        self.assertEqual(op_struct('test_plugin', 'terminate',
                                   executor='central_deployment_agent'),
                         operations['test_interface1.terminate'])
        self.assertEqual(op_struct('other_test_plugin', 'install',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.install'])
        self.assertEqual(op_struct('other_test_plugin', 'shutdown',
                                   executor='central_deployment_agent'),
                         operations['shutdown'])
        self.assertEqual(op_struct('other_test_plugin', 'shutdown',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.shutdown'])
        self.assertEqual(6, len(operations))

    def test_relative_path_import(self):
        bottom_level_yaml = self.BASIC_TYPE
        self.make_file_with_name(bottom_level_yaml, 'bottom_level.yaml')

        mid_level_yaml = self.BASIC_PLUGIN + """
imports:
    -   \"bottom_level.yaml\""""
        mid_file_name = self.make_yaml_file(mid_level_yaml)

        top_level_yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
imports:
    -   {0}""".format(mid_file_name)
        result = self.parse(top_level_yaml)
        self._assert_blueprint(result)

    def test_import_from_file_uri(self):
        yaml = self.create_yaml_with_imports([self.MINIMAL_BLUEPRINT], True)
        result = self.parse(yaml)
        self._assert_minimal_blueprint(result)

    def test_relative_file_uri_import(self):
        bottom_level_yaml = self.BASIC_TYPE
        self.make_file_with_name(bottom_level_yaml, 'bottom_level.yaml')

        mid_level_yaml = self.BASIC_PLUGIN + """
imports:
    -   \"bottom_level.yaml\""""
        mid_file_name = self.make_yaml_file(mid_level_yaml)

        top_level_yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
imports:
    -   {0}""".format('file:///' + pathname2url(mid_file_name))
        result = self.parse(top_level_yaml)
        self._assert_blueprint(result)

    def test_agent_plugin_in_node_contained_in_host_contained_in_container(self):  # noqa
        yaml = """
plugins:
  plugin:
    executor: host_agent
    source: source
node_templates:
  compute:
    type: cloudify.nodes.Compute
    relationships:
      - target: container
        type: cloudify.relationships.contained_in
  container:
    type: container
  app:
    type: app
    interfaces:
      interface:
        operation: plugin.operation
    relationships:
      - target: compute
        type: cloudify.relationships.contained_in
node_types:
  cloudify.nodes.Compute: {}
  container: {}
  app: {}
relationships:
  cloudify.relationships.contained_in: {}
"""
        result = self.parse(yaml)
        self.assertEqual('compute',
                         self.get_node_by_name(result, 'compute')['host_id'])

    def test_node_host_id_field(self):
        yaml = """
node_templates:
    test_node:
        type: cloudify.nodes.Compute
        properties:
            key: "val"
node_types:
    cloudify.nodes.Compute:
        properties:
            key: {}
            """
        result = self.parse(yaml)
        self.assertEqual('test_node', result['nodes'][0]['host_id'])

    def test_node_host_id_field_via_relationship(self):
        yaml = """
node_templates:
    test_node1:
        type: cloudify.nodes.Compute
    test_node2:
        type: another_type
        relationships:
            -   type: cloudify.relationships.contained_in
                target: test_node1
    test_node3:
        type: another_type
        relationships:
            -   type: cloudify.relationships.contained_in
                target: test_node2
node_types:
    cloudify.nodes.Compute: {}
    another_type: {}

relationships:
    cloudify.relationships.contained_in: {}
            """
        result = self.parse(yaml)
        self.assertEqual('test_node1', result['nodes'][1]['host_id'])
        self.assertEqual('test_node1', result['nodes'][2]['host_id'])

    def test_node_host_id_field_via_node_supertype(self):
        yaml = """
node_templates:
    test_node1:
        type: another_type
node_types:
    cloudify.nodes.Compute: {}
    another_type:
        derived_from: cloudify.nodes.Compute
            """
        result = self.parse(yaml)
        self.assertEqual('test_node1', result['nodes'][0]['host_id'])

    def test_node_host_id_field_via_relationship_derived_from_inheritance(
            self):
        yaml = """
node_templates:
    test_node1:
        type: cloudify.nodes.Compute
    test_node2:
        type: another_type
        relationships:
            -   type: test_relationship
                target: test_node1
node_types:
    cloudify.nodes.Compute: {}
    another_type: {}
relationships:
    cloudify.relationships.contained_in: {}
    test_relationship:
        derived_from: cloudify.relationships.contained_in
            """
        result = self.parse(yaml)
        self.assertEqual('test_node1', result['nodes'][1]['host_id'])

    def test_node_type_operation_override(self):
        yaml = """
node_templates:
    test_node1:
        type: cloudify.nodes.MyCompute
node_types:
    cloudify.nodes.Compute:
        interfaces:
            test_interface:
                start: test_plugin.start
    cloudify.nodes.MyCompute:
        derived_from: cloudify.nodes.Compute
        interfaces:
            test_interface:
                start: test_plugin.overriding_start

plugins:
    test_plugin:
        executor: host_agent
        source: dummy
"""
        result = self.parse(yaml)
        start_operation = result['nodes'][0]['operations']['start']
        self.assertEqual('overriding_start', start_operation['operation'])

    def test_node_type_node_template_operation_override(self):
        yaml = """
node_templates:
    test_node1:
        type: cloudify.nodes.Compute
        interfaces:
            test_interface:
                start: test_plugin.overriding_start

node_types:
    cloudify.nodes.Compute:
        interfaces:
            test_interface:
                start: test_plugin.start

plugins:
    test_plugin:
        executor: host_agent
        source: dummy
"""
        result = self.parse(yaml)
        start_operation = result['nodes'][0]['operations']['start']
        self.assertEqual('overriding_start', start_operation['operation'])

    def test_host_agent_plugins_to_install_in_plan(self):
        yaml = """
node_templates:
    test_node1:
        type: cloudify.nodes.Compute
    test_node2:
        type: cloudify.nodes.OtherCompute
node_types:
    cloudify.nodes.Compute:
        interfaces:
            test_interface:
                start:
                    implementation: test_plugin.start
                    inputs: {}

    cloudify.nodes.OtherCompute:
        derived_from: cloudify.nodes.Compute
        interfaces:
            test_interface:
                start:
                    implementation: other_plugin.start
                    inputs: {}

plugins:
    test_plugin:
        executor: host_agent
        source: dummy
    other_plugin:
        executor: host_agent
        source: dummy
"""
        result = self.parse(yaml)
        if result['nodes'][0]['type'] == 'cloudify.nodes.Compute':
            compute, othercompute = result['nodes']
        else:
            othercompute, compute = result['nodes']
        plugin1 = compute['plugins_to_install'][0]
        plugin2 = othercompute['plugins_to_install'][0]
        self.assertEqual('test_plugin', plugin1['name'])
        self.assertEqual(1, len(compute['plugins_to_install']))
        self.assertEqual(1, len(othercompute['plugins_to_install']))
        self.assertEqual(
            2, len(result[constants.HOST_AGENT_PLUGINS_TO_INSTALL]))
        self.assertIn(plugin1, result[constants.HOST_AGENT_PLUGINS_TO_INSTALL])
        self.assertIn(plugin2, result[constants.HOST_AGENT_PLUGINS_TO_INSTALL])
        self.assertEqual(result[constants.DEPLOYMENT_PLUGINS_TO_INSTALL],
                         [])
        self.assertEqual(result[constants.WORKFLOW_PLUGINS_TO_INSTALL],
                         [])

    def test_deployment_plugins_to_install_in_plan(self):
        yaml = """
node_templates:
    test_node1:
        type: cloudify.nodes.Compute
node_types:
    cloudify.nodes.Compute:
        interfaces:
            test_interface:
                start:
                    implementation: test_plugin.start
                    inputs: {}

plugins:
    test_plugin:
        executor: central_deployment_agent
        source: dummy
"""
        result = self.parse(yaml)
        plugin = result['nodes'][0]['deployment_plugins_to_install'][0]
        self.assertEqual('test_plugin', plugin['name'])
        self.assertEqual(1, len(result['nodes'][0][
                                     'deployment_plugins_to_install']))
        self.assertEqual(result[constants.HOST_AGENT_PLUGINS_TO_INSTALL],
                         [])
        self.assertEqual(result[constants.WORKFLOW_PLUGINS_TO_INSTALL],
                         [])

    def test_workflow_plugins_to_install_in_plan(self):
        yaml = self.BASIC_PLUGIN + """
workflows:
    workflow1: test_plugin.workflow1
"""
        result = self.parse(yaml)
        workflow_plugins_to_install = result['workflow_plugins_to_install']
        self.assertEqual(1, len(workflow_plugins_to_install))
        self.assertEqual('test_plugin', workflow_plugins_to_install[0]['name'])
        self.assertEqual(result[constants.HOST_AGENT_PLUGINS_TO_INSTALL],
                         [])
        self.assertEqual(result[constants.DEPLOYMENT_PLUGINS_TO_INSTALL],
                         [])

    def test_executor_override_node_types(self):
        yaml = """
node_templates:
    test_node1:
        type: cloudify.nodes.MyCompute
node_types:
    cloudify.nodes.Compute:
        interfaces:
            test_interface:
                start:
                    executor: central_deployment_agent
                    implementation: test_plugin.start
                    inputs: {}
    cloudify.nodes.MyCompute:
        derived_from: cloudify.nodes.Compute
        interfaces:
            test_interface:
                start:
                    executor: host_agent
                    implementation: test_plugin.start
                    inputs: {}

plugins:
    test_plugin:
        executor: host_agent
        source: dummy
"""
        result = self.parse(yaml)
        plugin = result['nodes'][0]['plugins_to_install'][0]
        self.assertEqual('test_plugin', plugin['name'])
        self.assertEqual(1, len(result['nodes'][0]['plugins_to_install']))

    def test_executor_override_plugin_declaration(self):
        yaml = """
node_templates:
    test_node1:
        type: cloudify.nodes.Compute
node_types:
    cloudify.nodes.Compute:
        interfaces:
            test_interface:
                start:
                    executor: central_deployment_agent
                    implementation: test_plugin.start
                    inputs: {}

plugins:
    test_plugin:
        executor: host_agent
        source: dummy
"""
        result = self.parse(yaml)
        plugin = result['nodes'][0]['deployment_plugins_to_install'][0]
        self.assertEqual('test_plugin', plugin['name'])
        self.assertEqual(1, len(result['nodes'][0][
            'deployment_plugins_to_install']))

    def test_executor_override_type_declaration(self):
        yaml = """
node_templates:
    test_node1:
        type: cloudify.nodes.Compute
        interfaces:
            test_interface:
                start:
                    executor: host_agent
                    inputs: {}

node_types:
    cloudify.nodes.Compute:
        interfaces:
            test_interface:
                start:
                    executor: central_deployment_agent
                    implementation: test_plugin.start
                    inputs: {}

plugins:
    test_plugin:
        executor: host_agent
        source: dummy
"""
        result = self.parse(yaml)
        plugin = result['nodes'][0]['plugins_to_install'][0]
        self.assertEqual('test_plugin', plugin['name'])
        self.assertEqual(1, len(result['nodes'][0][
            'plugins_to_install']))

    def test_import_resources(self):
        resource_file_name = 'resource_file.yaml'
        file_path = self.make_file_with_name(
            self.MINIMAL_BLUEPRINT, resource_file_name, 'resources')
        resources_base_path = os.path.dirname(file_path)
        yaml = """
imports:
    -   {0}""".format(resource_file_name)
        result = self.parse(yaml, resources_base_path=resources_base_path)
        self._assert_minimal_blueprint(result)

    def test_recursive_imports_with_inner_circular(self):
        bottom_level_yaml = """
imports:
    -   {0}
        """.format(
            os.path.join(self._temp_dir, "mid_level.yaml")) + self.BASIC_TYPE
        bottom_file_name = self.make_yaml_file(bottom_level_yaml)

        mid_level_yaml = self.BASIC_PLUGIN + """
imports:
    -   {0}""".format(bottom_file_name)
        mid_file_name = self.make_file_with_name(mid_level_yaml,
                                                 'mid_level.yaml')

        top_level_yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
imports:
    -   {0}""".format(mid_file_name)

        result = self.parse(top_level_yaml)
        self._assert_blueprint(result)

    def test_recursive_imports_with_complete_circle(self):
        bottom_level_yaml = """
imports:
    -   {0}
            """.format(
            os.path.join(self._temp_dir, "top_level.yaml")) + self.BASIC_TYPE
        bottom_file_name = self.make_yaml_file(bottom_level_yaml)

        mid_level_yaml = self.BASIC_PLUGIN + """
imports:
    -   {0}""".format(bottom_file_name)
        mid_file_name = self.make_yaml_file(mid_level_yaml)

        top_level_yaml = \
            self.BASIC_VERSION_SECTION_DSL_1_0 + \
            self.BASIC_NODE_TEMPLATES_SECTION +\
            """
imports:
    -   {0}""".format(mid_file_name)
        top_file_name = self.make_file_with_name(
            top_level_yaml, 'top_level.yaml')
        result = parse_from_path(top_file_name)
        self._assert_blueprint(result)

    def test_node_without_host_id(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + """
    test_node2:
        type: cloudify.nodes.Compute
node_types:
    cloudify.nodes.Compute: {}
    test_type:
        properties:
            key: {}
        """
        result = self.parse(yaml)
        self.assertEqual(2, len(result['nodes']))
        nodes = self._sort_result_nodes(result['nodes'], ['test_node',
                                                          'test_node2'])
        self.assertFalse('host_id' in nodes[0])
        self.assertEqual('test_node2', nodes[1]['host_id'])

    def test_multiple_instances(self):
        yaml = self.MINIMAL_BLUEPRINT + """
        instances:
            deploy: 2
            """
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_type', node['type'])
        self.assertEqual('val', node['properties']['key'])
        self.assertEqual(2, node['instances']['deploy'])

    def test_import_types_combination(self):
        yaml = self.create_yaml_with_imports([self.MINIMAL_BLUEPRINT + """
    test_node2:
        type: test_type2
        """]) + """
node_types:
    test_type2: {}
        """

        result = self.parse(yaml)
        self.assertEqual(2, len(result['nodes']))
        nodes = self._sort_result_nodes(result['nodes'], ['test_node',
                                                          'test_node2'])
        node1 = nodes[0]
        node2 = nodes[1]
        self.assertEqual('test_node', node1['id'])
        self.assertEqual('test_type', node1['type'])
        self.assertEqual('val', node1['properties']['key'])
        # self.assertEqual(1, node1['instances']['deploy'])
        self.assertEqual('test_node2', node2['id'])
        self.assertEqual('test_type2', node2['type'])
        # self.assertEqual(1, node2['instances']['deploy'])

    def test_relationship_operation_mapping_with_properties_injection(self):
        yaml = self.MINIMAL_BLUEPRINT + """
    test_node2:
        type: test_type
        relationships:
            -   type: test_relationship
                target: test_node
                source_interfaces:
                    test_interface1:
                        install:
                            implementation: test_plugin.install
                            inputs:
                                key: value
relationships:
    test_relationship: {}
plugins:
    test_plugin:
        executor: central_deployment_agent
        source: dummy
"""
        result = self.parse(yaml)
        self.assertEqual(2, len(result['nodes']))
        nodes = self._sort_result_nodes(result['nodes'], ['test_node',
                                                          'test_node2'])
        relationship1 = nodes[1]['relationships'][0]
        rel1_source_ops = relationship1['source_operations']
        self.assertEqual(
            op_struct('test_plugin', 'install', {'key': 'value'},
                      executor='central_deployment_agent'),
            rel1_source_ops['install'])
        self.assertEqual(
            op_struct('test_plugin', 'install', {'key': 'value'},
                      executor='central_deployment_agent'),
            rel1_source_ops['test_interface1.install'])

    def test_no_workflows(self):
        result = self.parse(self.MINIMAL_BLUEPRINT)
        self.assertEqual(result['workflows'], {})

    def test_empty_workflows(self):
        yaml = self.MINIMAL_BLUEPRINT + """
workflows: {}
"""
        result = self.parse(yaml)
        self.assertEqual(result['workflows'], {})

    def test_workflow_basic_mapping(self):
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + """
workflows:
    workflow1: test_plugin.workflow1
"""
        result = self.parse(yaml)
        workflows = result['workflows']
        self.assertEqual(1, len(workflows))
        self.assertEqual(workflow_op_struct('test_plugin', 'workflow1',),
                         workflows['workflow1'])
        workflow_plugins_to_install = result['workflow_plugins_to_install']
        self.assertEqual(1, len(workflow_plugins_to_install))
        self.assertEqual('test_plugin', workflow_plugins_to_install[0]['name'])

    def test_workflow_advanced_mapping(self):
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + """
workflows:
    workflow1:
        mapping: test_plugin.workflow1
        parameters:
            prop1:
                default: value1
            mandatory_prop: {}
            nested_prop:
                default:
                    nested_key: nested_value
                    nested_list:
                        - val1
                        - val2
"""
        result = self.parse(yaml)
        workflows = result['workflows']
        self.assertEqual(1, len(workflows))
        parameters = {
            'prop1': {'default': 'value1'},
            'mandatory_prop': {},
            'nested_prop': {
                'default': {
                    'nested_key': 'nested_value',
                    'nested_list': [
                        'val1',
                        'val2'
                    ]
                }
            }
        }
        self.assertEqual(workflow_op_struct('test_plugin',
                                            'workflow1',
                                            parameters),
                         workflows['workflow1'])
        workflow_plugins_to_install = result['workflow_plugins_to_install']
        self.assertEqual(1, len(workflow_plugins_to_install))
        self.assertEqual('test_plugin', workflow_plugins_to_install[0]['name'])

    def test_workflow_imports(self):
        workflows1 = """
workflows:
    workflow1: test_plugin.workflow1
"""
        workflows2 = """
plugins:
    test_plugin2:
        executor: central_deployment_agent
        source: dummy
workflows:
    workflow2: test_plugin2.workflow2
"""
        yaml = self.create_yaml_with_imports([
            self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS,
            workflows1,
            workflows2
        ])
        result = self.parse(yaml)
        workflows = result['workflows']
        self.assertEqual(2, len(workflows))
        self.assertEqual(workflow_op_struct('test_plugin', 'workflow1'),
                         workflows['workflow1'])
        self.assertEqual(workflow_op_struct('test_plugin2', 'workflow2'),
                         workflows['workflow2'])
        workflow_plugins_to_install = result['workflow_plugins_to_install']
        self.assertEqual(2, len(workflow_plugins_to_install))
        self.assertEqual('test_plugin', workflow_plugins_to_install[0]['name'])
        self.assertEqual('test_plugin2',
                         workflow_plugins_to_install[1]['name'])

    def test_workflow_parameters_empty_parameters(self):
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + """
workflows:
    test_workflow:
        mapping: test_plugin.workflow1
        parameters: {}
"""
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_type', node['type'])
        workflow = result['workflows']['test_workflow']
        self.assertEqual({}, workflow['parameters'])

    def test_workflow_parameters_empty_parameter(self):
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + """
workflows:
    test_workflow:
        mapping: test_plugin.workflow1
        parameters:
            key: {}
"""
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_type', node['type'])
        workflow = result['workflows']['test_workflow']
        self.assertEqual({'key': {}}, workflow['parameters'])

    def test_workflow_parameters_parameter_with_description_only(self):
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + """
workflows:
    test_workflow:
        mapping: test_plugin.workflow1
        parameters:
            key:
                description: parameter_desc
"""
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_type', node['type'])
        workflow = result['workflows']['test_workflow']
        self.assertEqual({'key': {'description': 'parameter_desc'}},
                         workflow['parameters'])

    def test_workflow_parameters_standard_parameter(self):
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + """
workflows:
    test_workflow:
        mapping: test_plugin.workflow1
        parameters:
            key:
                default: val
                description: parameter_desc
                type: string
"""
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual('test_type', node['type'])
        workflow = result['workflows']['test_workflow']
        self.assertEqual(
            {'key': {'default': 'val', 'description': 'parameter_desc',
                     'type': 'string'}},
            workflow['parameters'])

    def test_policy_type_properties_empty_properties(self):
        policy_types = dict(
            policy_types=dict(
                policy_type=dict(
                    source='the_source',
                    properties=dict())))
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + '\n' + \
            yml.safe_dump(policy_types)
        result = self.parse(yaml)
        self.assertEqual(result['policy_types'],
                         policy_types['policy_types'])

    def test_policy_type_properties_empty_property(self):
        policy_types = dict(
            policy_types=dict(
                policy_type=dict(
                    source='the_source',
                    properties=dict(
                        property=dict()))))
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + '\n' + \
            yml.safe_dump(policy_types)
        result = self.parse(yaml)
        self.assertEqual(result['policy_types'],
                         policy_types['policy_types'])

    def test_policy_type_properties_property_with_description_only(self):
        policy_types = dict(
            policy_types=dict(
                policy_type=dict(
                    source='the_source',
                    properties=dict(
                        property=dict(
                            description='property description')))))
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + '\n' + \
            yml.safe_dump(policy_types)
        result = self.parse(yaml)
        self.assertEqual(result['policy_types'],
                         policy_types['policy_types'])

    def test_policy_type_properties_property_with_default_only(self):
        policy_types = dict(
            policy_types=dict(
                policy_type=dict(
                    source='the_source',
                    properties=dict(
                        property=dict(
                            default='default_value')))))
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + '\n' + \
            yml.safe_dump(policy_types)
        result = self.parse(yaml)
        self.assertEqual(result['policy_types'],
                         policy_types['policy_types'])

    def test_policy_type_properties_standard_property(self):
        policy_types = dict(
            policy_types=dict(
                policy_type=dict(
                    source='the_source',
                    properties=dict(
                        property=dict(
                            default='default_value',
                            description='property description',
                            type='string')))))
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + '\n' + \
            yml.safe_dump(policy_types)
        result = self.parse(yaml)
        self.assertEqual(result['policy_types'],
                         policy_types['policy_types'])

    def test_policy_type_imports(self):
        policy_types = []
        for i in range(2):
            policy_types.append(dict(
                policy_types={
                    'policy_type{0}'.format(i): dict(
                        source='the_source',
                        properties=dict(
                            property=dict(
                                default='default_value',
                                description='property description')))}))

        yaml = self.create_yaml_with_imports([
            self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS,
            yml.safe_dump(policy_types[0]),
            yml.safe_dump(policy_types[1]),
        ])

        expected_result = dict(
            policy_types=policy_types[0]['policy_types'])
        expected_result['policy_types'].update(policy_types[1]['policy_types'])

        result = self.parse(yaml)
        self.assertEqual(result['policy_types'],
                         expected_result['policy_types'])

    def test_policy_trigger_imports(self):
        policy_triggers = []
        for i in range(2):
            policy_triggers.append(dict(
                policy_triggers={
                    'policy_trigger{0}'.format(i): dict(
                        source='the_source',
                        parameters=dict(
                            property=dict(
                                default='default_value',
                                description='property description',
                                type='string')))}))

        yaml = self.create_yaml_with_imports([
            self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS,
            yml.safe_dump(policy_triggers[0]),
            yml.safe_dump(policy_triggers[1]),
        ])

        expected_result = dict(
            policy_triggers=policy_triggers[0]['policy_triggers'])
        expected_result['policy_triggers'].update(policy_triggers[1][
            'policy_triggers'])

        result = self.parse(yaml)
        self.assertEqual(result['policy_triggers'],
                         expected_result['policy_triggers'])

    def test_groups_schema_properties_merge(self):
        yaml = self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS + """
policy_types:
    policy_type:
        properties:
            key1:
                default: value1
            key2:
                description: key2 description
            key3:
                default: value3
        source: source
groups:
    group:
        members: [test_node]
        policies:
            policy:
                type: policy_type
                properties:
                    key2: group_value2
                    key3: group_value3
"""
        result = self.parse(yaml)
        groups = result['groups']
        self.assertEqual(1, len(groups))
        group = groups['group']
        self.assertEqual(['test_node'], group['members'])
        self.assertEqual(1, len(group['policies']))
        policy = group['policies']['policy']
        self.assertEqual('policy_type', policy['type'])
        self.assertEqual({
            'key1': 'value1',
            'key2': 'group_value2',
            'key3': 'group_value3'
        }, policy['properties'])

    def test_groups_imports(self):
        groups = []
        for i in range(2):
            groups.append(dict(
                groups={
                    'group{0}'.format(i): dict(
                        members=['test_node'],
                        policies=dict(
                            policy=dict(
                                type='policy_type',
                                properties={},
                                triggers={})))}))
        policy_types = """
policy_types:
    policy_type:
        properties: {}
        source: source
"""
        yaml = self.create_yaml_with_imports([
            self.BLUEPRINT_WITH_INTERFACES_AND_PLUGINS,
            policy_types,
            yml.safe_dump(groups[0]),
            yml.safe_dump(groups[1])])

        expected_result = dict(
            groups=groups[0]['groups'])
        expected_result['groups'].update(groups[1]['groups'])

        result = self.parse(yaml)
        self.assertEqual(result['groups'],
                         expected_result['groups'])

    def test_operation_mapping_with_properties_injection(self):
        yaml = self.BASIC_NODE_TEMPLATES_SECTION + self.BASIC_PLUGIN + """
node_types:
    test_type:
        properties:
            key: {}
        interfaces:
            test_interface1:
                install:
                    implementation: test_plugin.install
                    inputs:
                        key:
                            default: value
"""
        result = self.parse(yaml)
        node = result['nodes'][0]
        self.assertEqual('test_type', node['type'])
        operations = node['operations']
        self.assertEqual(
            op_struct('test_plugin', 'install', {'key': 'value'},
                      executor='central_deployment_agent'),
            operations['install'])
        self.assertEqual(
            op_struct('test_plugin', 'install', {'key': 'value'},
                      executor='central_deployment_agent'),
            operations['test_interface1.install'])

    def test_merge_plugins_and_interfaces_imports(self):
        yaml = self.create_yaml_with_imports(
            [self.BASIC_NODE_TEMPLATES_SECTION, self.BASIC_PLUGIN]) + """
plugins:
    other_test_plugin:
        executor: central_deployment_agent
        source: dummy
node_types:
    test_type:
        properties:
            key: {}
        interfaces:
            test_interface1:
                install:
                    implementation: test_plugin.install
                    inputs: {}
                terminate:
                    implementation: test_plugin.terminate
                    inputs: {}
            test_interface2:
                start:
                    implementation: other_test_plugin.start
                    inputs: {}
                shutdown:
                    implementation: other_test_plugin.shutdown
                    inputs: {}
"""
        result = self.parse(yaml)
        node = result['nodes'][0]
        self._assert_blueprint(result)

        operations = node['operations']
        self.assertEqual(op_struct('other_test_plugin', 'start',
                                   executor='central_deployment_agent'),
                         operations['start'])
        self.assertEqual(op_struct('other_test_plugin', 'start',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.start'])
        self.assertEqual(op_struct('other_test_plugin', 'shutdown',
                                   executor='central_deployment_agent'),
                         operations['shutdown'])
        self.assertEqual(op_struct('other_test_plugin', 'shutdown',
                                   executor='central_deployment_agent'),
                         operations['test_interface2.shutdown'])

    def test_node_interfaces_operation_mapping(self):
        yaml = self.BASIC_PLUGIN + self.BASIC_NODE_TEMPLATES_SECTION + """
        interfaces:
            test_interface1:
                install: test_plugin.install
                terminate: test_plugin.terminate
node_types:
    test_type:
        properties:
            key: {}
            """
        result = self.parse(yaml)
        self._assert_blueprint(result)

    def test_property_schema_type_property_with_intrinsic_functions(self):
        yaml = """
node_templates:
    test_node:
        type: test_type
        properties:
            int1: { get_input: x }
node_types:
    test_type:
        properties:
            int1:
                type: integer
inputs:
    x: {}
        """
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])

    def test_property_schema_type_property(self):
        yaml = """
node_templates:
    test_node:
        type: test_type
        properties:
            string1: val
            string2: true
            string3: 5
            string4: 5.7
            boolean1: true
            boolean2: false
            boolean3: False
            boolean4: FALSE
            boolean5: Yes
            boolean6: On
            boolean7: No
            boolean8: Off
            integer1: 5
            integer2: -5
            integer3: 1000000000000
            integer4: 0
            float1: 5.7
            float2: 5.735935
            float3: 5.0
            float4: 5
            float5: -5.7
            dict1:
                test: 1
            dict2: {}
            list1: [1, 2]
            list2: []
            regex: ^.$

node_types:
    test_type:
        properties:
            string1:
                type: string
            string2:
                type: string
            string3:
                type: string
            string4:
                type: string
            boolean1:
                type: boolean
            boolean2:
                type: boolean
            boolean3:
                type: boolean
            boolean4:
                type: boolean
            boolean5:
                type: boolean
            boolean6:
                type: boolean
            boolean7:
                type: boolean
            boolean8:
                type: boolean
            integer1:
                type: integer
            integer2:
                type: integer
            integer3:
                type: integer
            integer4:
                type: integer
            float1:
                type: float
            float2:
                type: float
            float3:
                type: float
            float4:
                type: float
            float5:
                type: float
            dict1:
                type: dict
            dict2:
                type: dict
            list1:
                type: list
            list2:
                type: list
            regex:
                type: regex
            """
        result = self.parse(yaml)
        self.assertEqual(1, len(result['nodes']))
        node = result['nodes'][0]
        self.assertEqual('test_node', node['id'])
        self.assertEqual(node['properties'], {
            'boolean4': False,
            'boolean5': True,
            'boolean6': True,
            'boolean7': False,
            'boolean1': True,
            'boolean2': False,
            'boolean3': False,
            'boolean8': False,
            'float4': 5,
            'float5': -5.7,
            'float1': 5.7,
            'float2': 5.735935,
            'float3': 5.0,
            'integer2': -5,
            'integer3': 1000000000000,
            'integer4': 0,
            'integer1': 5,
            'dict1': {'test': 1},
            'dict2': {},
            'string4': 5.7,
            'string2': True,
            'string3': 5,
            'string1': 'val',
            'list1': [1, 2],
            'list2': [],
            'regex': '^.$'})

    def test_version_field(self):
        yaml = self.MINIMAL_BLUEPRINT + self.BASIC_VERSION_SECTION_DSL_1_0
        result = dsl_parse(yaml)
        self._assert_minimal_blueprint(result)

    def test_version_field_with_versionless_imports(self):
        imported_yaml = str()
        imported_yaml_filename = self.make_yaml_file(imported_yaml)
        yaml = """
imports:
    -   {0}""".format(imported_yaml_filename) + \
               self.BASIC_VERSION_SECTION_DSL_1_0 + \
               self.MINIMAL_BLUEPRINT
        result = dsl_parse(yaml)
        self._assert_minimal_blueprint(result)

    def test_version_field_with_imports_with_version(self):
        imported_yaml = self.BASIC_VERSION_SECTION_DSL_1_0
        imported_yaml_filename = self.make_yaml_file(imported_yaml)
        yaml = """
imports:
    -   {0}""".format(imported_yaml_filename) + \
               self.BASIC_VERSION_SECTION_DSL_1_0 + \
               self.MINIMAL_BLUEPRINT
        result = dsl_parse(yaml)
        self._assert_minimal_blueprint(result)

    def test_script_mapping(self):
        yaml = self.BASIC_VERSION_SECTION_DSL_1_0 + """
plugins:
    script:
        executor: central_deployment_agent
        install: false

node_types:
    type:
        interfaces:
            test:
                op:
                    implementation: stub.py
                    inputs: {}
                op2:
                    implementation: stub.py
                    inputs:
                        key:
                            default: value
relationships:
    relationship:
        source_interfaces:
            test:
                op:
                    implementation: stub.py
                    inputs: {}
        target_interfaces:
            test:
                op:
                    implementation: stub.py
                    inputs: {}
workflows:
    workflow: stub.py
    workflow2:
        mapping: stub.py
        parameters:
            key:
                default: value

node_templates:
    node1:
        type: type
        relationships:
            -   target: node2
                type: relationship
    node2:
        type: type

"""
        self.make_file_with_name(content='content',
                                 filename='stub.py')
        yaml_path = self.make_file_with_name(content=yaml,
                                             filename='blueprint.yaml')
        result = self.parse_from_path(yaml_path)
        node = [n for n in result['nodes'] if n['name'] == 'node1'][0]
        relationship = node['relationships'][0]

        operation = node['operations']['test.op']
        operation2 = node['operations']['test.op2']
        source_operation = relationship['source_operations']['test.op']
        target_operation = relationship['target_operations']['test.op']
        workflow = result['workflows']['workflow']
        workflow2 = result['workflows']['workflow2']

        def assert_operation(op, extra_properties=False):
            inputs = {'script_path': 'stub.py'}
            if extra_properties:
                inputs.update({'key': 'value'})
            self.assertEqual(op, op_struct(
                plugin_name=constants.SCRIPT_PLUGIN_NAME,
                mapping=constants.SCRIPT_PLUGIN_RUN_TASK,
                inputs=inputs,
                executor='central_deployment_agent'))

        assert_operation(operation)
        assert_operation(operation2, extra_properties=True)
        assert_operation(source_operation)
        assert_operation(target_operation)

        self.assertEqual(workflow['operation'],
                         constants.SCRIPT_PLUGIN_EXECUTE_WORKFLOW_TASK)
        self.assertEqual(1, len(workflow['parameters']))
        self.assertEqual(workflow['parameters']['script_path']['default'],
                         'stub.py')
        self.assertEqual(workflow['plugin'], constants.SCRIPT_PLUGIN_NAME)

        self.assertEqual(workflow2['operation'],
                         constants.SCRIPT_PLUGIN_EXECUTE_WORKFLOW_TASK)
        self.assertEqual(2, len(workflow2['parameters']))
        self.assertEqual(workflow2['parameters']['script_path']['default'],
                         'stub.py')
        self.assertEqual(workflow2['parameters']['key']['default'], 'value')
        self.assertEqual(workflow['plugin'], constants.SCRIPT_PLUGIN_NAME)

    def test_version(self):
        def assertion(version_str, expected):
            version = self.parse(self.MINIMAL_BLUEPRINT,
                                 dsl_version=version_str)['version']
            version = models.Version(version)
            self.assertEqual(version.raw,
                             version_str.split(' ')[1].strip())
            self.assertEqual(version.definitions_name, 'cloudify_dsl')
            self.assertEqual(version.definitions_version, expected)
        assertion(self.BASIC_VERSION_SECTION_DSL_1_0,
                  expected=(1, 0))
        assertion(self.BASIC_VERSION_SECTION_DSL_1_1,
                  expected=(1, 1))
        assertion(self.BASIC_VERSION_SECTION_DSL_1_2,
                  expected=(1, 2))

    def test_version_comparison(self):

        def parse_version(ver):
            parsed = version.parse_dsl_version('cloudify_dsl_{0}'.format(ver))
            major, minor, micro = parsed
            if micro is None:
                micro = 0
            return major, minor, micro

        versions = [
            (1, '1_0'),
            (1, '1_0_0'),
            (2, '1_0_1'),
            (3, '1_1'),
            (3, '1_1_0'),
            (4, '1_2'),
            (4, '1_2_0'),
            (5, '2_0'),
        ]

        for ord1, ver1 in versions:
            parsed_ver1 = parse_version(ver1)
            for ord2, ver2 in versions:
                parsed_ver2 = parse_version(ver2)
                if ord1 == ord2:
                    comp_func = self.assertEqual
                elif ord1 < ord2:
                    comp_func = self.assertLess
                else:
                    comp_func = self.assertGreater
                comp_func(parsed_ver1, parsed_ver2)

    def test_dsl_definitions(self):
        yaml = """
dsl_definitions:
  def1: &def1
    prop1: val1
    prop2: val2
  def2: &def2
    prop3: val3
    prop4: val4
node_types:
  type1:
    properties:
      prop1:
        default: default_val1
      prop2:
        default: default_val2
      prop3:
        default: default_val3
      prop4:
        default: default_val4
node_templates:
  node1:
    type: type1
    properties:
      <<: *def1
      <<: *def2
  node2:
    type: type1
    properties: *def1
  node3:
    type: type1
    properties: *def2
"""
        plan = self.parse_1_2(yaml)
        self.assertNotIn('dsl_definitions', plan)
        node1 = self.get_node_by_name(plan, 'node1')
        node2 = self.get_node_by_name(plan, 'node2')
        node3 = self.get_node_by_name(plan, 'node3')
        self.assertEqual({
            'prop1': 'val1',
            'prop2': 'val2',
            'prop3': 'val3',
            'prop4': 'val4',
        }, node1['properties'])
        self.assertEqual({
            'prop1': 'val1',
            'prop2': 'val2',
            'prop3': 'default_val3',
            'prop4': 'default_val4',
        }, node2['properties'])
        self.assertEqual({
            'prop1': 'default_val1',
            'prop2': 'default_val2',
            'prop3': 'val3',
            'prop4': 'val4',
        }, node3['properties'])

    def test_dsl_definitions_as_list(self):
        yaml = """
dsl_definitions:
  - &def1
    prop1: val1
    prop2: val2
  - &def2
    prop3: val3
    prop4: val4
node_types:
  type1:
    properties:
      prop1:
        default: default_val1
      prop2:
        default: default_val2
      prop3:
        default: default_val3
      prop4:
        default: default_val4
node_templates:
  node1:
    type: type1
    properties:
      <<: *def1
      <<: *def2
"""
        plan = self.parse_1_2(yaml)
        self.assertNotIn('dsl_definitions', plan)
        node1 = self.get_node_by_name(plan, 'node1')
        self.assertEqual({
            'prop1': 'val1',
            'prop2': 'val2',
            'prop3': 'val3',
            'prop4': 'val4',
        }, node1['properties'])

    def test_dsl_definitions_in_imports(self):
        imported_yaml = self.BASIC_VERSION_SECTION_DSL_1_2 + """
dsl_definitions:
  - &def1
    prop1:
        default: val1
node_types:
  type1:
    properties: *def1

"""
        imported_yaml_filename = self.make_yaml_file(imported_yaml)
        yaml = """
dsl_definitions:
  - &def1
    prop1: val2
imports:
    - {0}
node_templates:
  node1:
    type: type1
  node2:
    type: type1
    properties: *def1
""".format(imported_yaml_filename)

        plan = self.parse_1_2(yaml)
        self.assertNotIn('dsl_definitions', plan)
        node1 = self.get_node_by_name(plan, 'node1')
        node2 = self.get_node_by_name(plan, 'node2')
        self.assertEqual({
            'prop1': 'val1',
        }, node1['properties'])
        self.assertEqual({
            'prop1': 'val2',
        }, node2['properties'])

    def test_description_in_imports_with_source_description(self):
        import_description = "import"
        app_description = "app"
        imported_yaml = self.BASIC_VERSION_SECTION_DSL_1_3 + """
description: """ + import_description + """
node_types:
  type1:
     properties:
"""
        imported_yaml_filename = self.make_yaml_file(imported_yaml)
        app = self.BASIC_VERSION_SECTION_DSL_1_3 + """
description: """ + app_description + """
imports:
    - {0}
node_templates:
  node1:
    type: type1
    """.format(imported_yaml_filename)

        plan = self.parse(app)
        self.assertEqual(plan[constants.DESCRIPTION], app_description)

    def test_description_in_imports_without_source_description(self):
        import_description = "import"
        imported_yaml = self.BASIC_VERSION_SECTION_DSL_1_3 + """
description: """ + import_description + """
node_types:
  type1:
     properties:
"""
        imported_yaml_filename = self.make_yaml_file(imported_yaml)
        app = self.BASIC_VERSION_SECTION_DSL_1_3 + """
imports:
    - {0}
node_templates:
  node1:
    type: type1
    """.format(imported_yaml_filename)

        plan = self.parse(app)
        self.assertEqual(plan[constants.DESCRIPTION], import_description)

    def test_null_default(self):
        yaml = """
plugins:
  p:
    install: false
    executor: central_deployment_agent
node_types:
  type: {}
node_templates:
  node:
    type: type
workflows:
  workflow:
    mapping: p.workflow
    parameters:
      parameter:
        default: null
"""
        workflow = self.parse(yaml)['workflows']['workflow']
        parameter = workflow['parameters']['parameter']
        self.assertIn('default', parameter)

    def test_required_property(self):
        yaml = """
node_types:
  type:
    properties:
      none_required_prop:
        required: false
      required_prop:
        required: true
node_templates:
  node:
    type: type
    properties:
      required_prop: value
"""
        properties = self.parse_1_2(yaml)['nodes'][0]['properties']
        self.assertEqual(len(properties), 1)
        self.assertEqual(properties['required_prop'], 'value')

    def test_null_property_value(self):
        yaml = """
node_types:
  type:
    properties:
      prop1:
        default: null
      prop2:
        default: some_value
      prop3: {}
      prop4:
        required: false
node_templates:
  node:
    type: type
    properties:
      prop1: null
      prop2: null
      prop3: null
      prop4: null
"""
        properties = self.parse_1_2(yaml)['nodes'][0]['properties']
        self.assertEqual(len(properties), 4)
        for value in properties.values():
            self.assertIsNone(value)

    def test_validate_version_false(self):
        yaml = """
description: description
dsl_definitions:
  definition: value
plugins:
  plugin:
    executor: central_deployment_agent
    install: false
    install_arguments: --arg
node_types:
  type:
    interfaces:
      interface:
        op:
          implementation: plugin.task.op
          max_retries: 1
          retry_interval: 1
data_types:
  type:
    properties:
      prop:
        required: false
node_templates:
  node:
    type: type
"""
        self.assertRaises(exceptions.DSLParsingException,
                          self.parse, yaml,
                          dsl_version=self.BASIC_VERSION_SECTION_DSL_1_0,
                          validate_version=True)
        self.parse(yaml,
                   dsl_version=self.BASIC_VERSION_SECTION_DSL_1_0,
                   validate_version=False)

    def test_validate_version_false_different_versions_in_imports(self):
        imported1 = self.BASIC_VERSION_SECTION_DSL_1_0
        imported2 = self.BASIC_VERSION_SECTION_DSL_1_1
        imported3 = self.BASIC_VERSION_SECTION_DSL_1_2
        imported4 = self.BASIC_VERSION_SECTION_DSL_1_3
        yaml = self.create_yaml_with_imports([imported1,
                                              imported2,
                                              imported3,
                                              imported4])
        yaml += """
node_types:
  type: {}
node_templates:
  node:
    type: type
"""
        self.assertRaises(exceptions.DSLParsingException,
                          self.parse, yaml,
                          dsl_version=self.BASIC_VERSION_SECTION_DSL_1_0,
                          validate_version=True)
        self.parse(yaml,
                   dsl_version=self.BASIC_VERSION_SECTION_DSL_1_0,
                   validate_version=False)

    def test_plugin_fields(self):
        yaml = """
tosca_definitions_version: cloudify_dsl_1_2
node_types:
  type:
    properties:
      prop1:
        default: value
  cloudify.nodes.Compute:
    properties:
      prop1:
        default: value
node_templates:
  node1:
    type: type
    interfaces:
     interface:
       op: plugin1.op
  node2:
    type: cloudify.nodes.Compute
    interfaces:
     interface:
       op: plugin2.op
"""
        base_plugin_def = {'distribution': 'dist',
                           'distribution_release': 'release',
                           'distribution_version': 'version',
                           'install': True,
                           'install_arguments': '123',
                           'package_name': 'name',
                           'package_version': 'version',
                           'source': 'source',
                           'supported_platform': 'any'}
        deployment_plugin_def = base_plugin_def.copy()
        deployment_plugin_def['executor'] = 'central_deployment_agent'
        host_plugin_def = base_plugin_def.copy()
        host_plugin_def['executor'] = 'host_agent'
        raw_parsed = yml.safe_load(yaml)
        raw_parsed['plugins'] = {
            'plugin1': deployment_plugin_def,
            'plugin2': host_plugin_def
        }
        parsed = self.parse_1_2(yml.safe_dump(raw_parsed))
        expected_plugin1 = deployment_plugin_def.copy()
        expected_plugin1['name'] = 'plugin1'
        expected_plugin2 = host_plugin_def.copy()
        expected_plugin2['name'] = 'plugin2'
        plugin1 = parsed['deployment_plugins_to_install'][0]
        node2 = self.get_node_by_name(parsed, 'node2')
        plugin2 = node2['plugins_to_install'][0]
        self.assertEqual(expected_plugin1, plugin1)
        self.assertEqual(expected_plugin2, plugin2)
