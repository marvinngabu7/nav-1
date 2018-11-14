# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2011 Uninett AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with NAV. If not, see <http://www.gnu.org/licenses/>.
#
"""
A class that tries to retrieve all sensors from WeatherGoose II.

Uses the vendor-specifica IT-WATCHDOGS-V4-MIB to detect and collect
sensor-information.
"""
from django.utils.six import itervalues
from twisted.internet import defer

from nav.mibs import reduce_index
from nav.mibs import mibretriever
from nav.models.manage import Sensor
from nav.oids import OID

from .itw_mib import for_table


class ItWatchDogsMibV4(mibretriever.MibRetriever):
    """A class that tries to retrieve all sensors from WeatherGoose II"""
    from nav.smidumps.itw_mibv4 import MIB as mib

    oid_name_map = dict((OID(attrs['oid']), name)
                        for name, attrs in mib['nodes'].items())

    lowercase_nodes = dict((key.lower(), key)
                           for key in mib['nodes'])

    def _debug(self, msg, *args, **kwargs):
        return self._logger.debug(self.__class__.__name__ + ":: " + msg,
                                  *args, **kwargs)

    def _error(self, msg, *args, **kwargs):
        return self._logger.error(self.__class__.__name__ + ":: " + msg,
                                  *args, **kwargs)

    def _get_oid_for_sensor(self, sensor_name):
        """Return the OID for the given sensor-name as a string; Return
        None if sensor-name is not found.
        """
        oid_str = None
        nodes = self.mib.get('nodes', None)
        if nodes:
            sensor_def = nodes.get(sensor_name, None)
            if sensor_def:
                oid_str = sensor_def.get('oid', None)
        return oid_str

    def _make_result_dict(self, sensor_oid, base_oid, serial, desc,
                          u_o_m=None, precision=0, scale=None, name=None):
        """ Make a simple dictionary to return to plugin"""
        if not sensor_oid or not base_oid or not serial or not desc:
            return {}
        oid = OID(base_oid) + OID(sensor_oid)
        internal_name = serial + desc
        return {'oid': oid,
                'unit_of_measurement': u_o_m,
                'precision': precision,
                'scale': scale,
                'description': desc,
                'name': name,
                'internal_name': internal_name,
                'mib': self.get_module_name(),
                }

    @for_table('internalTable')
    def _get_internal_sensors_params(self, internal_sensors):
        sensors = []

        for temp_sensor in itervalues(internal_sensors):
            temp_avail = temp_sensor.get('internalAvail', None)
            if temp_avail:
                climate_oid = temp_sensor.get(0, None)
                serial = temp_sensor.get('internalSerial', None)
                name = temp_sensor.get('internalName', None)
                sensors.append(self._make_result_dict(
                    climate_oid,
                    self._get_oid_for_sensor('internalTemp'),
                    serial, 'internalTemp', precision=1, u_o_m=Sensor.UNIT_CELSIUS,
                    name=name))
                sensors.append(self._make_result_dict(
                    climate_oid,
                    self._get_oid_for_sensor('internalHumidity'),
                    serial, 'internalHumidity', u_o_m=Sensor.UNIT_PERCENT_RELATIVE_HUMIDITY,
                    name=name))
                sensors.append(self._make_result_dict(
                    climate_oid,
                    self._get_oid_for_sensor('internalDewPoint'),
                    serial, 'internalDewPoint', precision=1, u_o_m=Sensor.UNIT_CELSIUS,
                    name=name))

        return sensors

    @defer.inlineCallbacks
    def get_all_sensors(self):
        """ Try to retrieve all available sensors in this WxGoose"""
        # We only implement internalTable because we don't have any more sensors to test on
        tables = ['internalTable']

        result = []
        for table in tables:
            self._debug('get_all_sensors: table = %s', table)
            sensors = yield self.retrieve_table(
                                        table).addCallback(reduce_index)
            self._debug('get_all_sensors: %s = %s', table, sensors)
            handler = for_table.map.get(table, None)
            if not handler:
                self._error("There is not data handler for %s", table)
            else:
                method = getattr(self, handler)
                result.extend(method(sensors))

        defer.returnValue(result)
