#!/usr/bin/python
# lugins/modules/wasserver.py
# @version v1.06_2022-SEP-16
# @author Kevin Jeffery

import logging
import sys
import os
import os.path
import re
import json
import tempfile
# from os.path import expanduser

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.wasprofile import WASProfile # type: ignore[import]
from ansible.module_utils.wasserver import WASServer # type: ignore[import]

# Maintenance Package ID   7.0.0-WS-WAS-LinuxX64-FP0000045

    # def _version_compare(self, version):
    #     def normalize(v):
    #         v = re.sub(r'_b\d+$', '', v)
    #         return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split(".")]
    #     if normalize(self.facts['version']['version']) == normalize(version):
    #         return 0
    #     elif normalize(self.facts['version']['version']) > normalize(version):
    #         return 1
    #     elif normalize(self.facts['version']['version']) < normalize(version):
    #         return -1


def main():
    argument_spec=dict(
        log=dict(required=False, default='INFO', choices=['DEBUG', 'INFO', 'ERROR', 'CRITICAL']),
        force=dict(required=False, default=False, type='bool'),
        action=dict(required=True, type='str'),
        was_home=dict(required=True, type='path'),
        profile_name=dict(required=True, type='str'),
        username=dict(required=False, type='str'),
        password=dict(required=False, type='str', no_log=True),
        server_name=dict(required=True, type='str')
        )
    required_together = [
        ['username', 'password']
        ]
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False, required_together=required_together)
    # required_together=[]

    module.debug('Started was module')

    profile_inst = WASProfile(module)
    # profile_inst.parse_params()
    was_profile = profile_inst._search(profile_inst.profile_name)[0]
    if was_profile is None:
        warnings = ['No profile: {0}'.format(profile_inst.profile_name)]
        profile_inst.module.fail_json(changed=False, msg=warnings[0])
    if was_profile['security_settings']['enabled'].lower() == 'true':
            if profile_inst.module.params['username'] is None:
                profile_inst.module.fail_json(changed=False, msg='Error, username and password are required')

    server_inst = WASServer(profile_inst, was_profile)

    if profile_inst.action == 'get_all':
        server_inst.get_all()

    if server_inst.action == 'status':
        server_inst.status(username=server_inst.module.params['username'], password=server_inst.module.params['password'])
        
    if server_inst.action == 'start':
        server_inst.start(username=server_inst.module.params['username'], password=server_inst.module.params['password'])
        
    if server_inst.action == 'stop':
        server_inst.stop(username=server_inst.module.params['username'], password=server_inst.module.params['password'])
        
    module.fail_json(changed=False, msg="Error, Invalid action: {0}".format(server_inst.action))


if __name__ == '__main__':
    main()
