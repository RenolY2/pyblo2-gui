from io import BytesIO
from enum import Enum
from binascii import unhexlify

from .fs_helpers import *
from .texture_utils import *
#from wwlib.yaz0 import Yaz0

# BTI Header with CMPR and dimensions of 0 by 0
BASE_HEADER = unhexlify("0E01000000000000000000000000000000000000010100000100000000000020")


class WrapMode(Enum):
  ClampToEdge    = 0
  Repeat         = 1
  MirroredRepeat = 2

class FilterMode(Enum):
  Nearest              = 0
  Linear               = 1
  NearestMipmapNearest = 2
  NearestMipmapLinear  = 3
  LinearMipmapNearest  = 4
  LinearMipmapLinear   = 5

class BTI:
  def __init__(self, data, header_offset=0):
    self.data = data
    self.header_offset = header_offset
    
    self.read_header(data, header_offset=header_offset)
    
    blocks_wide = (self.width + (self.block_width-1)) // self.block_width
    blocks_tall = (self.height + (self.block_height-1)) // self.block_height
    image_data_size = blocks_wide*blocks_tall*self.block_data_size
    remaining_mipmaps = self.mipmap_count-1
    curr_mipmap_size = image_data_size
    while remaining_mipmaps > 0:
      # Each mipmap is a quarter the size of the last (half the width and half the height).
      curr_mipmap_size = curr_mipmap_size//4
      image_data_size += curr_mipmap_size
      remaining_mipmaps -= 1
      # Note: We don't actually read the smaller mipmaps, we only read the normal sized one, and when saving recalculate the others by scaling the normal one down.
      # This is to simplify things, but a full implementation would allow reading and saving each mipmap individually (since the mipmaps can actually have different contents).
    self.image_data = BytesIO(read_bytes(data, header_offset+self.image_data_offset, image_data_size))
    
    palette_data_size = self.num_colors*2
    self.palette_data = BytesIO(read_bytes(data, header_offset+self.palette_data_offset, palette_data_size))
  
  def read_header(self, data, header_offset=0):
    self.image_format = ImageFormat(read_u8(data, header_offset+0))
    
    self.alpha_setting = read_u8(data, header_offset+1)
    self.width = read_u16(data, header_offset+2)
    self.height = read_u16(data, header_offset+4)
    
    self.wrap_s = WrapMode(read_u8(data, header_offset+6))
    self.wrap_t = WrapMode(read_u8(data, header_offset+7))
    
    self.palettes_enabled = bool(read_u8(data, header_offset+8))
    self.palette_format = PaletteFormat(read_u8(data, header_offset+9))
    self.num_colors = read_u16(data, header_offset+0xA)
    self.palette_data_offset = read_u32(data, header_offset+0xC)
    
    self.min_filter = FilterMode(read_u8(data, header_offset+0x14))
    self.mag_filter = FilterMode(read_u8(data, header_offset+0x15))
    
    self.min_lod = read_u8(data, header_offset+0x16)
    self.max_lod = read_u8(data, header_offset+0x17) # seems to be equal to (mipmap_count-1)*8
    self.mipmap_count = read_u8(data, header_offset+0x18)
    self.unknown_3 = read_u8(data, header_offset+0x19)
    self.lod_bias = read_u16(data, header_offset+0x1A)
    
    self.image_data_offset = read_u32(data, header_offset+0x1C)
  
  def save_header_changes(self):
    write_u8(self.data, self.header_offset+0, self.image_format.value)
    
    write_u8(self.data, self.header_offset+1, self.alpha_setting)
    write_u16(self.data, self.header_offset+2, self.width)
    write_u16(self.data, self.header_offset+4, self.height)
    
    write_u8(self.data, self.header_offset+6, self.wrap_s.value)
    write_u8(self.data, self.header_offset+7, self.wrap_t.value)
    
    self.palettes_enabled = self.needs_palettes()
    write_u8(self.data, self.header_offset+8, int(self.palettes_enabled))
    write_u8(self.data, self.header_offset+9, self.palette_format.value)
    write_u16(self.data, self.header_offset+0xA, self.num_colors)
    write_u32(self.data, self.header_offset+0xC, self.palette_data_offset)
    
    write_u8(self.data, self.header_offset+0x14, self.min_filter.value)
    write_u8(self.data, self.header_offset+0x15, self.mag_filter.value)
    
    write_u8(self.data, self.header_offset+0x16, self.min_lod)
    write_u8(self.data, self.header_offset+0x17, self.max_lod)
    write_u8(self.data, self.header_offset+0x18, self.mipmap_count)
    write_u8(self.data, self.header_offset+0x19, self.unknown_3)
    write_u16(self.data, self.header_offset+0x1A, self.lod_bias)
    
    write_u32(self.data, self.header_offset+0x1C, self.image_data_offset)
  
  @property
  def block_width(self):
    return BLOCK_WIDTHS[self.image_format]
  
  @property
  def block_height(self):
    return BLOCK_HEIGHTS[self.image_format]
  
  @property
  def block_data_size(self):
    return BLOCK_DATA_SIZES[self.image_format]
  
  def needs_palettes(self):
    return self.image_format in IMAGE_FORMATS_THAT_USE_PALETTES
  
  def is_greyscale(self):
    if self.needs_palettes():
      return self.palette_format in GREYSCALE_PALETTE_FORMATS
    else:
      return self.image_format in GREYSCALE_IMAGE_FORMATS
  
  def render(self):
    image = decode_image(
      self.image_data, self.palette_data,
      self.image_format, self.palette_format,
      self.num_colors,
      self.width, self.height
    )

    return image
  
  def render_palette(self):
    colors = decode_palettes(
      self.palette_data, self.palette_format,
      self.num_colors, self.image_format
    )
    return colors
  
  def replace_image_from_path(self, new_image_file_path):
    self.image_data, self.palette_data, encoded_colors, self.width, self.height = encode_image_from_path(
      new_image_file_path, self.image_format, self.palette_format,
      mipmap_count=self.mipmap_count
    )
    self.num_colors = len(encoded_colors)
  
  def replace_image(self, new_image):
    self.image_data, self.palette_data, encoded_colors = encode_image(
      new_image, self.image_format, self.palette_format,
      mipmap_count=self.mipmap_count
    )
    self.num_colors = len(encoded_colors)
    self.width = new_image.width
    self.height = new_image.height

  def replace_palette(self, new_colors):
    encoded_colors = generate_new_palettes_from_colors(new_colors, self.palette_format)
    self.palette_data = encode_palette(encoded_colors, self.palette_format, self.image_format)
    self.num_colors = len(encoded_colors)
  
  def is_visually_equal_to(self, other):
    # Checks if a BTI would result in the exact same rendered PNG image data as another BTI, without actually rendering them both in order to improve performance.
    
    if not isinstance(other, BTI):
      return False
    
    if self.image_format != other.image_format:
      return False
    if self.palette_format != other.palette_format:
      return False
    if self.num_colors != other.num_colors:
      return False
    if self.width != other.width:
      return False
    if self.height != other.height:
      return False
    if read_all_bytes(self.image_data) != read_all_bytes(other.image_data):
      return False
    if read_all_bytes(self.palette_data) != read_all_bytes(other.palette_data):
      return False
    
    return True

class BTIFile(BTI): # For standalone .bti files (as opposed to textures embedded inside J3D models/animations)
  def __init__(self, data):
    #if Yaz0.check_is_compressed(data):
    #  data = Yaz0.decompress(data)
    super(BTIFile, self).__init__(data)
    self.dirty = False

  def mark_for_format_update(self):
    self.dirty = True

  @classmethod
  def create_placeholder(cls):
    data = BytesIO(BASE_HEADER)
    btifile = cls(data)
    return btifile

  @classmethod
  def create_from_image(cls, image):
    data = BytesIO(BASE_HEADER)
    btifile = cls(data)
    btifile.replace_image(image)
    return btifile

  def save_to_file(self, fp):
    self.save_changes()
    self.data.seek(0)
    fp.write(self.data.read())

  def save_changes(self):
    # Cut off the image and palette data first since we're replacing this data entirely.
    self.data.truncate(0x20)
    self.data.seek(0x20)
    
    self.image_data_offset = 0x20
    self.image_data.seek(0)
    self.data.write(self.image_data.read())
    
    if self.needs_palettes():
      self.palette_data_offset = 0x20 + data_len(self.image_data)
      self.palette_data.seek(0)
      self.data.write(self.palette_data.read())
    else:
      self.palette_data_offset = 0
    
    self.save_header_changes()

class BTIFileEntry(BTIFile):
  def __init__(self, file_entry):
    self.file_entry = file_entry
    self.file_entry.decompress_data_if_necessary()
    super(BTIFileEntry, self).__init__(self.file_entry.data)
