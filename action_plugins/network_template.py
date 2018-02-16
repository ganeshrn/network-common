# -*- coding: utf-8 -*-

# (c) 2018, Ansible by Red Hat, inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
# You should have received a copy of the GNU General Public License
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import re
import collections

from ansible import constants as C
from ansible.plugins.action.normal import ActionModule as ActionBase
from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.six import iteritems, string_types
from ansible.module_utils._text import to_text
from ansible.errors import AnsibleError, AnsibleUndefinedVariable

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


MISSING_KEY_OPTIONS = frozenset(('warn', 'fail', 'ignore'))


def warning(msg):
    if C.ACTION_WARNINGS:
        display.warning(msg)


class ActionModule(ActionBase):

    def set_args(self):
        """ sets instance variables based on passed arguments
        """
        self.source_dir = self._task.args.get('source_dir')
        if not os.path.isdir(self.source_dir):
            raise AnsibleError('%s does not appear to be a valid directory' % self.source_dir)

        self.exclude_files = self._task.args.get('exclude_files')
        self.include_files = self._task.args.get('include_files')

        self.private_vars = self._task.args.get('private_vars') or {}

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        self.set_args()

        variables = task_vars.copy()
        variables.update(self.private_vars)

        lines = list()
        include_files = self.included_files()

        for source in include_files:
            display.display('including file %s' % source)
            contents = self._loader.load_from_file(source)

            try:
                lines = self._process_template(contents, variables)
            except AnsibleError as exc:
                return {'failed': True, 'msg': to_text(exc)}

        return {'lines': lines,
                'text': '\n'.join(lines),
                'included_files': include_files}


    def _check_file(self, filename, matches):
        """ Checks the file against a list of matches

        If the filename is included as part of the list of matches, this
        method will return True.  If it is not, then this method will
        return False

        :param filename: The filename to be matched
        :param matches: The list of matches to test against

        :returns: True if the filename should be ignored otherwise False
        """
        if isinstance(matches, string_types):
            matches = [matches]
        if not isinstance(matches, list):
            raise AnsibleError("matches must be a valid list")
        for pattern in matches:
            if re.search(r'%s' % pattern, filename):
                return True
        return False

    def should_include(self, filename):
        if self.include_files:
            return self._check_file(filename, self.include_files)
        return True

    def should_exclude(self, filename):
        if self.exclude_files:
            return self._check_file(filename, self.exclude_files)
        return False

    def included_files(self):
        include_files = list()
        for filename in os.listdir(self.source_dir):
            filename = os.path.join(self.source_dir, filename)

            if not os.path.isfile(filename):
                continue
            elif self.should_exclude(os.path.basename(filename)):
                warning('excluding file %s' % filename)
                continue
            elif not self.should_include(os.path.basename(filename)):
                warning('skipping file %s' % filename)
                continue
            else:
                include_files.append(filename)
        return include_files

    def _process_template(self, contents, template_vars):
        lines = list()

        for item in contents:
            name = item.get('name')

            block = item.get('block')
            include = item.get('include')

            when = item.get('when')

            if include:
                if when is not None:
                    conditional = "{%% if %s %%}True{%% else %%}False{%% endif %%}"
                    if not self.template(conditional % when, template_vars, fail_on_undefined=False):
                        display.vvvvv("include '%s' skipped due to conditional check failure" % name)
                        continue
                lines.extend(self._process_include(item, template_vars))

            elif block:
                loop = item.get('loop')
                loop_data = None

                loop_control = item.get('loop_control') or {'loop_var': 'item'}

                if loop:
                    loop_data = self.template(loop, template_vars, fail_on_undefined=False, convert_bare=True)
                    if not loop_data:
                        warning("block '%s' skipped due to missing loop var '%s'" % (name, loop))
                        continue

                values = list()

                if isinstance(loop_data, collections.Mapping):
                    for item_key, item_value in iteritems(loop_data):
                        item_data = template_vars.copy()
                        key = loop_control['loop_var']
                        item_data[key] = {'key': item_key, 'value': item_value}

                        if when is not None:
                            conditional = "{%% if %s %%}True{%% else %%}False{%% endif %%}"
                            if not self.template(conditional % when, item_data, fail_on_undefined=False):
                                display.vvvvv("block '%s' skipped due to conditional check failure" % name)
                                continue

                        for entry in block:
                            if 'block' in entry or 'include' in entry:
                                templated_values = self.build([entry], item_data)
                            elif 'lines' not in entry:
                                raise AnsibleError("missing required block entry `lines` in dict")
                            else:
                                templated_values = self._process_block(entry, item_data)

                            if templated_values:
                                values.extend(templated_values)

                elif isinstance(loop_data, collections.Iterable):
                    for item_value in loop_data:
                        item_data = template_vars.copy()
                        key = loop_control['loop_var']
                        item_data[key] = item_value

                        if when is not None:
                            conditional = "{%% if %s %%}True{%% else %%}False{%% endif %%}"
                            if not self.template(conditional % when, item_data, fail_on_undefined=False):
                                display.vvvvv("block '%s' skipped due to conditional check failure" % name)
                                continue

                        for entry in block:
                            if 'block' in entry or 'include' in entry:
                                templated_values = self.build([entry], item_data)
                            elif 'lines' not in entry:
                                raise AnsibleError("missing required block entry `lines` in list")
                            else:
                                templated_values = self._process_block(entry, item_data)

                            if templated_values:
                                values.extend(templated_values)

                else:
                    for entry in block:
                        if when is not None:
                            conditional = "{%% if %s %%}True{%% else %%}False{%% endif %%}"
                            if not self.template(conditional % when, template_vars, fail_on_undefined=False):
                                display.vvvvv("block '%s' skipped due to conditional check failure" % name)
                                continue

                        if 'block' in entry or 'include' in entry:
                            templated_values = self.build([entry], template_vars)
                        elif 'lines' not in entry:
                            raise AnsibleError("missing required block entry `lines`")
                        else:
                            templated_values = self._process_block(entry, template_vars)

                        if templated_values:
                            values.extend(templated_values)

                if values:
                    lines.extend(values)

            else:
                values = self._process_block(item, template_vars)
                if values:
                    lines.extend(values)

        return lines

    def _template_items(self, block, data):
        name = block.get('name')
        items = to_list(block['lines'])

        required = block.get('required')

        join = block.get('join')
        join_delimiter = block.get('join_delimiter') or ' '

        indent = block.get('indent')

        missing_key = block.get('missing_key') or 'warn'
        if missing_key not in MISSING_KEY_OPTIONS:
            raise AnsibleError('option missing_key expected one of %s, got %s' % (', '.join(MISSING_KEY_OPTIONS), missing_key))

        fail_on_undefined = missing_key == 'fail'
        warn_on_missing_key = missing_key == 'warn'

        values = list()

        for item in items:
            templated_value = self.template(item, data, fail_on_undefined=fail_on_undefined)

            if templated_value:
                if '__omit_place_holder__' in templated_value:
                    continue
                if isinstance(templated_value, string_types):
                    values.append(templated_value)
                elif isinstance(templated_value, collections.Iterable):
                    values.extend(templated_value)
            else:
                if required:
                    raise AnsibleError("block '%s' is missing required key" % name)
                elif warn_on_missing_key:
                    warning("line '%s' skipped due to missing key" % item)

            if join and values:
                values = [join_delimiter.join(values)]

            if indent:
                values = [(indent * ' ') + line.strip() for line in values]

        return values

    def _process_block(self, block, data):
        name = block.get('name')
        when = block.get('when')

        loop = block.get('loop')
        loop_data = None

        loop_control = block.get('loop_control') or {'loop_var': 'item'}

        values = list()

        if when is not None:
            conditional = "{%% if %s %%}True{%% else %%}False{%% endif %%}"
            if not self.template(conditional % when, data, fail_on_undefined=False):
                display.vvvv("block '%s' skipped due to conditional check failure" % name)
                return values

        if loop:
            loop_data = self.template(loop, data, fail_on_undefined=False, convert_bare=True)
            if not loop_data:
                warning("block '%s' skipped due to missing loop var '%s'" % (name, loop))
                return values

        if isinstance(loop_data, collections.Mapping):
            for item_key, item_value in iteritems(loop_data):
                item_data = data.copy()
                key = loop_control['loop_var']
                item_data[key] = {'key': item_key, 'value': item_value}

                templated_values = self._template_items(block, item_data)

                if templated_values:
                    values.extend(templated_values)

        elif isinstance(loop_data, collections.Iterable):
            for item_value in loop_data:
                item_data = data.copy()
                key = loop_control['loop_var']
                item_data[key] = item_value

                templated_values = self._template_items(block, item_data)

                if templated_values:
                    values.extend(templated_values)

        else:
            values = self._template_items(block, data)

        return values

    def _process_include(self, item, variables):
        name = item.get('name')
        include = item['include']

        src = self.template(include, variables)
        source = self._find_needle('templates', src)

        when = item.get('when')

        if when:
            conditional = "{%% if %s %%}True{%% else %%}False{%% endif %%}"
            if not self.template(conditional % when, variables, fail_on_undefined=False):
                display.vvvvv("include '%s' skipped due to conditional check failure" % name)
                return []

        display.display('including file %s' % source)
        include_data = self._loader.load_from_file(source)

        template_data = item.copy()

        # replace include directive with block directive and contents of
        # included file.  this will preserve other values such as loop,
        # loop_control, etc
        template_data.pop('include')
        template_data['block'] = include_data

        return self.build([template_data], variables)

    def template(self, value, data=None, fail_on_undefined=False, convert_bare=False):
        try:
            data = data or {}
            tmp_avail_vars = self._templar._available_variables
            self._templar.set_available_variables(data)
            res = self._templar.template(value, convert_bare=convert_bare)
        except AnsibleUndefinedVariable:
            if fail_on_undefined:
                raise
            res = None
        finally:
            self._templar.set_available_variables(tmp_avail_vars)
        return res
