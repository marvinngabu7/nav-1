package no.ntnu.nav.getDeviceData.dataplugins.Netbox;

import java.util.*;
import java.sql.*;

import no.ntnu.nav.logger.*;
import no.ntnu.nav.Database.*;
import no.ntnu.nav.getDeviceData.Netbox;
import no.ntnu.nav.getDeviceData.dataplugins.*;
import no.ntnu.nav.getDeviceData.dataplugins.Device.DeviceHandler;


/**
 * DataHandler plugin for getDeviceData; provides an interface for storing
 * netbox data.
 *
 * @see NetboxContainer
 */

public class NetboxHandler implements DataHandler {

	private static final boolean DB_COMMIT = true;

	private static Map deviceMap;
	private static Map netboxMap;
	

	/**
	 * Fetch initial data from device and netbox tables.
	 */
	public synchronized void init(Map persistentStorage) {
		if (persistentStorage.containsKey("initDone")) return;
		persistentStorage.put("initDone", null);

		Map m;
		ResultSet rs;
		long dumpBeginTime,dumpUsedTime;

		Log.setDefaultSubsystem("NetboxHandler");

		try {
		
			// device
			dumpBeginTime = System.currentTimeMillis();
			m  = Collections.synchronizedMap(new HashMap());
			rs = Database.query("SELECT deviceid,serial FROM device");
			while (rs.next()) {
				m.put(rs.getString("serial"), rs.getString("deviceid"));
			}
			deviceMap = m;
			dumpUsedTime = System.currentTimeMillis() - dumpBeginTime;
			Log.d("INIT", "Dumped device in " + dumpUsedTime + " ms");

			// netbox
			dumpBeginTime = System.currentTimeMillis();
			m = Collections.synchronizedMap(new HashMap());
			rs = Database.query("SELECT deviceid,serial,hw_ver,sw_ver,netboxid,typeid,sysname FROM device JOIN netbox USING (deviceid)");
			while (rs.next()) {
				NetboxData n = new NetboxData(rs.getString("serial"),
																			rs.getString("hw_ver"),
																			rs.getString("sw_ver"),
																			null,
																			rs.getString("typeid"),
																			rs.getString("sysname"));
				n.setDeviceid(rs.getInt("deviceid"));

				String key = rs.getString("netboxid");
				m.put(key, n);
			}
			netboxMap = m;
			dumpUsedTime = System.currentTimeMillis() - dumpBeginTime;
			Log.d("INIT", "Dumped module in " + dumpUsedTime + " ms");

		} catch (SQLException e) {
			Log.e("INIT", "SQLException: " + e.getMessage());
		}

	}

	/**
	 * Return a DataContainer object used to return data to this
	 * DataHandler.
	 */
	public DataContainer dataContainerFactory() {
		return new NetboxContainer(this);
	}
	
	/**
	 * Store the data in the DataContainer in the database.
	 */
	public void handleData(Netbox nb, DataContainer dc) {
		if (!(dc instanceof NetboxContainer)) return;
		NetboxContainer nc = (NetboxContainer)dc;
		if (!nc.isCommited()) return;

		// Because it's possible for serial to be empty, but we can still
		// identify the device by deviceid in netbox, we need to check the
		// deviceid if serial is empty.
		NetboxData n = (NetboxData)nc.getNetbox();
		String netboxid = nb.getNetboxidS();
		NetboxData oldn = (NetboxData)netboxMap.get(netboxid);
		if (n.hasEmptySerial()) {
			n.setDeviceid(oldn.getDeviceid());
		}

		// Let DeviceHandler update the device table first
		DeviceHandler dh = new DeviceHandler();
		dh.handleData(nb, dc);

		Log.setDefaultSubsystem("NetboxHandler");

		try {

				// Check if we need to update netbox
			if (!oldn.equalsNetboxData(n)) {
				// We need to update netbox
				Log.i("UPDATE_NETBOX", "netboxid="+netboxid+" deviceid="+n.getDeviceidS()+" typeid="+n.getType()+" sysname="+n.getSysname());

				String[] set = {
					"deviceid", n.getDeviceidS(),
					"typeid", n.getType(),
					"sysname", n.getSysname()
				};
				String[] where = {
					"netboxid", netboxid
				};
				Database.update("netbox", set, where);
			}
			
			if (DB_COMMIT) Database.commit(); else Database.rollback();
			
		} catch (SQLException e) {
			Log.e("HANDLE", "SQLException: " + e.getMessage());
			e.printStackTrace(System.err);
		}
	}
	
}
