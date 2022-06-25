from copy import copy, deepcopy
from math import radians, sin, cos
from .binary_io import *
from binascii import hexlify, unhexlify
from .mat1.mat1 import MAT1
from .mat1.datatypes import Color


class Node(object): 
    def __init__(self):
        self.children = []
        self.materials: MAT1 = None
        self.textures = None 

    def print_hierarchy(self, indent=0):
        for child in self.children:
            if isinstance(child, Node):
                child.print_hierarchy(indent+4)
            else:
                print("{0}{1}".format(indent*"-", child.name))
    
    @classmethod
    def from_file(cls, f, materials=None, textures=None):
        node = cls()
        node.materials = materials 
        node.textures = textures

        last = None

        next = peek_id(f)
        while next != b"EXT1":
            if next == b"BGN1":
                f.read(8)

                childnode = Node.from_file(f, node.materials, node.textures)
                last.child = childnode
                for child in childnode.children:
                    child.parent = last

                #node.children.append(childnode)
                last = None
            elif next == b"END1" or next == b"EXT1":
                f.read(8)
                return node 
            elif next == b"TEX1":
                node.textures = TextureNames.from_file(f)
                print("set the tex1", node.textures)
                node.children.append(node.textures)
            elif next == b"FNT1":
                node.children.append(FontNames.from_file(f))
            elif next == b"MAT1":
                print("Set the materials")
                thing = f.tell()
                mat1 = MAT1.from_file(f)
                spot = f.tell()
                f.seek(thing)
                Item.from_file(f)
                print("compare", hex(spot), hex(f.tell()))
                node.materials = mat1#Item.from_file(f)
                node.children.append(node.materials)
                print(len(mat1.materials), "materials")
                #print(mat1.material_names.strings)
            
            elif next == b"PAN2":
                last = Pane.from_file(f)
                node.children.append(last)
            elif next == b"PIC2":
                last = Picture.from_file(f, materials)

                node.children.append(last)
            elif next == b"WIN2":
                last = Window.from_file(f, materials)
                node.children.append(last)
            elif next == b"TBX2":
                last = Textbox.from_file(f, materials)
                node.children.append(last)
            elif not next:
                raise RuntimeError("malformed file?")
            else:
                raise RuntimeError("Unknown: {0}".format(next))
            
            next = peek_id(f)
        
        return node 
    
    def write(self, f):
        count = 0
        for child in self.children:
            """if isinstance(child, Node):
                f.write(b"BGN1")
                write_uint32(f, 8)
                count += child.write(f) + 2
                f.write(b"END1")
                write_uint32(f, 8)
            else:
                count += 1
                child.write(f)"""

            count += 1
            if isinstance(child, Pane):
                child.write(f, self.materials)
            else:
                child.write(f)
            if hasattr(child, "child") and child.child is not None:
                f.write(b"BGN1")
                write_uint32(f, 8)
                if isinstance(child.child, Pane):
                    count += child.child.write(f, self.materials) + 2
                else:
                    count += child.child.write(f) + 2
                
                f.write(b"END1")
                write_uint32(f, 8)

        return count

    def serialize(self):
        result = []
        for child in self.children:
            if isinstance(child, MAT1):
                result.append(child.postprocess_serialize(self.textures))
            else:
                result.append(child.serialize())
                if hasattr(child, "child") and child.child is not None:
                    result.append(child.child.serialize())
        
        return result 
    
    @classmethod 
    def deserialize(cls, obj, materials=None, textures=None):
        node = cls()
        node.textures = textures
        node.materials = materials

        last = None

        for item in obj:
            add_item = True
            if isinstance(item, list):
                bloitem = Node.deserialize(item, node.materials, node.textures)
                last.child = bloitem
                for child in bloitem.children:
                    child.parent = last
                last = None
                add_item = False
            elif item["type"] == "TEX1":
                bloitem = TextureNames.deserialize(item)
                node.textures = bloitem
            elif item["type"] == "FNT1":
                bloitem = FontNames.deserialize(item)
            elif item["type"] == "PAN2":
                bloitem = Pane.deserialize(item)
                last = bloitem
            elif item["type"] == "WIN2":
                bloitem = Window.deserialize(item)
                last = bloitem
            elif item["type"] == "TBX2":
                bloitem = Textbox.deserialize(item)
                last = bloitem
            elif item["type"] == "PIC2":
                bloitem = Picture.deserialize(item)
                matindex = node.materials.get_mat_index(bloitem.material)
                bloitem._material = node.materials.materials[matindex]
                last = bloitem
            elif item["type"] == "MAT1":
                bloitem = MAT1.preprocess_deserialize(item, node.textures)
                node.materials = bloitem
            else:
                raise RuntimeError("Unknown item {0}".format(item["type"]))
            if add_item:
                node.children.append(bloitem)
        
        return node 
    
        
class Item(object):
    def __init__(self, name):
        self.name = name
        self.data = b""

    @classmethod 
    def from_file(cls, f):
        resname = str(f.read(4), "ascii")
        item = cls(resname)
        item.name = resname
        print(resname, "hey")
        size = read_uint32(f)
        item.data = f.read(size-8)
        return item 
    
    def write(self, f):
        f.write(bytes(self.name, "ascii"))
        write_uint32(f, len(self.data) + 8)
        f.write(self.data)
    
    def serialize(self):
        result = {"type": self.name,
                "data": str(hexlify(self.data), encoding="ascii")}
        
        return result 
        
    @classmethod 
    def deserialize(cls, obj):
        item = cls(obj["type"])
        item.data = unhexlify(obj["data"])
        return item 


class Pane(object):
    def __init__(self):
        self.hide = False  # Not a blo feature, hides element in editor only

        self.name = "PAN2"
        self.p_name = "PAN2"
        self.p_enabled = 1
        self.child = None
        self.parent = None
        self.p_anchor = None
        self.p_size_x = None
        self.p_size_y = None
        self.p_scale_x = None
        self.p_scale_y = None
        self.p_offset_x = None
        self.p_offset_y = None
        self.p_rotation = None
        self.p_panename = None
        self.p_secondaryname = None

    def add_child(self, child_pane):
        if self.child is not None:
            self.child.children.append(child_pane)
            child_pane.parent = self
        else:
            self.child = Node()
            self.child.materials = self.parent.child.materials
            self.child.textures = self.parent.child.textures
            self.child.children.append(child_pane)
            child_pane.parent = self

    def copy(self, children=False, parent=None):
        copied = copy(self)
        copied.parent = parent
        if children and self.child is not None:
            copied.child = copy(self.child)
            copied.child.children = [child.copy(children, copied) for child in self.child.children]
        else:
            copied.child = None
        return copied

    @classmethod
    def new(cls):
        pane = cls()

        pane.p_anchor = 0
        pane.p_size_x = 10.0
        pane.p_size_y = 10.0
        pane.p_scale_x = 1.0
        pane.p_scale_y = 1.0
        pane.p_offset_x = 0.0
        pane.p_offset_y = 0.0
        pane.p_rotation = 0.0
        pane.p_panename = "New_Pane"
        pane.p_secondaryname = "        "
        pane.p_unk1 = 0
        pane.p_unk4 = 0.0

        return pane

    @classmethod
    def from_file(cls, f):
        start = f.tell()
        pane = cls()
        pane.p_name = read_name(f)
        if pane.p_name not in ("PAN2", "pan2"):
            raise RuntimeError("Not a PAN2 or pan2 section but {}".format(pane.name))
        size = read_uint32(f)
        assert size == 0x48
        unk = read_uint16(f)
        assert unk == 0x40

        pane.p_unk1 = read_uint16(f)  # 0xA
        pane.p_enabled = read_uint8(f)  # 0xC
        pane.p_anchor = read_uint8(f)  # 0xD
        
        re = f.read(2)
        assert re == b"RE" or re == b"\x00\x00"
        pane.p_panename = f.read(0x8).decode("ascii")
        pane.p_secondaryname = f.read(0x8).decode("ascii")
        #unknown = f.read(0x8)
        #assert unknown == b"\x00"*8
        pane.p_size_x = read_float(f)
        pane.p_size_y = read_float(f)
        pane.p_scale_x = read_float(f)
        pane.p_scale_y = read_float(f)
        unk = read_float(f)
        assert unk == 0.0 
        unk = read_float(f)
        assert unk == 0.0 
        
        pane.p_rotation = read_float(f)
        pane.p_offset_x = read_float(f)
        pane.p_offset_y = read_float(f)
        pane.p_unk4 = read_float(f)
        
        assert f.tell() == start + 0x48
        return pane

    def write(self, f, mat1):
        start = f.tell()
        write_name(f, self.p_name)
        write_uint32(f, 0x48)
        write_uint16(f, 0x40)

        write_uint16(f, self.p_unk1)
        write_uint8(f, self.p_enabled)
        write_uint8(f, self.p_anchor)
        f.write(b"RE")
        f.write(bytes(self.p_panename, encoding="ascii"))
        f.write(bytes(self.p_secondaryname, encoding="ascii"))

        write_float(f, self.p_size_x)
        write_float(f, self.p_size_y)
        write_float(f, self.p_scale_x)
        write_float(f, self.p_scale_y)

        write_float(f, 0.0)
        write_float(f, 0.0)

        write_float(f, self.p_rotation)
        write_float(f, self.p_offset_x)
        write_float(f, self.p_offset_y)
        write_float(f, self.p_unk4)

        assert f.tell() == start + 0x48

    def serialize(self):
        result = {}
        result["type"] = "PAN2"
        result["p_type"] = self.p_name

        for key, val in self.__dict__.items():
            if key.startswith("_"):
                print(key)
                continue

            if key != "name" and key != "p_name" and key != "child" and key != "parent" and key != "widget" and key != "hide":
                if isinstance(val, bytes):
                    raise RuntimeError("hhhe")
                result[key] = val
        return result

    def assign_value(self, src, field):
        self.__dict__[field] = src[field]

    @classmethod
    def deserialize(cls, obj):
        assert "p_type" in obj and obj["p_type"] in ("PAN2", "pan2")
        pane = cls()
        pane.p_name = obj["p_type"]
        pane.assign_value(obj, "p_unk1")
        pane.assign_value(obj, "p_enabled")
        pane.assign_value(obj, "p_anchor")
        pane.assign_value(obj, "p_panename")
        pane.assign_value(obj, "p_secondaryname")
        pane.assign_value(obj, "p_size_x")
        pane.assign_value(obj, "p_size_y")
        pane.assign_value(obj, "p_scale_x")
        pane.assign_value(obj, "p_scale_y")
        pane.assign_value(obj, "p_rotation")
        pane.assign_value(obj, "p_offset_x")
        pane.assign_value(obj, "p_offset_y")
        pane.assign_value(obj, "p_unk4")

        return pane

    def get_anchor_offset(self):
        w, h = self.p_size_x, self.p_size_y
        offset_x = 0.0
        offset_y = 0.0
        if self.p_anchor == 1:  # Center-Top anchor
            offset_x = -w / 2
        elif self.p_anchor == 2:  # Top-Right anchor
            offset_x = -w
        elif self.p_anchor == 3:  # Center-Left anchor
            offset_y = -h / 2
        elif self.p_anchor == 4:  # Center anchor
            offset_x = -w / 2
            offset_y = -h / 2
        elif self.p_anchor == 5:  # Center-right anchor
            offset_x = -w
            offset_y = -h / 2
        elif self.p_anchor == 6:  # Bottom-left anchor
            offset_y = -h
        elif self.p_anchor == 7:  # Center-Bottom anchor
            offset_x = -w / 2
            offset_y = -h
        elif self.p_anchor == 8:  # Bottom-right anchor
            offset_x = -w
            offset_y = -h

        return offset_x, offset_y

    def _get_middle_panespace(self):
        if self.p_anchor == 1:
            middle_x = 0
            middle_y = +self.p_size_y/2.0
        elif self.p_anchor == 2:
            middle_x = -self.p_size_x / 2.0
            middle_y = +self.p_size_y / 2.0
        elif self.p_anchor == 3:
            middle_x = +self.p_size_x / 2.0
            middle_y = 0
        elif self.p_anchor == 4:
            middle_x = 0
            middle_y = 0
        elif self.p_anchor == 5:
            middle_x = 0-self.p_size_x / 2.0
            middle_y = 0
        elif self.p_anchor == 6:
            middle_x = +self.p_size_x / 2.0
            middle_y = -self.p_size_y / 2.0
        elif self.p_anchor == 7:
            middle_x = 0
            middle_y = -self.p_size_y / 2.0
        elif self.p_anchor == 8:
            middle_x = -self.p_size_x / 2.0
            middle_y = -self.p_size_y / 2.0
        else:
            middle_x = +self.p_size_x / 2.0
            middle_y = +self.p_size_y / 2.0

        return middle_x, middle_y

    def _get_middle(self):
        middle_x, middle_y = self._get_middle_panespace()
        alpha = radians(-self.p_rotation)
        new_middle_x = middle_x*cos(alpha) - middle_y*sin(alpha)
        new_middle_y = middle_x*sin(alpha) + middle_y*cos(alpha)

        return new_middle_x+self.p_offset_x, new_middle_y+self.p_offset_y

    def _set_middle(self, middle_x, middle_y):
        offsetx, offsety = self._get_middle_panespace()
        alpha = radians(-self.p_rotation)
        new_offset_x = offsetx * cos(alpha) - offsety * sin(alpha)
        new_offset_y = offsetx * sin(alpha) + offsety * cos(alpha)
        self.p_offset_x = middle_x - new_offset_x
        self.p_offset_y = middle_y - new_offset_y

    def resize(self, diff_x, diff_y, diff_x_box, diff_y_box):
        middle_x, middle_y = self._get_middle()

        middle_x = middle_x + diff_x/2.0
        middle_y = middle_y + diff_y/2.0

        #self.p_offset_x += diff_x#/2.0
        #self.p_offset_y += diff_y#/2.0
        # side_x = 1 for "right resize", side_x = -1 for "left resize"
        # side_y = 1 for "up resize", side_y = -1 for "bottom resize" (in coordinate system where +y is up and -y is down)
        self.p_size_x += diff_x_box
        self.p_size_y += diff_y_box

        self._set_middle(middle_x, middle_y)


# Draw a window: 4 corner elements + side and one filling material
class Window(Pane):
    def __init__(self):
        super().__init__()
        self.name = "WIN2"

    def copy(self, children=False, parent=None):
        copied = copy(self)
        copied.parent = parent
        copied.subdata = deepcopy(self.subdata)
        if children:
            copied.child = self.child.copy(children, copied)
        return copied

    @classmethod
    def new(cls):
        window = super(Window, cls).new()
        window.name = "WIN2"
        window.size = 0
        window.padding = b"\xFF"*8

        window.subdata = [{}, {}, {}, {}]
        for i in range(4):
            window.subdata[i]["material"] = ""
            window.subdata[i]["sub_unk2"] = 0
            window.subdata[i]["sub_unk3"] = 0

        window.unkbyte1 = 0
        window.unkbyte2 = 0
        window.unk3 = 0
        window.unk4 = 0
        window.unk5 = 0
        window.unk6 = 0
        window.unk7 = 0
        window.material = -1

        return window

    @classmethod
    def from_file(cls, f, mat1):
        start = f.tell()
        name = read_name(f)
        size = read_uint32(f)
        assert size == 0x90

        if name != "WIN2":
            raise RuntimeError("Not a WIN2 section")

        window = super(Window, cls).from_file(f)
        window.name = name

        window.size = read_uint16(f)
        reserved = f.read(6)
        assert reserved == b"RESERV" or reserved == b"\x00"*7
        window.padding = str(hexlify(f.read(8)), encoding="ascii")#.decode("ascii", errors="backslashreplace")
        #assert window.padding == "\xFF"*8
        window.subdata = [{}, {}, {}, {}]
        for i in range(4):
            mat_index = read_uint16(f)
            window.subdata[i]["material"] = mat1.materials[mat_index].name

        window.unkbyte1 = read_uint8(f)
        window.unkbyte2 = read_uint8(f)
        window.unk3 = read_uint16(f)
        window.unk4 = read_uint16(f)
        window.unk5 = read_uint16(f)
        window.unk6 = read_uint16(f)
        window.unk7 = read_uint16(f)
        mat_index = read_uint16(f)
        window.material = mat1.materials[mat_index].name
        
        re = f.read(2)
        assert re == b"RE" or re == b"\x00\x00"
        
        for i in range(4):
            window.subdata[i]["sub_unk2"] = read_uint16(f)
        for i in range(4):
            window.subdata[i]["sub_unk3"] = read_uint32(f)
        assert f.tell() == start+0x90
        return window 

    def write(self, f, mat1):
        start = f.tell()
        write_name(f, self.name)
        write_uint32(f, 0x90)
        super().write(f, mat1) # Write pane
        write_uint16(f, self.size)

        f.write(b"RESERV")
        f.write(unhexlify(self.padding))
        assert len(unhexlify(self.padding)) == 8
        for i in range(4):
            index = mat1.get_mat_index(self.subdata[i]["material"])
            write_int16(f, index)

        write_uint8(f, self.unkbyte1)
        write_uint8(f, self.unkbyte2)
        write_uint16(f, self.unk3)
        write_uint16(f, self.unk4)
        write_uint16(f, self.unk5)
        write_uint16(f, self.unk6)
        write_uint16(f, self.unk7)
        index = mat1.get_mat_index(self.subdata[i]["material"])
        write_int16(f, index)

        f.write(b"RE")

        for i in range(4):
            write_uint16(f, self.subdata[i]["sub_unk2"])

        for i in range(4):
            write_uint32(f, self.subdata[i]["sub_unk3"])

        assert f.tell() == start + 0x90

    def serialize(self):
        result = super().serialize()
        result["type"] = "WIN2"
        
        return result 

    @classmethod
    def deserialize(cls, obj):
        assert "type" in obj and obj["type"] == "WIN2"
        window = super(Window, cls).deserialize(obj)

        window.assign_value(obj, "size")
        window.assign_value(obj, "padding")
        window.assign_value(obj, "subdata")
        window.assign_value(obj, "unkbyte1")
        window.assign_value(obj, "unkbyte2")
        window.assign_value(obj, "unk3")
        window.assign_value(obj, "unk4")
        window.assign_value(obj, "unk5")
        window.assign_value(obj, "unk6")
        window.assign_value(obj, "unk7")
        window.assign_value(obj, "material")

        return window


# Draw a texture in the GUI
class Picture(Pane):
    def __init__(self):
        super().__init__()
        self.name = "PIC2"

    def copy(self, children=False, parent=None):
        copied = copy(self)
        copied.parent = parent
        copied.color1 = deepcopy(self.color1)
        copied.color2 = deepcopy(self.color2)

        if children and self.child is not None:
            copied.child = self.child.copy(children, copied)
        return copied

    @classmethod
    def new(cls):
        picture = super(Picture, cls).new()
        picture.name = "PIC2"
        picture.size = 0
        picture.unk_index = 0
        picture.material = 0
        picture._material = None

        color1 = {}
        color2 = {}

        color1["unk1"] = 0
        color1["unk2"] = 0
        color2["unk1"] = 0
        color2["unk2"] = 0

        color1["unknowns"] = [0 for x in range(4)]
        color2["unknowns"] = [0 for x in range(4)]
        color1["col1"] = [0 for x in range(4)]
        color1["col2"] = [0 for x in range(4)]
        color2["col1"] = [0 for x in range(4)]
        color2["col2"] = [0 for x in range(4)]

        picture.color1 = color1
        picture.color2 = color2

        return picture

    @classmethod
    def from_file(cls, f, mat1):
        start = f.tell()
        name = read_name(f)
        size = read_uint32(f)
        if name != "PIC2":
            raise RuntimeError("Not a PIC2 section: {}".format(name))
        picture = super(Picture, cls).from_file(f)
        picture.name = name

        picture.size = read_uint16(f)
        picture.unk_index = read_uint16(f)
        mat_index = read_uint16(f)
        picture.material = mat1.materials[mat_index].name
        picture._material = mat1.materials[mat_index]

        re = f.read(2)
        assert re == b"RE" or re == b"\x00\x00"
        color1 = {}
        color2 = {}
        
        color1["unk1"] = read_uint16(f)
        color1["unk2"] = read_uint16(f)
        color2["unk1"] = read_uint16(f)
        color2["unk2"] = read_uint16(f)
        
        color1["unknowns"] = [read_uint16(f) for x in range(4)]
        color2["unknowns"] = [read_uint16(f) for x in range(4)]
        color1["col1"] = [read_uint8(f) for x in range(4)]
        color1["col2"] = [read_uint8(f) for x in range(4)]
        color2["col1"] = [read_uint8(f) for x in range(4)]
        color2["col2"] = [read_uint8(f) for x in range(4)]
        
        picture.color1 = color1 
        picture.color2 = color2 
        
        assert f.tell() == start+0x80
        return picture 

    def write(self, f, mat1):
        start = f.tell()
        write_name(f, self.name)
        write_uint32(f, 0x80)
        super().write(f, mat1)  # Write pane
        write_uint16(f, self.size)
        write_uint16(f, self.unk_index)
        write_uint16(f, mat1.get_mat_index(self.material))
        f.write(b"RE")
        write_uint16(f, self.color1["unk1"])
        write_uint16(f, self.color1["unk2"])
        write_uint16(f, self.color2["unk1"])
        write_uint16(f, self.color2["unk2"])

        for x in range(4):
            write_uint16(f, self.color1["unknowns"][x])
        for x in range(4):
            write_uint16(f, self.color2["unknowns"][x])

        for x in range(4):
            write_uint8(f, self.color1["col1"][x])
        for x in range(4):
            write_uint8(f, self.color1["col2"][x])
        for x in range(4):
            write_uint8(f, self.color2["col1"][x])
        for x in range(4):
            write_uint8(f, self.color2["col2"][x])

        assert f.tell() == start + 0x80

    def serialize(self):
        result = super().serialize()
        result["type"] = "PIC2"
        
        return result

    @classmethod
    def deserialize(cls, obj):
        assert "type" in obj and obj["type"] == "PIC2"
        window = super(Picture, cls).deserialize(obj)

        window.assign_value(obj, "size")
        window.assign_value(obj, "unk_index")
        window.assign_value(obj, "material")
        window.assign_value(obj, "color1")
        window.assign_value(obj, "color2")

        return window


# Create text. Requires a material with font and an initialized font.
class Textbox(Pane):
    def __init__(self):
        super().__init__()
        self.name = "TBX2"

    def copy(self, children=False, parent=None):
        copied = copy(self)
        copied.parent = parent
        copied.color_top = deepcopy(self.color_top)
        copied.color_bottom = deepcopy(self.color_bottom)

        if children:
            copied.child = self.child.copy(children, copied)
        return copied

    @classmethod
    def new(cls):
        textbox = super(Textbox, cls).new()
        textbox.size = 0
        textbox.unk1 = 0
        textbox.material = 0
        textbox.signedunk3 = 0
        textbox.signedunk4 = 0
        textbox.unk5 = 0
        textbox.unk6 = 0
        textbox.unk7byte = 0
        textbox.unk8byte = 0
        textbox.color_top = Color(0, 0, 0, 0)
        textbox.color_bottom = Color(0, 0, 0, 0)
        textbox.unk11 = 0
        textbox.text_cutoff = 0
        textbox.text = ""

        return textbox

    @classmethod
    def from_file(cls, f, mat1):
        start = f.tell()
        name = read_name(f)
        size = read_uint32(f)

        if name != "TBX2":
            raise RuntimeError("Not a TBX2 section")
        textbox = super(Textbox, cls).from_file(f)

        textbox.size = read_uint16(f)
        textbox.unk1 = read_uint16(f)
        mat_index = read_uint16(f)
        textbox.material = mat1.materials[mat_index].name
        textbox._material = mat1.materials[mat_index]

        textbox.signedunk3 = read_int16(f)
        textbox.signedunk4 = read_int16(f)
        textbox.unk5 = read_uint16(f)
        textbox.unk6 = read_uint16(f)
        textbox.unk7byte = read_uint8(f)
        textbox.unk8byte = read_uint8(f)
        textbox.color_top = Color.from_file(f)
        textbox.color_bottom = Color.from_file(f)
        textbox.unk11 = read_uint8(f)
        res = f.read(3)
        assert res == b"RES" or res == b"\x00\x00\x00"
        textbox.text_cutoff = read_uint16(f)
        stringlength = read_uint16(f)
        assert f.tell() == start+0x70
        textbox.text = f.read(stringlength).decode("shift_jis_2004")
        f.seek(start+size)
        return textbox

    def write(self, f, mat1):
        start = f.tell()
        write_name(f, self.name)
        write_uint32(f, 0x70)
        super().write(f, mat1)

        write_uint16(f, self.size)
        write_uint16(f, self.unk1)
        write_uint16(f, mat1.get_mat_index(self.material))
        write_int16(f, self.signedunk3)
        write_int16(f, self.signedunk4)
        write_uint16(f, self.unk5)
        write_uint16(f, self.unk6)
        write_uint8(f, self.unk7byte)
        write_uint8(f, self.unk8byte)
        self.color_top.write(f)  #write_uint32(f, self.unk9)
        self.color_bottom.write(f)  #write_uint32(f, self.unk10)
        write_uint8(f, self.unk11)
        f.write(b"RES")
        write_uint16(f, self.text_cutoff)

        text = bytes(self.text, encoding="shift_jis_2004")
        write_uint16(f, len(text))
        assert f.tell() == start + 0x70
        f.write(text)
        #f.write(b"\x00")
        write_pad(f, 8)
        curr = f.tell()
        f.seek(start+4)
        write_uint32(f, curr-start)
        f.seek(curr)
    
    def serialize(self):
        result = super().serialize()
        result["type"] = "TBX2"
        result["color_top"] = self.color_top.serialize()
        result["color_bottom"] = self.color_bottom.serialize()

        return result

    @classmethod
    def deserialize(cls, obj):
        assert "type" in obj and obj["type"] == "TBX2"
        window = super(Textbox, cls).deserialize(obj)

        window.assign_value(obj, "size")
        window.assign_value(obj, "unk1")
        window.assign_value(obj, "material")
        window.assign_value(obj, "signedunk3")
        window.assign_value(obj, "signedunk4")
        window.assign_value(obj, "unk5")
        window.assign_value(obj, "unk6")
        window.assign_value(obj, "unk7byte")
        window.assign_value(obj, "unk8byte")
        #window.assign_value(obj, "unk9")
        window.color_top = Color.deserialize(obj["color_top"])  #window.assign_value(obj, "unk10")
        window.color_bottom = Color.deserialize(obj["color_bottom"])
        window.assign_value(obj, "unk11")
        window.assign_value(obj, "text_cutoff")

        window.assign_value(obj, "text")

        return window


class ResourceReference(Item):
    def __init__(self):
        super().__init__(self.ResName())
        self.references = []
    
    @staticmethod
    def ResName():
        raise RuntimeError("Implement this!")
        
    @classmethod
    def from_file(cls, f):
        start = f.tell()
        if f.read(4) != bytes(cls.ResName(), encoding="ascii"):
            raise RuntimeError("Not a {0} section".format(cls.ResName()))
        resreference = cls()
        size = read_uint32(f)
        
        rescount = read_uint16(f)
        idk = read_uint16(f)
        assert idk == 0xFFFF 
        headersize = read_uint32(f)
        assert headersize == 0x10
        
        restart = f.tell()
        
        rescount2 = read_uint16(f)
        assert rescount == rescount2 
        
        for i in range(rescount):
            f.seek(restart + 2 + i*2)
            offset = read_uint16(f)
            
            f.seek(restart + offset)
            unk = read_uint8(f)
            length = read_uint8(f)
            assert unk == 0x2 
            name = str(f.read(length), "shift_jis_2004")
            
            resreference.references.append(name)
            
        f.seek(start+size)
        return resreference

    def write(self, f):
        start = f.tell()
        f.write(bytes(self.ResName(), encoding="ascii"))
        f.write(b"ABCD")
        write_uint16(f, len(self.references))
        f.write(b"\xFF\xFF")
        write_uint32(f, 0x10)
        offsets = {}
        namestart = f.tell()
        write_uint16(f, len(self.references))
        f.write(b"\xAB\xCD"*len(self.references))
        #write_pad(f, 2)

        for ref in self.references:
            if ref not in offsets:
                offsets[ref] = f.tell()-namestart
                write_uint8(f, 0x2)
                write_uint8(f, len(ref))
                f.write(bytes(ref, encoding="shift_jis_2004"))
                #write_pad(f, 4)
        write_pad(f, 0x20)
        curr = f.tell()
        f.seek(namestart+2)
        for ref in self.references:
            offset = offsets[ref]
            write_uint16(f, offset)


        f.seek(start+4)
        write_uint32(f, curr-start)
        f.seek(curr)

    def serialize(self):
        result = {"type": self.ResName()}
        result["references"] = self.references 
        
        return result

    @classmethod
    def deserialize(cls, obj):
        res = cls()
        assert obj["type"] == cls.ResName()
        res.references = obj["references"]
        return res


class TextureNames(ResourceReference):
    @staticmethod
    def ResName():
        return "TEX1"


class FontNames(ResourceReference):
    @staticmethod
    def ResName():
        return "FNT1"
    

class Information(object):
    def __init__(self, width, height):
        self.width = width 
        self.height = height 
        self.val1 = self.val2 = self.val3 = self.val4 = 0
    
    @classmethod 
    def from_file(cls, f):
        if f.read(4) != b"INF1":
            raise RuntimeError("Not an INF1 section!")
        
        size = read_uint32(f)
        assert size == 0x20
        width = read_uint16(f)
        height = read_uint16(f)
        inf = cls(width, height)
        inf.val1 = read_uint8(f)
        inf.val2 = read_uint8(f)
        inf.val3 = read_uint8(f)
        inf.val4 = read_uint8(f)
        f.read(size-0x10) # Padding
        
        return inf 
    
    def write(self, f):
        f.write(b"INF1")
        write_uint32(f, 0x20)
        write_uint16(f, self.width)
        write_uint16(f, self.height)
        write_uint8(f, self.val1)
        write_uint8(f, self.val2)
        write_uint8(f, self.val3)
        write_uint8(f, self.val4)
        write_pad(f, 0x20)
        
    def serialize(self):
        result = {}
        result["type"] = "INF1"
        result["width"] = self.width 
        result["height"] = self.height 
        result["values"] = [self.val1, self.val2, self.val3, self.val4]
        
        return result 
        
    @classmethod
    def deserialize(cls, obj):
        assert obj["type"] == "INF1"
        info = cls(obj["width"], obj["height"])
        info.val1 = obj["values"][0]
        info.val2 = obj["values"][1]
        info.val3 = obj["values"][2]
        info.val4 = obj["values"][3]
        
        return info 
        
        
class ScreenBlo(object):
    def __init__(self):
        self.root = Node()
        self.info = Information(640, 480)
    
    def print_hierarchy(self):
        print("INF1 - {0} {1}".format(self.info.width, self.info.height))
        self.root.print_hierarchy(4)

    def find_elements_that_use_material(self, material, node=None):
        if node is None:
            node = self.root

        elements = []

        for child in node.children:
            if isinstance(child, (Window, )):
                if material.name in (
                    child.material,
                    child.subdata[0]["material"], child.subdata[1]["material"],
                    child.subdata[2]["material"], child.subdata[3]["material"]
                ):
                    elements.append(child.p_panename)
            elif isinstance(child, (Picture, )):
                if child.material == material.name:
                    elements.append(child.p_panename)
            elif isinstance(child, (Textbox, )):
                if child.material == material.name:
                    elements.append(child.p_panename)
            if isinstance(child, (Window, Picture, Textbox, Pane)) and child.child is not None:
                elements.extend(self.find_elements_that_use_material(material, child.child))

        return elements




    @classmethod 
    def from_file(cls, f):
        magic = f.read(8)
        if magic != b"SCRNblo2":
            raise RuntimeError("Unsupported magic: {0}".format(magic))
        
        total_size = read_uint32(f)
        count = read_uint32(f)
        
        svr = f.read(0x10) # ignored
        
        blo = cls()
        blo.info = Information.from_file(f)
        
        blo.root = Node.from_file(f)

        return blo

    def write(self, f):
        start = f.tell()
        f.write(b"SCRNblo2")
        f.write(b"ABCD0123")  # placeholder for size + count
        f.write(b"SVR1")
        f.write(b"\xFF"*12)

        self.info.write(f)
        count = self.root.write(f)
        f.write(b"EXT1")
        write_uint32(f, 0x8)
        write_pad(f, 0x20)
        curr = f.tell()

        f.seek(0x8)
        write_uint32(f, curr-start)
        write_uint32(f, count+2)  # Add in INF and EXT section
        f.seek(curr)

    def serialize(self):
        result = []
        result.append(self.info.serialize())
        result.append(self.root.serialize())
        
        return result

    @classmethod
    def deserialize(cls, obj):
        blo = cls()
        assert obj[0]["type"] == "INF1"
        blo.info = Information.deserialize(obj[0])
        blo.root = Node.deserialize(obj[1])

        return blo


if __name__ == "__main__":
    """
    pane = Pane()
    pane.p_offset_x = 0
    pane.p_offset_y = 0
    pane.p_size_x = 150
    pane.p_size_y = 100

    for i in range(9):
        pane.p_anchor = 1
        x, y = pane._get_middle()
        pane._set_middle(x, y)

        print(pane.p_offset_x, pane.p_offset_y)

    """
    import json 
    import sys
    inputfile = sys.argv[1]
    if len(sys.argv) > 2:
        outfile = sys.argv[2]
    else:
        outfile = None

    if inputfile.endswith(".blo"):
        if outfile is None:
            outfile = inputfile+".json"
        with open(inputfile, "rb") as f:
            blo = ScreenBlo.from_file(f)

        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(blo.serialize(), f, indent=4, ensure_ascii=False)

    elif inputfile.endswith(".json"):
        if outfile is None:
            outfile = inputfile+".blo"
        with open(inputfile, "r", encoding="utf-8") as f:
            blo = ScreenBlo.deserialize(json.load(f))

        with open(outfile, "wb") as f:
            blo.write(f)


    """inputfile = "cave_pikmin.blo"
    #inputfile = "courseselect_under.blo"
    #inputfile = "anim_text.blo"
    outputfile = inputfile + ".json"
    with open(inputfile, "rb") as f:
    #with open("anim_text.blo", "rb") as f:
    #with open("challenge_modo_1p_2p.blo", "rb") as f:
    #with open("cave_pikmin.blo", "rb") as f:
        blo = ScreenBlo.from_file(f)
    blo.print_hierarchy()
    #with open("texnames.txt", "w") as f:
    #    for name in blo.root.children[0].references:
    #        f.write(name)
    #        f.write("\n")
            
    result = blo.serialize()
    with open(outputfile, "w") as f:
        json.dump(result, f, indent=4)

    with open(inputfile+"_2.blo", "wb") as f:
        blo.write(f)

    with open(outputfile, "r") as f:
        data = json.load(f)
        blo = ScreenBlo.deserialize(data)

    with open(outputfile+"_2.json", "w") as f:
        json.dump(blo.serialize(), f, indent=4)

    with open(inputfile+"_3.blo", "wb") as f:
        blo.write(f)

    with open(inputfile+"_2.blo", "rb") as f:
        newblo = ScreenBlo.from_file(f)

    with open(inputfile + "_4.blo", "wb") as f:
        newblo.write(f)

    with open(inputfile + "_4.blo.json", "w") as f:
        json.dump(newblo.serialize(), f, indent=4)
    """
    """with open(inputfile, "rb") as f:
        f.seek(0x20)
        for i in range(0xA4):
            da = Item.from_file(f)"""