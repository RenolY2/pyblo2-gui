import os
from OpenGL.GL import *
from PyQt5.QtGui import QImage

from lib.blo.tex.bti import BTIFile
from PIL import Image

from widgets.editor_widgets import open_error_dialog
FOLDER = "Folder"
RARC = "RARC"


class ImageTooLarge(Exception):
    pass


class GLTexture(object):
    def __init__(self, qimage):
        self.ID = None
        self.qimage = qimage

        self.dirty = True

    def update_texture(self):
        if self.dirty:
            self.gl_init()
            self.dirty = False

    def set_image(self, qimage):
        self.qimage = qimage
        self.dirty = True

    def gl_init(self):
        if self.ID is None:
            ID = glGenTextures(1)
        else:
            glDeleteTextures(1, self.ID)
            ID = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, ID)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)

        qimage = self.qimage
        imgdata = bytes(qimage.bits().asarray(qimage.width() * qimage.height() * 4))
        glTexImage2D(GL_TEXTURE_2D, 0, 4, qimage.width(), qimage.height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, imgdata)

        self.ID = ID


class TextureBundle(object):
    def __init__(self, img, qimg):
        self.bti = None
        self.img = img
        self.qimg = qimg
        self.dirty = True

    def update_bti(self):
        if self.dirty:
            if self.bti is None:
                self.bti = BTIFile.create_from_image(self.img)
            else:
                self.bti.replace_image(self.img)
            self.dirty = False


class TextureHandler(object):
    def __init__(self):
        self.textures = {}
        self.textures_render = {}
        self.origin = None
        self.dirty = True

    def update_gl(self):
        if self.dirty:
            for texname, tex in self.textures_render.items():
                tex.update_texture()
            self.dirty = False

    def init_from_path(self, path):
        texname = os.path.basename(path)
        with Image.open(path) as img:
            img.load()
        img = img.convert("RGBA")
        qimg = QImage(img.tobytes(), img.width, img.height, img.width * 4, QImage.Format_RGBA8888)
        #qimg = QImage(path).convertToFormat(QImage.Format_RGBA8888)
        if qimg.width() > 1024 or qimg.height() > 1024:
            exception = ImageTooLarge("Image exceeds 1024x1024!")
            exception.width = qimg.width()
            exception.height = qimg.height()
            raise exception
        self.textures[texname.lower()] = TextureBundle(img, qimg)
        self.textures_render[texname.lower()] = GLTexture(qimg)
        self.dirty = True
        return texname

    def get_bti(self, name):
        return self.textures[name.lower()].bti

    def update_format(self, name):
        self.textures[name.lower()].bti.dirty = True

    def init_from_folder(self, path):
        self.textures = {}
        self.origin = FOLDER
        self.dirty = True

        for filename in os.listdir(path):
            if filename.lower().endswith(".bti"):
                filepath = os.path.join(path, filename)

                with open(filepath, "rb") as f:
                    bti = BTIFile(f)
                    img = bti.render()
                    qimg = QImage(img.tobytes(), bti.width, bti.height, bti.width * 4, QImage.Format_RGBA8888)

                    self.textures[filename.lower()] = (bti, qimg)
                    self.textures_render[filename.lower()] = GLTexture(qimg)

    def rename(self, old, new):
        old_lo, new_lo = old.lower(), new.lower()
        assert old_lo in self.textures
        assert new_lo not in self.textures

        tmp = self.textures[old_lo]
        tmp_render = self.textures_render[old_lo]

    def get_texture_image(self, texname):
        if texname.lower() in self.textures:
            return self.textures[texname.lower()].qimg
        else:
            return None

    def init_from_arc(self, arc):
        self.textures = {}
        self.origin = RARC