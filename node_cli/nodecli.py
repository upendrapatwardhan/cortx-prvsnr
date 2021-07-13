#!/usr/bin/env python3

# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import sys
import os
import traceback
import asyncio
import errno
import shlex
from getpass import getpass
from cmd import Cmd
import pathlib
import argparse



class Response(object):
    def __init__(self, rc=0, output=''):
        self._rc = int(rc)
        self._output = output

    def output(self):
        return self._output

    def rc(self):
        return self._rc

    def __str__(self):
        return '%d: %s' % (self._rc, self._output)



class NodeCli(Cmd):
    def __init__(self, args):
        super(NodeCli, self).__init__()
        self.intro = 'Node cli interface'
        self.prompt = 'nodecli>> '
        if len(args) > 1:
            self.args = args[1:]
        else:
            self.args = "help"

    def preloop(self):
        #TODO Set Logger
        Log.init("nodecli",
             backup_count = 10,
             file_size_in_mb = 10,
             log_path = '/var/log/seagate/nodecli/',
             level = 'INFO')

    def emptyline(self):
        pass

    def precmd(self, command):
        if command.strip():
            self.args = shlex.split(command)
        return command

    def process_direct_command(self, command):
        obj = CliClient()
        response = obj.call(command)
        if response:
            # convert dict response in Response object 
            # to fit in cli framework format.
            response = Response(output=response)
            command.process_response(out=sys.stdout, err=sys.stderr,
                                 response=response)

    def default(self, cmd):
        try:
            # TODO: make below configs global use of config file
            cmd_dir = '/opt/seagate/cortx/provisioner/node_cli/schema'
            # permission to fit in cli framework
            permissions = {
                'node': {'bypass': True},
                'cluster': {'bypass': True},
                'storageset': {'bypass': True}
            }
            command = CommandFactory.get_command(self.args, component_cmd_dir=cmd_dir, permissions=permissions)
            channel_name = f"""process_{command.comm.get("type", "")}_command"""
            if not hasattr(self, channel_name):
                err_str = f"Invalid communication protocol {command.comm.get('type','')} selected."
                sys.stderr(err_str)
            getattr(self, channel_name)(command)
            Log.debug(f"{cmd}: Command executed")
        except SystemExit:
            Log.debug(f" Command executed system exit")
        except KeyboardInterrupt:
            Log.debug(f"Stopped via keyboard interrupt.")
            self.do_exit()
        except Exception as e:
            Log.critical(f"{e}")
            self.do_exit()

    def do_exit(self, args=""):
        sys.exit()

if __name__ == '__main__':
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..'))
    sys.path.append(os.path.join(os.path.dirname(pathlib.Path(os.path.realpath(__file__))), '..', '..'))
    from cortx.utils.cli_framework.command_factory import CommandFactory
    from node_cli.client import CliClient
    from cortx.utils.log import Log
    from cortx.utils.conf_store.conf_store import Conf
    try:
        NodeCli(sys.argv).cmdloop()
    except KeyboardInterrupt:
        Log.debug(f"Stopped via keyboard interrupt.")
        sys.stdout.write("\n")
    except Exception as e:
        Log.critical(f"{e}")
        sys.stderr.write('Some error occurred.\nPlease try login again.\n')
