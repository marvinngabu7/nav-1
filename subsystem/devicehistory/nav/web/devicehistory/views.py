# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009 UNINETT AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License version 2 as published by the Free
# Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.  You should have received a copy of the GNU General Public License
# along with NAV. If not, see <http://www.gnu.org/licenses/>.
#

import time
from datetime import date
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.utils.datastructures import SortedDict

from nav.django.context_processors import account_processor
from nav.django.shortcuts import render_to_response, object_list
from nav.models.manage import Room, Location, Netbox, Module
from nav.models.event import AlertHistory, AlertHistoryMessage, AlertHistoryVariable, AlertType, EventType
from nav.web.message import new_message, Messages
from nav.web.templates.DeviceHistoryTemplate import DeviceHistoryTemplate
from nav.web.quickselect import QuickSelect

from nav.web.devicehistory.utils.history import History
from nav.web.devicehistory.utils.error import register_error_events

DeviceQuickSelect_view_history_kwargs = {
    'button': 'View %s history',
    'module': True,
    'netbox_label': '%(sysname)s [%(ip)s - %(device__serial)s]',
}
DeviceQuickSelect_post_error_kwargs = {
    'button': 'Add %s error event',
    'location': False,
    'room': False,
    'module': True,
    'netbox_label': '%(sysname)s [%(ip)s - %(device__serial)s]',
}


# Often used timelimits, in seconds:
ONE_DAY = 24 * 3600
ONE_WEEK = 7 * ONE_DAY

HISTORY_PER_PAGE = 100

_ = lambda a: a

# NOTE:
# Search is using POST instead of GET, which would be more correct, because of
# constraints in IE that limits the length of an URL to around 2000 characters.

def devicehistory_search(request):
    DeviceQuickSelect = QuickSelect(**DeviceQuickSelect_view_history_kwargs)
    from_date = request.POST.get('from_date', date.fromtimestamp(time.time() - 7 * 24 * 60 * 60))
    to_date = request.POST.get('to_date', date.fromtimestamp(time.time() + 24 * 60 * 60))
    types = request.POST.getlist('type')

    selected_types = {'event': [], 'alert': []}
    for type in types:
        if type.find('_') != -1:
            splitted = type.split('_')
            if splitted[0] == 'e':
                selected_types['event'].append(splitted[1])
            else:
                selected_types['alert'].append(splitted[1])

    alert_types = AlertType.objects.select_related(
        'event_type'
    ).all().order_by('event_type__id', 'name')
    event_types = {}
    for a in alert_types:
        if a.event_type.id not in event_types:
            event_types[a.event_type.id] = []
        event_types[a.event_type.id].append(a)

    info_dict = {
        'active': {'devicesearch': True},
        'quickselect': DeviceQuickSelect,
        'selected_types': selected_types,
        'event_type': event_types,
        'from_date': from_date,
        'to_date': to_date,
    }
    return render_to_response(
        DeviceHistoryTemplate,
        'devicehistory/history_search.html',
        info_dict,
        RequestContext(
            request,
            processors=[account_processor]
        )
    );

def devicehistory_view(request):
    DeviceQuickSelect = QuickSelect(**DeviceQuickSelect_view_history_kwargs)
    from_date = request.POST.get('from_date', date.fromtimestamp(time.time() - ONE_WEEK))
    to_date = request.POST.get('to_date', date.fromtimestamp(time.time() + ONE_DAY))
    types = request.POST.getlist('type')
    group_by = request.POST.get('group_by', 'netbox')
    try:
        page = int(request.POST.get('page', '1'))
    except ValueError:
        page = 1

    selected_types = {'event': [], 'alert': []}
    for type in types:
        if type.find('_') != -1:
            splitted = type.split('_')
            if splitted[0] == 'e':
                selected_types['event'].append(splitted[1])
            else:
                selected_types['alert'].append(splitted[1])

    type_filter = []
    if selected_types['event']:
        type_filter.append(Q(event_type__in=selected_types['event']))
    if selected_types['alert']:
        type_filter.append(Q(alert_type__in=selected_types['alert']))

    if group_by == "location":
        order_by = ["location_name"]
    elif group_by == "room":
        order_by = ["room_descr"]
    elif group_by == "module":
        order_by = ["module_name"]
    elif group_by == "device":
        order_by = ["device"]
    elif group_by == "datetime":
        order_by = []
    else:
        order_by = ["netbox"]

    order_by.append("-start_time")
    order_by.append("-end_time")

    # FIXME check that date is a valid "yyyy-mm-dd" string

    selection = DeviceQuickSelect.handle_post(request)

    # Fetch history for selected items.
    # Also fetches additional info about location, room, netbox and module.
    alert_history = AlertHistory.objects.select_related(
        'event_type', 'alert_type', 'device'
    ).filter(
        Q(device__netbox__room__location__id__in=selection['location']) |
        Q(device__netbox__room__id__in=selection['room']) |
        Q(device__netbox__id__in=selection['netbox']) |
        Q(device__netbox__module__id__in=selection['module']),
        Q(start_time__lte=to_date) &
        (
            Q(end_time__gte=from_date) |
            (
                Q(end_time__isnull=True) &
                Q(start_time__gte=from_date)
            )
        ),
        *type_filter
    ).extra(
        select={
            'location_name': 'location.descr',
            'room_descr': 'room.descr',
            'netbox_name': 'netbox.sysname',
            'module_name': 'module.module',
        },
        tables=[
            'location',
        ],
        where=[
            '''(
               room.locationid = location.locationid AND
               netbox.roomid = room.roomid AND
               netbox.deviceid = device.deviceid
            )'''
        ],
    ).order_by(*order_by)

    paginator = Paginator(alert_history, HISTORY_PER_PAGE)

    try:
        history = paginator.page(page)
    except (EmptyPage, InvalidPage):
        history = paginator.page(paginator.num_pages)

    # Fetch related messages
    msgs = AlertHistoryMessage.objects.filter(
        alert_history__in=[h.id for h in history.object_list],
        language='en',
    ).values('alert_history', 'message', 'type', 'state')

    grouped_history = SortedDict()
    for a in history.object_list:
        a.extra_messages = {}
        for m in msgs:
            if a.id == m['alert_history']:
                if not a.extra_messages.has_key(m['state']):
                    a.extra_messages[m['state']] = {
                        'sms': None,
                        'email': None,
                        'jabber': None,
                    }
                a.extra_messages[m['state']][m['type']] = m['message']

        if group_by == "location":
            key = a.location_name
        elif group_by == "room":
            key = a.room_descr
        elif group_by == "module":
            key = a.module_name
        elif group_by == "device":
            key = a.device.serial
        elif group_by == "datetime":
            key = a.start_time
        else:
            key = a.netbox_name

        if not grouped_history.has_key(key):
            grouped_history[key] = []
        grouped_history[key].append(a)
    history.grouped_history = grouped_history


    alert_types = AlertType.objects.select_related(
        'event_type'
    ).all().order_by('event_type__id', 'name')
    event_types = {}
    for a in alert_types:
        if a.event_type.id not in event_types:
            event_types[a.event_type.id] = []
        event_types[a.event_type.id].append(a)

    info_dict = {
        'active': {'devicehistory': True},
        'history': history,
        'selection': selection,
        'selected_types': selected_types,
        'event_type': event_types,
        'from_date': from_date,
        'to_date': to_date,
        'group_by': group_by,
    }
    return render_to_response(
        DeviceHistoryTemplate,
        'devicehistory/history_view.html',
        info_dict,
        RequestContext(
            request,
            processors=[account_processor]
        )
    )

def error_form(request):
    DeviceQuickSelect = QuickSelect(**DeviceQuickSelect_post_error_kwargs)
    if request.method == 'POST':
        return register_error(request)

    info_dict = {
        'active': {'error': True},
        'quickselect': DeviceQuickSelect,
    }
    return render_to_response(
        DeviceHistoryTemplate,
        'devicehistory/register_error.html',
        info_dict,
        RequestContext(
            request,
            processors=[account_processor]
        )
    );

def register_error(request):
    DeviceQuickSelect = QuickSelect(**DeviceQuickSelect_post_error_kwargs)
    selection = DeviceQuickSelect.handle_post(request)
    error_comment = request.POST.get('error_comment', None)

    register_error_events(request, selection=selection, comment=error_comment)

    return HttpResponseRedirect(reverse('devicehistory-registererror'))

def delete_module(request):
    params = []
    confirm_deletion = False
    if request.method == 'POST':
        module_ids = request.POST.getlist('module')
        params.append('module.moduleid IN (%s)' % ",".join([id for id in module_ids]))
        confirm_deletion = True

    modules = AlertHistory.objects.extra(
        select={
            'module_id': 'module.moduleid',
            'module': 'module.module',
            'module_description': 'module.descr',
            'netbox_name': 'netbox.sysname',
            'downtime': 'NOW() - alerthist.start_time',
        },
        tables=[
            'device',
            'module',
            'netbox',
        ],
        where=[
            'device.deviceid=alerthist.deviceid',
            'module.deviceid=device.deviceid',
            'netbox.netboxid=module.netboxid',
            'module.up=\'n\'',
            'alerthist.end_time=\'infinity\'',
            'alerthist.eventtypeid=\'moduleState\'',
        ] + params
    ).order_by('start_time')

    info_dict = {
        'active': {'module': True},
        'confirm_delete': confirm_deletion,
        'modules': modules,
    }
    return render_to_response(
        DeviceHistoryTemplate,
        'devicehistory/delete_module.html',
        info_dict,
        RequestContext(
            request,
            processors=[account_processor]
        )
    )

def do_delete_module(request):
    if request.method != 'POST' or not request.POST.get('confirm_delete', False):
        return HttpResponseRedirect(reverse('devicehistory-module'))

    module_ids = request.POST.getlist('module')
    params = [
        'module.moduleid IN (%s)' % ",".join([id for id in module_ids])
    ]

    history = AlertHistory.objects.extra(
        select={
            'module': 'module.moduleid',
        },
        tables=[
            'device',
            'module',
            'netbox',
        ],
        where=[
            'device.deviceid=alerthist.deviceid',
            'module.deviceid=device.deviceid',
            'netbox.netboxid=module.netboxid',
            'module.up=\'n\'',
            'alerthist.end_time=\'infinity\'',
            'alerthist.eventtypeid=\'moduleState\'',
        ] + params
    )

    if history.count() == 0:
        new_message(
            request,
            _('No modules selected'),
            Messages.NOTICE
        )
        return HttpResponseRedirect(reverse('devicehistory-module'))

    # FIXME should there be posted an event, telling the event/alert system
    # that this module is now deleted?
    modules = Module.objects.filter(id__in=[id for module in history])

    new_message(
        request,
        _('Deleted selected modules.'),
        Messages.SUCCESS,
    )

    modules.delete()

    return HttpResponseRedirect(reverse('devicehistory-module'))
