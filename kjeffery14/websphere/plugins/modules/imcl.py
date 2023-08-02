#!/usr/bin/python
# plugins/modules/imcl.py
# @version v1.04_2023-APR-18
# @author Kevin Jeffery

import sys
import os
import re
import json
import tempfile
from os.path import expanduser
from ansible.module_utils.basic import AnsibleModule # type: ignore[import]

class imcl:
    def __init__(self, module):
        imcl = '/eclipse/tools/imcl'
        self.module = module
        self.facts = {}
        self.install_cmd = imcl + ' install {0} -acceptLicense -sharedResourcesDirectory {1} ' # install packageID SharedResources
        self.list_cmd = imcl + ' listInstalledPackages -long' # listInstalledPackages
        self.uninstall_cmd = imcl + ' uninstall {0} ' # uninstall packageID[_version][,featureID]
        self.version_cmd = imcl + ' version' # version

    def parse_params(self):
        self.module.debug("*** Process all Arguments")
        self.logLevel           = self.module.params['log']
        self.force              = self.module.params['force']
        self.action             = self.module.params['action']
        self.path               = self.module.params['iim_home']
        self.shared             = self.module.params['iim_shared']
        self.facts              = self._get_version()

    def get_version(self):
        self.module.exit_json(changed=False, data=self.facts)

    def get_all(self):
        self.module.exit_json(changed=False, data=self._get_all())

    def get(self, package_id):
        self.module.exit_json(changed=False, data=self._get(package_id))

    def install(self, package_id, install_directory, repositories, properties=None, feature_id=None, preferences=None):
        reply = self._get(package_id)
        warnings = []
        if reply['installed'] and reply['install_location'] == install_directory:
            warnings.append('Found: {0} Version: {1}'.format(package_id, reply['version']))
            self.module.exit_json(changed=False, warnings=warnings, data=reply)
        cmd = self.path + self.install_cmd.format(package_id, self.shared) + \
            '-installationDirectory {0} -repositories {1}'.format(install_directory, ','.join(repositories))
        if properties is not None:
            cmd += ' -properties {0}'.format(','.join(properties))
        if preferences is not None:
            cmd += ' -preferences {0}'.format(','.join(preferences))
        stdout = self._imcl_command(cmd, 'Error> Could not install {0}'.format(package_id))[1]
        stdout_lines = stdout.split('\n')
        for line in stdout_lines:
            if line.strip():
                warnings.append(line.strip())
        self.module.exit_json(changed=True, warnings=warnings)

    def install_multi(self, package_list, install_directory, repositories, properties=None, feature_id=None, preferences=None):
        warnings = []
        for package_id in package_list:
            reply = self._get(package_id)
            if reply['installed'] and reply['install_location'] == install_directory:
                warnings.append('Found: {0} Version: {1}'.format(package_id, reply['version']))
        if len(warnings) > 0:
            self.module.exit_json(changed=False, warnings=warnings, data=reply)
        cmd = self.path + self.install_cmd.format(' '.join(package_list), self.shared) + \
            '-installationDirectory {0} -repositories {1}'.format(install_directory, ','.join(repositories))
        if properties is not None:
            cmd += ' -properties {0}'.format(','.join(properties))
        if preferences is not None:
            cmd += ' -preferences {0}'.format(','.join(preferences))
        stdout = self._imcl_command(cmd, 'Error> Could not install {0}'.format(' '.join(package_list)))[1]
        stdout_lines = stdout.split('\n')
        for line in stdout_lines:
            if line.strip():
                warnings.append(line.strip())
        self.module.exit_json(changed=True, warnings=warnings)

    def update(self, package_id, repositories, properties=None, feature_id=None, preferences=None):
        reply = self._get(package_id)
        warnings = []
        if not reply['installed']:
            'Not found: {0}'.format(package_id)
            self.module.fail_json(changed=False, msg='Not found: {0}'.format(package_id))
        cmd = self.path + self.install_cmd.format(package_id, self.shared) + ' -repositories {0}'.format(','.join(repositories))
        if properties is not None:
            cmd += ' -properties {0}'.format(','.join(properties))
        if preferences is not None:
            cmd += ' -preferences {0}'.format(','.join(preferences))
        stdout = self._imcl_command(cmd, 'Error> Could not install {0}'.format(package_id))[1]
        stdout_lines = stdout.split('\n')
        for line in stdout_lines:
            if line.strip():
                warnings.append(line.strip())
        self.module.exit_json(changed=True, warnings=warnings)

    def uninstall(self, package_id, install_directory=None):
        reply = self._get(package_id)
        warnings = []
        if not reply['installed']:
            warnings.append('Not found: {0}'.format(package_id))
            self.module.exit_json(changed=False, warnings=warnings, data=reply)
        cmd = self.path + self.uninstall_cmd.format(package_id)
        if install_directory is not None:
            cmd += '-installationDirectory {0} '.format(install_directory)
        stdout = self._imcl_command(cmd, 'Error> Could not uninstall {0}'.format(package_id))[1]
        stdout_lines = stdout.split('\n')
        for line in stdout_lines:
            if line.strip():
                warnings.append(line.strip())
        self.module.exit_json(changed=True, warnings=warnings)

    def _process_config_line(self, line, sep=': ', comment_char='#'):
        l = line.strip()
        key = None
        value = None
        if l and not l.startswith(comment_char):
            key_value = l.split(sep)
            if len(key_value) < 2:
                return l, value
            key = key_value[0].strip()
            value = sep.join(key_value[1:])
        return key, value

    def _imcl_command(self, cmd, error_msg):
        rc, stdout, stderr = self.module.run_command(cmd, use_unsafe_shell=True)
        if stderr != '' or rc != 0:
            self.module.fail_json(changed=False, msg=error_msg, stderr=stderr, rc=rc, stdout=stdout)
        return rc, stdout, stderr

    def _get_version(self):
        reply = {'installed': False}
        if not os.path.exists(self.path):
            return reply
        reply['installed'] = True
        stdout = self._imcl_command(self.path + self.version_cmd, "Error, could not get imcl version")[1]
        config_info = stdout.split('\n')
        for config_line in config_info:
            key, value = self._process_config_line(config_line)
            if value is None:
                continue
            key = key.replace(' ','_').lower()
            reply[key] = value
        return reply

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

    def _get_all(self):
        reply = []
        if not self.facts['installed']:
            return reply
        stdout = self._imcl_command(self.path + self.list_cmd, "Error> Could not list installed")[1]
        for line in stdout.split('\n'):
            pkg_info = line.strip().split(' : ')
            if len(pkg_info) == 4:
                package = {'installed': True, 'install_location': pkg_info[0], 'package_id': pkg_info[1].split('_')[0],'internal_version': pkg_info[1].split('_')[1], 'display_name': pkg_info[2], 'version': pkg_info[3] }
                reply.append(package)
        return reply

    def _get(self, package_id):
        reply = {'installed': False}
        pkg_list = self._get_all()
        if len(pkg_list) == 0:
            return reply
        for pkg in pkg_list:
            if pkg['package_id'] == package_id:
                return pkg
        return reply

def main():
    module = AnsibleModule(
        argument_spec=dict(
        log=dict(required=False, default='INFO', choices=['DEBUG', 'INFO', 'ERROR', 'CRITICAL']),
        force=dict(required=False, default=False, type='bool'),
        action=dict(required=True, type='str', choices=[
            'version', #
            'install', # Install packageID[_version][,featureID]
            'install_multi', # Install packageID[_version],packageID[_version]
            'update',
            'uninstall', # Uninstall package
            'get',
            'get_all'
        ]),
        iim_home=dict(required=True, type='path'),
        iim_shared=dict(required=True, type='path'),
        package_id=dict(required=False, type='str'),
        package_list=dict(required=False, type='list'),
        install_directory=dict(required=False, type='path'),
        repositories=dict(required=False, type='list'),
        feature_id=dict(required=False, type='list'),
        preferences=dict(required=False, type='list'),
        properties=dict(required=False, type='list')
       ),
        supports_check_mode=False
   )

    module.debug('Started imcl module')

    inst = imcl(module)
    inst.parse_params()

    if inst.action == "version":
        inst.get_version()

    if inst.action == 'get_all':
        inst.get_all()

    if inst.action == 'install_multi':
        package_list = module.params['package_list']
        install_directory = module.params['install_directory']
        repositories = module.params['repositories']
        if package_list is None:
            module.fail_json(changed=False, msg="Error, package_list is required")
        if install_directory is None or repositories is None:
            module.fail_json(changed=False, msg="Error, install_directory and repositories are required")
        inst.install_multi(package_list, install_directory, repositories, module.params['properties'],
            module.params['feature_id'], module.params['preferences'])

    # Methods below require package_id
    package_id = module.params['package_id']
    if package_id is None:
        module.fail_json(changed=False, msg="Error, package_id is required")

    if inst.action == 'get':
        inst.get(package_id)

    if inst.action == 'uninstall':
        inst.uninstall(package_id)

    if inst.action == 'install':
        install_directory = module.params['install_directory']
        repositories = module.params['repositories']
        if install_directory is None or repositories is None:
            module.fail_json(changed=False, msg="Error, install_directory and repositories are required")
        inst.install(package_id, install_directory, repositories, module.params['properties'],
            module.params['feature_id'], module.params['preferences'])

    if inst.action == 'update':
        repositories = module.params['repositories']
        if repositories is None:
            module.fail_json(changed=False, msg="Error, repositories is required")
        inst.update(package_id, repositories, module.params['properties'],
            module.params['feature_id'], module.params['preferences'])

    module.fail_json(changed=False, msg="Error, Invalid action: {0}".format(inst.action))


if __name__ == '__main__':
    main()
