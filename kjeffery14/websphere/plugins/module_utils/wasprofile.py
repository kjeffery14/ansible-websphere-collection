#!/usr/bin/python
# plugins/module_utils/wasprofile.py
# @version v1.08_2022-SEP-18
# @author Kevin Jeffery

import logging
import sys
import os
import os.path
import re
import json
import tempfile
# from os.path import expanduser
from ansible_collections.kjeffery14.websphere.plugins.module_utils.wascommand import WASCommand #type: ignore[import]

class WASProfile:
    def __init__(self, module):
        self.module = module
        self.facts = {}
        self.profile_params = dict(
            dmgr={'hostName': {'required': True}, 'nodeName': {'required': True}, 'cellName': {'required': False}, \
                'enableAdminSecurity': {'required': False}, 'isDefault': {'required': False}},
            managed={'hostName': {'required': True}, 'nodeName': {'required': True}, \
                'cellName': {'required': False}, 'isDefault': {'required': False}}
        )
        self.module.debug("*** Process Arguments")
        self.logLevel           = self.module.params['log']
        self.force              = self.module.params['force']
        if 'action' in module.params:
            self.action             = self.module.params['action']
        self.was_home           = self.module.params['was_home']
        self.profile_name       = self.module.params['profile_name']
        self.was_command = WASCommand(self.module, self.was_home)
        self.facts['versionInfo']   = self._get_version_info()

    # def version(self):
    #     self.module.exit_json(changed=False, data=self.facts['versionInfo'])
    
    def get_all(self):
        self.module.exit_json(changed=False, data=self._get_profiles(details=True))

    def search(self, profile_name=None):
        if profile_name is None:
            profile_name=self.profile_name
        profile, warnings = self._search(profile_name)
        if profile is None:
            self.module.exit_json(changed=False, warnings=warnings, msg=warnings[0])
        self.module.exit_json(changed=False, warnings=warnings, data=profile)

    def get(self):
        self.module.exit_json(changed=False, data=self._get(self.profile_name))

    def create(self, profile_path, profile_type, profile_params, username=None, password=None):
        profile_name = self.profile_name
        warnings = []
        if self._check(profile_name):
            warnings.append('Create, Profile exists: {0}'.format(profile_name))
            self.module.exit_json(changed=False, warnings=warnings, msg=warnings[0])
        if profile_type not in self.facts['versionInfo']['templates']:
            self.module.fail_json(changed=False, msg='Error, No template: {0}'.format(profile_type))
        if profile_type not in self.profile_params:
            self.module.fail_json(changed=False, msg='Error, Not supported: {0}'.format(profile_type))
        missing_required = False
        for name, value in self.profile_params[profile_type].items():
            if 'required' in value and value['required'] and name not in profile_params:
                warnings.append('Required: {0}'.format(name))
                missing_required = True
        if missing_required:
            self.module.fail_json(changed=False, msg='Error, Missing parameters', warnings=warnings)
        template_path = self.was_home + '/profileTemplates/' + profile_type
        cmd = self.was_command.commands['create_sh'].format(profile_name, profile_path, template_path)
        if 'enableAdminSecurity' in profile_params:
            #  and profile_params['enableAdminSecurity'] == 'true'
            if username is None or password is None:
                self.module.fail_json(changed=False, msg='Error, username and password are required')
            cmd += '-adminUserName ' + username + ' -adminPassword \"' + password + '\" '
        for name, value in profile_params.items():
            if name in self.profile_params[profile_type]:
                if isinstance(value, bool):
                    value = str(value).lower()
                cmd += '-' + name + ' \"' + value + '\" '
            else:
                warnings.append('Not supported: {0}'.format(name))
        rc, stdout, stderr = self.was_command.execute(cmd, 'Error, failed to create: {0}'.format(profile_name))
        self.module.exit_json(changed=True, rc=rc, stdout=stdout, stderr=stderr, msg='Profile created: {0}'.format(profile_name), warnings=warnings, data=self._get(profile_name))

    def delete(self):
        profile_name = self.profile_name
        profile, warnings = self._search(profile_name)
        if profile is None:
            self.module.exit_json(changed=False, warnings=warnings, msg=warnings[0])
        if profile['federated'] and not self.force:
            warnings.append('Profile is federated.  Remove node before deleting or force deletion and cleanup dmgr later')
            self.module.exit_json(changed=False, warnings=warnings, msg=warnings[0])
        cmd = self.was_command.commands['delete_sh'].format(profile_name)
        rc, stdout, stderr = self.was_command.execute(cmd, '', ignore_errors=True)
        if rc > 0 and 'The profile no longer exists' not in stdout:
            self.module.fail_json(rc=rc, stdout=stdout, stderr=stderr, msg='Error, Delete failed - Profile: {0}'.format(profile_name))
        msg = 'Profile deleted: {0}'.format(profile_name)
        self.module.exit_json(changed=True, rc=rc, stdout=stdout, stderr=stderr, msg=msg)

    # def server_status(self, server_name, username=None, password=None):
    #     # Usage: serverStatus.sh <server name> [-username <username>] [-password <password>] [-profileName <profile>]
    #     profile_name = self.profile_name
    #     if not self._check(profile_name):
    #         warnings = ['Server Status, No profile: {0}'.format(profile_name)]
    #         self.module.exit_json(changed=False, warnings=warnings, msg=warnings[0])
    #     rc, stdout, stderr, data = self._server_status(profile_name, server_name, username, password)
    #     self.module.exit_json(changed=False, rc=rc, stdout=stdout, stderr=stderr, data=data)
    
    # def start_server(self, server_name, username=None, password=None):
    #     profile_name = self.profile_name
    #     # Usage: startServer.sh <server name> [-username <username>] [-password <password>] [-profileName <profile>] [-replaceLog]
    #     if self._check(profile_name):
    #         profile = self._get(profile_name)
    #     else:
    #         warnings = ['Start Server, No profile: {0}'.format(profile_name)]
    #         self.module.exit_json(changed=False, warnings=warnings, msg=warnings[0])
    #     cmd = self.was_command.commands['start_server_sh'].format(profile_name, server_name)
    #     if profile['security_settings']['enabled'].lower() == 'true':
    #         if username is None or password is None:
    #             self.module.fail_json(changed=False, msg='Error, username and password are required')
    #         cmd += '-username {0} -password {1} '.format(username, password)
    #     data = self._server_status(profile_name, server_name, username, password, profile)[3]
    #     if data['started']:
    #         self.module.exit_json(changed=False, msg="Running - Profile: {0}, Server: {1}".format(profile_name, server_name))
    #     rc, stdout, stderr = self.was_command.execute(cmd, "Error, Start failed - Profile: {0}, Server {1}".format(profile_name, server_name))
    #     self.module.exit_json(changed=True, rc=rc, stdout=stdout, stderr=stderr, msg="Started - Profile: {0}, Server: {1}".format(profile_name, server_name))
        
    # def stop_server(self, server_name, username=None, password=None):
    #     profile_name = self.profile_name
    #     # Usage: stopServer.sh <server name> [-username <username>] [-password <password>] [-profileName <profile>] [-replaceLog]
    #     if self._check(profile_name):
    #         profile = self._get(profile_name)
    #     else:
    #         warnings = ['Stop Server, No profile: {0}'.format(profile_name)]
    #         self.module.exit_json(changed=False, warnings=warnings, msg=warnings[0])
    #     cmd = self.was_command.commands['stop_server_sh'].format(profile_name, server_name)
    #     if profile['security_settings']['enabled'].lower() == 'true':
    #         if username is None or password is None:
    #             self.module.fail_json(changed=False, msg='Error, username and password are required')
    #         cmd += '-username {0} -password {1} '.format(username, password)
    #     data = self._server_status(profile_name, server_name, username, password, profile)[3]
    #     if not data['started']:
    #         self.module.exit_json(changed=False, msg="Not running - Profile: {0}, Server: {1}".format(profile_name, server_name))
    #     rc, stdout, stderr = self.was_command.execute(cmd, "Error, Stop failed - Profile: {0}, Server {1}".format(profile_name, server_name))
    #     self.module.exit_json(changed=True, rc=rc, stdout=stdout, stderr=stderr, msg="Stopped - Profile: {0}, Server: {1}".format(profile_name, server_name))

    def remove_node(self, username=None, password=None):
        profile_name = self.profile_name
        profile, warnings = self._search(profile_name)
        if profile is None:
            self.module.exit_json(changed=False, warnings=warnings, msg=warnings[0])
        cmd = self.was_command.commands['remove_node_sh'].format(profile_name)
        if profile['security_settings']['enabled'].lower() == 'true':
            if username is None or password is None:
                self.module.fail_json(changed=False, msg='Error, username and password are required')
            cmd += '-username {0} -password {1} '.format(username, password)
        if profile['federated']:
            rc, stdout, stderr = self.was_command.execute(cmd, "Error, could not unfederate node")
            self.module.exit_json(changed=True, rc=rc, stdout=stdout, stderr=stderr, msg="Unfederated: {0}".format(profile_name))
        self.module.exit_json(changed=False, msg="Nothing to do")

    def add_node(self, dmgr_host, dmgr_port=None, username=None, password=None):
        profile_name = self.profile_name
        if username is None or password is None:
            self.module.fail_json(changed=False, msg='Error, username and password are required')
        # [-startingport <portnumber>]
        # [-nodeagentshortname <name>]
        # [-excludesecuritydomains]
        # [-help]
        profile = self._get(profile_name)
        if profile['federated']:
            self.module.exit_json(changed=False, msg='Already federated - Profile: {0}'.format(profile_name))
        if dmgr_port is not None:
            cmd = self.was_command.commands['add_node_sh'].format(profile_name, dmgr_host, dmgr_port)
        else:
            cmd = self.was_command.commands['add_node_sh'].format(profile_name, dmgr_host, '')
        cmd += '-username {0} -password {1} '.format(username, password)
        rc, stdout, stderr = self.was_command.execute(cmd, "Error, failed to federate node - Profile: {0}".format(profile_name))
        self.module.exit_json(changed=True, rc=rc, stdout=stdout, stderr=stderr, msg="Federated node - Profile: {0}".format(profile_name))

    def get_clusters(self, username=None, password=None):
        profile_name = self.profile_name
        profile = self._search(profile_name)[0]
        if profile is None:
            self.module.fail_json(msg='Get Clusters, No profile: {0}'.format(profile_name))
        cmd = self.was_command.commands['wsadmin_jython'].format(profile_name)
        if profile['security_settings']['enabled'].lower() == 'true':
            if username is None or password is None:
                self.module.fail_json(changed=False, msg='Error, username and password are required')
            cmd += '-userid {0} -password {1} '.format(username, password)
        cmd += '"AdminClusterManagement.listClusters()"'
        rc, stdout, stderr = self.was_command.execute(cmd, 'Error,')
        self.module.exit_json(changed=False, rc=rc, stdout=stdout, stderr=stderr, msg=stdout)

    def wsadmin(self, script, lang, profile_script=None, username=None, password=None):
        changed = False
        warnings = []
        profile_name = self.profile_name
        profile = self._search(profile_name)[0]
        if profile is None:
            self.module.fail_json(msg='Get Clusters, No profile: {0}'.format(profile_name))
        if lang == 'jacl':
            cmd = self.was_command.commands['wsadmin_jacl'].format(profile_name)
        else:
            cmd = self.was_command.commands['wsadmin_jython'].format(profile_name)
        if profile['security_settings']['enabled'].lower() == 'true':
            if username is None or password is None:
                self.module.fail_json(changed=False, msg='Error, username and password are required')
            cmd += '-user {0} -password {1} '.format(username, password)
        if profile_script is not None:
            cmd += '-profile {0} '.format(profile_script)
        cmd += '-f {0}'.format(script)
        rc, stdout, stderr = self.was_command.execute(cmd, 'Error, {0}'.format(script))
        stdout_lines = stdout.split('\n')
        for line in stdout_lines:
            line = line.strip()
            if len(line) == 0: continue
            if 'ansible_changed' in line:
                result = json.loads(line)
                changed = result['ansible_changed']
                warnings = result['warnings']
        self.module.exit_json(changed=changed, rc=rc, stdout=stdout, stderr=stderr, msg=stdout, warnings=warnings)

    def _search(self, profile_name):
        warnings = []
        if self._check(profile_name):
            return self._get(profile_name), warnings
        warnings.append('Internal Search, No profile: {0}'.format(profile_name))
        return None, warnings

    def _server_status(self, profile_name, server_name, username=None, password=None, profile=None):
        if profile is None:
            if self._check(profile_name):
                profile = self._get(profile_name)
            else:
                self.module.exit_json(changed=False, warnings=['Internal Status, No profile: {0}'.format(profile_name)])
        cmd = self.was_command.commands['server_status_sh'].format(profile_name, server_name)
        if profile['security_settings']['enabled'].lower() == 'true':
            if username is None or password is None:
                self.module.fail_json(changed=False, msg='Error, username and password are required')
            cmd += '-username {0} -password {1} '.format(username, password)
        result={'state': 'STOPPED', 'started': False}
        rc, stdout, stderr = self.was_command.execute( cmd, \
            "Error, could not get server status for Profile: {0} Server: {1}".format(profile_name, server_name))
        for line in stdout.split('\n'):
            if 'ADMU0508I' in line and 'STARTED' in line:
                result['state'] = 'STARTED'
                result['started'] = True
        return rc, stdout, stderr, result

    def _get_profiles(self, details=False):
        reply = []
        std_out = self.was_command.execute(self.was_command.commands['list_profiles_sh'], "Error, could not list profiles")[1]
        profile_list = std_out.split('\n')[0][1:-1].split(', ')
        for profile_name in profile_list:
            if details:
                profile_obj = self._get(profile_name)
            else:
                profile_obj = {'profile_name': profile_name}
            reply.append(profile_obj)
        return reply

    def _check(self, profile_name):
        for profile in self._get_profiles():
            if profile['profile_name'] == profile_name:
                return True
        return False

    def _get(self, profile_name):
        profile_obj = {'profile_name': profile_name}
        std_out = self.was_command.execute(self.was_command.commands['profile_path_sh'].format(profile_name), "Error, could not get profile path")[1]
        profile_obj['path'] = std_out.split('\n')[0]
        profile_obj['dmgr'] = os.path.exists(profile_obj['path'] + '/bin/startManager.sh')
        profile_obj['federated'] = False
        profile_obj['cell_name'] = self._get_subdirectories(profile_obj['path'] + '/config/cells')[0]
        cell_path = profile_obj['path'] + '/config/cells/' + profile_obj['cell_name']
        nodes_path = cell_path + '/nodes'
        profile_obj['security_settings'] = self._get_xml_tags(cell_path + '/security.xml', 'security:Security')[0]
        profile_obj['nodes'] = {}
        if os.path.exists(nodes_path):
            node_list = self._get_subdirectories(nodes_path)
            for node in node_list:
                profile_obj['nodes'][node] = {}
                profile_obj['nodes'][node]['node'] = self._get_xml_tags(nodes_path + '/' + node + '/serverindex.xml','serverindex:ServerIndex' )[0]
                profile_obj['nodes'][node]['servers'] = self._get_xml_tags(nodes_path + '/' + node + '/serverindex.xml','serverEntries')
                for server in profile_obj['nodes'][node]['servers']:
                    if server['serverName'] == 'nodeagent':
                        profile_obj['federated'] = True
        return profile_obj

    def _get_subdirectories(self, path):
        result = []
        contents = os.listdir(path)
        for item in contents:
            if os.path.isdir(path + '/' + item):
                result.append(item)
        return result

    def _remove_whitespace(self, strData):
        ret_value = ""
        space = ""
        try:
            list_words = strData.split()
            for word in list_words:
                ret_value += space + word
                space = " "
        except:
            return ""
        return ret_value

    def _load_properties(self, filepath, sep='=', comment_char='#'):
        """
        Read the file passed as parameter as a properties file.
        """
        props = {}
        try:
            with open(filepath, "rt") as f:
                for line in f:
                    key, value = self._get_key_and_value(line, sep, comment_char)
                    if key:
                        props[key] = value
            f.close()
        except OSError as err:
            if f:
                f.close()
            self.module.fail_json(changed=True, msg=str(err))
        return props

    def _get_key_and_value(self, line, sep='=', comment_char='#'):
        l = line.strip()
        key = None
        value = None
        if l and not l.startswith(comment_char):
            key_value = l.split(sep)
            key = key_value[0].strip()
            value = sep.join(key_value[1:]).strip().strip('"')
        return key, value

    def _get_xml_tags(self, xml_path, tag_name):
        stdout = self.module.run_command("grep '<" + tag_name + "' " + xml_path, use_unsafe_shell=False)[1]
        tags = stdout.split('\n')
        result = []
        for tag in tags:
            if tag.strip():
                result.append(self._parse_xml_entry(tag, tag_name))
        return result

    def _parse_xml_entry(self, xml_entry, tag_name):
        entry_string = xml_entry.replace('<','').replace('"','').replace('>','').strip()
        result = {}
        settings = entry_string.split()
        last_key = ''
        for setting in settings:
            if setting.startswith(tag_name) or \
            setting.startswith('xmlns:') or \
            setting.startswith('xmi:'):
                continue
            key, value = self._get_key_and_value(setting)
            if value:
                last_key = key
                result[key] = value
            else:
                result[last_key] += ',' + key
        return result

    def _get_version_info(self):
        stdout = self.was_command.execute(self.was_command.commands['version_info_sh'], "Error, could not get versionInfo")[1]
        reply = {'product': {}, 'fixpack': {}, 'sdkfix': {}}
        reply['templates'] = os.listdir(self.was_home + '/profileTemplates')
        config_info = stdout.split('\n')
        product = False
        fixpack = False
        sdkfix = False
        for line in config_info:
            config_line = line.strip()
            if not config_line or config_line.startswith('-'):
                continue
            if 'Installed Product' in config_line:
                product = True
                fixpack = False
                sdkfix = False
                continue
            if 'WS-WAS-' in config_line:
                reply['fixpack']['id'] = self._get_config_value(config_line)
                product = False
                fixpack = True
                sdkfix = False
                continue
            if 'WS-WASSDK-' in config_line:
                reply['sdkfix']['id'] = self._get_config_value(config_line)
                product = False
                fixpack = False
                sdkfix = True
                continue
            if product:
                if config_line.startswith('Name'):
                    reply['product']['name'] = self._get_config_value(config_line)
                if config_line.startswith('Version'):
                    reply['product']['version'] = self._get_config_value(config_line)
                if config_line.startswith('ID'):
                    reply['product']['id'] = self._get_config_value(config_line)
                if config_line.startswith('Build Level'):
                    reply['product']['build_level'] = self._get_config_value(config_line)
                if config_line.startswith('Build Date'):
                    reply['product']['build_date'] = self._get_config_value(config_line)
                if config_line.startswith('Architecture'):
                    reply['product']['architecture'] = self._get_config_value(config_line)
                    product = False
            if fixpack:
                if config_line.startswith('Description'):
                    reply['fixpack']['description'] = self._get_config_value(config_line)
                if config_line.startswith('Build Date'):
                    reply['fixpack']['build_date'] = self._get_config_value(config_line)
                    fixpack = False
            if sdkfix:
                if config_line.startswith('Description'):
                    reply['sdkfix']['description'] = self._get_config_value(config_line)
                if config_line.startswith('Build Date'):
                    reply['sdkfix']['build_date'] = self._get_config_value(config_line)
                    sdkfix = False

        return reply

    def _get_config_value(self, config_line):
        return config_line[25:]
# Maintenance Package ID   7.0.0-WS-WAS-LinuxX64-FP0000045

    def _version_compare(self, version):
        def normalize(v):
            v = re.sub(r'_b\d+$', '', v)
            return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split(".")]
        if normalize(self.facts['version']['version']) == normalize(version):
            return 0
        elif normalize(self.facts['version']['version']) > normalize(version):
            return 1
        elif normalize(self.facts['version']['version']) < normalize(version):
            return -1
