import struct
from ..binary_io import *
from .enums import *
from .datatypes import *


class StringTable(object):
    def __init__(self):
        self.strings = []
    
    @classmethod
    def from_file(cls, f):
        stringtable = cls()
        
        start = f.tell()
        
        string_count = read_uint16(f)
        f.read(2) # 0xFFFF
        
        offsets = []
        
        for i in range(string_count):
            hash = read_uint16(f)
            string_offset = read_uint16(f)
            
            offsets.append(string_offset)
        
        for offset in offsets:
            f.seek(start+offset)
            
            # Read 0-terminated string 
            string_start = f.tell()
            string_length = 0
            
            while f.read(1) != b"\x00":
                string_length += 1 
            
            f.seek(start+offset)
            
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
            f.seek(start+4 + (i*4) + 2)
            write_uint16(f, offset-start)

        f.seek(end)

    def serialize(self):
        return self.strings

    @classmethod
    def deserialize(cls, obj):
        stringtable = cls()
        stringtable.strings = obj

        return stringtable


def get_index_or_add(array, value):
    if value is None:
        return -1
    elif value in array:
        return array.index(value)
    else:
        array.append(value)
        return len(array)-1


def deserialize_array(array, func):
    result = []
    for item in array:
        if item is None:
            result.append(item)
        else:
            result.append(func(item))

    return result


def read_index_array(f, offset, size, count):
    values = []
    read_at = None
    if size == 1:
        read_at = read_int8_at 
    elif size == 2:
        read_at = read_int16_at 
    
    for i in range(count):
        value = read_at(f, offset + i*size)
        values.append(value)
    
    return values


def write_index_array(f, array, offset, size, count):
    assert len(array) == count

    values = []
    write_at = None
    if size == 1:
        write_at = write_int8_at
    elif size == 2:
        write_at = write_int16_at

    for i in range(count):
        write_at(f, array[i], offset + i * size)


class MaterialInitData(object):
    def __init__(self):
        self.name = ""
        
    @classmethod
    def from_array(cls, f, start, i, offsets, real_i):
        initdata = cls()



        #start = f.tell()
        
        f.seek(start + i * 0xE8) # 0xE8 is size of Material Init Data entry
        initdatastart = f.tell()
        #f.seek(start)
        if offsets["IndirectInitData"] != 0:
            initdata.indirectdata = IndirectInitData.from_array(f, offsets["IndirectInitData"], real_i)
        else:
            initdata.indirectdata = None

        initdata.flag = read_int8_at(f, initdatastart + 0x0)
        cullmodeIndex = read_int8_at(f, initdatastart + 0x1)


        initdata.cullmode = CullModeSetting.from_array(f, offsets["GXCullMode"], cullmodeIndex)

        colorChannelNumIndex = read_int8_at(f, initdatastart + 0x2)
        initdata.color_channel_count = read_int8_at(f, offsets["UcArray2_ColorChannelCount"]+colorChannelNumIndex)

        texGenNumIndex = read_int8_at(f, initdatastart + 0x3)
        initdata.tex_gen_count = read_int8_at(f, offsets["TexCoordInfo"]+texGenNumIndex)

        tevStageNumIndex = read_int8_at(f, initdatastart + 0x4)
        initdata.tev_stage_count = read_int8_at(f, offsets["UCArray6_Tevstagenums"] + tevStageNumIndex)

        ditherIndex = read_int8_at(f, initdatastart + 0x5)
        initdata.dither = read_int8_at(f, offsets["UcArray7_Dither"] + ditherIndex)
        unk = read_int8_at(f, initdatastart + 0x6)
        initdata.unk = unk
        
        # 0x7 padding
        assert read_int8_at(f, initdatastart + 0x7) == 0x00
        
        # 2 Mat Colors starting at 0x8 (2 byte index)
        matColorIndices = read_index_array(f, initdatastart + 0x8, 2, 2)
        initdata.matcolors = []
        for index in matColorIndices:
            if index == -1:
                initdata.matcolors.append(None)
            else:
                color = Color.from_array(f, offsets["MaterialColor"], index)
                initdata.matcolors.append(color)
        
        # 4 ColorChans starting at 0xC (2 byte index) 
        colorChanIndices = read_index_array(f, initdatastart + 0xC, 2, 4)
        initdata.color_channels = []
        for i in range(4):
            index = colorChanIndices[i]
            if index == -1:
                initdata.color_channels.append(None)
            else:
                initdata.color_channels.append(ChannelControl.from_array(f, offsets["ColorChannelInfo"], index))
                #if i < 2 or initdata.color_channel_count != 0:
                #    initdata.color_channels.append(ChannelControl.from_array(f, offsets["ColorChannelInfo"], index))
                #else:
                #    initdata.color_channels.append(None)



        # 8 texcoords starting at 0x14 (2 byte index)
        texCoordIndices = read_index_array(f, initdatastart + 0x14, 2, 8)
        initdata.tex_coord_generators = []
        for index in texCoordIndices:
            if index == -1:
                initdata.tex_coord_generators.append(None)
            else:
                texcoord = TexCoordInfo.from_array(f, offsets["TexCoordInfo"], index)
                initdata.tex_coord_generators.append(texcoord)

        # 8 tex matrices starting at 0x24 (2 byte index) 
        texMatrixIndices = read_index_array(f, initdatastart + 0x24, 2, 8)
        initdata.tex_matrices = []
        for index in texMatrixIndices:
            texmatrix = None if index == -1 else TexMatrix.from_array(f, offsets["TexMatrixInfo"], index)
            initdata.tex_matrices.append(texmatrix)

        # 0x34-0x37 padding
        
        # Textures?
        texcount = 0
        
        textureIndices = read_index_array(f, initdatastart + 0x38, 2, 8)
        initdata.textures = []

        for i in range(8):
            index = read_int16_at(f, initdatastart + 0x38 + i*2)
            if index != -1: # Up to 0x48
                texcount += 1
                initdata.textures.append(read_int16_at(f, offsets["UsArray4_TextureIndices"] + index*2))
            else:
                initdata.textures.append(None)

        font_index = read_int16_at(f, initdatastart + 0x48)

        initdata.font = None if font_index == -1 else FontNumber.from_array(f, offsets["UsArray5"], font_index)
        
        tevkcolor_indices = read_index_array(f, initdatastart + 0x4A, 2, 4)
        initdata.tevkcolors = []
        for index in tevkcolor_indices:
            tevkcolor = None if index == -1 else TevKColor.from_array(f, offsets["GXColor2_TevKColors"], index)
            initdata.tevkcolors.append(tevkcolor)

        TevKColorSels = read_index_array(f, initdatastart + 0x52, 1, 16)
        initdata.tevkcolor_selects = TevKColorSels

        TevKAlphaSels = read_index_array(f, initdatastart + 0x62, 1, 16)
        initdata.tevkalpha_selects = TevKAlphaSels

        tevOrderIndices = read_index_array(f, initdatastart + 0x72, 2, 16)
        initdata.tevorders = []
        for index in tevOrderIndices:
            tevorder = None if index == -1 else TevOrder.from_array(f, offsets["TevOrderInfo"], index)
            initdata.tevorders.append(tevorder)

        tevcolor_indices = read_index_array(f, initdatastart + 0x92, 2, 4)
        initdata.tevcolors = []
        for index in tevcolor_indices:
            tevcolor = None if index == -1 else TevColor.from_array(f, offsets["GXColorS10_TevColor"], index)
            initdata.tevcolors.append(tevcolor)
        
        tevstageIndices = read_index_array(f, initdatastart + 0x9A, 2, 16)
        initdata.tevstages = []
        for index in tevstageIndices:
            tevstage = None if index == -1 else TevStage.from_array(f, offsets["TevStageInfo2"], index)
            initdata.tevstages.append(tevstage)

        tevstageSwapModes = read_index_array(f, initdatastart + 0xBA, 2, 16)
        initdata.tevstage_swapmodes = []
        for index in tevstageSwapModes:
            swapmode = None if index == -1 else TevSwapMode.from_array(f, offsets["TevSwapModeInfo"], index)
            initdata.tevstage_swapmodes.append(swapmode)


        # 4 tevswapmode tables starting at 0xDA (2 byte index)
        tevswapmodeTableIndices = read_index_array(f, initdatastart + 0xDA, 2, 4)
        initdata.tev_swapmode_tables = []
        for index in tevswapmodeTableIndices:
            swapmode_table = None if index == -1 else TevSwapModeTable.from_array(f, offsets["TevSwapModeTableInfo"], index)
            initdata.tev_swapmode_tables.append(swapmode_table)


        alphacompIndex = read_int16_at(f, initdatastart + 0xE2)
        initdata.alphacomp = AlphaCompare.from_array(f, offsets["AlphaCompInfo"], alphacompIndex)
        blendIndex = read_int16_at(f, initdatastart + 0xE4)
        initdata.blend = Blend.from_array(f, offsets["BlendInfo"], blendIndex)

        # 2 byte padding
        assert read_int16_at(f, initdatastart + 0xE6) == 0x0000
        return initdata

    def write_and_fill_data(self, f, dataarrays):
        start = f.tell()
        write_int8(f, self.flag)  # 0x00
        write_int8(f, get_index_or_add(dataarrays["GXCullMode"], self.cullmode))  # 0x01
        write_int8(f, get_index_or_add(dataarrays["UcArray2_ColorChannelCount"], self.color_channel_count))  # 0x02
        write_int8(f, get_index_or_add(dataarrays["UcArray3_TexGenCount"], self.tex_gen_count))  # 0x03
        write_int8(f, get_index_or_add(dataarrays["UCArray6_Tevstagenums"], self.tev_stage_count))  # 0x04
        write_int8(f, get_index_or_add(dataarrays["UcArray7_Dither"], self.dither))  # 0x05
        write_int8(f, self.unk) # 0x06
        write_uint8(f, 0x00)   # 0x07 padding
        assert f.tell() - start == 0x8

        for color in self.matcolors:  # 0x8
            write_int16(f, get_index_or_add(dataarrays["MaterialColor"], color))

        for color_channel in self.color_channels:  # 0xC
            print("adding value", color_channel)
            print(dataarrays["ColorChannelInfo"])
            write_int16(f, get_index_or_add(dataarrays["ColorChannelInfo"], color_channel))
        assert f.tell() - start == 0x14
        for texcoord in self.tex_coord_generators:  # 0x14
            write_int16(f, get_index_or_add(dataarrays["TexCoordInfo"], texcoord))
        assert f.tell() - start == 0x24

        for tex_matrix in self.tex_matrices:  # 0x24
            write_int16(f, get_index_or_add(dataarrays["TexMatrixInfo"], tex_matrix))

        f.write(b"\xFF\xFF\xFF\xFF")  # 0x34 - 0x37 padding

        assert f.tell() - start == 0x38
        for tex_index in self.textures:  # 0x38
            write_int16(f, get_index_or_add(dataarrays["UsArray4_TextureIndices"], tex_index))

        write_int16(f, get_index_or_add(dataarrays["UsArray5"], self.font))  # 0x48
        assert f.tell() - start == 0x4A
        for tevkcolor in self.tevkcolors: # 0x4A
            write_int16(f, get_index_or_add(dataarrays["GXColor2_TevKColors"], tevkcolor))

        for color_sel in self.tevkcolor_selects:  # 0x52
            write_int8(f, color_sel)

        for alpha_sel in self.tevkalpha_selects:  # 0x62
            write_int8(f, alpha_sel)

        for tev_order in self.tevorders:  # 0x72
            write_int16(f, get_index_or_add(dataarrays["TevOrderInfo"], tev_order))

        for tev_color in self.tevcolors:  # 0x92
            write_int16(f, get_index_or_add(dataarrays["GXColorS10_TevColor"], tev_color))

        for tev_stage in self.tevstages:  # 0x9A
            write_int16(f, get_index_or_add(dataarrays["TevStageInfo2"], tev_stage))

        for tev_stage_swapmode in self.tevstage_swapmodes:  # 0xBA
            write_int16(f, get_index_or_add(dataarrays["TevSwapModeInfo"], tev_stage_swapmode))

        for tev_stage_swapmode_table in self.tev_swapmode_tables:  # 0xDA
            write_int16(f, get_index_or_add(dataarrays["TevSwapModeTableInfo"], tev_stage_swapmode_table))

        write_int16(f, get_index_or_add(dataarrays["AlphaCompInfo"], self.alphacomp))
        write_int16(f, get_index_or_add(dataarrays["BlendInfo"], self.blend))
        f.write(b"\x00\x00")  # padding
        print(hex(f.tell() - start))
        assert f.tell() - start == 0xE8

    def serialize(self):
        result = {}
        for k, v in self.__dict__.items():
            if isinstance(v, (UnknownData, GXEnum, Color)):
                result[k] = v.serialize()
            elif isinstance(v, list):
                newlist = []
                for val in v:
                    if isinstance(val, (UnknownData, GXEnum, Color)):
                        newlist.append(val.serialize())
                    else:
                        newlist.append(val)
                result[k] = newlist
            else:
                result[k] = v

        return result

    @classmethod
    def deserialize(cls, obj):
        matinitdata = cls()
        matinitdata.name = obj["name"]
        matinitdata.flag = obj["flag"]
        matinitdata.cullmode = CullModeSetting.deserialize(obj["cullmode"])
        matinitdata.color_channel_count = obj["color_channel_count"]
        matinitdata.tex_gen_count = obj["tex_gen_count"]
        matinitdata.tev_stage_count = obj["tev_stage_count"]
        matinitdata.dither = obj["dither"]
        matinitdata.unk = obj["unk"]
        matinitdata.matcolors = deserialize_array(obj["matcolors"], Color.deserialize)
        matinitdata.color_channels = deserialize_array(obj["color_channels"], ChannelControl.deserialize)
        matinitdata.tex_coord_generators = deserialize_array(obj["tex_coord_generators"], TexCoordInfo.deserialize)
        matinitdata.tex_matrices = deserialize_array(obj["tex_matrices"], TexMatrix.deserialize)
        matinitdata.textures = obj["textures"]
        for tex in matinitdata.textures:
            assert not isinstance(tex, str)

        if obj["font"] is None:
            matinitdata.font = None
        else:
            matinitdata.font = FontNumber.deserialize(obj["font"])
        matinitdata.tevkcolors = deserialize_array(obj["tevkcolors"], TevKColor.deserialize)
        matinitdata.tevkcolor_selects = obj["tevkcolor_selects"]
        matinitdata.tevkalpha_selects = obj["tevkalpha_selects"]
        matinitdata.tevorders = deserialize_array(obj["tevorders"], TevOrder.deserialize)
        matinitdata.tevcolors = deserialize_array(obj["tevcolors"], TevColor.deserialize)
        matinitdata.tevstages = deserialize_array(obj["tevstages"], TevStage.deserialize)
        matinitdata.tevstage_swapmodes = deserialize_array(obj["tevstage_swapmodes"], TevSwapMode.deserialize)
        matinitdata.tev_swapmode_tables = deserialize_array(obj["tev_swapmode_tables"], TevSwapModeTable.deserialize)
        matinitdata.alphacomp = AlphaCompare.deserialize(obj["alphacomp"])
        matinitdata.blend = Blend.deserialize(obj["blend"])
        if "indirectdata" not in obj:
            matinitdata.indirectdata = None
        elif obj["indirectdata"] is None:
            matinitdata.indirectdata = None
        else:
            matinitdata.indirectdata = IndirectInitData.deserialize(obj["indirectdata"])

        return matinitdata

        
class MAT1(object):
    def __init__(self):
        self.name = "MAT1"
        #self.material_names = StringTable()
        self.materials = []
        
    @classmethod
    def from_file(cls, f):
        start = f.tell()
        
        magic = f.read(4)
        if magic != b"MAT1":
            raise RuntimeError("Not a MAT1 section!")
        mat1 = cls()    
        sectionsize = read_uint32(f)
        material_count = read_uint16(f)
        
        f.read(2) # padding 
        
        # Material Index Remap:
        # If iterating over material count, take i, multiply by 2, get index in remap table, that's the index into
        # materialinitdata
        
        offsets = {}
        for datatype in ("MaterialInitData", "MaterialIndexRemapTable", "MaterialNames", "IndirectInitData", "GXCullMode", "MaterialColor",
                        "UcArray2_ColorChannelCount", "ColorChannelInfo", "UcArray3_TexGenCount", "TexCoordInfo", "TexMatrixInfo", "UsArray4_TextureIndices",
                        "UsArray5", "TevOrderInfo", "GXColorS10_TevColor", "GXColor2_TevKColors", "UCArray6_Tevstagenums", "TevStageInfo2",
                        "TevSwapModeInfo", "TevSwapModeTableInfo", "AlphaCompInfo", "BlendInfo", "UcArray7_Dither"):
            
            offsets[datatype] = start + read_uint32(f)
        
        if offsets["IndirectInitData"] == start or offsets["IndirectInitData"]-offsets["MaterialNames"] < 5:
            offsets["IndirectInitData"] = 0
        #assert offsets["IndirectInitData"] == 0

        f.seek(offsets["MaterialNames"])
        material_names = StringTable.from_file(f)
        
        for i in range(material_count):
            f.seek(offsets["MaterialIndexRemapTable"] + i*2)
            initdataindex = read_uint16(f)
            
            f.seek(offsets["MaterialInitData"])
            materialinitdata = MaterialInitData.from_array(f, offsets["MaterialInitData"], initdataindex, offsets, i)
            materialinitdata.name = material_names.strings[i]
            mat1.materials.append(materialinitdata)
        f.seek(start+sectionsize)
        return mat1

    def write(self, f):
        start = f.tell()
        f.write(b"MAT1")
        f.write(b"FOOB")  # Fill in later
        write_int16(f, len(self.materials))
        f.write(b"\xFF\xFF")  # padding

        offsets = {}
        dataarrays = {}


        sections = ("MaterialInitData", "MaterialIndexRemapTable", "MaterialNames", "IndirectInitData", "GXCullMode",
            "MaterialColor",
            "UcArray2_ColorChannelCount", "ColorChannelInfo", "UcArray3_TexGenCount", "TexCoordInfo", "TexMatrixInfo",
            "UsArray4_TextureIndices",
            "UsArray5", "TevOrderInfo", "GXColorS10_TevColor", "GXColor2_TevKColors", "UCArray6_Tevstagenums",
            "TevStageInfo2",
            "TevSwapModeInfo", "TevSwapModeTableInfo", "AlphaCompInfo", "BlendInfo", "UcArray7_Dither")
        offsets_start = f.tell()
        for datatype in sections:
            offsets[datatype] = None
            dataarrays[datatype] = []
            f.write(b"FOOB")

        dataarrays["GXCullMode"] = [CullModeSetting(2),
                                    CullModeSetting(1),
                                    CullModeSetting(0)]

        has_indirectdata = False
        offsets["MaterialInitData"] = f.tell()-start
        for material in self.materials:
            material.write_and_fill_data(f, dataarrays)
            if material.indirectdata is not None:
                has_indirectdata = True

        dataarrays["ColorChannelInfo"].append(ChannelControl.deserialize("0001FFFF"))
        dataarrays["TexCoordInfo"].append(TexCoordInfo.deserialize("01043CFF"))


        offsets["MaterialIndexRemapTable"] = f.tell()-start
        for i, material in enumerate(self.materials):
            write_int16(f, i)
        write_pad(f, 4)
        offsets["MaterialNames"] = f.tell()-start
        material_names = StringTable()

        for material in self.materials:
            material_names.strings.append(material.name)
        material_names.write(f)

        write_pad(f, 4)
        offsets["IndirectInitData"] = 0  # TODO: Implement Indirect Data

        if has_indirectdata:
            offsets["IndirectInitData"] = f.tell()-start
            for mat in self.materials:
                if mat.indirectdata is None:
                    f.write(b"\x00"*0x128)
                else:
                    mat.indirectdata.write(f)

        for datatype in sections[4:]:
            offsets[datatype] = f.tell()-start
            if len(dataarrays[datatype]) == 0:
                offsets[datatype] = 0
                continue
            #print("offset", offsets[datatype])
            if datatype in ("UcArray2_ColorChannelCount", "UcArray3_TexGenCount", "UCArray6_Tevstagenums", "UcArray7_Dither"):
                for data in dataarrays[datatype]:
                    write_uint8(f, data)
            elif datatype in ("UsArray4_TextureIndices", ):
                for data in dataarrays[datatype]:
                    print(data, type(data))
                    write_uint16(f, data)
            else:
                for data in dataarrays[datatype]:
                    print(data)
                    data.write(f)

            write_pad(f, 4)
        write_pad(f, 0x20)
        total = f.tell()

        f.seek(offsets_start)
        for datatype in sections:
            offset = offsets[datatype]
            write_uint32(f, offset)

        f.seek(start+4)
        write_uint32(f, total-start)  # section size

        f.seek(total)

    def serialize(self):
        result = {"type": "MAT1"}
        #result["MaterialNames"] = self.material_names.serialize()
        result["Materials"] = [mat.serialize() for mat in self.materials]

        return result

    # Turn indices into texture names
    def postprocess_serialize(self, textures):
        result = self.serialize()
        if textures is not None:
            for material in result["Materials"]:
                for i in range(len(material["textures"])):
                    val = material["textures"][i]
                    if val is not None:
                        if val < len(textures.references):
                            material["textures"][i] = textures.references[val]

        return result

    @classmethod
    def deserialize(cls, obj):
        assert obj["type"] == "MAT1"

        mat1 = cls()
        for material in obj["Materials"]:
            mat1.materials.append(MaterialInitData.deserialize(material))

        return mat1
    
    # Resolve texture names into indices
    @classmethod
    def preprocess_deserialize(cls, obj, textures):
        if textures is not None:
            for material in obj["Materials"]:
                for i in range(len(material["textures"])):
                    val = material["textures"][i]
                    if isinstance(val, str):
                        if val in textures.references:
                            pos = textures.references.index(val)
                        else:
                            textures.references.append(val)
                            pos = len(textures.references)-1
                            assert textures.references[pos] == val
                        material["textures"][i] = pos

            for material in obj["Materials"]:
                for i in range(len(material["textures"])):
                    val = material["textures"][i]
                    assert not isinstance(val, str)
        deserialized = cls.deserialize(obj)
        for material in deserialized.materials:
            for tex in material.textures:
                assert not isinstance(tex, str)
        return deserialized
