# SPDX-FileCopyrightText: 2017 Radomir Dopieralski for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Version of adafruit_register classes that account for the read
and write registers being different
"""

try:
    from typing import Optional, Type
except ImportError:
    pass


# pylint: disable=too-many-arguments
class _RWDifferentBit:
    def __init__(
        self,
        read_register_address: int,
        write_register_address: int,
        bit: int,
        register_width: int = 1,
        lsb_first: bool = True,
    ) -> None:
        self._read_register = read_register_address
        self._write_register = write_register_address
        self.bit_mask = 1 << (bit % 8)  # the bitmask *within* the byte!
        self.buffer = bytearray(1 + register_width)
        if lsb_first:
            self.byte = bit // 8 + 1  # the byte number within the buffer
        else:
            self.byte = register_width - (bit // 8)  # the byte number within the buffer

    def __get__(
        self,
        obj: "adafruit_si7021.SI7021",
        objtype: Optional[Type["adafruit_si7021.SI7021"]] = None,
    ) -> bool:
        self.buffer[0] = self._read_register
        with obj.i2c_device as i2c:
            i2c.write_then_readinto(self.buffer, self.buffer, out_end=1, in_start=1)
        return bool(self.buffer[self.byte] & self.bit_mask)

    def __set__(self, obj: "adafruit_si7021.SI7021", value: bool) -> None:
        self.buffer[0] = self._read_register
        with obj.i2c_device as i2c:
            i2c.write_then_readinto(self.buffer, self.buffer, out_end=1, in_start=1)
            if value:
                self.buffer[self.byte] |= self.bit_mask
            else:
                self.buffer[self.byte] &= ~self.bit_mask
            self.buffer[0] = self._write_register
            i2c.write(self.buffer)


# pylint: disable=too-many-arguments
class _RWDifferentBits:
    def __init__(  # pylint: disable=too-many-arguments
        self,
        num_bits: int,
        read_register_address: int,
        write_register_address: int,
        lowest_bit: int,
        register_width: int = 1,
        lsb_first: bool = True,
        signed: bool = False,
    ) -> None:
        self.bit_mask = ((1 << num_bits) - 1) << lowest_bit
        # print("bitmask: ",hex(self.bit_mask))
        if self.bit_mask >= 1 << (register_width * 8):
            raise ValueError("Cannot have more bits than register size")
        self._read_register = read_register_address
        self._write_register = write_register_address
        self.lowest_bit = lowest_bit
        self.buffer = bytearray(1 + register_width)
        self.lsb_first = lsb_first
        self.sign_bit = (1 << (num_bits - 1)) if signed else 0

    def __get__(
        self,
        obj: "adafruit_si7021.SI7021",
        objtype: Optional[Type["adafruit_si7021.SI7021"]] = None,
    ) -> int:
        self.buffer[0] = self._read_register
        with obj.i2c_device as i2c:
            i2c.write_then_readinto(self.buffer, self.buffer, out_end=1, in_start=1)
        # read the number of bytes into a single variable
        reg = 0
        order = range(len(self.buffer) - 1, 0, -1)
        if not self.lsb_first:
            order = reversed(order)
        for i in order:
            reg = (reg << 8) | self.buffer[i]
        reg = (reg & self.bit_mask) >> self.lowest_bit
        # If the value is signed and negative, convert it
        if reg & self.sign_bit:
            reg -= 2 * self.sign_bit
        return reg

    def __set__(self, obj: "adafruit_si7021.SI7021", value: int):
        self.buffer[0] = self._read_register
        value <<= self.lowest_bit  # shift the value over to the right spot
        with obj.i2c_device as i2c:
            i2c.write_then_readinto(self.buffer, self.buffer, out_end=1, in_start=1)
            reg = 0
            order = range(len(self.buffer) - 1, 0, -1)
            if not self.lsb_first:
                order = range(1, len(self.buffer))
            for i in order:
                reg = (reg << 8) | self.buffer[i]
            # print("old reg: ", hex(reg))
            reg &= ~self.bit_mask  # mask off the bits we're about to change
            reg |= value  # then or in our new value
            # print("new reg: ", hex(reg))
            for i in reversed(order):
                self.buffer[i] = reg & 0xFF
                reg >>= 8
            self.buffer[0] = self._write_register
            i2c.write(self.buffer)
