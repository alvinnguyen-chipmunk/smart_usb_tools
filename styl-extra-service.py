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
from pyudev import Context, Monitor
from pyudev.glib import GUDevMonitorObserver as MonitorObserver

MAXTIME = 1
MOUNT_DIR = "/home/alvin/.extra_service_tmp_dir"

CURRENT_DISK = "None"

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

def mount_action(partitions, directory):
    print 'mount_action: partitions:{0}'.format(partitions)
    print 'mount_action: directory:{0}'.format(directory)

    dirlist = []
    number = 0
    for partition in partitions:
        print 'partition iter {0}: {1}'.format(number, partition)
        tmp = '{0}_{1}'.format(MOUNT_DIR, number)
        print 'tmp {0}: {1}'.format(number, tmp)
        dirlist.append(tmp)
        number += 1

    print 'dirlist: {0}'.format(dirlist)

    if os.path.exists(directory):
        return False
    command = 'mkdir -p {0}'.format(directory)
    print 'command:{0}'.format(command)
    result = get_from_shell(command)
    print 'result:{0}'.format(result)
    if result:
        return False
    # Mount part

    return True

def umount_action(partitions, directory):
    print 'unmount_action: device:{0}'.format(partitions)
    print 'unmount_action: directory:{0}'.format(directory)
    command = 'rm -rf {0}'.format(directory)
    print 'command:{0}'.format(command)
    result = get_from_shell(command)
    print 'result:{0}'.format(result)
    if result:
        return False

    return True

def add_device_event():
    timeout = TimeOut(MAXTIME)
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
        timeout = TimeOut(MAXTIME)
        while True:
            print 'alvinnguyen '
            if not timeout.OnTime():
                break

def device_event(observer, action, dev):

    success = True

    print 'Processing for event {0} on dev {1} .....'.format(action, dev)

    if action == 'add':
        print 'dev.device_node:  {0}'.format(dev.device_node)
        partitions = add_device_event()
        print '====> partitions: {0}'.format(partitions)
        if partitions:
            success = mount_action(partitions, MOUNT_DIR)
            if success:
                print '************* MKDIR and MOUNT is OK ****************'
            else:
                print '============== MKDIR and MOUNT is FALSE =============='
            success = umount_action(partitions, MOUNT_DIR)
            if success:
                print '************* RM and UMOUNT is OK ****************'
            else:
                print '============== RM and UMOUNT is FALSE =============='
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
