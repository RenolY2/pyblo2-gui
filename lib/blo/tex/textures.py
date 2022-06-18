import os
from OpenGL.GL import *
from PyQt5.QtGui import QImage

from lib.blo.tex.bti import BTIFile
FOLDER = "Folder"
RARC = "RARC"


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
        qimg = QImage(path).convertToFormat(QImage.Format_RGBA8888)
        self.textures[texname.lower()] = (None, qimg)
        self.textures_render[texname.lower()] = GLTexture(qimg)
        self.dirty = True
        return texname

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

    def get_texture_image(self, texname):
        if texname.lower() in self.textures:
            return self.textures[texname.lower()][1]
        else:
            return None

    def init_from_arc(self, arc):
        self.textures = {}
        self.origin = RARC