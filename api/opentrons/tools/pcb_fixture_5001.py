'''
Script for running on the 5001-stepper-driver PCBA testing fixture

Runs on a Raspberry-Pi, and uses the Opentrons API to test PCBA functionality

Requirements:
 - Must place a Smoothieware HEX file on the R-Pi's flash drive
 - Must have OT2 button connected
 - Must have pre-flashed pipette PCBA connected to the I2C testing points
 - Must have motors connected to the X and Y axes only (not the ZABC axes)
'''


import glob
import os
import subprocess

from opentrons import robot
from opentrons.drivers.rpi_drivers import gpio
from opentrons.tools.factory_test import test_smoothie_gpio, run_quiet_process


def _get_firmware_file_path():
    filepath = '/mnt/usbdrive/*.hex'
    files = list(glob.glob(filepath))
    if len(files):
        return files[0]
    else:
        raise Exception('No HEX file found')


def upload_firmware():
    robot._driver.simulating = False
    robot._driver._smoothie_programming_mode()
    if robot._driver._connection:
        robot._driver._connection.close()
    port_name = '/dev/ttyAMA0'  # this should never change
    baudrate = 115200
    file_name = _get_firmware_file_path()
    # run lpc21isp, THIS WILL TAKE AROUND 1 MINUTE TO COMPLETE
    update_cmd = 'lpc21isp -wipe -donotstart {0} {1} {2} 12000'.format(
        file_name, port_name, baudrate)
    res = subprocess.check_output(update_cmd, shell=True)
    if not res:
        raise Exception('Failed running lpc21isp')
    res = [l for l in res.decode().split('\n') if l]
    if 'Download Finished...' not in res[-1]:
        raise Exception('lpc21isp error: {}'.format(res[-1]))


def test_smoothie_gpio():

    from opentrons.drivers import serial_communication
    from opentrons.drivers.smoothie_drivers.driver_3_0 import SMOOTHIE_ACK

    def _write_and_return(msg):
        return serial_communication.write_and_return(
            msg + '\r\n\r\n',
            SMOOTHIE_ACK,
            robot._driver._connection,
            timeout=1)

    robot.connect()
    d = robot._driver
    # make sure the driver is currently working as expected
    version_response = _write_and_return('version')
    if 'version' not in version_response:
        raise Exception('Failed connecting to Smoothie')

    [_write_and_return('version') for i in range(10)]
    data = [_write_and_return('version') for i in range(100)]
    if len(set(data)) > 2:
        raise Exception('Failed data-loss test')

    d._connection.reset_input_buffer()
    # drop the HALT line LOW, and make sure there is an error state
    d._smoothie_hard_halt()

    old_timeout = int(d._connection.timeout)
    d._connection.timeout = 1  # 1 second
    r = d._connection.readline().decode()
    if 'ALARM' not in r:
        raise Exception('Failed HALT line test')

    d._reset_from_error()
    d._connection.timeout = old_timeout

    # drop the ISP line to LOW, and make sure it is dead
    d._smoothie_programming_mode()
    failed_isp = False
    try:
        _write_and_return('M999')
        failed_isp = True
    except Exception:
        pass
    if failed_isp:
        raise Exception('Failed ISP line test')

    # toggle the RESET line to LOW, and make sure it is NOT dead
    d._smoothie_reset()
    r = _write_and_return('M119')
    if 'X_max' not in r:
        raise Exception('Failed RESET line test')


def test_motors_move():
    robot.connect()
    port = robot._driver._connection
    port.reset_input_buffer()

    # GIVE ALL AXES THE SAME SETTINGS
    # steps/mm
    port.write(b'M92 X80 Y80 Z80 A80 B160 C160 M400r\n\r\n')
    # acceleration
    port.write(b'M204 S10000 X2000 Y2000 Z2000 A2000 B2000 C2000 M400\r\n\r\n')
    # speeds
    port.write(b'G0 F20000 M203.1 X200 Y200 Z200 A200 B200 C200 M400\r\n\r\n')
    port.reset_input_buffer()

    # X AXIS
    # no current
    port.write(b'M907 X0.0 Y0.0 Z0.0 A0.0 B0.0 C0.0 G4 P0.05 M400\r\n\r\n')
    port.reset_input_buffer()
    port.write(b'G91 G0 X400 M400\r\n\r\n')
    port.reset_input_buffer()
    # full current
    port.write(b'M907 X2.0 Y2.0 Z2.0 A2.0 B2.0 C2.0 G4 P0.05 M400\r\n\r\n')
    port.reset_input_buffer()
    port.write(b'G91 G0 X400 M400\r\n\r\n')
    port.reset_input_buffer()

    # Y AXIS
    # no current
    port.write(b'M907 X0.0 Y0.0 Z0.0 A0.0 B0.0 C0.0 G4 P0.05 M400\r\n\r\n')
    port.reset_input_buffer()
    port.write(b'G91 G0 Y400 M400\r\n\r\n')
    port.reset_input_buffer()
    # full current
    port.write(b'M907 X2.0 Y2.0 Z2.0 A2.0 B2.0 C2.0 G4 P0.05 M400\r\n\r\n')
    port.reset_input_buffer()
    port.write(b'G91 G0 Y400 M400\r\n\r\n')
    port.reset_input_buffer()

    # disable motors (while still at 2.0 amps!!)
    port.write(b'M18 M400\r\n\r\n')
    port.reset_input_buffer()


def test_pipette_reads():
    # read from either left or right pipettes, and assert we got some data
    robot.connect()
    right = robot._driver.read_pipette_model('right')
    left = robot._driver.read_pipette_model('left')
    if not right and not left:
        raise Exception('No Pipette Found!')


def wait_for_button_press():
    # wait for the button to be let go of
    while robot._driver.read_button():
        pass
    # wait for the button to be pressed again
    while not robot._driver.read_button():
        pass
    robot._driver._set_button_light(red=False, green=False, blue=True)


def main():
    wait_for_button_press()
    upload_firmware()
    test_smoothie_gpio()    
    test_pipette_reads()
    test_motors_move()
    print('PASS')
    robot._driver._set_button_light(red=False, green=True, blue=False)


if __name__ == "__main__":
    robot._driver._set_button_light(red=True, green=True, blue=True)
    while True:
        try:
            main()
        except KeyboardInterrupt:
            exit()
        except Exception as e:
            print('FAIL')
            robot._driver._set_button_light(red=True, green=False, blue=False)
            print(e)
