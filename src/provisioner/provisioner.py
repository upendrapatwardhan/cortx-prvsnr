# CORTX Python common library.
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

import errno
from cortx.utils.process import SimpleProcess
from cortx.utils.conf_store import Conf
from cortx.utils.security.cipher import Cipher
from cortx.provisioner.error import CortxProvisionerError
from cortx.provisioner.config_store import ConfigStore
from cortx.provisioner.config import CortxConfig
from cortx.provisioner.cluster import CortxCluster,  CortxStorageSet


class CortxProvisioner:
    """ CORTX Provosioner """

    _cortx_conf_url = "yaml:///etc/cortx/cluster.conf"
    _solution_index = "solution_conf"

    @staticmethod
    def init():
        pass

    @staticmethod
    def config_apply(solution_conf_url: str, cortx_conf_url: str = None):
        """
        Description:
        Parses input config and store in CORTX config location

        Parameters:
        [IN]  Solution Config URL
        [OUT] CORTX Config URL
        """

        Conf.load(CortxProvisioner._solution_index, solution_conf_url)

        if cortx_conf_url is None:
            cortx_conf_url = CortxProvisioner._cortx_conf_url
        cortx_config_store = ConfigStore(cortx_conf_url)
        # source code for encrypting and storing secret key
        cluster_id = Conf.get(CortxProvisioner._solution_index, 'cluster>id')
        if cluster_id is None:
            raise CortxProvisionerError(errno.EINVAL, 'Cluster ID not specified')
        encryption_key = Cipher.gen_key(cluster_id, 'cluster')
        for key in Conf.get_keys(CortxProvisioner._solution_index):
            # TODO: use /etc/cortx/solution/secret to confirm secret 
            if key.endswith('secret'):
                secret_val = Conf.get(CortxProvisioner._solution_index, key)
                val = None
                with open(os.path.join('/etc/cortx/solution/secret', secret_val)) as f:
                    val = f.read()
                if val is None:
                    raise CortxProvisionerError(errno.EINVAL,
                        'Could not find the Secret in /etc/cortx/solution/secret')
                val = Cipher.encrypt(encryption_key, val.encode('ascii'))
                Conf.set(CortxProvisioner._solution_index, key, val)

        if Conf.get(CortxProvisioner._solution_index, 'cluster') is not None:
            CortxProvisioner.config_apply_cluster(cortx_config_store)

        if Conf.get(CortxProvisioner._solution_index, 'cortx') is not None:
            CortxProvisioner.config_apply_cortx(cortx_config_store)


    @staticmethod
    def config_apply_cortx(cortx_config_store):
        """ Convert CORTX config into confstore keys """
        cortx_config = Conf.get(CortxProvisioner._solution_index, 'cortx')
        cs = CortxConfig(cortx_config)
        cs.save(cortx_config_store)

    @staticmethod
    def config_apply_cluster(cortx_config_store):
        node_map = {}
        try:
            node_types = Conf.get(CortxProvisioner._solution_index, 'cluster>node_types')
            cluster_id = Conf.get(CortxProvisioner._solution_index, 'cluster>id')
            cluster_name = Conf.get(CortxProvisioner._solution_index, 'cluster>name')
            storage_sets = Conf.get(CortxProvisioner._solution_index, 'cluster>storage_sets')
            for key in [cluster_id, cluster_name, storage_sets, node_types]:
                if key is None:
                    raise CortxProvisionerError(
                        errno.EINVAL,
                        f"One of the key [id, name,storage_sets,node_types]"
                        " is unspecified for cluster.")

            for node_type in node_types:
                node_map[node_type['name']] = node_type


            cluster_keys = [('id', cluster_id), ('name', cluster_name)]
            cortx_config_store.set('cluster', cluster_keys)

            nodes = []
            for storage_set in storage_sets:
                for node in storage_set['nodes']:
                    node_type = node['type']
                    node = dict(node_map[node_type], **node)
                    components = {}
                    for component in node.pop('components'):
                        comp_name = component.get('name')
                        components.update({
                            comp_name:  component.get('services')
                            })
                    node['components'] = components
                    if node['type'] == 'storage_node':
                        cvg_list = node.pop('storage')
                        node['storage'] = {
                            'cvg_count': len(cvg_list),
                            'cvg': cvg_list
                        }
                    node['storage_set'] = storage_set['name']
                    node['storage_set_count'] = len(storage_sets)
                    node['cluster_id'] = cluster_id
                    nodes.append(node)

            cs = CortxCluster(nodes)
            cs.save(cortx_config_store)
            cs = CortxStorageSet(storage_sets)
            cs.save(cortx_config_store)
        except KeyError as e:
            raise CortxProvisionerError(
                errno.EINVAL,
                f'Error occurred while applying cluster_config {e}')

    @staticmethod
    def cluster_bootstrap(cortx_conf_url: str = None):
        """
        Description:
        Configures Cluster Components
        1. Reads Cortx Config and obtain cluster components
        2. Invoke Mini Provisioners of cluster components

        Paramaters:
        [IN] CORTX Config URL
        """

        if cortx_conf_url is None:
            cortx_conf_url = CortxProvisioner._cortx_conf_url
        cortx_config_store = ConfigStore(cortx_conf_url)

        node_id = Conf.machine_id
        if node_id is None:
            raise CortxProvisionerError(errno.EINVAL, 'Invalid node_id: %s', \
                node_id)

        components = cortx_config_store.get(f'node>{node_id}>components')
        mp_interfaces = ['post_install', 'prepare', 'config', 'init']
        for interface in mp_interfaces:
            for comp_name in components.keys():
                services = cortx_config_store.get(
                    f'node>{node_id}>components>{comp_name}>services')
                service = 'all' if services is None else ','.join(services)
                cmd_proc = SimpleProcess(f"{comp_name}_setup {interface} " \
                    f"--config {cortx_conf_url} --services %s" % service)
                _, err, rc = cmd_proc.run()
                if rc != 0:
                    raise CortxProvisionerError(rc, "Unable to execute " \
                        "%s phase for %s. %s", interface, comp_name, err)