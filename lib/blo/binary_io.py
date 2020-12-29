import struct 


def read_name(f):
    return str(f.read(4), "ascii")


def write_name(f, name):
    if len(name) != 4:
        raise RuntimeError("Name length not 4")
    f.write(bytes(name, encoding="ascii"))


def read_uint32(f):
    return struct.unpack(">I", f.read(4))[0]


def read_uint16(f):
    return struct.unpack(">H", f.read(2))[0]
    
    
def read_int16(f):
    return struct.unpack(">h", f.read(2))[0]


def read_int16_at(f, offset):
    f.seek(offset)
    return struct.unpack(">h", f.read(2))[0]

    
def read_uint8(f):
    return struct.unpack(">B", f.read(1))[0]

    
def read_uint8_at(f, offset):
    f.seek(offset)
    return struct.unpack(">B", f.read(1))[0]
    
    
def read_int8_at(f, offset):
    f.seek(offset)
    return struct.unpack(">B", f.read(1))[0]


def read_float(f):
    return struct.unpack(">f", f.read(4))[0]


def peek_id(f):
    out = f.peek(4)
    return out[:4]
    
    
def write_uint32(f, val):
    f.write(struct.pack(">I", val))
    
    
def write_uint16(f, val):
    f.write(struct.pack(">H", val))


def write_int16(f, val):
    f.write(struct.pack(">h", val))


def write_uint8(f, val):
    f.write(struct.pack(">B", val))


def write_int8(f, val):
    f.write(struct.pack(">b", val))


def write_int16_at(f, val, offset):
    f.seek(offset)
    f.write(struct.pack(">h", val))


def write_int8_at(f, val, offset):
    f.seek(offset)
    f.write(struct.pack(">b", val))

    
def write_float(f, val):
    f.write(struct.pack(">f", val))


padding_msg = b"This is padding data to align"


def write_pad(f, multiple):
    next_aligned_pos = (f.tell() + (multiple-1)) & ~(multiple-1)

    for i in range(next_aligned_pos - f.tell()):
        f.write(padding_msg[i%len(padding_msg):i%len(padding_msg)+1])
    #f.write(b"\x00"*(next_aligned_pos - f.tell()))
