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

from extra_config_header import *

# ################################################################################################################################################## #
def update_emv_configure_systemd_service_togle(is_start):
    systemd1 = bus.get_object('org.freedesktop.systemd1',  '/org/freedesktop/systemd1')
    manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')
    print 'EMV: Enter update_emv_configure_systemd_service_togle'
    try:
        if is_start:
            command = 'ps -auwx | grep -in "{0}" | grep -v grep'.format(SVC_APP)
            result = get_from_shell(command)
            if result:
                return Error.SUCCESS
            else:   
                manager.RestartUnit('styl-readersvcd.service', 'fail')
                print 'EMV: Start styl-readersvcd.service'
        else:
            manager.StopUnit('styl-readersvcd.service', 'fail')
            print 'EMV: Stop styl-readersvcd.service'
    except:
        return Error.FAIL

    return Error.SUCCESS

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
    checksumer = '{0}/{1}'.format(emv_location, md5_file)

    if not os.path.exists(emv_location) or not os.path.exists(emv_loader) or not os.path.exists(checksumer):
        return Error.FAIL

    is_error = False
    # Start readersvcd service
    if update_emv_configure_systemd_service_togle(True)!=Error.SUCCESS:
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
        try:
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
        except:
            is_error = True

    if not is_error:
        command = '{0}'.format(emv_loader)
        result = bash_command(command)
        print "result is: {0}".format(result)
        if result == 0:
            is_error = False
        else:
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
    led_alert_set_all(LED_COLOR.OFF_COLOR)

    # Check need update EMV configure and do it if needed
    state = check_update_emv_configure(EMV_LOCATION, EMV_FLAG)
    if state:    
        led_alert_set_all(LED_COLOR.RUNNING_COLOR)
        print 'CHECK UPDATE EMV CONFIGURE IS: OK'
        state = update_emv_configure(EMV_LOCATION, EMV_LOAD_CONFIG_SH, MD5_FILE)
        led_alert_do(state, LED.EMV_UPDATE, 'EMV Configure Reload')
        command = 'echo  0 > {0}/{1}'.format(EMV_LOCATION, EMV_FLAG)
        result = exec_command(command)
        os.system('sync')
        led_alert_flicker(LED_COLOR.OFF_COLOR)
    else:
        print 'CHECK UPDATE EMV CONFIGURE IS: NO'

    print 'Exit extra service script .......'
# ################################################################################################################################################## #
