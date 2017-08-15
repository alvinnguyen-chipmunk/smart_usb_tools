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
##  yellowfin-extra-bootup.py : Python script will be execute by script on /etc/profile                                         ##
##              - Check flags of EMV configure reload                                                                           ##
##              - If the flags is enable                                                                                        ##
##                  + Update EMV configure files                                                                                ##
##              - LED alert for working result                                                                                  ##
##                                                                                                                              ##
##       Create:    2017-08-15 10:00:00                                                                                         ##
##       Modified:  --                                                                                                          ##
##       Author:    Alvin Nguyen (alvin.nguyen@styl.solutions)                                                                  ##
##                                                                                                                              ##
##################################################################################################################################

import pyudev
import os
import subprocess
import dbus, uuid
import hashlib, re
import smbus
import time
from time import sleep
from pyudev import Context, Monitor

TIMEOUT_VALUE = 30

class TimeOut:
    def __init__(self, deadtime):
        self.timeout = time.time() + deadtime

    def OnTime(self):
        if time.time() > self.timeout:
            return False
        else:
            return True

# EMV global variable
EMV_FLAG                    = "emv_flag"
EMV_CONFIG_DIR              = "emv"
EMV_LOCATION                = "/home/root/emv"
EMV_LOAD_CONFIG_SH          = "emv_load_config.sh"
SVC_APP                     = "svc"
USE_SVC_SYSTEMD             = False
MD5_FILE                    = "checksum-md5"
EMV_FLAG_PATH               = "/home/root/emv/update"

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
    STARTED_COLOR = 0x04
    MOUNT_COLOR   = 0x05
    NONE_COLOR    = 0x06
    RUNNING_COLOR = 0x07

class LED:
    AGPS     = 1
    WIFI     = 2
    EMV      = 3
    TESTTOOL = 4

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

def exec_command(command):
    result = subprocess.Popen(command, shell=True, stdout=None, stderr=None)
    return result

def bash_command(command):
    try:
        result = subprocess.check_call(['bash', command])
        return result
    except:
        return -1

def checkcall_command(command):
    try:
        result = subprocess.check_call([command])
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
    global USE_SVC_SYSTEMD
    systemd1 = bus.get_object('org.freedesktop.systemd1',  '/org/freedesktop/systemd1')
    manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')
    print 'EMV: Enter update_emv_configure_systemd_service_togle'
    try:
        if is_start:
            command = 'ps auwx | grep -in "{0}" | grep -v grep'.format(SVC_APP)
            result = get_from_shell(command)
            if not result:
                USE_SVC_SYSTEMD = True
                manager.RestartUnit('styl-readersvcd.service', 'fail')
                print 'EMV: Start styl-readersvcd.service'
        else:
            if USE_SVC_SYSTEMD:
                manager.StopUnit('styl-readersvcd.service', 'fail')
                USE_SVC_SYSTEMD = False
                print 'EMV: Stop styl-readersvcd.service'
    except:
        return False

    return True

def check_update_emv_configure(emv_location, emv_flag):
    if not emv_location or not emv_flag:
        return False

    emv_checker = '{0}/{1}'.format(emv_location, emv_flag)

    if not os.path.exists(emv_location) or not os.path.exists(emv_checker):
        return False

    lines = [line.rstrip('\n') for line in open(emv_checker)]
    if len(lines)!=1:
        return False

    if lines[0] == '1':
        return True

    return False


def update_emv_configure(emv_location, emv_load_config_sh, md5_file):
    if not emv_location or not emv_load_config_sh or not md5_file:
        return Error.FAIL

    emv_loader = '{0}/{1}'.format(emv_location, emv_load_config_sh)

    if not os.path.exists(emv_location) or not os.path.exists(emv_loader):
        return Error.FAIL

    is_error = False
    # Start readersvcd service
    if not update_emv_configure_systemd_service_togle(True):
        return Error.FAIL

    #verify checksum
    os.chdir(emv_location)
    lines = [line.rstrip('\n') for line in open(md5_file)]
    for line in lines:
        elements = re.findall(r"[\w'.]+", line)
        print 'len(elements): {0}'.format(len(elements))
        print 'elements[0]: {0}'.format(elements[0])
        print 'elements[1]: {0}'.format(elements[1])
        # Correct original md5 goes here
        original_md5 = elements[0]
        file_name = elements[1]
        with open(file_name) as file_to_check:
                # read contents of the file
                data = file_to_check.read()
                # pipe contents of the file through
                md5_returned = hashlib.md5(data).hexdigest()
        if original_md5 == md5_returned:
                print "MD5 verified."
        else:
                print "MD5 verification failed!."
                is_error = True

    if not is_error:
        command = '{0}'.format(emv_loader)
        result = bash_command(command)
        if result == '0':
            is_error = True

    # Stop readersvcd service
    update_emv_configure_systemd_service_togle(False)

    if not is_error:
        return Error.SUCCESS
    else:
        return Error.FAIL
# ################################################################################################################################################## #

# ################################################################################################################################################## #
if __name__ == '__main__':
    print 'Start extra service script .......'

    # Initialization I2C LED
    led_alert_init()
    led_alert_set_all(LED_COLOR.STARTED_COLOR)

    # Check need update EMV configure and do it if needed
    state = check_update_emv_configure(EMV_LOCATION, EMV_FLAG)
    if state:
	# Initialization I2C LED
        led_alert_init()
        led_alert_set_all(LED_COLOR.RUNNING_COLOR)
        print 'CHECK UPDATE EMV CONFIGURE IS: OK'
        state = update_emv_configure(EMV_LOCATION, EMV_LOAD_CONFIG_SH, MD5_FILE)
        led_alert_set_all(LED_COLOR.NONE_COLOR)
        led_alert_do(state, LED.EMV, 'EMV Configure')
        command = 'echo  0 > {0}/{1}'.format(EMV_LOCATION, EMV_FLAG)
        result = exec_command(command)
        print 'ECHO result: {0}'.format(result)
    else:
        print 'CHECK UPDATE EMV CONFIGURE IS: NO'

    print 'Exit extra service script .......'
# ################################################################################################################################################## #
