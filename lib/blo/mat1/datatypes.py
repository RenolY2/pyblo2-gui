from binascii import hexlify, unhexlify
from ..binary_io import *

from .enums import *


class Color(object):
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    @classmethod
    def from_array(cls, f, start, i):
        f.seek(start + i*4)
        return cls.from_file(f)

    @classmethod
    def from_file(cls, f):
        r, g, b, a = read_uint8(f), read_uint8(f), read_uint8(f), read_uint8(f)

        return cls(r, g, b, a)

    def write(self, f):
        write_uint8(f, self.r)
        write_uint8(f, self.g)
        write_uint8(f, self.b)
        write_uint8(f, self.a)

    def serialize(self):
        return [self.r, self.g, self.b, self.a]

    @classmethod
    def deserialize(cls, obj):
        color = cls(*obj)
        return color

    def __eq__(self, other):
        return self.r == other.r and self.g == other.g and self.b == other.b and self.a == other.a

"""
class ChannelControl(object):
    def __init__(self):
        #self.enabled = False
        #self.material_source_color = ColorSource()
        #self.light_mask = LightId()
        #self.diffuse_function = DiffuseFunction()
        #self.attentuation_function = J3DAttentuationFunction()
        #self.ambient_source_color = ColorSource()
        self.unk1 = 0
        self.unk2 = 0

    @classmethod
    def from_file(cls, f):
        channel_control = cls()
        channel_control.unk1 = read_uint8(f)
        channel_control.unk2 = read_uint8(f)
        #channel_control.enabled = read_uint8(f) != 0
        #channel_control.material_source_color = ColorSource.from_file(f)
        #channel_control.light_mask = LightId.from_file(f)
        #channel_control.diffuse_function = DiffuseFunction.from_file(f)
        #channel_control.attentuation_function = J3DAttentuationFunction.from_file(f)
        #channel_control.ambient_source_color = ColorSource.from_file(f)
        #f.read(2) # Padding

        return channel_control

    @classmethod
    def from_array(cls, f, start, i):
        f.seek(start + i * 2)
        return cls.from_file(f)

    def write(self, f):
        #write_uint8(f, int(self.enabled != 0))
        #self.material_source_color.write(f)
        #self.light_mask.write(f)
        #self.diffuse_function.write(f)
        #self.attentuation_function.write(f)
        #self.ambient_source_color.write(f)
        #f.write(b"\xFF\xFF")
        write_uint8(f, self.unk1)
        write_uint8(f, self.unk2)
"""


class UnknownData(object):
    size = 0

    def __init__(self):
        self.data = b""

    @classmethod
    def from_file(cls, f):
        obj = cls()
        obj.data = f.read(cls.size)
        return obj

    @classmethod
    def from_array(cls, f, start, i):
        f.seek(start + i*cls.size)
        return cls.from_file(f)

    def write(self, f):
        assert len(self.data) == self.size
        f.write(self.data)

    def serialize(self):
        return str(hexlify(self.data), encoding="ascii")

    @classmethod
    def deserialize(cls, obj):
        unkobj = cls()
        unkobj.data = unhexlify(obj)
        assert len(unkobj.data) == cls.size
        return unkobj

    def __eq__(self, other):
        #print(self, other)
        assert type(self) == type(other)
        return self.data == other.data


class ChannelControl(UnknownData):
    size = 4


class AlphaChannelControl(UnknownData):
    size = 4
    # Potentially: Only one byte is used by J2D?
    #@classmethod
    #def from_array(cls, f, start, i):
    #    f.seek(start + i * cls.size) <--- maybe? compare newColorChan in pikmin 2
    #    return cls.from_file(f)


class TexCoordInfo(UnknownData):
    size = 0x4  # only 3 bytes used, see newTexCoord


class TevOrder(UnknownData):
    size = 0x4  # 3 bytes used


class TevStage(UnknownData):
    size = 0x14


class Dither(UnknownData):
    size = 0x1


class Blend(UnknownData):
    size = 0x4


class AlphaCompare(UnknownData):
    size = 0x8


class TevKColor(UnknownData):
    size = 0x4


class TevColor(UnknownData): # Signed 10bit color
    size = 0x8


class TevSwapModeTable(UnknownData):
    size = 0x4


class TevSwapMode(UnknownData):
    size = 0x4


class TexMatrix(UnknownData):
    size = 0x24


class FontNumber(UnknownData):
    size = 0x2


class IndirectInitData(UnknownData):
    size = 0x128  # All indirect data
