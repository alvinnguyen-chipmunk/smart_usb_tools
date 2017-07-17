#!/usr/bin/env python

##################################################################################################################################
##      yellowfin-extra-service.py : Python script will to do:                                                                  ##
##              - Detect USB plugin then mount it                                                                               ##
##              - Search for Wifi pass, AGPS key, EMV configure file                                                            ##
##              - Update information found                                                                                      ##
##              - LED alert for working result                                                                                  ##
##                                                                                                                              ##
##       Create:    2017-07-06 14:30:00                                                                                         ##
##       Modified:  -                                                                                                           ##
##       Author:    Alvin Nguyen (alvin.nguyen@styl.solutions)                                                                  ##
##       Copyright: STYL Solutions Pte. Lte.                                                                                    ##
##                                                                                                                              ##
##################################################################################################################################

import pyudev
import os
import subprocess
import dbus, uuid
from time import time, sleep
from pyudev import Context, Monitor
import smbus

# Mount global variable
MOUNT_DIR                   = ".extra_service_tmp_dir"
CHECK_FSTYPE_1              = "OEM-ID \"mkfs.fat\""
CHECK_FSTYPE_2              = "FAT"
CHECK_FSTYPE                = True

# STYLAGPS global variable
STYLAGPS_CONFIG             = "stylagps.conf"
STYLAGPS_LOCATION           = "/etc/stylagps/stylagps.conf"

# Wireless global variable
WIRELESS_PASSWD             = "wireless.passwd"
CONNECTION_PATH             = None

# EMV global variable
EMV_CONFIG_DIR              = "emv"
EMV_LOCATION                = "/home/root/emv"
EMV_LOAD_CONFIG_SH          = "emv_load_config.sh"
SVC_APP                     = "svc"
USE_SVC_SYSTEMD             = False

# LED global variable
STYL_LED_BOARD_I2C_ADDRESS  = 0x20
PD9535_CONFIG_REG_PORT0     = 0x06
PD9535_CONFIG_REG_PORT1     = 0x07
PD9535_OUT_REG_PORT0        = 0x02
PD9535_OUT_REG_PORT1        = 0x03
PD9535_CONFIG_OUT_PORT      = 0x00

# Return value class
class Error:
    SUCCESS     = 1
    FAIL        = 2
    NONE        = 3

class LED_COLOR:
    OFF_COLOR     = 0x00
    SUCCESS_COLOR = 0x01
    FAILURE_COLOR = 0x02
    MOUNT_COLOR   = 0x05
    NONE_COLOR    = 0x06
    RUNNING_COLOR = 0x07

class LED:
    AGPS = 1
    WIFI = 2
    EMV  = 3

# DBUS global variable
bus     = dbus.SystemBus()

# MSBUS global variable
# 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
msbus   = smbus.SMBus(0)

# ################################################################################################################################################## #
class TimeOut:
    def __init__(self, deadtime):
        self.timeout = time.time() + deadtime

    def OnTime(self):
        if time.time() > self.timeout:
            return False
        else:
            return True

def find_file_in_path(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None

def find_dir_in_path(name, path):
    for root, dirs, files in os.walk(path):
        if name in dirs:
            return os.path.join(root, name)
    return None

# Used as a quick way to handle shell commands #
def get_from_shell_raw(command):
    try:
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.stdout.readlines()
    except:
        return 'Error when execute "{0}"'.format(command)

def get_from_shell(command):
    result = get_from_shell_raw(command)
    for i in range(len(result)):
        result[i] = result[i].strip() # strip out white space #
    return result

def bash_command(command):
    try:
        result = subprocess.check_call(['bash', command])
        return result
    except:
        return -1

# ################################################################################################################################################## #

# ################################################################################################################################################## #
def led_alert_init():
    try:
        ret = msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_CONFIG_REG_PORT0, PD9535_CONFIG_OUT_PORT)
        ret = msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_CONFIG_REG_PORT1, PD9535_CONFIG_OUT_PORT)

    except:
        print 'Initialization I2C LED : FAILURED'

def led_alert_set(light_index, light_color):
    light_value = -1
    try:
        if  light_index == LED.AGPS:
            light_value = msbus.read_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0);
            light_value = (light_value & 0x00F8) | light_color
            msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0, light_value)
        elif light_index == LED.WIFI:
            light_value = msbus.read_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0);
            light_value = (light_value & 0x00C7) | (light_color << 3)
            msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0, light_value)
        elif light_index == LED.EMV:
            light_value = msbus.read_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT1);
            light_value = (light_value & 0x00F8) | light_color
            msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT1, light_value)

    except:
        print 'Set light color for I2C LED : FAILURED'

def led_alert_set_all(light_color):
    led_alert_set(LED.AGPS, light_color)
    led_alert_set(LED.WIFI, light_color)
    led_alert_set(LED.EMV , light_color)

def led_alert_do(state, index, string):
    if state == Error.FAIL:
        led_alert_set(index, LED_COLOR.FAILURE_COLOR)
        print 'Update {0} fail'.format(string)
    elif state == Error.SUCCESS:
        led_alert_set(index, LED_COLOR.SUCCESS_COLOR)
        print 'Update {0} success'.format(string)
    elif state == Error.NONE:
        led_alert_set(index, LED_COLOR.NONE_COLOR)
        print 'Not found {0}'.format(string)
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def update_emv_configure_systemd_service_togle(is_start):
    systemd1 = bus.get_object('org.freedesktop.systemd1',  '/org/freedesktop/systemd1')
    manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')

    try:
        if is_start:
            command = 'ps auwx | grep -in "{0}" | grep -v grep'.format(SVC_APP)
            result = get_from_shell(command)
            if not result:
                USE_SVC_SYSTEMD = True
                manager.RestartUnit('styl-readersvcd.service', 'fail')
        else:
            if USE_SVC_SYSTEMD:
                manager.StopUnit('styl-readersvcd.service', 'fail')
                USE_SVC_SYSTEMD = False

    except:
        return False

    return True


def update_emv_configure(directory, emv_config_dir, emv_location, emv_load_config_sh):
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

    # Copy all *.json files in new_config_dir to old EMV configure directory
    command = 'cp {0}/*.json {1}'.format(new_config_dir, emv_location)
    result = get_from_shell(command)
    if result:
        return Error.FAIL

    # Start readersvcd service
    if not update_emv_configure_systemd_service_togle(True):
        return Error.FAIL

    # Run emv_loader to load all *.json files to reader
    command = '{0}'.format(emv_loader)
    result = bash_command(command)

    # Stop readersvcd service
    update_emv_configure_systemd_service_togle(False)

    if result != 0:
        return Error.FAIL

    return Error.SUCCESS
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def update_wireless_passwd_connection_new(ssid_string, psk_string):
    print 'update_wireless_passwd_connection_new - ssid: {0}'.format(ssid_string)
    print 'update_wireless_passwd_connection_new - psk: {0}'.format(psk_string)

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

    print connection

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
    path = find_file_in_path(wireless_passwd, directory)
    if path:
        lines = [line.rstrip('\n') for line in open(path)]
        elements = line.split(":")
        if len(elements)!=2:
            return Error.FAIL
        connection = update_wireless_passwd_connection_find_by_name(elements[0])
        if connection:
            print "WIRELESS: UPDATE"
            # update secrets then update connection
            update_wireless_passwd_connection_change_secrets(CONNECTION_PATH, connection, elements[1])
            # Change the connection with Update()
            proxy = bus.get_object("org.freedesktop.NetworkManager", CONNECTION_PATH)
            settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings.Connection")
            settings.Update(connection)
        else:
            print "WIRELESS: NEW"
            # create a new connection
            update_wireless_passwd_connection_new(elements[0], elements[1])
        return Error.SUCCESS
    return Error.FAIL
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def update_geolocation_key(directory, stylagps_config, stylagps_location):
    if not directory or not stylagps_config or not stylagps_location:
        return Error.FAIL
    if not os.path.exists(stylagps_location):
        return Error.NONE
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
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def umount_action(partition, directory):
    command = 'umount {0}'.format(partition)
    result = get_from_shell(command)
    print 'umount_action: umount: result: {0}'.format(result)
    command = 'rm -rf {0}'.format(directory)
    result = get_from_shell(command)
    print 'umount_action: rm: result: {0}'.format(result)

def mount_action(partition, directory):
    if CHECK_FSTYPE:
        command = 'file -s {0}'.format(partition)
        result = get_from_shell(command)
        print 'mount_action: result: {0}'.format(result)
        if not result:
            return False

        #if result[0].find(CHECK_FSTYPE_1)==-1:
        #    return False
        if result[0].find(CHECK_FSTYPE_2)==-1:
            return False
        else:
            print 'Found a partition with {0} type'.format(CHECK_FSTYPE_2)

    command = 'mkdir -p {0}'.format(directory)
    result = get_from_shell(command)
    print 'mount_action: mkdir result: {0}'.format(result)
    if not result:
        command = 'mount {0} {1}'.format(partition, directory)
        result = get_from_shell(command)
        print 'mount_action: mount: result: {0}'.format(result)
        if not result and os.path.ismount(directory):
            return True
    return False
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def remove_device_event():
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
            # Initialization I2C LED
            led_alert_init()
            # Set running state for I2C LED
            led_alert_set_all(LED_COLOR.RUNNING_COLOR)
            # Mount partitions on USB device
            print 'partition: {0}'.format(partition)
            print 'MOUNT_DIR: {0}'.format(MOUNT_DIR)
            if mount_action(partition, MOUNT_DIR):

                # Search and update for Google geolocation API key
                state = update_geolocation_key(MOUNT_DIR, STYLAGPS_CONFIG, STYLAGPS_LOCATION)
                led_alert_do(state, LED.AGPS, 'Google geolocation API key')

                # Search and update for Wireless password
                state = update_wireless_passwd(MOUNT_DIR, WIRELESS_PASSWD)
                led_alert_do(state, LED.WIFI, 'Wifi information')

                # Search and update for EMV configure
                state = update_emv_configure(MOUNT_DIR, EMV_CONFIG_DIR, EMV_LOCATION, EMV_LOAD_CONFIG_SH)
                led_alert_do(state, LED.EMV, 'EMV Configure')

                # Done, now umount for this partition
                sleep(1)
                umount_action(partition, MOUNT_DIR)

            else:
                led_alert_set_all(LED_COLOR.MOUNT_COLOR)

    elif device.action == 'remove':
        remove_device_event()
# ################################################################################################################################################## #

# ################################################################################################################################################## #
if __name__ == '__main__':
    print 'Start extra service script .......'

    home_dir = os.path.expanduser("~")
    MOUNT_DIR = '{0}/{1}'.format(home_dir, MOUNT_DIR)
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='block')  # Remove this line to listen for all devices.
    monitor.start()
    for device in iter(monitor.poll, None):
        device_event(device)

    print 'Exit extra service script .......'
# ################################################################################################################################################## #
