#!/usr/bin/python
# plugins/modules/wasprofile.py
# @version v1.07_2022-SEP-18
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
from ansible_collections.kjeffery14.websphere.plugins.module_utils.wasprofile import WASProfile # type: ignore[import]

def main():
    argument_spec=dict(
        log=dict(required=False, default='INFO', choices=['DEBUG', 'INFO', 'ERROR', 'CRITICAL']),
        force=dict(required=False, default=False, type='bool'),
        action=dict(required=True, type='str'),
        was_home=dict(required=True, type='path'),
        profile_name=dict(required=False, type='str'),
        username=dict(required=False, type='str'),
        password=dict(required=False, type='str', no_log=True),
        dmgr_host=dict(required=False, type='str'),
        dmgr_port=dict(required=False, type='int'),
        server_name=dict(required=False, type='str'),
        profile_path=dict(required=False, type='path'),
        profile_type=dict(required=False, type='str', choices=['cell','default','dmgr','managed','management','secureproxy']),
        profile_params=dict(required=False, type='dict'),
        script=dict(required=False,type='path'),
        lang=dict(required=False, type='str', choices=['jacl', 'jython']),
        profile=dict(required=False, type='path')
        )
    required_together = [
        ['profile_path', 'profile_type', 'profile_params'],
        ['username','password'],
        ['script','lang']
        ]
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False, required_together=required_together)

    module.debug('Started was module')

    profile_inst = WASProfile(module)

    if profile_inst.action == "version":
        profile_inst.version()

    if profile_inst.action == 'get_all':
        profile_inst.get_all()

    if profile_inst.action == "get":
        if profile_inst.profile_name is None:
            module.fail_json(changed=False, msg="Error, profile_name is required")
        profile_inst.get()

    if profile_inst.action == "search":
        if profile_inst.profile_name is None:
            module.fail_json(changed=False, msg="Error, profile_name is required")
        profile_inst.search()

    if profile_inst.action == "create":
        if profile_inst.profile_name is None:
            module.fail_json(changed=False, msg="Error, profile_name is required")
        if profile_inst.module.params['profile_type'] is None:
            module.fail_json(changed=False, msg="Error, profile settings are required")
        profile_inst.create(profile_inst.module.params['profile_path'], \
            profile_inst.module.params['profile_type'], profile_inst.module.params['profile_params'], \
            username=profile_inst.module.params['username'], password=profile_inst.module.params['password'])

    if profile_inst.action == "delete":
        if profile_inst.profile_name is None:
            module.fail_json(changed=False, msg="Error, profile_name is required")
        profile_inst.delete()

    if profile_inst.action == "add_node":
        if profile_inst.profile_name is None or profile_inst.module.params['dmgr_host'] is None:
            module.fail_json(changed=False, msg="Error, name and dmgr_host are required")
        profile_inst.add_node(profile_inst.module.params['dmgr_host'], \
            dmgr_port=profile_inst.module.params['dmgr_port'], \
            username=profile_inst.module.params['username'], password=profile_inst.module.params['password'])

    if profile_inst.action == "remove_node":
        if profile_inst.profile_name is None:
            module.fail_json(changed=False, msg="Error, profile_name is required")
        profile_inst.remove_node(username=profile_inst.module.params['username'], password=profile_inst.module.params['password'])

    # if profile_inst.action == 'server_status':
    #     if profile_inst.profile_name is None or profile_inst.module.params['server_name'] is None:
    #         module.fail_json(changed=False, msg="Error, name and server_name are required")
    #     profile_inst.server_status(profile_inst.module.params['server_name'], \
    #         username=profile_inst.module.params['username'], password=profile_inst.module.params['password'])
        
    # if profile_inst.action == 'start_server':
    #     if profile_inst.profile_name is None or profile_inst.module.params['server_name'] is None:
    #         module.fail_json(changed=False, msg="Error, name and server_name are required")
    #     profile_inst.start_server(profile_inst.module.params['server_name'], \
    #         username=profile_inst.module.params['username'], password=profile_inst.module.params['password'])
        
    # if profile_inst.action == 'stop_server':
    #     if profile_inst.profile_name is None or profile_inst.module.params['server_name'] is None:
    #         module.fail_json(changed=False, msg="Error, name and server_name are required")
    #     profile_inst.stop_server(profile_inst.module.params['server_name'], \
    #         username=profile_inst.module.params['username'], password=profile_inst.module.params['password'])
        
    if profile_inst.action == 'get_clusters':
        if profile_inst.profile_name is None:
            module.fail_json(changed=False, msg="Error, profile_name is required")
        profile_inst.get_clusters(username=profile_inst.module.params['username'], password=profile_inst.module.params['password'])

    if profile_inst.action == 'wsadmin':
        if profile_inst.profile_name is None:
            module.fail_json(changed=False, msg="Error, profile_name is required")
        lang = profile_inst.module.params['lang']
        script = profile_inst.module.params['script']
        if script is None:
            module.fail_json(changed=False, msg="Error, script and lang are required")
        profile_inst.wsadmin(script=script, lang=lang, profile_script=profile_inst.module.params['profile'], username=profile_inst.module.params['username'], password=profile_inst.module.params['password'])

    module.fail_json(changed=False, msg="Error, Invalid action: {0}".format(profile_inst.action))


if __name__ == '__main__':
    main()
