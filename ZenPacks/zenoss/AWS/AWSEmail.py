###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2013, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
log = logging.getLogger("zen.useraction.actions")

from zope.schema.vocabulary import SimpleVocabulary
from zope.interface import implements

from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t
from Products.Zuul.interfaces.actions import IInfo
from Products.Zuul.interfaces import actions
from Products.Zuul.infos.actions import ActionFieldProperty
from Products.Zuul.infos import InfoBase

from ZenPacks.zenoss.AWS.utils import getSESRegions

import textwrap


class IAWSEmailHostActionContentInfo(IInfo):

    body_content_type = schema.Choice(
        title=_t(u'Body Content Type'),
        vocabulary=SimpleVocabulary.fromValues(actions.getNotificationBodyTypes()),
        description=_t(u'The content type of the body for emails.'),
        default=u'html'
    )

    subject_format = schema.TextLine(
        title=_t(u'Message (Subject) Format'),
        description=_t(u'The template for the subject for emails.'),
        default=_t(u'[zenoss] ${evt/device} ${evt/summary}')
    )

    body_format = schema.Text(
        title=_t(u'Body Format'),
        description=_t(u'The template for the body for emails.'),
        default=textwrap.dedent(text=u'''
        Device: ${evt/device}
        Component: ${evt/component}
        Severity: ${evt/severity}
        Time: ${evt/lastTime}
        Message:
        ${evt/message}
        <a href="${urls/eventUrl}">Event Detail</a>
        <a href="${urls/ackUrl}">Acknowledge</a>
        <a href="${urls/closeUrl}">Close</a>
        <a href="${urls/eventsUrl}">Device Events</a>
        ''')
    )

    clear_subject_format = schema.TextLine(
        title=_t(u'Clear Message (Subject) Format'),
        description=_t(u'The template for the subject for CLEAR emails.'),
        default=_t(u'[zenoss] CLEAR: ${evt/device} ${clearEvt/summary}')
    )

    clear_body_format = schema.Text(
        title=_t(u'Body Format'),
        description=_t(u'The template for the body for CLEAR emails.'),
        default=textwrap.dedent(text=u'''
        Event: '${evt/summary}'
        Cleared by: '${evt/clearid}'
        At: ${evt/stateChange}
        Device: ${evt/device}
        Component: ${evt/component}
        Severity: ${evt/severity}
        Message:
        ${evt/message}
        <a href="${urls/reopenUrl}">Reopen</a>
        ''')
    )

    email_from = schema.Text(
        title=_t(u'From Address for Emails'),
        description=_t(u'The user from which the e-mail originated on the Zenoss server.'),
        default=u'root@localhost.localdomain'
    )

    aws_account_name = schema.Text(
        title=_t(u'AWS Account Name'),
        description=_t(u'Name of the AWS account you\'ll be using.'),
    )

    aws_region = schema.Choice(
        title=_t(u'AWS Region'),
        vocabulary=SimpleVocabulary.fromValues(getSESRegions()),
        description=_t(u'List of available AWS Regions.'),
        default=getSESRegions()[0]
    )

    aws_access_key = schema.Text(
        title=_t(u'AWS Access Key'),
        description=_t(u'Access Key for the AWS account.'),
    )

    aws_secret_key = schema.Password(
        title=_t(u'AWS Secret Key'),
        description=_t(u'Secret Key for the AWS account.'),
    )


class AWSEmailHostActionContentInfo(InfoBase):
    implements(IAWSEmailHostActionContentInfo)

    body_content_type = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'body_content_type')
    subject_format = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'subject_format')
    body_format = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'body_format')
    clear_subject_format = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'clear_subject_format')
    clear_body_format = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'clear_body_format')
    email_from = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'email_from')
    aws_account_name = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'aws_account_name')
    aws_region = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'aws_region')
    aws_access_key = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'aws_access_key')
    aws_secret_key = ActionFieldProperty(IAWSEmailHostActionContentInfo, 'aws_secret_key')
