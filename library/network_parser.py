#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2018, Ansible by Red Hat, inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'network'}


DOCUMENTATION = """
---
module: network_parser
version_added: "2.5"
author: "Peter Sprygada (@private)"
short_description: Parse the output of a command and generate Ansible facts
description:
  - Generate Ansible facts from the output of a command based on a set
    of rules defined in a parser file.  The parser file is based on a set
    of directives that defines how to parse the output.
options:
  parser:
    description:
      - The full path filename of the parser to use to parse the output of
        the command provided in C(contents).
    required: yes
  contents:
    description:
      - The text contents that should be used as input to the parser to
        generate a set of facts.  Typically, this would be the output from a
        command.
    required: yes
"""

EXAMPLES = """
- name: parse the output of show interfaces
  network_parser:
    parser: parsers/show_interface.yaml
    contents: "{{ lookup('file', 'output/show_interface.txt') }}"
"""

RETURN = """
network_facts:
  description: The JSON data returned from parsing the contents
  returned: always
"""
