from PyQt5.QtWidgets import QMenu, QAction, QFileDialog
from PyQt5.QtCore import pyqtSignal
from lib.blo.tex.textures import TextureHandler


class TextureHandlerMenu(QMenu):
    filter_update = pyqtSignal()

    def __init__(self, editor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        self.texture_handler = TextureHandler()

        self.setTitle("Textures")

        self.load_folder_action = QAction("Load From Folder", self)
        self.load_folder_action.triggered.connect(self.load_folder)
        self.addAction(self.load_folder_action)

        self.load_archive_action = QAction("Load From Archive", self)
        self.load_archive_action.triggered.connect(self.load_archive)
        self.addAction(self.load_archive_action)

        self.save_file_action = QAction("Save To Folder", self)
        self.save_file_action.triggered.connect(self.save_to_folder)
        self.addAction(self.save_file_action)

    def save_to_folder(self):
        filepath = QFileDialog.getExistingDirectory(
            self, "Choose Texture Folder",
            "")
        if filepath:
            self.texture_handler.save_to_folder(filepath)

    def load_folder(self):
        filepath = QFileDialog.getExistingDirectory(
            self, "Choose Texture Folder",
            "")
        if filepath:
            self.texture_handler.init_from_folder(self.editor.blo_file.root.textures.references,
                                                  filepath)

    def load_archive(self):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            "",
            "Archive (*.arc, *.szs);;All files (*)")
