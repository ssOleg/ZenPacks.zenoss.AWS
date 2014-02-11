##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import json

from Products.ZenModel.ZenPack import ZenPackBase, ZenPackDependentsException

from collections import defaultdict


# Modules containing model classes. Used by zenchkschema to validate
# bidirectional integrity of defined relationships.
productNames = (
    'EC2Account',
    'EC2Instance',
    'EC2Region',
    'EC2Volume',
    'EC2VPC',
    'EC2VPCSubnet',
    'EC2Zone',
    'VPNGateway',
    'EC2ElasticIP',
    'EC2Image',
    'S3Bucket',
    'SQSQueue',
    'EC2Snapshot',
    'EC2ReservedInstance',
)

# Useful to avoid making literal string references to module and class names
# throughout the rest of the ZenPack.
MODULE_NAME = {}
CLASS_NAME = {}
for product_name in productNames:
    ZP_NAME = 'ZenPacks.zenoss.AWS'
    MODULE_NAME[product_name] = '.'.join([ZP_NAME, product_name])
    CLASS_NAME[product_name] = '.'.join([ZP_NAME, product_name, product_name])

EC2INSTANCE_TYPES = defaultdict(lambda: '')
try:
    json_data = open(os.path.join(os.path.dirname(__file__), 'aws.json'))
    data = json.load(json_data)
    all_types = data['services']['Elastic Compute Cloud']['instance_types']
    EC2INSTANCE_TYPES = {}
    for i_type in all_types:
        EC2INSTANCE_TYPES[i_type] = '; '.join(
            ['%s: %s' % (k, v) for (k, v) in all_types[i_type].items()]
        )
except:
    pass


class ZenPack(ZenPackBase):
    '''
    ZenPack loader.
    '''
    packZProperties = [
        ('zAWSDiscover', '', 'awsdiscoverfield'),
        ('zAWSRegionPEM', '', 'multilinekeypath'),
        # ('zRemodelEnabled', 'false', 'bool'),
    ]

    def install(self, app):
        try:
            import ZenPacks.zenoss.ZenAWS
            available = True
        except ImportError:
            available = False

        if available:
            raise ZenPackDependentsException("This ZenPack supersedes the older ZenAWS (ZenPacks.zenoss.ZenAWS) "
                            "ZenPack that was installed by default on versions of Zenoss prior to 4.2.4. "
                            "Please remove ZenAWS before installing this ZenPack. This will remove the /EC2 "
                            "device class and the EC2Manager device within. After installing this ZenPack, "
                            "you will be able to add a new EC2 Account with much greater functionality.")

        super(ZenPack, self).install(app)
        # Update relations after zenpack upgrade.
        self._updateDeviceRelations()

    def _updateDeviceRelations(self):
        '''
        Update relations of the existing AWS devices and their components.
        '''
        for d in self.dmd.Devices.getSubDevicesGen():
            if 'aws' in d.getPrimaryUrlPath().lower():
                d.buildRelations()
                for obj in d.componentSearch():
                    obj.getObject().buildRelations()
