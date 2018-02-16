#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2017, Ansible by Red Hat, inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'network'}


DOCUMENTATION = """
---
module: network_template
version_added: "2.5"
author: "Peter Sprygada (@privateip)"
short_description: Render a configuration from facts
description:
  - The module will render a device configuration from the available set of
    facts for the host.
options:
  src:
    description:
      - The name of the template to process.  The template filename can be
        provided as an absolute path or a relative path.  If it is a relative
        path, the module will check in the templates folder for the file.
    required: true
  private_vars:
    description:
      - Set of variables to be used by the template in addition to the host
        facts collection.  This value accepts a dict object of key /value
        pairs.
    required: false
    default: null
"""

EXAMPLES = """
- name: render a configuration template
  network_template:
    src: config.yaml

- name: render a configuration template with private vars
  network_template:
    src: config.yaml
    private_vars:
        hostname: localhost
        domain_name: ansible.com
"""

RETURN = """
text:
  description: The output from processing the template
  returned: always
  sample: "hostname localhost\nip domain-name ansible.com"
lines:
  description: The text output broken into lines
  returned: always
  sample:
    - hostname localhost
    - ip domain-name ansible.com
"""
