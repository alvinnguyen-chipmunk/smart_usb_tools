#!/usr/bin/env python

##################################################################################################################################
##  (C) Copyright 2009 STYL Solutions Co., Ltd. , All rights reserved                                                           ##
##                                                                                                                              ##
##  This source code and any compilation or derivative thereof is the sole                                                      ##
##  property of STYL Solutions Co., Ltd. and is provided pursuant to a                                                          ##
##  Software License Agreement.  This code is the proprietary information                                                       ##
##  of STYL Solutions Co., Ltd and is confidential in nature.  Its use and                                                      ##
##  dissemination by any party other than STYL Solutions Co., Ltd is                                                            ##
##  strictly limited by the confidential information provisions of the                                                          ##
##  agreement referenced above.                                                                                                 ##
##                                                                                                                              ##
##  extra_config_runtime.py : Python script will to do:                                                                         ##
##              - Detect USB plugin then mount FAT partitions on USB device                                                     ##
##              - Search for Wireless information, AGPS key information, EMV configure files, Test-tool flags                   ##
##              - If Wireless information found                                                                                 ##
##                  + Update the exist wireless connection                                                                      ##
##                    or                                                                                                        ##
##                  + Create a wireless connection                                                                              ##
##              - If AGPS information found                                                                                     ##
##                    Update file /etc/stylagps/stylagps.conf                                                                   ##
##              - If EMV configure files found                                                                                  ##
##                    Copy to MMC, the files will be process by other script when system reboot.                                ##
##              - If Test-tool flags found                                                                                      ##
##                    Execute Test-tool application (ask Mr. Thinh for more information)                                        ##
##                                                                                                                              ##
##              - LED alert for working result                                                                                  ##
##                                                                                                                              ##
##       Create:    2017-07-06 14:30:00                                                                                         ##
##       Modified:  2017-08-30 08:30:00                                                                                         ##
##       Author:    Alvin Nguyen (alvin.nguyen@styl.solutions)                                                                  ##
##                                                                                                                              ##
##################################################################################################################################

from extra_config_header import *

# ################################################################################################################################################## #
def prepare_update_emv_configure(directory, emv_config_dir, emv_location, emv_load_config_sh, md5_file):
    if not directory or not emv_config_dir or not emv_location:
        return Error.FAIL

    new_config_dir = find_dir_in_path(emv_config_dir, directory)
    if not new_config_dir:
        return Error.NONE

    emv_loader = '{0}/{1}'.format(emv_location, emv_load_config_sh)

    if not os.path.exists(emv_location) or not os.path.exists(emv_loader):
        return Error.FAIL

    # Remove all *.json files in old EMV configure directory
    command = 'rm -rf {0}/*.json'.format(emv_location)
    result = get_from_shell(command)
    if result:
        return Error.FAIL

    # Gen md5 checksum information
    try:
        os.chdir(new_config_dir)
        command = 'md5sum *.json > {0}'.format(MD5_FILE)
        exec_command(command)
        command = '{0}/(1)'.format(new_config_dir, MD5_FILE)
        if not os.path.exists(new_config_dir):
            return Error.FAIL

        # Copy all *.json files in new_config_dir to old EMV configure directory
        command = 'cp {0}/*.json {1}'.format(new_config_dir, emv_location)
        result = get_from_shell(command)
        if result:
            return Error.FAIL

        # Copy checksum file in new_config_dir to old EMV configure directory
        command = 'cp {0}/{1} {2}'.format(new_config_dir, MD5_FILE, emv_location)
        result = get_from_shell(command)
        if result:
            return Error.FAIL

        os.system("sync")
        os.chdir(emv_location)

        return Error.SUCCESS

    except:
        return Error.FAIL

    
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def update_wireless_passwd_connection_new(ssid_string, psk_string):

    s_con = dbus.Dictionary({
    'type': '802-11-wireless',
    'uuid': str(uuid.uuid4()),
    'id': ssid_string})

    s_wifi = dbus.Dictionary({
        'ssid': dbus.ByteArray(ssid_string),
        'mode': 'infrastructure',
    })

    s_wsec = dbus.Dictionary({
        'key-mgmt': 'wpa-psk',
        'auth-alg': 'open',
        'psk': psk_string.rstrip(),
    })

    s_ip4 = dbus.Dictionary({'method': 'auto'})
    s_ip6 = dbus.Dictionary({'method': 'ignore'})

    connection = dbus.Dictionary({
        'connection': s_con,
        '802-11-wireless': s_wifi,
        '802-11-wireless-security': s_wsec,
        'ipv4': s_ip4,
        'ipv6': s_ip6
         })

    #print connection

    proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings")
    settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")
    nm = dbus.Interface(proxy, "org.freedesktop.NetworkManager")

    settings.AddConnection(connection)

def update_wireless_passwd_connection_change_secrets_in_one_setting(proxy, config, setting_name, new_secret):
    # Add new secret values to the connection config
    secrets = proxy.GetSecrets(setting_name)
    for setting in secrets:
        for key in secrets[setting]:
            config[setting_name][key] = new_secret.rstrip()

def update_wireless_passwd_connection_change_secrets(con_path, config, new_secret):
    # Get existing secrets; we grab the secrets for each type of connection
    # (since there isn't a "get all secrets" call because most of the time
    # you only need 'wifi' secrets or '802.1x' secrets, not everything) and
    # set new values into the connection settings (config)
    con_proxy = bus.get_object("org.freedesktop.NetworkManager", con_path)
    connection_secrets = dbus.Interface(con_proxy, "org.freedesktop.NetworkManager.Settings.Connection")
    update_wireless_passwd_connection_change_secrets_in_one_setting(connection_secrets, config, '802-11-wireless-security', new_secret)

def update_wireless_passwd_connection_find_by_name(name):
    # Ask the settings service for the list of connections it provides
    global CONNECTION_PATH

    proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings")
    settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")
    connection_paths = settings.ListConnections()

    # Get the settings and look for connection's name
    for path in connection_paths:
        con_proxy = bus.get_object("org.freedesktop.NetworkManager", path)
        connection = dbus.Interface(con_proxy, "org.freedesktop.NetworkManager.Settings.Connection")
        try:
            config = connection.GetSettings()
        except Exception, e:
            pass

        # Find connection by the id
        s_con = config['connection']
        if name == s_con['id']:
            CONNECTION_PATH = path
            return config
        # Find connection by the uuid
        if name == s_con['uuid']:
            CONNECTION_PATH = path
            return config

    return None


def update_wireless_passwd(directory, wireless_passwd):
    if not directory or not wireless_passwd:
        return Error.FAIL
    try:
        path = find_file_in_path(wireless_passwd, directory)
        if path:        
            lines = [line.rstrip('\n') for line in open(path)]
            for line in lines:
                #print 'Wireless update for: {0}'.format(line)
                elements = line.split(":")
                if len(elements)!=2:
                    return Error.FAIL
                connection = update_wireless_passwd_connection_find_by_name(elements[0])
                if connection:
                    #print "WIRELESS: UPDATE"
                    # update secrets then update connection
                    update_wireless_passwd_connection_change_secrets(CONNECTION_PATH, connection, elements[1])
                    # Change the connection with Update()
                    proxy = bus.get_object("org.freedesktop.NetworkManager", CONNECTION_PATH)
                    settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings.Connection")
                    settings.Update(connection)
                else:
                    #print "WIRELESS: NEW"
                    # create a new connection
                    update_wireless_passwd_connection_new(elements[0], elements[1])
            return Error.SUCCESS
        return Error.NONE
    except:
        return Error.FAIL
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def execute_testtool_configure(directory, tt_pattern, tt_flags, tt_flags_dir):
    if not directory or not tt_pattern or not tt_flags or not tt_flags_dir:
        return Error.FAIL

    try:
        path = find_file_in_path(tt_pattern, directory)
        if path:
            # Create a flag file for factory testtool application if it is't exist    
            if not find_file_in_path(tt_flags, tt_flags_dir):
                command = 'echo "testing" > {0}/{1}'.format(tt_flags_dir, tt_flags)
                if get_from_shell(command):
                    styl_error("Create flag file of factory testtool fail.")
                    return Error.FAIL
            return execute_testtool_configure_do(tt_flags, tt_flags_dir)
        else:
            return Error.NONE
    except:
        return Error.FAIL

# ################################################################################################################################################## #

# ################################################################################################################################################## #
def execute_scanner_configure(directory, scanner_pattern, scanner_flag, scanner_flag_dir):
	if not directory or not scanner_pattern or not scanner_flag or not scanner_flag_dir:
		return Error.FAIL
	if not is_dir_exist(scanner_flag_dir):
		command = 'mkdir -p {0}'.format(scanner_flag_dir)		
		if get_from_shell(command):
			styl_error("create flag directory of scanner setup fail.")
			return Error.FAIL
	try:
		path = find_file_in_path(scanner_pattern, directory)
		if path:
			
			command = 'echo 1 > {0}/{1}'.format(scanner_flag_dir, scanner_flag)
			if get_from_shell(command):
				styl_error("create flag file of scanner setup fail.")
				return Error.FAIL
		else:
			return Error.NONE
	except:
		return Error.FAIL
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def update_geolocation_key(directory, stylagps_config, stylagps_location):
    if not directory or not stylagps_config or not stylagps_location:
        return Error.FAIL
    
    if not library_is_exist(STYLAGPS_PKGCONFIG):
        return Error.NONE

    try:
        path = find_file_in_path(stylagps_config, directory)
        if path:
            command = 'mv {0} {1}.bak'.format(stylagps_location, stylagps_location)
            result = get_from_shell(command)
            command = 'cp {0} {1}'.format(path, stylagps_location)
            result = get_from_shell(command)
            if not result:
                return Error.SUCCESS
            else:
                return Error.FAIL
        else:
            return Error.NONE
    except:
        return Error.FAIL

# ################################################################################################################################################## #

# ################################################################################################################################################## #
def umount_action(partition, directory):
    try:
        command = 'umount {0}'.format(partition)
        result = get_from_shell(command)
        if not result:
            return Error.SUCCESS
    except:
        return Error.FAIL
    return Error.FAIL

def mount_action(partition, directory):
    try:
        if CHECK_FSTYPE:
            command = 'file -s {0}'.format(partition)
            result = get_from_shell(command)
            if not result:
                return Error.FAIL

            #if result[0].find(CHECK_FSTYPE_1)==-1:
            #    return False
            if result[0].find(CHECK_FSTYPE_2)==-1:
                return Error.NONE
            else:
                styl_log('Found a partition with {0} type'.format(CHECK_FSTYPE_2))

            command = 'mkdir -p {0}'.format(directory)
            result = get_from_shell(command)
            if not result:
                command = 'mount {0} {1}'.format(partition, directory)
                result = get_from_shell(command)
                if not result and os.path.ismount(directory):
                    return Error.SUCCESS
    except:
        return Error.FAIL
    return Error.FAIL
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def remove_device_event():
    led_alert_init()
    led_alert_set_all(LED_COLOR.OFF_COLOR)
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def device_event(device):

    if device.action == 'add':
        check = device.device_type
        if check != 'partition':
            return

        partition = device.device_node

        if partition:
            # Mount partitions on USB device
            state = mount_action(partition, MOUNT_DIR)
            if state==Error.SUCCESS:
                # Set running state for I2C LED
                led_alert_set_all(LED_COLOR.RUNNING_COLOR)

                # Search and update for Google geolocation API key
                state = update_geolocation_key(MOUNT_DIR, STYLAGPS_CONFIG, STYLAGPS_LOCATION)
                led_alert_do(state, LED.AGPS, 'Google geolocation API key')

                # Search and update for Wireless password
                state = update_wireless_passwd(MOUNT_DIR, WIRELESS_PASSWD)
                led_alert_do(state, LED.WIFI, 'Wifi information')

                # Search and prepare to update for EMV configure
                state = prepare_update_emv_configure(MOUNT_DIR, EMV_CONFIG_DIR, EMV_LOCATION, EMV_LOAD_CONFIG_SH, MD5_FILE)
                led_alert_do(state, LED.EMV, 'EMV Configure')
                if state==Error.SUCCESS:
                    command = 'echo  1 > {0}/{1}'.format(EMV_LOCATION, EMV_FLAG)
                    result = exec_command(command)
                    os.system("sync")
		
		# Search and run scanner configure
		state = execute_scanner_configure(MOUNT_DIR, SCANNER_PATTERN, SCANNER_FLAG, SCANNER_FLAG_PATH)
		# Check error code then show to user
		
                # Search and run test tool
                state = execute_testtool_configure(MOUNT_DIR, TT_PATTERN, TT_FLAGS, TT_FLAGS_DIR)
                led_alert_do(state, LED.TESTTOOL, 'TestTool Flags')

                # Done, now umount for this partition
                state = umount_action(partition, MOUNT_DIR)
                if state==Error.SUCCESS:
                    led_alert_flicker(LED_COLOR.OFF_COLOR)

            elif state==Error.FAIL:
                led_alert_set_all(LED_COLOR.MOUNT_COLOR)
            elif state==Error.NONE:
                styl_log('Not found FAT partition in device.')

    elif device.action == 'remove':
        check = device.device_type
        if check != 'partition':
            return
        remove_device_event()
# ################################################################################################################################################## #

# ################################################################################################################################################## #
if __name__ == '__main__':
    styl_log('Start')	

    # Initialization I2C LED
    led_alert_init()
    led_alert_set_all(LED_COLOR.OFF_COLOR)    
    
    home_dir = os.path.expanduser("~")
    MOUNT_DIR = '{0}/{1}'.format(home_dir, MOUNT_DIR)
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='block')  # Remove this line to listen for all devices.
    monitor.start()
    for device in iter(monitor.poll, None):
        device_event(device)

    styl_log('Exit')
# ################################################################################################################################################## #
