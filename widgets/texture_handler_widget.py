from io import BytesIO
from PyQt5.QtWidgets import QMenu, QAction, QFileDialog, QMessageBox
from PyQt5.QtCore import pyqtSignal
from lib.blo.tex.textures import TextureHandler
from lib.blo.readblo2 import ScreenBlo
from widgets.editor_widgets import open_error_dialog


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

        #self.load_archive_action = QAction("Load From Archive", self)
        #self.load_archive_action.triggered.connect(self.load_archive)
        #self.addAction(self.load_archive_action)

        self.save_file_action = QAction("Save To Folder", self)
        self.save_file_action.triggered.connect(self.save_to_folder)
        self.addAction(self.save_file_action)

        self.clean_up_action = QAction("Clean Up Current Archive", self)
        self.clean_up_action.triggered.connect(self.clean_up)
        self.addAction(self.clean_up_action)

    def clean_up(self):
        if self.editor.loaded_archive is None:
            open_error_dialog("No archive loaded, cannot do Texture Cleanup.", self)
        if self.editor.loaded_archive is not None:
            root = self.editor.loaded_archive.root
            try:
                img = root["timg"]
            except FileNotFoundError:
                open_error_dialog("Archive has no TIMG folder, cannot do Texture Cleanup.", self)
            else:
                used_textures = {}
                for name, blofile in root["scrn"].files.items():
                    if name.lower().endswith(".blo"):
                        if name == self.editor.loaded_archive_file:
                            blo_file = self.editor.layout_file
                        else:
                            blo_file = ScreenBlo.from_file(BytesIO(blofile.getvalue()))
                        for tex in blo_file.root.textures.references:
                            used_textures[tex.lower()] = True
                for_deletion = []
                for tex in root["timg"].files:
                    if tex.lower() not in used_textures:
                        for_deletion.append(tex)
                print(used_textures.keys())
                print(for_deletion)
                result = QMessageBox.question(self, "Texture Clean-Up",
                                              ("The following texture(s) are (probably) unused (not referenced by a"
                                               "blo file in the currently loaded archive.)\n"
                                               "{0}\n"
                                              "Are you sure you want to delete the texture(s)?".format(
                                                  ", ".join(for_deletion))),
                                              QMessageBox.Yes | QMessageBox.No)
                if result == QMessageBox.Yes:
                    for tex in for_deletion:
                        del root["timg"].files[tex]

                    print("Textures removed")



    def save_to_folder(self):
        filepath = QFileDialog.getExistingDirectory(
            self, "Choose Texture Folder",
            "")
        if filepath:
            self.texture_handler.save_to_folder(
                self.editor.layout_file.root.textures.references,
                filepath)

    def load_folder(self):
        filepath = QFileDialog.getExistingDirectory(
            self, "Choose Texture Folder",
            "")
        if filepath:
            self.texture_handler.init_from_folder(self.editor.layout_file.root.textures.references,
                                                  filepath)

    def load_archive(self):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            "",
            "Archive (*.arc, *.szs);;All files (*)")
