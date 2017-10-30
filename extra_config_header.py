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
##  extra_config_header.py : Python script header - consist some define for:                                                    ##
##              - extra_config_runtime.py                                                                                       ##
##              and                                                                                                             ##
##              - extra_config_boottime.py                                                                                      ##
##                                                                                                                              ##
##       Create:    2017-07-06 16:30:00                                                                                         ##
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

# Mount global variable
MOUNT_DIR                   = ".extra_service_tmp_dir"
CHECK_FSTYPE_1              = "OEM-ID \"mkfs.fat\""
CHECK_FSTYPE_2              = "FAT"
CHECK_FSTYPE                = True

# STYLAGPS global variable
STYLAGPS_CONFIG             = "stylagps.conf"
STYLAGPS_LOCATION           = "/etc/stylagps/stylagps.conf"
STYLAGPS_PKGCONFIG          = "stylagps"

# Wireless global variable
WIRELESS_PASSWD             = "wireless.passwd"
CONNECTION_PATH             = None

# EMV global variable
EMV_FLAG                    = "emv_flag"
EMV_CONFIG_DIR              = "emv"
EMV_LOCATION                = "/home/root/emv"
EMV_LOAD_CONFIG_SH          = "emv_load_config.sh"
SVC_APP                     = "/home/root/svc"
USE_SVC_SYSTEMD             = False
MD5_FILE                    = "checksum-md5"
EMV_FLAG_PATH               = "/home/root/emv/update"

# SCANNER global variable
SCANNER_FLAG		    = "scanner_flag"
SCANNER_FLAG_PATH	    = "/home/root/scanner/update"
SCANNER_SETUP_UTILS_PATH    = "/usr/bin"
SCANNER_SETUP_UTILS	    = "StylScannerSetup"

# TestTool global variable
TT_PATTERN                  = "yellowfin_test_tool"
TT_FLAGS_DIR                = "/var"
TT_FLAGS                    = "factorytest.mrk"

# LED global variable
STYL_LED_BOARD_I2C_ADDRESS  = 0x20
PD9535_CONFIG_REG_PORT0     = 0x06
PD9535_CONFIG_REG_PORT1     = 0x07
PD9535_OUT_REG_PORT0        = 0x02
PD9535_OUT_REG_PORT1        = 0x03
PD9535_CONFIG_OUT_PORT      = 0x00

LDCONFIG_TOOL               = "/sbin/ldconfig"

# Some daemon name
SYSTEMD_READER_SVC          = "styl-readersvcd.service"
SYSTEMD_APLAY               = "styl-aplayd.service"
SYSTEMD_TESTTOOL            = "styl-factory-test-tool.service"
SYSTEMD_EXTRASERVICE        = "styl-yellowfin-extra-config-runtime.service"

# Index for DBUS Struct element
# Visit https://www.freedesktop.org/wiki/Software/systemd/dbus/ for more index 
DBUS_STRUCT_NAME            = 0 # The primary unit name as string
DBUS_STRUCT_READABLE        = 1 # The human readable description string
DBUS_STRUCT_LOADSTATE       = 2 # The load state (i.e. whether the unit file has been loaded successfully)
DBUS_STRUCT_ACTIVESTATE     = 3 # The active state (i.e. whether the unit is currently started or not)
DBUS_STRUCT_SUBSTATE        = 4 # The sub state (a more fine-grained version of the active state that is specific to the unit type, which the active state is not)


# Return value class
class Error:
    SUCCESS     = 1
    FAIL        = 2
    NONE        = 3

#   0: OFF
#   1: BLUE
#   2: RED
#   3: PINK
#   4: GREEN
#   5: CYAN
#   6: YELLOW
#   7: WHITE

class LED_COLOR:
    OFF_COLOR     = 0x00
    SUCCESS_COLOR = 0x01        # Blue
    FAILURE_COLOR = 0x02        # Red
    MOUNT_COLOR   = 0x03        # Pink
    OTHER_2_COLOR = 0x04        # Green
    OTHER_1_COLOR = 0x05        # Cyan
    NONE_COLOR    = 0x06        # Yellow
    RUNNING_COLOR = 0x07        # Write

class LED:
    AGPS            = 1
    WIFI            = 2
    EMV             = 3
    EMV_UPDATE      = 4
    TESTTOOL        = 5

# DBUS global variable
bus = dbus.SystemBus()

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

class bcolors:
    HEADER      = '\033[95m'
    OKBLUE      = '\033[94m'
    OKGREEN     = '\033[92m'
    WARNING     = '\033[93m'
    FAIL        = '\033[91m'
    ENDC        = '\033[0m'
    BOLD        = '\033[1m'
    UNDERLINE   = '\033[4m'


def styl_log(string):
    print '[STYL Extra Config Service]: {1}INFO: {0} {2}'.format(string, bcolors.OKGREEN, bcolors.ENDC)

def styl_error(string):
    print '[STYL Extra Config Service]: {1}ERROR: {0} {2}'.format(string, bcolors.FAIL, bcolors.ENDC)

def styl_warning(string):
    print '[STYL Extra Config Service]: {1}ERROR: {0} {2}'.format(string, bcolors.WARNING, bcolors.ENDC)

def styl_debug(string):
    print '[STYL Extra Config Service]: {1}DEBUG: {0} {2}'.format(string, bcolors.OKBLUE, bcolors.ENDC)
    
def find_file_in_path(name, path):
    try:
        for root, dirs, files in os.walk(path):
            if name in files:
                return os.path.join(root, name)
    except:
        return None

def find_dir_in_path(name, path):
    try:
        for root, dirs, files in os.walk(path):
            if name in dirs:
                return os.path.join(root, name)
    except:
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
    try:
        result = subprocess.Popen(command, shell=True, stdout=None, stderr=None)
        return result
    except:
        return None

def bash_command(command):
    try:
        result = subprocess.check_call(['bash', command])
        return result
    except:
        return -101

def checkcall_command(command):
    try:
        result = subprocess.check_call([command])
        return result
    except:
        return -101

# ################################################################################################################################################## #

# ################################################################################################################################################## #
def led_alert_init():
    try:
        ret = msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_CONFIG_REG_PORT0, PD9535_CONFIG_OUT_PORT)
        ret = msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_CONFIG_REG_PORT1, PD9535_CONFIG_OUT_PORT)

    except:
        styl_error('Initialization I2C LED : FAILURED')

def led_alert_flicker(off_color):
    light_value_port0 = -1
    light_value_port1 = -1
    try:
        light_value_port0 = msbus.read_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0);
        light_value_port1 = msbus.read_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT1);

        msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0, off_color)
        msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT1, off_color)
        sleep(0.25)
        msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0, light_value_port0)
        msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT1, light_value_port1)
        sleep(0.25)
        msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0, off_color)
        msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT1, off_color)
        sleep(0.25)
        msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0, light_value_port0)
        msbus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT1, light_value_port1)
        sleep(0.25)
    except:
        styl_error('Flicker I2C LED : FAILURED')

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
        elif light_index == LED.EMV_UPDATE:
            led_alert_set_all(light_color)

    except:
        styl_error('Set light color for I2C LED : FAILURED')

def led_alert_set_all(light_color):
    led_alert_set(LED.AGPS, light_color)
    led_alert_set(LED.WIFI, light_color)
    led_alert_set(LED.EMV , light_color)

def led_alert_do(state, index, string):
    if state == Error.FAIL:
        led_alert_set(index, LED_COLOR.FAILURE_COLOR)
        styl_log('Processing for {0} fail'.format(string))
    elif state == Error.SUCCESS:
        led_alert_set(index, LED_COLOR.SUCCESS_COLOR)
        styl_log('Processing for {0} success'.format(string))
    elif state == Error.NONE:
        led_alert_set(index, LED_COLOR.NONE_COLOR)
        styl_log('Do not anything for {0}'.format(string))

# ################################################################################################################################################## #

# ################################################################################################################################################## #
def library_is_exist(package):
    command = '{0} -p | grep {1} > /dev/null'.format(LDCONFIG_TOOL, package)
    try:
        return os.system(command) == 0
    except:
        return -101
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def svc_check_exist():
    command = 'ps | grep -in "{0}" | grep -v grep'.format(SVC_APP)
    result = get_from_shell(command)
    if result:
        #styl_error('Conflict with '{0}' was already running'.format(SVC_APP))
        return True
    return False
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def execute_testtool_configure_execute(tt_flags, tt_flags_dir, systemd_manager):
    systemd_manager.StartUnit(SYSTEMD_TESTTOOL, 'replace')
    sleep(0.25)
    return Error.SUCCESS
# ################################################################################################################################################## #

# ################################################################################################################################################## #
def execute_testtool_configure_do(tt_flags, tt_flags_dir):
    try:
        systemd1 = bus.get_object('org.freedesktop.systemd1',  '/org/freedesktop/systemd1')
        manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')

        all_service = manager.ListUnits()

        for service_iter in all_service:
            if service_iter[DBUS_STRUCT_NAME] == SYSTEMD_TESTTOOL:
                if service_iter[DBUS_STRUCT_ACTIVESTATE] == "active" and  service_iter[DBUS_STRUCT_SUBSTATE] == "running":
                    styl_log("Ignore Factory Testtool flag because Factory Testtool already was running.")
                    return Error.NONE

        if svc_check_exist():
            for service_iter in all_service:
                if service_iter[DBUS_STRUCT_NAME] == SYSTEMD_READER_SVC:
                    if service_iter[DBUS_STRUCT_ACTIVESTATE] == "active" and  service_iter[DBUS_STRUCT_SUBSTATE] == "running":
                        # if svc is running, will execute factory testool application when svc be executed by styl-readersvcd service (SYSTEMD_READER_SVC)
                        return execute_testtool_configure_execute(tt_flags, tt_flags_dir, manager)                            
            return Error.FAIL
        else:
            # if svc isn't running, will execute factory testool application.
            return execute_testtool_configure_execute(tt_flags, tt_flags_dir, manager)
    except:
        return Error.FAIL
# ################################################################################################################################################## #
