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
##  extra_config_boottime.py : Python script will be execute by script on /etc/profile                                          ##
##              - Check flags of EMV configure reload                                                                           ##
##              - If the flags is enable                                                                                        ##
##                  + Update EMV configure files                                                                                ##
##              - LED alert for working result                                                                                  ##
##                                                                                                                              ##
##       Create:    2017-08-15 10:00:00                                                                                         ##
##       Modified:  2017-11-02 17:30:00                                                                                         ##
##       Author:    Alvin Nguyen (alvin.nguyen@styl.solutions)                                                                  ##
##                                                                                                                              ##
##################################################################################################################################

from extra_config_header import *

start_svc = False
# ################################################################################################################################################## #
def systemd_workaround():
    try:
        systemd1 = bus.get_object('org.freedesktop.systemd1',  '/org/freedesktop/systemd1')
        manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')
        
        manager.StopUnit(SYSTEMD_TESTTOOL, 'replace')
        manager.StopUnit(SYSTEMD_READER_SVC, 'replace')
        manager.StopUnit(SYSTEMD_APLAY, 'replace')
        
        styl_log('Systemd workaround done.')
    except:
        styl_error('Systemd workaround FAIL.')

# ################################################################################################################################################## #

# ################################################################################################################################################## #
def update_emv_configure_systemd_service_togle(is_start):
    global start_svc
    systemd1 = bus.get_object('org.freedesktop.systemd1',  '/org/freedesktop/systemd1')
    manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')
    try:
        if is_start:
            command = 'ps | grep -in "{0}" | grep -v grep'.format(SVC_APP)
            result = get_from_shell(command)
            if result:
                styl_error('Conflict with {0} was already running'.format(SVC_APP))
                return Error.FAIL
            else:
                start_svc = True
                manager.RestartUnit(SYSTEMD_READER_SVC, 'replace')
                
            manager.StopUnit(SYSTEMD_EXTRASERVICE, 'replace')
        else:
            
            if start_svc:
                manager.StopUnit(SYSTEMD_READER_SVC, 'replace')

            manager.RestartUnit(SYSTEMD_EXTRASERVICE, 'replace')
    except:
        return Error.FAIL
    
    sleep(1)

    return Error.SUCCESS

def check_running_setup_scanner(scanner_flag_path, scanner_flag):
    if not scanner_flag_path or not scanner_flag:
        return False;

    scanner_checker = '{0}/{1}'.format(scanner_flag_path, scanner_flag)
    if not os.path.exists(scanner_checker):
        return False
    try:
        lines = [line.rstrip('\n') for line in open(scanner_checker)]
        if len(lines)!=1:
            return False
        if lines[0] == '1':
            return True
    except:
        return False
    return False

def setup_scanner_auto_mode(scanner_utils_path, scanner_utils):
    if not scanner_utils_path or not scanner_utils:
        return Error.FAIL

    scanner_setup = '{0}/{1}'.format(scanner_utils_path, scanner_utils)
    if not os.path.exists(scanner_setup):
        return Error.FAIL

    command = '{0}'.format(scanner_setup)
    result = executable_command(command)
    styl_log('Scanner setup result: {0}'.format(result))
    if result == 0:
        return Error.SUCCESS
    else:
        return Error.FAIL

def check_update_emv_configure(emv_location, emv_flag):
    if not emv_location or not emv_flag:
        return False

    emv_checker = '{0}/{1}'.format(emv_location, emv_flag)

    if not os.path.exists(emv_location) or not os.path.exists(emv_checker):
        return False
    try:
        lines = [line.rstrip('\n') for line in open(emv_checker)]
        if len(lines)!=1:
            return False

        if lines[0] == '1':
            return True
    except:
        return False
    return False	

def update_emv_configure(emv_location, emv_load_config_sh, md5_file):
    if not emv_location or not emv_load_config_sh or not md5_file:
        return Error.FAIL

    emv_loader = '{0}/{1}'.format(emv_location, emv_load_config_sh)
    checksumer = '{0}/{1}'.format(emv_location, md5_file)

    if not os.path.exists(emv_location) or not os.path.exists(emv_loader) or not os.path.exists(checksumer):
        return Error.FAIL

    # Start readersvcd service
    if update_emv_configure_systemd_service_togle(True)!=Error.SUCCESS:
        return Error.FAIL

    is_error = False

    #verify checksum
    try:
        os.chdir(emv_location)    
        lines = [line.rstrip('\n') for line in open(md5_file)]
        for line in lines:
            elements = re.findall(r"[\w'.]+", line)
            # Correct original md5 goes here
            original_md5 = elements[0]
            file_name = elements[1]
            try:
                with open(file_name) as file_to_check:
                    # read contents of the file
                    data = file_to_check.read()
                    # pipe contents of the file through
                    md5_returned = hashlib.md5(data).hexdigest()
                if original_md5 == md5_returned:
                    styl_log("MD5 verified.")
                else:
                    styl_log("MD5 verification failed!.")
                    is_error = True
            except:
                is_error = True
    except:
        is_error = True

    if not is_error:
        command = '{0}'.format(emv_loader)
        result = bash_command(command)
        if result == 0:
            is_error = False
        else:
            is_error = True

    if not is_error:
        return Error.SUCCESS
    else:
        return Error.FAIL
# ################################################################################################################################################## #

# ################################################################################################################################################## #
if __name__ == '__main__':
    styl_log('Start extra service script .......')

    # Initialization I2C LED
    led_alert_init()
    led_alert_set_all(LED_COLOR.RUNNING_COLOR)
    systemd_workaround()

    # Check need update EMV configure and do it if needed
    state = check_update_emv_configure(EMV_LOCATION, EMV_FLAG)
    if state:        
        styl_log('EMV configure update flag: enable')
        state = update_emv_configure(EMV_LOCATION, EMV_LOAD_CONFIG_SH, MD5_FILE)
        # Stop readersvcd service
        update_emv_configure_systemd_service_togle(False)
        command = 'echo  0 > {0}/{1}'.format(EMV_LOCATION, EMV_FLAG)
        result = exec_command(command)
        os.system('sync')
        led_alert_done(state, LED.EMV, 'EMV Configure Reload')
    else:
        styl_log('EMV configure update flag: disable')

    # Check need run STYL Setup Scanner
    state = check_running_setup_scanner(SCANNER_FLAG_PATH, SCANNER_FLAG)
    if state:
        styl_log('Scanner configure update flag: enable')
        state = setup_scanner_auto_mode(SCANNER_SETUP_UTILS_PATH, SCANNER_SETUP_UTILS)        
        # Clear flag
        command = 'echo  0 > {0}/{1}'.format(SCANNER_FLAG_PATH, SCANNER_FLAG)
        result = exec_command(command)
        os.system('sync')
        led_alert_done(state, LED.SCANNER, 'Scanner Setup')
    else:
        styl_log('Scanner configure update flag: disable')

    # Check flag file for factory testool
    if find_file_in_path(TT_FLAGS, TT_FLAGS_DIR):
        state = execute_testtool_configure_do(TT_FLAGS, TT_FLAGS_DIR)
        led_alert_done(state, LED.TESTTOOL, 'Factory Testtool Execute')
    else:
        styl_log('Factory Testtool was executed before.')    

    led_alert_flash(LED_COLOR.OFF_COLOR, LED_COLOR.RUNNING_COLOR)
    led_alert_set_all(LED_COLOR.OFF_COLOR)
    styl_log('Exit extra service script .......')
# ################################################################################################################################################## #
