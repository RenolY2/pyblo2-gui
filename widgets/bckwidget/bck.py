import struct

BCKFILEMAGIC = b"J3D1bck1"
PADDING = b"This is padding data to align"


def read_uint32(f):
    return struct.unpack(">I", f.read(4))[0]


def read_uint16(f):
    return struct.unpack(">H", f.read(2))[0]


def read_sint16(f):
    return struct.unpack(">h", f.read(2))[0]


def read_uint8(f):
    return struct.unpack(">B", f.read(1))[0]


def read_sint8(f):
    return struct.unpack(">b", f.read(1))[0]


def read_float(f):
    return struct.unpack(">f", f.read(4))[0]


def write_uint32(f, val):
    f.write(struct.pack(">I", val))


def write_uint16(f, val):
    f.write(struct.pack(">H", val))


def write_sint16(f, val):
    f.write(struct.pack(">h", val))


def write_uint8(f, val):
    f.write(struct.pack(">B", val))


def write_sint8(f, val):
    f.write(struct.pack(">b", val))


def write_float(f, val):
    f.write(struct.pack(">f", val))


def write_padding(f, multiple):
    next_aligned = (f.tell() + (multiple - 1)) & ~(multiple - 1)

    diff = next_aligned - f.tell()

    for i in range(diff):
        pos = i % len(PADDING)
        f.write(PADDING[pos:pos + 1])


# Find the start of the sequence seq in the list in_list, if the sequence exists
def find_sequence(in_list, seq):
    matchup = 0
    start = -1

    found = False
    started = False

    for i, val in enumerate(in_list):
        if val == seq[matchup]:
            if not started:
                start = i
                started = True

            matchup += 1
            if matchup == len(seq):
                # start = i-matchup
                found = True
                break
        else:
            matchup = 0
            start = -1
            started = False
    if not found:
        start = -1

    return start


class StringTable(object):
    def __init__(self):
        self.strings = []

    @classmethod
    def from_file(cls, f):
        stringtable = cls()

        start = f.tell()

        string_count = read_uint16(f)
        f.read(2)  # 0xFFFF

        offsets = []

        print("string count", string_count)

        for i in range(string_count):
            hash = read_uint16(f)
            string_offset = read_uint16(f)

            offsets.append(string_offset)

        for offset in offsets:
            f.seek(start + offset)

            # Read 0-terminated string
            string_start = f.tell()
            string_length = 0

            while f.read(1) != b"\x00":
                string_length += 1

            f.seek(start + offset)

            if string_length == 0:
                stringtable.strings.append("")
            else:
                stringtable.strings.append(f.read(string_length).decode("shift-jis"))

        return stringtable

    def hash_string(self, string):
        hash = 0

        for char in string:
            hash *= 3
            hash += ord(char)
            hash = 0xFFFF & hash  # cast to short

        return hash

    def write(self, f):
        start = f.tell()
        f.write(struct.pack(">HH", len(self.strings), 0xFFFF))

        for string in self.strings:
            hash = self.hash_string(string)

            f.write(struct.pack(">HH", hash, 0xABCD))

        offsets = []

        for string in self.strings:
            offsets.append(f.tell())
            f.write(string.encode("shift-jis"))
            f.write(b"\x00")

        end = f.tell()

        for i, offset in enumerate(offsets):
            f.seek(start + 4 + (i * 4) + 2)
            write_uint16(f, offset - start)

        f.seek(end)


def hermite(t, p0, m0, p1, m1):
    return (2*(t**3) - 3*(t**2) + 1)*p0 + \
           ((t**3) - 2*(t**2) + t)*m0 + \
           (-2*(t**3) + 3*(t**2))*p1 + \
           ((t**3) - (t**2))*m1


class AnimComponent(object):
    def __init__(self, time, value, tangentIn, tangentOut=0.0):
        self.time = time
        self.value = value
        self.tangentIn = tangentIn
        self.tangentOut = tangentOut

    def convert_rotation(self, rotscale):
        self.value *= rotscale
        self.tangentIn *= rotscale
        self.tangentOut *= rotscale

    def serialize(self):
        return [self.time, self.value, self.tangentIn, self.tangentOut]

    @classmethod
    def from_array(cls, offset, index, count, valarray, tanType):
        if count == 1:
            return cls(0.0, valarray[offset + index], 0.0, 0.0)

        else:
            if tanType == 0:
                time = valarray[offset + index * 3]
                value = valarray[offset + index * 3 + 1]
                tangent_in = valarray[offset + index * 3 + 2]

                return cls(time, value, tangent_in, tangent_in)
            elif tanType == 1:
                time = valarray[offset + index * 4]
                value = valarray[offset + index * 4 + 1]
                tangent_in = valarray[offset + index * 4 + 2]
                tangent_out = valarray[offset + index * 4 + 3]

                return cls(time, value, tangent_in, tangent_out)
            else:
                raise RuntimeError("unknown tangent type: {0}".format(tanType))


def interpolate(t, frame1: AnimComponent, frame2: AnimComponent):
    assert frame1.time <= t <= frame2.time
    diff = frame2.time - frame1.time
    t_relative = t - frame1.time
    return hermite(t_relative/diff, frame1.value, frame1.tangentOut, frame2.value, frame2.tangentIn)


class JointAnimation(object):
    def __init__(self, jointindex):
        self.jointindex = jointindex

        self.scale = {"X": [], "Y": [], "Z": []}
        self.rotation = {"X": [], "Y": [], "Z": []}
        self.translation = {"X": [], "Y": [], "Z": []}

        self._scale_offsets = {}
        self._rotation_offsets = {}
        self._translation_offsets = {}

    def _get_previous_frame_index(self, field, axis, time):
        assert time >= 0

        for i in range(len(field[axis])-1):
            curr = field[axis][i]
            next = field[axis][i+1]
            if curr.time <= time < next.time:
                return i

        # Return last frame
        return len(field[axis])-1

    def _interpolate_field(self, field, axis, time):
        prev_i = self._get_previous_frame_index(field, axis, time)
        next_i = prev_i+1

        prev_frame = field[axis][prev_i]

        if next_i >= len(field[axis]):
            return prev_frame.value

        next_frame = field[axis][next_i]

        return interpolate(time, prev_frame, next_frame)

    def interpolate(self, time):
        offset_x = self._interpolate_field(self.translation, "X", time)
        offset_y = self._interpolate_field(self.translation, "Z", time)

        scale_x = self._interpolate_field(self.scale, "X", time)
        scale_y = self._interpolate_field(self.scale, "Z", time)

        rotation = self._interpolate_field(self.rotation, "Y", time)
        return offset_x, offset_y, scale_x, scale_y, rotation

    def serialize(self):
        return [self.jointindex, self.scale, self.rotation, self.translation]

    def add_scale(self, axis, scale):
        self.scale[axis].append(scale)

    def add_rotation(self, axis, rotation):
        self.rotation[axis].append(rotation)

    def add_translation(self, axis, translation):
        self.translation[axis].append(translation)

    def add_scale_vec(self, u, v, w):
        self.add_scale("X", u)
        self.add_scale("Y", v)
        self.add_scale("Z", w)

    def add_rotation_vec(self, u, v, w):
        self.add_rotation("X", u)
        self.add_rotation("Y", v)
        self.add_rotation("Z", w)

    def add_translate_vec(self, u, v, w):
        self.add_rotation("X", u)
        self.add_rotation("Y", v)
        self.add_rotation("Z", w)

    def _set_scale_offset(self, axis, val):
        self._scale_offsets[axis] = val

    def _set_rotation_offset(self, axis, val):
        self._rotation_offsets[axis] = val

    def _set_translation_offset(self, axis, val):
        self._translation_offsets[axis] = val


from json import JSONEncoder


class MyEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


class Keyframe(object):
    def __init__(self, time,
                 x=None, y=None, z=None,
                 x_rot=None, y_rot=None, z_rot=None,
                 x_scale=None, y_scale=None, z_scale=None):
        self.time = time
        self.x = x
        self.y = y
        self.z = z
        self.x_rotate = x_rot
        self.y_rotate = y_rot
        self.z_rotate = z_rot
        self.x_scale = x_scale
        self.y_scale = y_scale
        self.z_scale = z_scale


class BCKFile(object):
    def __init__(self):
        self.loop_mode = 0
        self.angle_scale = 0
        self.duration = 0
        self.animations = []

    @classmethod
    def from_file(cls, f):
        header = f.read(8)
        if header != BCKFILEMAGIC:
            raise RuntimeError("Invalid header. Expected {} but found {}".format(BCKFILEMAGIC, header))

        size = read_uint32(f)
        print("Size of btk: {} bytes".format(size))
        sectioncount = read_uint32(f)
        assert sectioncount == 1

        svr_data = f.read(16)

        ttk_start = f.tell()

        ttk_magic = f.read(4)
        ttk_sectionsize = read_uint32(f)

        loop_mode = read_uint8(f)
        anglescale = read_sint8(f)
        duration = read_uint16(f)

        rotScale = (2.0 ** anglescale) * (180.0 / 32768.0)
        jointAnimCount = read_uint16(f)
        scaleFloatCount = read_uint16(f)
        rotationShortsCount = read_uint16(f)
        translateFloatCount = read_uint16(f)
        print(hex(f.tell()))
        jointAnimationEntriesOffset = read_uint32(f) + ttk_start
        scaleFloatsOffset = read_uint32(f) + ttk_start
        rotationShortsOffset = read_uint32(f) + ttk_start
        translateFloatsOffset = read_uint32(f) + ttk_start

        scaleDefault = None
        rotationDefault = None
        translateDefault = None

        scaleFloats = []
        rotationShorts = []
        translateFloats = []

        # Scale value bank
        f.seek(scaleFloatsOffset)
        print("Scale count:", scaleFloatCount, scaleFloatCount)
        for i in range(scaleFloatCount):
            scaleFloats.append(read_float(f))

        # Rotation value bank
        f.seek(rotationShortsOffset)
        for i in range(rotationShortsCount):
            rotationShorts.append(read_sint16(f))

        # Translate value bank
        f.seek(translateFloatsOffset)
        print(hex(translateFloatsOffset), translateFloatCount)

        for i in range(translateFloatCount):
            translateFloats.append(read_float(f))

        animations = []

        f.seek(jointAnimationEntriesOffset)
        for i in range(jointAnimCount):
            jointanim = JointAnimation(i)

            values = struct.unpack(">" + "H" * 27, f.read(0x36))

            x_scale, x_rot, x_trans = values[:3], values[3:6], values[6:9]
            y_scale, y_rot, y_trans = values[9:12], values[12:15], values[15:18]
            z_scale, z_rot, z_trans = values[18:21], values[21:24], values[24:27]
            # Scale
            countX, offsetX, tanTypeX = x_scale
            countY, offsetY, tanTypeY = y_scale
            countZ, offsetZ, tanTypeZ = z_scale
            print("Scale")

            for j in range(countX):
                jointanim.add_scale("X", AnimComponent.from_array(offsetX, j, countX, scaleFloats, tanTypeX))

            for j in range(countY):
                jointanim.add_scale("Y", AnimComponent.from_array(offsetY, j, countY, scaleFloats, tanTypeY))

            for j in range(countZ):
                jointanim.add_scale("Z", AnimComponent.from_array(offsetZ, j, countZ, scaleFloats, tanTypeZ))

            # Rotation
            countX, offsetX, tanTypeX = x_rot
            countY, offsetY, tanTypeY = y_rot
            countZ, offsetZ, tanTypeZ = z_rot

            print("Rotation")
            for j in range(countX):
                comp = AnimComponent.from_array(offsetX, j, countX, rotationShorts, tanTypeX)
                comp.convert_rotation(rotScale)
                jointanim.add_rotation("X", comp)

            for j in range(countY):
                comp = AnimComponent.from_array(offsetY, j, countY, rotationShorts, tanTypeY)
                comp.convert_rotation(rotScale)
                jointanim.add_rotation("Y", comp)

            for j in range(countZ):
                comp = AnimComponent.from_array(offsetZ, j, countZ, rotationShorts, tanTypeZ)
                comp.convert_rotation(rotScale)
                jointanim.add_rotation("Z", comp)

            # Translate
            countX, offsetX, tanTypeX = x_trans
            countY, offsetY, tanTypeY = y_trans
            countZ, offsetZ, tanTypeZ = z_trans

            print("Translation")
            for j in range(countX):
                jointanim.add_translation("X", AnimComponent.from_array(offsetX, j, countX, translateFloats, tanTypeX))

            for j in range(countY):
                jointanim.add_translation("Y", AnimComponent.from_array(offsetY, j, countY, translateFloats, tanTypeY))

            for j in range(countZ):
                jointanim.add_translation("Z", AnimComponent.from_array(offsetZ, j, countZ, translateFloats, tanTypeZ))

            animations.append(jointanim)

        bck = cls()
        bck.loop_mode = loop_mode
        bck.angle_scale = anglescale
        bck.duration = duration
        bck.animations = animations
        return bck


"""    
import json
with open("ma_jump.bck", "rb") as f:
    anims = read_bck(f)
with open("databck.json", "w") as f:
    json.dump(anims, f, cls=MyEncoder, indent=" "*4)"""