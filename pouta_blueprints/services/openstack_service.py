import novaclient
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


class GetFlavor(task.Task):
    def execute(self, flavor_name, config):
        logger.debug("getting flavor %s" % flavor_name)
        nc = get_openstack_nova_client(config)
        return nc.flavors.find(name=flavor_name).id


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


class ProvisionInstance(task.Task):
    def execute(self, display_name, image, flavor, key_name, security_group, config):
        logger.debug("provisioning instance %s" % display_name)
        logger.debug("image=%s, flavor=%s, key=%s, secgroup=%s" % (image, flavor, key_name, security_group))
        nc = get_openstack_nova_client(config)

        try:
            instance = nc.servers.create(
                display_name,
                image,
                flavor,
                key_name=key_name,
                security_groups=[security_group])
        except Exception as e:
            logger.error("error provisioning instance: %s" % e)
            raise e

        logger.debug("instance provisioned")

        self.instance_id = instance.id
        logger.debug("instance provisioning ok")
        return instance.id

    def revert(self, config, **kwargs):
        logger.debug("revert: deleting instance %s", kwargs)
        if getattr(self, 'instance_id'):
            nc = get_openstack_nova_client(config)
            nc.servers.delete(self.instance_id)
        else:
            logger.debug("revert: no instance_id stored, unable to revert")


class AllocateIPForInstance(task.Task):
    def execute(self, server_id, config):
        logger.debug("Allocate IP for server %s" % server_id)

        nc = get_openstack_nova_client(config)
        retries = 0
        while nc.servers.get(server_id).status is "BUILDING" or not nc.servers.get(server_id).networks:
            time.sleep(5)
            retries += 1
            if retries > 30:
                raise RuntimeError('Server %s is stuck in building' % server_id)

        ips = nc.floating_ips.findall(instance_id=None)
        server = nc.servers.get(server_id)
        allocated_from_pool = False
        if not ips:
            logger.debug("No allocated free IPs left, trying to allocate one\n")
            try:
                ip = nc.floating_ips.create(pool="public")
                allocated_from_pool = True
            except novaclient.exceptions.ClientException as e:
                logger.warning("Cannot allocate IP, quota exceeded?\n")
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
        return address_data


flow = lf.Flow('ProvisionInstance').add(
    gf.Flow('BootInstance').add(
        GetImage('get_image', provides='image'),
        GetFlavor('get_flavor', provides='flavor'),
        CreateSecurityGroup('create_security_group', provides='security_group'),
        ProvisionInstance('provision_instance', provides='server_id')
    ),
    AllocateIPForInstance('allocate_ip_for_instance', provides='ip'),
)


class OpenStackService(object):
    def __init__(self, config=None):
        if config:
            self._config = config
        else:
            self._config = None

    def provision_instance(self, display_name, image_name, flavor_name, key_name, master_sg_name=None):
        try:
            return taskflow.engines.run(flow, engine='parallel', store=dict(
                image_name=image_name,
                flavor_name=flavor_name,
                display_name=display_name,
                key_name=key_name,
                master_sg_name=master_sg_name,
                config=self._config))
        except Exception as e:
            logger.error("Flow failed")
            logger.error(e)
            return {'error': 'flow failed'}

    def deprovision_instance(self, instance_id):
        nc = get_openstack_nova_client(self._config)
        server = nc.servers.get(instance_id)
        name = server.name

        logger.info('Deleting instance %s' % instance_id)
        nc.servers.delete(instance_id)

        time.sleep(5)

        logger.info('Deleting security group %s' % name)
        sg = nc.security_groups.find(name=name)
        nc.security_groups.delete(sg.id)

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
