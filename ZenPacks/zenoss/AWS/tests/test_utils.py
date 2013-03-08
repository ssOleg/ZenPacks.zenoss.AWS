##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import transaction
from zope.event import notify

from Products.Five import zcml

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.Utils import monkeypatch
from Products.Zuul import getFacade
from Products.Zuul.catalog.events import IndexingEvent

from ZenPacks.zenoss.AWS import CLASS_NAME


@monkeypatch('Products.Zuul')
def get_dmd():
    """
    Retrieve the DMD object. Handle unit test connection oddities.

    This has to be monkeypatched on Products.Zuul instead of
    Products.Zuul.utils because it's already imported into Products.Zuul
    by the time this monkeypatch happens.
    """
    try:
        # original is injected by the monkeypatch decorator.
        return original()

    except AttributeError:
        connections = transaction.get()._synchronizers.data.values()[:]
        for cxn in connections:
            app = cxn.root()['Application']
            if hasattr(app, 'zport'):
                return app.zport.dmd


def add_obj(relationship, obj):
    relationship._setObject(obj.id, obj)
    obj = relationship._getOb(obj.id)
    obj.index_object()
    notify(IndexingEvent(obj))
    return obj


class TestUtils(BaseTestCase):
    def afterSetUp(self):
        super(TestUtils, self).afterSetUp()

        # Must load ZenPack ZCML to get PathReporter adapters.
        import ZenPacks.zenoss.AWS
        zcml.load_config('configure.zcml', ZenPacks.zenoss.AWS)

        dc = self.dmd.Devices.createOrganizer('/AWS/EC2')
        dc.setZenProperty('zPythonClass', 'ZenPacks.zenoss.AWS.EC2Account')

        self.account = dc.createInstance('account')
        self.account.setPerformanceMonitor('localhost')
        self.account.index_object()
        notify(IndexingEvent(self.account))

        from ZenPacks.zenoss.AWS.EC2Region import EC2Region
        region = add_obj(self.account.regions, EC2Region('region'))

        from ZenPacks.zenoss.AWS.EC2Zone import EC2Zone
        add_obj(region.zones, EC2Zone('zone1'))
        add_obj(region.zones, EC2Zone('zone2'))

        from ZenPacks.zenoss.AWS.EC2Instance import EC2Instance
        add_obj(region.instances, EC2Instance('instance'))

        from ZenPacks.zenoss.AWS.EC2Volume import EC2Volume
        add_obj(region.volumes, EC2Volume('volume1'))
        add_obj(region.volumes, EC2Volume('volume2'))

    def test_updateToMany(self):
        from ZenPacks.zenoss.AWS.utils import updateToMany

        device_facade = getFacade('device')

        instance = self.account.getObjByPath(
            'regions/region/instances/instance')

        # Add one volume.
        updateToMany(
            instance.volumes,
            instance.region().volumes,
            CLASS_NAME['EC2Volume'],
            ['volume1'])

        self.assertEqual(instance.volumes.countObjects(), 1)
        self.assertEqual(instance.volumes()[0].id, 'volume1')

        instance_volumes = device_facade.getComponents(
            instance.getPrimaryUrlPath(),
            meta_type='EC2Volume')

        self.assertTrue('volume1' in [b.id for b in instance_volumes.results])

        # Add two volumes.
        updateToMany(
            instance.volumes,
            instance.region().volumes,
            CLASS_NAME['EC2Volume'],
            ['volume1', 'volume2'])

        self.assertEqual(instance.volumes.countObjects(), 2)
        self.assertEqual(
            set(x.id for x in instance.volumes()),
            set(('volume1', 'volume2')))

        instance_volumes = device_facade.getComponents(
            instance.getPrimaryUrlPath(),
            meta_type='EC2Volume')

        self.assertEqual(instance_volumes.total, 2)

        # Remove one volume.
        updateToMany(
            instance.volumes,
            instance.region().volumes,
            CLASS_NAME['EC2Volume'],
            ['volume2'])

        self.assertEqual(instance.volumes.countObjects(), 1)
        self.assertEqual(instance.volumes()[0].id, 'volume2')

        instance_volumes = device_facade.getComponents(
            instance.getPrimaryUrlPath(),
            meta_type='EC2Volume')

        self.assertTrue('volume2' in [b.id for b in instance_volumes.results])

        # Remove all volumes.
        updateToMany(
            instance.volumes,
            instance.region().volumes,
            CLASS_NAME['EC2Volume'],
            [])

        self.assertEqual(instance.volumes.countObjects(), 0)

        instance_volumes = device_facade.getComponents(
            instance.getPrimaryUrlPath(),
            meta_type='EC2Volume')

        self.assertEqual(instance_volumes.total, 0)

    def test_updateToOne(self):
        from ZenPacks.zenoss.AWS.utils import updateToOne

        zone1 = self.account.getObjByPath('regions/region/zones/zone1')
        zone2 = self.account.getObjByPath('regions/region/zones/zone2')
        instance = self.account.getObjByPath(
            'regions/region/instances/instance')

        updateToOne(
            instance.zone,
            instance.region().zones,
            CLASS_NAME['EC2Zone'],
            'zone1')

        self.assertFalse(instance.zone() is None)
        self.assertEqual(instance.zone().id, zone1.id)
        self.assertEqual(zone1.instances.countObjects(), 1)
        self.assertEqual(zone1.instances()[0].id, instance.id)

        updateToOne(
            instance.zone,
            instance.region().zones,
            CLASS_NAME['EC2Zone'],
            'zone2')

        self.assertEqual(zone1.instances.countObjects(), 0)

        self.assertFalse(instance.zone() is None)
        self.assertEqual(instance.zone().id, zone2.id)
        self.assertEqual(zone2.instances.countObjects(), 1)
        self.assertEqual(zone2.instances()[0].id, instance.id)

        updateToOne(
            instance.zone,
            instance.region().zones,
            CLASS_NAME['EC2Zone'],
            None)

        self.assertTrue(instance.zone() is None)
        self.assertEqual(zone1.instances.countObjects(), 0)
        self.assertEqual(zone2.instances.countObjects(), 0)

        updateToOne(
            instance.zone,
            instance.region().zones,
            CLASS_NAME['EC2Zone'],
            '')

        self.assertTrue(instance.zone() is None)
        self.assertEqual(zone1.instances.countObjects(), 0)
        self.assertEqual(zone2.instances.countObjects(), 0)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestUtils))
    return suite
