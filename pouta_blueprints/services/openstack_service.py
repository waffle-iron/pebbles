import novaclient
from novaclient.exceptions import NotFound
from novaclient.v2 import client

import taskflow.engines
from taskflow.patterns import linear_flow as lf
from taskflow.patterns import graph_flow as gf
from taskflow import task

import logging
import os
import json
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_openstack_nova_client(config):
    if config:
        if config.get('M2M_CREDENTIAL_STORE'):
            logger.debug("loading credentials from %s" % config.get('M2M_CREDENTIAL_STORE'))
            m2m_config = json.load(open(config.get('M2M_CREDENTIAL_STORE')))
            source_config = m2m_config
        else:
            logger.debug("using config as provided")
            source_config = config
    else:
        logger.debug("no config, trying environment vars")
        source_config = os.environ

    os_username = source_config['OS_USERNAME']
    os_password = source_config['OS_PASSWORD']
    os_tenant_name = source_config['OS_TENANT_NAME']
    os_auth_url = source_config['OS_AUTH_URL']

    return client.Client(os_username, os_password, os_tenant_name, os_auth_url, service_type="compute")


class GetImage(task.Task):
    def execute(self, image_name, config):
        logger.debug("getting image %s" % image_name)
        nc = get_openstack_nova_client(config)
        return nc.images.find(name=image_name).id

    def revert(self, *args, **kwargs):
        pass


class GetFlavor(task.Task):
    def execute(self, flavor_name, config):
        logger.debug("getting flavor %s" % flavor_name)
        nc = get_openstack_nova_client(config)
        return nc.flavors.find(name=flavor_name).id

    def revert(self, *args, **kwargs):
        pass


class CreateSecurityGroup(task.Task):
    def execute(self, display_name, master_sg_name, config):
        logger.debug("create security group %s" % display_name)
        security_group_name = display_name
        nc = get_openstack_nova_client(config)

        self.secgroup = nc.security_groups.create(
            security_group_name,
            "Security group generated by Pouta Blueprints")

        if master_sg_name:
            master_sg = nc.security_groups.find(name=master_sg_name)
            nc.security_group_rules.create(
                self.secgroup.id,
                ip_protocol='tcp',
                from_port=1,
                to_port=65535,
                group_id=master_sg.id
            )
            nc.security_group_rules.create(
                self.secgroup.id,
                ip_protocol='udp',
                from_port=1,
                to_port=65535,
                group_id=master_sg.id
            )
            nc.security_group_rules.create(
                self.secgroup.id,
                ip_protocol='icmp',
                from_port=-1,
                to_port=-1,
                group_id=master_sg.id
            )

        logger.info("Created security group %s" % self.secgroup.id)

        return self.secgroup.id

    def revert(self, config, **kwargs):
        logger.debug("revert: delete security group")
        nc = get_openstack_nova_client(config)
        nc.security_groups.delete(self.secgroup.id)


# noinspection PyDeprecation
class CreateRootVolume(task.Task):
    def execute(self, display_name, image, root_volume_size, config):
        if root_volume_size:
            logger.debug("creating a root volume for instance %s from image %s" %
                         (display_name, image))
            nc = get_openstack_nova_client(config)
            volume_name = '%s-root' % display_name

            volume = nc.volumes.create(
                size=root_volume_size,
                imageRef=image,
                display_name=volume_name
            )
            self.volume_id = volume.id
            retries = 0
            while nc.volumes.get(volume.id).status not in ('available'):
                logger.debug("...waiting for volume to be ready")
                time.sleep(5)
                retries += 1
                if retries > 30:
                    raise RuntimeError('Volume creation %s is stuck')

            return volume.id
        else:
            logger.debug("no root volume defined")
            return ""

    def revert(self, config, **kwargs):
        logger.debug("revert: delete root volume")

        try:
            if getattr(self, 'volume_id', None):
                nc = get_openstack_nova_client(config)
                nc.volumes.delete(self.volume_id)
            else:
                logger.debug("revert: no volume_id stored, unable to revert")
        except Exception as e:
            logger.error('revert: deleting volume failed: %s' % e)


# noinspection PyDeprecation
class CreateDataVolume(task.Task):
    def execute(self, display_name, data_volume_size, config):
        if data_volume_size:
            logger.debug("creating a data volume for instance %s, size %d" %
                         (display_name, data_volume_size))
            nc = get_openstack_nova_client(config)
            volume_name = '%s-data' % display_name

            volume = nc.volumes.create(
                size=data_volume_size,
                display_name=volume_name
            )
            self.volume_id = volume.id
            retries = 0
            while nc.volumes.get(volume.id).status not in ('available'):
                logger.debug("...waiting for volume to be ready")
                time.sleep(5)
                retries += 1
                if retries > 30:
                    raise RuntimeError('Volume creation %s is stuck')

            return volume.id
        else:
            logger.debug("no root volume defined")
            return ""

    def revert(self, config, **kwargs):
        logger.debug("revert: delete root volume")

        try:
            if getattr(self, 'volume_id', None):
                nc = get_openstack_nova_client(config)
                nc.volumes.delete(self.volume_id)
            else:
                logger.debug("revert: no volume_id stored, unable to revert")
        except Exception as e:
            logger.error('revert: deleting volume failed: %s' % e)


class ProvisionInstance(task.Task):
    def execute(self, display_name, image, flavor, key_name, security_group, extra_sec_groups,
                root_volume_id, config):
        logger.debug("provisioning instance %s" % display_name)
        logger.debug("image=%s, flavor=%s, key=%s, secgroup=%s" % (image, flavor, key_name, security_group))
        nc = get_openstack_nova_client(config)

        sgs = [security_group]
        if extra_sec_groups:
            sgs.extend(extra_sec_groups)
        try:
            if len(root_volume_id):
                bdm = {'vda': '%s:::1' % (root_volume_id)}
            else:
                bdm = None

            instance = nc.servers.create(
                display_name,
                image,
                flavor,
                key_name=key_name,
                security_groups=sgs,
                block_device_mapping=bdm)

        except Exception as e:
            logger.error("error provisioning instance: %s" % e)
            raise e

        self.instance_id = instance.id
        logger.debug("instance provisioning successful")
        return instance.id

    def revert(self, config, **kwargs):
        logger.debug("revert: deleting instance %s", kwargs)
        try:
            if getattr(self, 'instance_id', None):
                nc = get_openstack_nova_client(config)
                nc.servers.delete(self.instance_id)
            else:
                logger.debug("revert: no instance_id stored, unable to revert")
        except Exception as e:
            logger.error('revert: deleting instance failed: %s' % e)


# noinspection PyDeprecation
class AllocateIPForInstance(task.Task):
    def execute(self, server_id, allocate_public_ip, config):
        logger.debug("Allocate IP for server %s" % server_id)

        nc = get_openstack_nova_client(config)
        retries = 0
        while nc.servers.get(server_id).status is "BUILDING" or not nc.servers.get(server_id).networks:
            logger.debug("...waiting for server to be ready")
            time.sleep(5)
            retries += 1
            if retries > 30:
                raise RuntimeError('Server %s is stuck in building' % server_id)

        server = nc.servers.get(server_id)
        if allocate_public_ip:

            ips = nc.floating_ips.findall(instance_id=None)
            allocated_from_pool = False
            if not ips:
                logger.debug("No allocated free IPs left, trying to allocate one")
                try:
                    ip = nc.floating_ips.create(pool="public")
                    allocated_from_pool = True
                except novaclient.exceptions.ClientException as e:
                    logger.warning("Cannot allocate IP, quota exceeded?")
                    raise e
            else:
                ip = ips[0]
            try:
                server.add_floating_ip(ip)
            except Exception as e:
                logger.error(e)

            address_data = {
                'public_ip': ip.ip,
                'allocated_from_pool': allocated_from_pool,
                'private_ip': server.networks.values()[0][0],
            }
        else:
            address_data = {
                'public_ip': None,
                'allocated_from_pool': False,
                'private_ip': server.networks.values()[0][0],
            }

        return address_data

    def revert(self, *args, **kwargs):
        pass


class AttachDataVolume(task.Task):
    def execute(self, server_id, data_volume_id, config):
        logger.debug("Allocate IP for server %s" % server_id)

        if data_volume_id:
            nc = get_openstack_nova_client(config)
            retries = 0

            while nc.servers.get(server_id).status is "BUILDING" or not nc.servers.get(server_id).networks:
                logger.debug("...waiting for server to be ready")
                time.sleep(5)
                retries += 1
                if retries > 30:
                    raise RuntimeError('Server %s is stuck in building' % server_id)

            nc.volumes.create_server_volume(server_id, data_volume_id, '/dev/vdc')

    def revert(self, *args, **kwargs):
        pass


flow = lf.Flow('ProvisionInstance').add(
    gf.Flow('BootInstance').add(
        GetImage('get_image', provides='image'),
        GetFlavor('get_flavor', provides='flavor'),
        CreateSecurityGroup('create_security_group', provides='security_group'),
        CreateRootVolume('create_root_volume', provides='root_volume_id'),
        CreateDataVolume('create_data_volume', provides='data_volume_id'),
        ProvisionInstance('provision_instance', provides='server_id')
    ),
    AllocateIPForInstance('allocate_ip_for_instance', provides='ip'),
    AttachDataVolume('attach_data_volume'),
)


class OpenStackService(object):
    def __init__(self, config=None):
        if config:
            self._config = config
        else:
            self._config = None

    def provision_instance(self, display_name, image_name, flavor_name, key_name,
                           extra_sec_groups=None, master_sg_name=None, allocate_public_ip=True,
                           root_volume_size=0, data_volume_size=0):
        try:
            return taskflow.engines.run(flow, engine='parallel', store=dict(
                image_name=image_name,
                flavor_name=flavor_name,
                display_name=display_name,
                key_name=key_name,
                master_sg_name=master_sg_name,
                extra_sec_groups=extra_sec_groups,
                allocate_public_ip=allocate_public_ip,
                root_volume_size=root_volume_size,
                data_volume_size=data_volume_size,
                config=self._config))
        except Exception as e:
            logger.error("Flow failed")
            logger.error(e)
            return {'error': 'flow failed'}

    def deprovision_instance(self, instance_id, name=None, error_if_not_exists=False):
        nc = get_openstack_nova_client(self._config)

        if not name:
            server = nc.servers.get(instance_id)
            name = server.name

        logger.info('Deleting instance %s' % instance_id)

        # before we delete it, we list attached volumes
        volumes = nc.volumes.get_server_volumes(instance_id)

        try:
            nc.servers.delete(instance_id)
        except NotFound as e:
            if error_if_not_exists:
                raise e
            else:
                logger.info('Instance already deleted')

        time.sleep(5)

        logger.info('Deleting security group %s' % name)
        try:
            sg = nc.security_groups.find(name=name)
            nc.security_groups.delete(sg.id)
        except NotFound as e:
            if error_if_not_exists:
                raise e
            else:
                logger.info('Security group already deleted')

        for vol in volumes:
            # load details
            vol.get()
            if vol.display_name == '%s-data' % name:
                logger.info('Deleting server data volume %s' % vol.id)
                nc.volumes.delete(vol.id)
            else:
                logger.debug(
                    'Skipping server data volume %s, name %s does not match %s' %
                    (vol.id, vol.display_name, '%s-data' % name)
                )

    def upload_key(self, key_name, key_file):
        nc = get_openstack_nova_client(self._config)
        try:
            nc.keypairs.find(name=key_name)
            logger.debug('Key already exists: %s' % key_name)
            return
        except:
            pass

        with open(key_file, "r") as pkfile:
            public_key = pkfile.read().replace('\n', '')

        nc.keypairs.create(key_name, public_key)
        logger.info('created key %s' % key_name)

    def delete_key(self, key_name):
        logger.debug('Deleting key: %s' % key_name)
        nc = get_openstack_nova_client(self._config)
        try:
            key = nc.keypairs.find(name=key_name)
            key.delete()
        except:
            logger.warning('Key not found: %s' % key_name)
