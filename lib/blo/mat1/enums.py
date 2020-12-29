from enum import Enum, IntEnum
from ..binary_io import *


class GXEnum(object):
    enum = IntEnum("PlaceHolder", ["NONE"], start=0)

    def __init__(self, value=0):
        self.value = self.enum(value)

    @classmethod
    def from_array(cls, f, start, i):
        f.seek(start + i)
        return cls.from_file(f)

    @classmethod
    def from_file(cls, f):
        value = read_uint8(f)
        cullmode = cls()
        cullmode.value = cls.enum(value)
        return cullmode

    def write(self, f):
        write_uint8(f, self.value)

    def serialize(self):
        return str(self.value)

    @classmethod
    def deserialize(cls, obj):
        for member in cls.enum:
            if str(member) == obj:
                setting = cls()
                setting.value = member
                return setting

        raise RuntimeError("Not a member of this enum: {0}".format(obj))

    def __eq__(self, other):
        return type(self) == type(other) and self.value == other.value


class GXEnum_4_byte(GXEnum):
    @classmethod
    def from_array(cls, f, start, i):
        f.seek(start + i*4)
        return cls.from_file(f)

    @classmethod
    def from_file(cls, f):
        value = read_uint32(f)
        cullmode = cls()
        cullmode.value = cls.enum(value)
        return cullmode

    def write(self, f):
        write_uint32(f, self.value)


class CullModeSetting(GXEnum_4_byte):
    enum = IntEnum("CullMode", ["NONE", "FRONT", "BACK", "ALL"], start=0)


class ColorSource(GXEnum):
    enum = IntEnum("ColorSource", ["REGISTER", "VERTEX"], start=0)


LIGHTID_ENUMS = []
# Need to generate 256 enums for the 256 possible combinations of light ids 0-7
for i in range(256):
    if i == 0:
        lightid = "NONE"
    else:
        lightid = "LIGHT"

        for j in range(8):
            if i & (1 << j):
                lightid += str(j)
    LIGHTID_ENUMS.append(lightid)


class LightId(GXEnum):
    enum = IntEnum("LightId", LIGHTID_ENUMS, start=0)


class DiffuseFunction(GXEnum):
    enum = IntEnum("DiffuseFunction", ["NONE", "SIGNED", "CLAMP"], start=0)


class J3DAttentuationFunction(GXEnum):
    enum = IntEnum("AttentuationFunction", ["NONE", "SPEC", "NONE_2", "SPOT"], start=0)


if __name__ == "__main__":
    from io import BytesIO

    data = BytesIO()
    data.write(b"\x03")
    data.seek(0)
    setting = CullModeSetting.from_file(data)
    print(setting.value)
    setting.value = CullModeSetting.enum.NONE
    setting.write(data)

    data.seek(0)
    print(data.read())
