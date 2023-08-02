#!/usr/bin/python
# plugins/module_utils/wascommand.py
# @version v1.05_2020-OCT-07
# @author Kevin Jeffery

import logging
import sys
import os
import os.path
import re
import json
import tempfile

class WASCommand():
    def __init__(self, module, was_home):
        self.module = module
        self.was_home = was_home
        self.commands = dict(
            version_info_sh = '/bin/versionInfo.sh -maintenancePackages', 
            list_profiles_sh = '/bin/manageprofiles.sh -listProfiles', 
            profile_path_sh = '/bin/manageprofiles.sh -getPath -profileName {0}', 
            delete_sh = '/bin/manageprofiles.sh -delete -profileName {0}', 
            create_sh = '/bin/manageprofiles.sh -create -profileName {0} -profilePath {1} -templatePath {2} ', 
            server_status_sh = '/bin/serverStatus.sh {1} -profileName {0} ', 
            start_server_sh = '/bin/startServer.sh {1} -profileName {0} -replacelog ', 
            stop_server_sh = '/bin/stopServer.sh {1} -profileName {0} -replacelog ', 
            add_node_sh = '/bin/addNode.sh {1} {2} -profileName {0} -noagent ', 
            remove_node_sh = '/bin/removeNode.sh -profileName {0} -replacelog ',
            wsadmin_jacl = '/bin/wsadmin.sh -lang jacl -profileName {0} ',
            wsadmin_jython = '/bin/wsadmin.sh -lang jython -profileName {0} ',
            username_password = '-username {0} -password {1} '
        )

    def execute(self, cmd, error_msg, ignore_errors=False):
        rc, stdout, stderr = self.module.run_command(self.was_home + cmd, use_unsafe_shell=True)
        # error_msg += '; ' + self.was_home + cmd
        if ignore_errors:
            return rc, stdout, stderr
        if stderr != '' or rc != 0:
            self.module.fail_json(changed=False, msg=error_msg, stderr=stderr, rc=rc, stdout=stdout)
        return rc, stdout, stderr
