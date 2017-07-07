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
import glib
import os
import re
import subprocess
import dbus, uuid
from time import sleep
from pyudev import Context, Monitor
from pyudev.glib import GUDevMonitorObserver as MonitorObserver

MAXTIME = 10
MOUNT_DIR = "/home/alvin/.extra_service_tmp_dir"

STYLAGPS_CONFIG = "stylagps.conf"
STYLAGPS_LOCATION = "/etc/stylagps/stylagps.conf"

WIRELESS_PASSWD = "wireless.passwd"

class TimeOut:
    def __init__(self, deadtime):
        self.timeout = time.time() + deadtime

    def OnTime(self):
        if time.time() > self.timeout:
            return False
        else:
            return True

# Used as a quick way to handle shell commands #
def get_from_shell_raw(command):
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.stdout.readlines()

def get_from_shell(command):
    result = get_from_shell_raw(command)
    for i in range(len(result)):
        result[i] = result[i].strip() # strip out white space #
    return result

def update_geolocation_key(directorys, stylagps_config, stylagps_location):
    if not directorys and not stylagps_config and not stylagps_location:
        return False

    for directory in directorys:
        path = '{0}/{1}'.format(directory, stylagps_config)
        print 'Path is: {0}'.format(path)
        if os.path.isfile(path):
            print 'Found on: {0}'.format(path)
            command = 'sudo cp {0} {1}'.format(path, stylagps_location)
            print 'command 1:{0}'.format(command)
            result = get_from_shell(command)
            print 'result:{0}'.format(result)
            if not result:
                return True
            else:
                return False
    return False

def update_wireless_passwd_connection_new(ssid_string, psk_string):
    s_con = dbus.Dictionary({
    'type': '802-11-wireless',
    'uuid': str(uuid.uuid4()),
    'id': ssid_string})

    s_wifi = dbus.Dictionary({
    'ssid': dbus.ByteArray(ssid_string),
    'mode': 'infrastructure'})

    s_wsec = dbus.Dictionary({
    'key-mgmt': 'wpa-psk',
    'auth-alg': 'open',
    'psk': psk_string})

    s_ip4 = dbus.Dictionary({'method': 'auto'})
    s_ip6 = dbus.Dictionary({'method': 'ignore'})

    con = dbus.Dictionary({
    'connection': s_con,
    '802-11-wireless': s_wifi,
    '802-11-wireless-security': s_wsec,
    'ipv4': s_ip4,
    'ipv6': s_ip6})

    bus = dbus.SystemBus()

    proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/Settings")
    settings = dbus.Interface(proxy, "org.freedesktop.NetworkManager.Settings")

    settings.AddConnection(con)

def update_wireless_passwd_file_parse(path):
    lines = [line.rstrip('\n') for line in open(path)]

    for line in lines:
        print 'line is: {0}'.format(line)
        elements = line.split(":")
        for element in elements:
            print 'element is: {0}'.format(element)
        update_wireless_passwd_connection_new(elements[0], elements[1])


def update_wireless_passwd(directorys, wireless_passwd):
    if not directorys:
        return False

    for directory in directorys:
        path = '{0}/{1}'.format(directory, wireless_passwd)
        print 'Path is: {0}'.format(path)
        if os.path.isfile(path):
            print 'Found on: {0}'.format(path)
            ret = update_wireless_passwd_file_parse(path)
            return ret

    return False


def mount_action(partitions, directory):
    print 'mount_action: partitions:{0}'.format(partitions)
    print 'mount_action: directory:{0}'.format(directory)

    directorys = []
    number = 0
    for partition in partitions:
        print 'partition iter {0}: {1}'.format(number, partition)
        directory = '{0}_{1}'.format(MOUNT_DIR, number)
        print 'directory {0}: {1}'.format(number, directory)
        command = 'mkdir -p {0}'.format(directory)
        print 'command 1:{0}'.format(command)
        result = get_from_shell(command)
        print 'result:{0}'.format(result)
        if not result:
            command = 'sudo mount {0} {1}'.format(partition, directory)
            print 'command 2:{0}'.format(command)
            result = get_from_shell(command)
            print 'result:{0}'.format(result)
            if not result and os.path.ismount(directory):
                print 'directorys 1:{0}'.format(directorys)
                directorys.append(directory)
                print 'directorys 2:{0}'.format(directorys)
        number += 1

    print 'OK ===> directorys: {0}'.format(directorys)

    return directorys

def umount_action(partitions, directorys):
    print 'unmount_action: partitions:{0}'.format(partitions)
    print 'unmount_action: directorys:{0}'.format(directorys)

    for partition in partitions:
        print 'partition: {0}'.format(partition)
        command = 'sudo umount {0}'.format(partition)
        print 'command 1:{0}'.format(command)
        result = get_from_shell(command)
        print 'result:{0}'.format(result)

    for directory in directorys:
        print 'directory: {0}'.format(directory)
        command = 'rm -rf {0}'.format(directory)
        print 'command 1:{0}'.format(command)
        result = get_from_shell(command)
        print 'result:{0}'.format(result)

def add_device_event():
    timeout = TimeOut(MAXTIME)
    sleep(3) # sleep waiting USB driver do completed
    while True:
        removable = [device for device in context.list_devices(subsystem='block', DEVTYPE='disk') if device.attributes.asstring('removable') == "1"]
        if removable or not timeout.OnTime():
            break
    print 'removable:{0}'.format(removable)
    for device in removable:
        print 'device:{0}'.format(device)
        print 'device.device_node:{0}'.format(device.device_node)
        timeout = TimeOut(MAXTIME)
        while True:
            partitions = [device.device_node for device in context.list_devices(subsystem='block', DEVTYPE='partition', parent=device)]
            if partitions or not timeout.OnTime():
                break
        print 'partitions 2:{0}'.format(partitions)
        print("All removable partitions: {}".format(", ".join(partitions)))

        return partitions
    return None

def remove_device_event():
    print 'remove usb'

def device_event(observer, action, dev):

    success = True

    print 'Processing for event {0} on dev {1} .....'.format(action, dev)

    if action == 'add':
        #print 'dev.device_node:  {0}'.format(dev.device_node)
        #print 'dev.sys_number:  {0}'.format(dev.sys_number)
        #print 'dev.sys_name:  {0}'.format(dev.sys_name)
        #print 'dev.context:  {0}'.format(dev.context)
        #print 'dev.sys_path:  {0}'.format(dev.sys_path)
        #print 'dev.device_number:  {0}'.format(dev.device_number)
        #print 'dev.device_links:  {0}'.format(dev.device_links)
        #print 'dev.device_type:  {0}'.format(dev.device_type)
        #print 'dev.children:  {0}'.format(dev.children)
        check = dev.device_type
        print 'check:  {0}'.format(check)
        if check != 'usb_interface':
            return

        partitions = add_device_event()
        print '====> partitions: {0}'.format(partitions)
        if partitions:

            # Mount partitions on USB device #
            directorys = mount_action(partitions, MOUNT_DIR)

            # Search and update for Google geolocation API key
            success = update_geolocation_key(directorys, STYLAGPS_CONFIG, STYLAGPS_LOCATION)
            if success:
                print 'Update Google geolocation API key success'
            else:
                print 'Update Google geolocation API key fail'

            # Search and update for Wireless password
            success = update_wireless_passwd(directorys, WIRELESS_PASSWD)
            if success:
                print 'Update Wireless password success'
            else:
                print 'Update Wireless password fail'

            tmp = raw_input('Press any key to continue: ')

            umount_action(partitions, directorys)
        else:
            print 'Nothing to do'

    if action == 'remove':
        remove_device_event()

    print 'Processing for event {0} on dev {1} .... Done.'.format(action, dev)


if __name__ == '__main__':
    print 'Start service script .......'

    context = Context()
    monitor = Monitor.from_netlink(context)

    monitor.filter_by(subsystem='usb')
    observer = MonitorObserver(monitor)

    observer.connect('device-event', device_event)
    monitor.start()

    glib.MainLoop().run()

    print 'Exit service script .......'
