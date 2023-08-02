#!/usr/bin/python
# plugins/module_utils/wasserver.py
# @version v1.06_2020-OCT-12
# @author Kevin Jeffery

import logging
import sys
import os
import os.path
import re
import json
import tempfile
from ansible_collections.kjeffery14.websphere.plugins.module_utils.wascommand import WASCommand # type: ignore[import]

class WASServer():
    def __init__(self, profile_inst, was_profile):
        self.profile_inst = profile_inst
        self.was_profile = was_profile
        self.module = profile_inst.module
        self.facts = {}
        self.module.debug("*** Process Arguments")
        self.logLevel           = self.module.params['log']
        self.force              = self.module.params['force']
        self.action             = self.module.params['action']
        self.was_home           = self.module.params['was_home']
        self.profile_name       = self.module.params['profile_name']
        self.server_name        = self.module.params['server_name']
        self.was_command        = WASCommand(self.module, self.was_home)

    def get_all(self):
        data = {}
        self.module.exit_json(changed=False, data=data)

    def status(self, username=None, password=None):
        # Usage: serverStatus.sh <server name> [-username <username>] [-password <password>] [-profileName <profile>]
        if not self._check(self.server_name):
            msg = 'Server Status, No server: {0}'.format(self.server_name)
            self.module.fail_json(changed=False, msg=msg)
        rc, stdout, stderr, data = self._server_status(username, password)
        self.module.exit_json(changed=False, rc=rc, stdout=stdout, stderr=stderr, data=data)
    
    def start(self, username=None, password=None):
        # Usage: startServer.sh <server name> [-username <username>] [-password <password>] [-profileName <profile>] [-replaceLog]
        if not self._check(self.server_name):
            msg = 'Start Server, No server: {0}'.format(self.server_name)
            self.module.fail_json(changed=False, msg=msg)
        cmd = self.was_command.commands['start_server_sh'].format(self.profile_name, self.server_name)
        if username is not None:
            cmd += '-username {0} -password {1} '.format(username, password)
        data = self._server_status(username, password)[3]
        if data['started']:
            self.module.exit_json(changed=False, msg="Running - Profile: {0}, Server: {1}".format(self.profile_name, self.server_name))
        rc, stdout, stderr = self.was_command.execute(cmd, "Error, Start failed - Profile: {0}, Server {1}".format(self.profile_name, self.server_name))
        self.module.exit_json(changed=True, rc=rc, stdout=stdout, stderr=stderr, msg="Started - Profile: {0}, Server: {1}".format(self.profile_name, self.server_name))
        
    def stop(self, username=None, password=None):
        # Usage: stopServer.sh <server name> [-username <username>] [-password <password>] [-profileName <profile>] [-replaceLog]
        if not self._check(self.server_name):
            msg = 'Stop Server, No server: {0}'.format(self.server_name)
            self.module.exit_json(changed=False, msg=msg)
        cmd = self.was_command.commands['stop_server_sh'].format(self.profile_name, self.server_name)
        if username is None or password is None:
            cmd += '-username {0} -password {1} '.format(username, password)
        data = self._server_status(username, password)[3]
        if not data['started']:
            self.module.exit_json(changed=False, msg="Not running - Profile: {0}, Server: {1}".format(self.profile_name, self.server_name))
        rc, stdout, stderr = self.was_command.execute(cmd, "Error, Stop failed - Profile: {0}, Server {1}".format(self.profile_name, self.server_name))
        self.module.exit_json(changed=True, rc=rc, stdout=stdout, stderr=stderr, msg="Stopped - Profile: {0}, Server: {1}".format(self.profile_name, self.server_name))

    def _server_status(self, username=None, password=None):
        cmd = self.was_command.commands['server_status_sh'].format(self.profile_name, self.server_name)
        if username is not None:
            cmd += '-username {0} -password {1} '.format(username, password)
        result={'state': 'STOPPED', 'started': False}
        rc, stdout, stderr = self.was_command.execute( cmd, \
            "Error, could not get server status for Profile: {0} Server: {1}".format(self.profile_name, self.server_name))
        for line in stdout.split('\n'):
            if 'ADMU0508I' in line and 'STARTED' in line:
                result['state'] = 'STARTED'
                result['started'] = True
        return rc, stdout, stderr, result

    def _check(self, server_name):
        for node in self.was_profile['nodes'].values():
            for server in node['servers']:
                if server['serverName'] == server_name:
                    return True
        return False
