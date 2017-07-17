#!/usr/bin/python

import smbus

# 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
bus = smbus.SMBus(0)

STYL_LED_BOARD_I2C_ADDRESS = 0x20

PD9535_CONFIG_REG_PORT0 = 0x06
PD9535_CONFIG_REG_PORT1 = 0x07

PD9535_OUT_REG_PORT0 = 0x02
PD9535_OUT_REG_PORT1 = 0x03

PD9535_CONFIG_OUT_PORT = 0x00

YELLOW_COLOR = 0x01


def StylLedInit():
    ret = False
    ret = bus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_CONFIG_REG_PORT0, PD9535_CONFIG_OUT_PORT)
    print ret
    ret = bus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_CONFIG_REG_PORT1, PD9535_CONFIG_OUT_PORT)
    print ret

def StylLedSetSingle():

    # LED 1
    CurrentPortVal = bus.read_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0)
    CurrentPortVal = (CurrentPortVal & 0x00F8) | YELLOW_COLOR

    retval = bus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0, CurrentPortVal)

    # LED 2
    CurrentPortVal = bus.read_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0)
    CurrentPortVal = (CurrentPortVal & 0x00C7) | (YELLOW_COLOR << 3)

    retval = bus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT0, CurrentPortVal)

    # LED 3
    CurrentPortVal = bus.read_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT1)
    CurrentPortVal = (CurrentPortVal & 0x00F8) | YELLOW_COLOR;

    retval = bus.write_byte_data(STYL_LED_BOARD_I2C_ADDRESS, PD9535_OUT_REG_PORT1, CurrentPortVal)

if __name__ == '__main__':
    print 'Start service script .......'

    StylLedInit()

    StylLedSetSingle()

    print 'Exit service script .......'
