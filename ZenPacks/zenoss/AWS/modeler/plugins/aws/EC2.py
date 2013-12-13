##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import collections
from itertools import chain

from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap

from Products.ZenUtils.Utils import prepId

from ZenPacks.zenoss.AWS import MODULE_NAME
from ZenPacks.zenoss.AWS.utils import addLocalLibPath

addLocalLibPath()

from boto.ec2.connection import EC2Connection
from boto.vpc import VPCConnection
from boto.s3.connection import S3Connection
from boto.sqs.connection import SQSConnection
from boto.sqs import regions as get_sqs_regions

'''
Models regions, instance types, zones, instances, volumes, VPCs and VPC
subnets for an Amazon EC2 account.
'''


class EC2(PythonPlugin):
    deviceProperties = PythonPlugin.deviceProperties + (
        'ec2accesskey',
        'ec2secretkey',
        )

    def collect(self, device, log):
        return True

    def process(self, device, results, log):
        log.info(
            'Modeler %s processing data for device %s',
            self.name(), device.id)

        accesskey = getattr(device, 'ec2accesskey', None)
        if not accesskey:
            log.error('%s: EC2 access key not set. Not discovering.')
            return

        secretkey = getattr(device, 'ec2secretkey', None)
        if not secretkey:
            log.error('%s: EC2 secret key not set. Not discovering.')
            return

        maps = collections.OrderedDict([
            ('regions', []),
            ('s3buckets', []),
            ('instance types', []),
            ('zones', []),
            ('VPCs', []),
            ('VPC subnets', []),
            ('VPNGateways', []),
            ('instances', []),
            ('volumes', []),
            ('queues', []),
            ('account', []),
            ])

        instance_filters = {
            'instance-state-name': [
                'pending',
                'running',
                'shutting-down',
                'stopping',
                'stopped',
                ],
            }

        ec2conn = EC2Connection(accesskey, secretkey)
        s3connection = S3Connection(accesskey, secretkey)

        region_oms = []
        for region in set(ec2conn.get_all_regions() + get_sqs_regions()):
            region_id = prepId(region.name)

            region_oms.append(ObjectMap(data={
                'id': region_id,
                'title': region.name,
            }))

            ec2regionconn = EC2Connection(accesskey, secretkey, region=region)
            vpcregionconn = VPCConnection(accesskey, secretkey, region=region)
            sqsconnection = SQSConnection(accesskey, secretkey, region=region)
            # Zones
            maps['zones'].append(
                zones_rm(
                    region_id,
                    ec2regionconn.get_all_zones()))

            # VPCs
            maps['VPCs'].append(
                vpcs_rm(
                    region_id,
                    vpcregionconn.get_all_vpcs()))

            # VPNGateways
            maps['VPNGateways'].append(
                vpn_gateways_rm(
                    region_id,
                    vpcregionconn.get_all_vpn_gateways()
                )
            )

            maps['queues'].append(
                vpn_queues_rm(
                    region_id,
                    sqsconnection.get_all_queues()
                )
            )

            # VPC Subnets
            maps['VPC subnets'].append(
                vpc_subnets_rm(
                    region_id,
                    vpcregionconn.get_all_subnets()))

            # Instances
            maps['instances'].append(
                instances_rm(
                    region_id,
                    ec2regionconn.get_all_instances(
                        filters=instance_filters)))

            # Volumes
            maps['volumes'].append(
                volumes_rm(
                    region_id,
                    ec2regionconn.get_all_volumes()))

        # Regions
        maps['regions'].append(RelationshipMap(
            relname='regions',
            modname=MODULE_NAME['EC2Region'],
            objmaps=region_oms))

        # S3Buckets
        maps['s3buckets'].append(
            s3buckets_rm(s3connection.get_all_buckets()))

        # Trigger discovery of instance guest devices.
        maps['account'].append(ObjectMap(data={
            'setDiscoverGuests': True,
            }))

        return list(chain.from_iterable(maps.itervalues()))


def name_or(tags, default):
    '''
    Return value of Name tag if it exists, or default otherwise.
    '''
    if 'Name' in tags:
        return tags['Name']

    return default


def to_boolean(string):
    '''
    Return a boolean given a string representation of a boolean.
    '''
    return {
        'true': True,
        'false': False,
        }.get(string.lower())


def zones_rm(region_id, zones):
    '''
    Return zones RelationshipMap given region_id and ZoneInfo ResultSet.
    '''
    zone_data = []
    for zone in zones:
        zone_data.append({
            'id': prepId(zone.name),
            'title': zone.name,
            'state': zone.state,
            })

    return RelationshipMap(
        compname='regions/%s' % region_id,
        relname='zones',
        modname=MODULE_NAME['EC2Zone'],
        objmaps=zone_data)


def vpcs_rm(region_id, vpcs):
    '''
    Return vpcs RelationshipMap given region_id and VPCInfo ResultSet.
    '''
    vpc_data = []
    for vpc in vpcs:
        if 'Collector' in vpc.tags:
            collector = prepId(vpc.tags['Collector'])
        else:
            collector = None

        vpc_data.append({
            'id': prepId(vpc.id),
            'title': name_or(vpc.tags, vpc.id),
            'cidr_block': vpc.cidr_block,
            'state': vpc.state,
            'collector': collector,
            })

    return RelationshipMap(
        compname='regions/%s' % region_id,
        relname='vpcs',
        modname=MODULE_NAME['EC2VPC'],
        objmaps=vpc_data)

def vpn_gateways_rm(region_id, gateways):
    '''
    Return VPN Gateways RelationshipMap given region_id and list of VpnGateway objects
    '''
    objmaps = []
    for gateway in gateways:
        objmaps.append({
            'id': prepId(gateway.id),
            'title': name_or(gateway.tags, gateway.id),
            'state': gateway.state,
            'availability_zone': gateway.availability_zone,
            'gateway_type': gateway.type,
        })

    return RelationshipMap(
        compname='regions/%s' % region_id,
        relname='vpn_gateways',
        modname=MODULE_NAME['VPNGateway'],
        objmaps=objmaps
    )

def vpn_queues_rm(region_id, qs):
    objmaps = []
    for q in qs:
        objmaps.append({
            'id': prepId(q.id),
            'title': name_or(q.name),
        })

    return RelationshipMap(
        compname='regions/%s' % region_id,
        relname='queues',
        modname=MODULE_NAME['SQSQueue'],
        objmaps=objmaps
    )


def vpc_subnets_rm(region_id, subnets):
    '''
    Return vpc_subnets RelationshipMap given region_id and a SubnetInfo
    ResultSet.
    '''
    vpc_subnet_data = []
    for subnet in subnets:
        vpc_subnet_data.append({
            'id': prepId(subnet.id),
            'title': name_or(subnet.tags, subnet.id),
            'available_ip_address_count': subnet.available_ip_address_count,
            'cidr_block': subnet.cidr_block,
            'defaultForAz': to_boolean(subnet.defaultForAz),
            'mapPublicIpOnLaunch': to_boolean(subnet.mapPublicIpOnLaunch),
            'state': subnet.state,
            'setVPCId': subnet.vpc_id,
            'setZoneId': subnet.availability_zone,
            })

    return RelationshipMap(
        compname='regions/%s' % region_id,
        relname='vpc_subnets',
        modname=MODULE_NAME['EC2VPCSubnet'],
        objmaps=vpc_subnet_data)


def instances_rm(region_id, reservations):
    '''
    Return instances RelationshipMap given region_id and an InstanceInfo
    ResultSet.
    '''
    instance_data = []
    for instance in chain.from_iterable(r.instances for r in reservations):
        zone_id = prepId(instance.placement) if instance.placement else None
        subnet_id = prepId(instance.subnet_id) if instance.subnet_id else None

        instance_data.append({
            'id': prepId(instance.id),
            'title': name_or(instance.tags, instance.id),
            'instance_id': instance.id,
            'public_dns_name': instance.public_dns_name,
            'private_ip_address': instance.private_ip_address,
            'image_id': instance.image_id,
            'instance_type': instance.instance_type,
            'launch_time': instance.launch_time,
            'state': instance.state,
            'platform': getattr(instance, 'platform', ''),
            'detailed_monitoring': instance.monitored,
            'setZoneId': zone_id,
            'setVPCSubnetId': subnet_id,
            })

    return RelationshipMap(
        compname='regions/%s' % region_id,
        relname='instances',
        modname=MODULE_NAME['EC2Instance'],
        objmaps=instance_data)


def volumes_rm(region_id, volumes):
    '''
    Return volumes RelationshipMap given region_id and a VolumeInfo
    ResultSet.
    '''
    volume_data = []
    for volume in volumes:
        if volume.attach_data.instance_id:
            instance_id = prepId(volume.attach_data.instance_id)
        else:
            instance_id = None

        volume_data.append({
            'id': prepId(volume.id),
            'title': name_or(volume.tags, volume.id),
            'volume_type': volume.type,
            'create_time': volume.create_time,
            'size': volume.size / (1024 ** 3),
            'iops': volume.iops,
            'status': volume.status,
            'attach_data_status': volume.attach_data.status,
            'attach_data_devicepath': volume.attach_data.device,
            'setInstanceId': instance_id,
            'setZoneId': volume.zone,
            })

    return RelationshipMap(
        compname='regions/%s' % region_id,
        relname='volumes',
        modname=MODULE_NAME['EC2Volume'],
        objmaps=volume_data)


def s3buckets_rm(buckets):
    '''
    Return buckets RelationshipMap given a BucketInfo
    ResultSet.
    '''
    bucket_oms = []
    for bucket in buckets:
        bucket_oms.append(ObjectMap(data={
            'id': prepId(bucket.name),
            'title': bucket.name,
            'creation_date': bucket.creation_date,
            }))

    return RelationshipMap(
        relname='s3buckets',
        modname=MODULE_NAME['S3Bucket'],
        objmaps=bucket_oms)
