#!/usr/bin/env python

##################################################################################################################################
##      Styl-extra-service.py : Python script will to do:                                                                       ##
##              - Detect USB plugin then mount it                                                                               ##
##              - Search for Wifi pass, AGPS key, EMV configure file                                                            ##
##              - Update information found                                                                                      ##
##                                                                                                                              ##
##       Create:    2017-07-06 14:30:00                                                                                         ##
##       Modified:  -                                                                                                           ##
##       Author:    Alvin Nguyen (alvin.nguyen@styl.solutions)                                                                  ##
##       Copyright: STYL Solutions Pte. Lte.                                                                                    ##
##                                                                                                                              ##
##################################################################################################################################

import pyudev
import time
import os
import re
import sys
import subprocess
import dbus, uuid
from time import sleep
from pyudev import Context, Monitor

MOUNT_DIR = ".extra_service_tmp_dir"

STYLAGPS_CONFIG = "stylagps.conf"
STYLAGPS_LOCATION = "/etc/stylagps/stylagps.conf"

WIRELESS_PASSWD = "wireless.passwd"

SU = "sudo"
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

# Used as a quick way to handle shell commands #
def get_from_shell_raw(command):
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.stdout.readlines()

def get_from_shell(command):
    result = get_from_shell_raw(command)
    for i in range(len(result)):
        result[i] = result[i].strip() # strip out white space #
    return result
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

    con = dbus.Dictionary({
        'connection': s_con,
        '802-11-wireless': s_wifi,
        '802-11-wireless-security': s_wsec,
        'ipv4': s_ip4,
        'ipv6': s_ip6
         })

    print con

    bus = dbus.SystemBus()

    proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings")
    settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")

    settings.AddConnection(con)

def update_wireless_passwd(directory, wireless_passwd):
    if not directory and not wireless_passwd:
        return False

    path = find_file_in_path(wireless_passwd, directory)
    print 'Path is: {0}'.format(path)
    if path:
        print 'Found on: {0}'.format(path)
        lines = [line.rstrip('\n') for line in open(path)]
        elements = line.split(":")
        if len(elements)==2:
            update_wireless_passwd_connection_new(elements[0], elements[1])
            return True

    return False
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def update_geolocation_key(directory, stylagps_config, stylagps_location):
    if not directory and not stylagps_config and not stylagps_location:
        return False

    if not os.path.exists(stylagps_location):
        return False

    print 'update_geolocation_key: directory is: {0}'.format(directory)
    print 'update_geolocation_key: stylagps_config is: {0}'.format(stylagps_config)
    path = find_file_in_path(stylagps_config, directory)
    print 'Path is: {0}'.format(path)
    if path:
        print 'Found on: {0}'.format(path)
        command = '{2} mv {0} {1}.bak'.format(stylagps_location, stylagps_location, SU)
        print 'command 1:{0}'.format(command)
        result = get_from_shell(command)
        print 'result:{0}'.format(result)
        command = '{2} cp {0} {1}'.format(path, stylagps_location, SU)
        print 'command 1:{0}'.format(command)
        result = get_from_shell(command)
        print 'result:{0}'.format(result)
        if not result:
            return True
        else:
            return False

    return False
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def umount_action(partition, directory):
    print 'unmount_action: partition:{0}'.format(partition)
    print 'unmount_action: directories:{0}'.format(directory)

    command = '{1} umount {0}'.format(partition, SU)
    print 'umount_action: command 1: {0}'.format(command)
    result = get_from_shell(command)
    print 'umount_action: result: {0}'.format(result)

    command = 'rm -rf {0}'.format(directory)
    print 'umount_action: command 2: {0}'.format(command)
    result = get_from_shell(command)
    print 'umount_action: result: {0}'.format(result)

def mount_action(partition, directory):
    print 'mount_action: partitions:{0}'.format(partition)
    print 'mount_action: directory:{0}'.format(directory)

    command = 'mkdir -p {0}'.format(directory)
    print 'mount_action: command: {0}'.format(command)
    result = get_from_shell(command)
    print 'mount_action: result: {0}'.format(result)
    if not result:
        command = '{2} mount {0} {1}'.format(partition, directory, SU)
        print 'mount_action: command: {0}'.format(command)
        result = get_from_shell(command)
        print 'result:{0}'.format(result)
        if not result and os.path.ismount(directory):
            return True
    return False
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def remove_device_event():
    print 'remove partition'
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def device_event(device):

    print 'Processing for event {0} on device {1} .....'.format(device.action, device)
    success = True

    if device.action == 'add':
        print 'device.device_node:  {0}'.format(device.device_node)
        print 'device.sys_number:  {0}'.format(device.sys_number)
        print 'device.sys_name:  {0}'.format(device.sys_name)
        print 'device.context:  {0}'.format(device.context)
        print 'device.sys_path:  {0}'.format(device.sys_path)
        print 'device.device_number:  {0}'.format(device.device_number)
        print 'device.device_links:  {0}'.format(device.device_links)
        print 'device.device_type:  {0}'.format(device.device_type)
        print 'device.children:  {0}'.format(device.children)
        print 'device.subsystem: {0}'.format(device.subsystem)
        check = device.device_type
        print 'check:  {0}'.format(check)
        if check != 'partition':
            return

        partition = device.device_node
        print '====> partition: {0}'.format(partition)

        if partition:

            # Mount partitions on USB device #
            if mount_action(partition, MOUNT_DIR):
                # Search and update for Google geolocation API key
                success = update_geolocation_key(MOUNT_DIR, STYLAGPS_CONFIG, STYLAGPS_LOCATION)
                if success:
                    print 'Update Google geolocation API key success'
                else:
                    print 'Update Google geolocation API key fail'

                # Search and update for Wireless password
                success = update_wireless_passwd(MOUNT_DIR, WIRELESS_PASSWD)
                if success:
                    print 'Update Wireless password success'
                else:
                    print 'Update Wireless password fail'

                sleep(1)

                umount_action(partition, MOUNT_DIR)
        else:
            print '************** Nothing to do ******************'

    if device.action == 'remove':
        remove_device_event()

    print 'Processing for event {0} on device {1} .... Done.'.format(device.action, device)
# ################################################################################################################################################## #

# ################################################################################################################################################## #
if __name__ == '__main__':
    print 'Start service script .......'

    home_dir = os.path.expanduser("~")
    MOUNT_DIR = '{0}/{1}'.format(home_dir, MOUNT_DIR)
    print 'MOUNT_DIR: {0}'.format(MOUNT_DIR)

    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='block')  # Remove this line to listen for all devices.
    monitor.start()

    for device in iter(monitor.poll, None):
        print('{0.action} on {0.device_path}'.format(device))
        device_event(device)

    print 'Exit service script .......'
# ################################################################################################################################################## #
