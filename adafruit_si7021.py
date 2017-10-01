# The MIT License (MIT)
#
# Copyright (c) 2017 Radomir Dopieralski for Adafruit Industries.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
``adafruit_si7021``
===================

This is a CircuitPython driver for the SI7021 temperature and humidity sensor.

"""


from micropython import const
try:
    import struct
except:
    import ustruct as struct

import sys

from adafruit_bus_device.i2c_device import I2CDevice


HUMIDITY = const(0xf5)
TEMPERATURE = const(0xf3)
_RESET = const(0xfe)
_READ_USER1 = const(0xe7)
_USER1_VAL = const(0x3a)


def _crc(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for i in range(8):
            if crc & 0x80:
                crc <<= 1
                crc ^= 0x131
            else:
                crc <<= 1
    return crc


class SI7021:
    """
    A driver for the SI7021 temperature and humidity sensor.
    """

    def __init__(self, i2c, address=0x40):
        self.i2c_device = I2CDevice(i2c, address)
        self.init()
        self._measurement = 0

    def init(self):
        self.reset()
        # Make sure the USER1 settings are correct.
        while True:
            # While restarting, the sensor doesn't respond to reads or writes.
            try:
                data = bytearray([_READ_USER1])
                with self.i2c_device as i2c:
                    i2c.write(data, stop=False)
                    i2c.read_into(data)
                value = data[0]
            except OSError as e:
                if e.args[0] not in ('I2C bus error', 19): # errno 19 ENODEV
                    raise
            else:
                break
        if value != _USER1_VAL:
            raise RuntimeError("bad USER1 register (%x!=%x)" % (
                value, _USER1_VAL))

    def _command(self, command):
        with self.i2c_device as i2c:
            i2c.write(struct.pack('B', command))

    def _data(self):
        data = bytearray(3)
        data[0] = 0xff
        while True:
            # While busy, the sensor doesn't respond to reads.
            try:
                with self.i2c_device as i2c:
                    i2c.read_into(data)
            except OSError as e:
                if e.args[0] not in ('I2C bus error', 19): # errno 19 ENODEV
                    raise
            else:
                if data[0] != 0xff: # Check if read succeeded.
                    break
        value, checksum = struct.unpack('>HB', data)
        if checksum != _crc(data[:2]):
            raise ValueError("CRC mismatch")
        return value

    def reset(self):
        self._command(_RESET)

    @property
    def relative_humidity(self):
        """The measured relative humidity in percents."""
        self.start_measurement(HUMIDITY)
        value = self._data()
        self._measurement = 0
        return value * 125 / 65536 - 6

    @property
    def temperature(self):
        """The measured temperature in degrees Celcius."""
        self.start_measurement(TEMPERATURE)
        value = self._data()
        self._measurement = 0
        return value * 175.72 / 65536 - 46.85

    def start_measurement(self, what):
        """
        Starts a measurement.

        Starts a measurement of either ``HUMIDITY`` or ``TEMPERATURE``
        depending on the ``what`` argument. Returns immediately, and the
        result of the measurement can be retrieved with the
        ``temperature`` and ``relative_humidity`` properties. This way it
        will take much less time.

        This can be useful if you want to start the measurement, but don't
        want the call to block until the measurement is ready -- for instance,
        when you are doing other things at the same time.
        """
        if what not in (HUMIDITY, TEMPERATURE):
            raise ValueError()
        if not self._measurement:
            self._command(what)
        elif self._measurement != what:
            raise RuntimeError("other measurement in progress")
        self._measurement = what
