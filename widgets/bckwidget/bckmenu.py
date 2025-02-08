from io import BytesIO
from PyQt5.QtWidgets import QMenu, QAction, QFileDialog, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
#from lib.blo.tex.textures import TextureHandler
from lib.blo.readblo2 import ScreenBlo
from widgets.editor_widgets import open_error_dialog
from widgets.bckwidget.j3d_animation_editor.animation_editor import GenEditor
#from blo_editor import LayoutEditor
#from blo_editor_widgets import BolMapViewer
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blo_editor import LayoutEditor
    from blo_editor_widgets import BolMapViewer
    from lib.blo.readblo2 import Pane


class BCKControls(QWidget):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_editor: LayoutEditor = parent.parent
        #self.setMinimumWidth(400)
        self.setContentsMargins(0, 0, 0, 0)
        self.vbox = QVBoxLayout(self)
        self.setLayout(self.vbox)

        self.apply_anim_button = QtWidgets.QPushButton("Link to BCK", self)
        self.apply_anim_button.pressed.connect(self.link_or_unlink_bck)

        self.link_anim_hierarchy = QtWidgets.QPushButton("Link Hierarchy", self)
        self.unlink_anim_hierarchy = QtWidgets.QPushButton("Unlink Hierarchy", self)
        self.link_anim_hierarchy.pressed.connect(partial(self.hierarchy_set_animated, True))
        self.unlink_anim_hierarchy.pressed.connect(partial(self.hierarchy_set_animated, False))

        apply_layout = QHBoxLayout(self)
        apply_layout.addWidget(self.apply_anim_button)
        apply_layout.addWidget(self.link_anim_hierarchy)
        apply_layout.addWidget(self.unlink_anim_hierarchy)
        self.vbox.addLayout(apply_layout)

        #apply_hierarchy_layout = QHBoxLayout(self)
        #apply_hierarchy_layout.addWidget(self.link_anim_hierarchy)
        #apply_hierarchy_layout.addWidget(self.unlink_anim_hierarchy)
        #self.vbox.addLayout(apply_hierarchy_layout)

        self.play_button = QtWidgets.QPushButton("Play", self)
        self.fps_box = QtWidgets.QSpinBox(self)
        self.frame_count = QtWidgets.QSpinBox(self)


        self.button_setkeyframe = QtWidgets.QPushButton("Set Keyframe", self)
        self.button_setkeyframe.pressed.connect(self.set_keyframe)

        self.button_fromkeyframe = QtWidgets.QPushButton("Set Pos from Animation", self)
        self.button_fromkeyframe.pressed.connect(self.restore_from_frame)



        play_layout = QHBoxLayout(self)
        play_layout.addWidget(self.play_button)
        play_layout.addWidget(self.fps_box)
        play_layout.addWidget(self.frame_count)
        self.vbox.addLayout(play_layout)




        keyframe_layout = QHBoxLayout(self)
        keyframe_layout.addWidget(self.button_setkeyframe)
        self.vbox.addLayout(keyframe_layout)

        keyframe_more_layout = QHBoxLayout(self)
        self.button_pos_keyframe = QtWidgets.QPushButton("Pos Key")
        self.button_scale_keyframe = QtWidgets.QPushButton("Scale Key")
        self.button_rotation_keyframe = QtWidgets.QPushButton("Rotation Key")
        #keyframe_more_layout.addWidget(self.button_pos_keyframe)
        #keyframe_more_layout.addWidget(self.button_scale_keyframe)
        #keyframe_more_layout.addWidget(self.button_rotation_keyframe)
        self.vbox.addLayout(keyframe_more_layout)

        restorekeyframe_layout = QHBoxLayout(self)
        restorekeyframe_layout.addWidget(self.button_fromkeyframe)
        self.vbox.addLayout(restorekeyframe_layout)



        self.fps = 30
        self.play_button.pressed.connect(self.play_or_pause)
        self.fps_box.setValue(self.fps)
        self.fps_box.valueChanged.connect(self.update_fps)
        self.frame_count.setMaximum(2**31-1)
        self.frame_count.valueChanged.connect(self.update_frame)

    def set_keyframe(self):
        element = self.main_editor.get_selected()

        if element is not None and self.main_editor.animation_menu.anim_editor is not None:
            self.main_editor.animation_menu.anim_editor.set_or_add_keyframe(
                self.frame_count.value(), element.p_bckindex,
                element.p_offset_x, element.p_offset_y,
                element.p_scale_x, element.p_scale_y,
                element.p_rotation
            )
            self.main_editor.animation_menu.anim_editor.refresh_bck()

    def restore_from_frame(self):
        element = self.main_editor.get_selected()
        anim_editor = self.main_editor.animation_menu.anim_editor
        if element is not None and anim_editor is not None:
            if element.p_bckindex < len(anim_editor.animation.animations):
                anim = anim_editor.animation.animations[element.p_bckindex]
                anim_values = anim.interpolate(self.frame_count.value())
                element.p_offset_x, element.p_offset_y = anim_values[0:2]
                element.p_scale_x, element.p_scale_y = anim_values[2:4]
                element.p_rotation = anim_values[4]
                self.main_editor.pik_control.update_info()
                self.main_editor.level_view.do_redraw()

    def reset_link_button(self):
        self.apply_anim_button.setText("Link to BCK")

    def update_link_button(self):
        element = self.main_editor.get_selected()

        if element is not None:
            try:
                if element.animated:
                    self.apply_anim_button.setText("Unlink from BCK")
                else:
                    self.apply_anim_button.setText("Link to BCK")
                self.apply_anim_button.setEnabled(True)
                self.link_anim_hierarchy.setEnabled(True)
                self.unlink_anim_hierarchy.setEnabled(True)
            except:
                self.apply_anim_button.setEnabled(False)
                self.link_anim_hierarchy.setEnabled(False)
                self.unlink_anim_hierarchy.setEnabled(False)

    def update_frame(self, value):
        if self.fps == 0:
            anim_time = 0.0
        else:
            anim_time = value/self.fps
        self.main_editor.level_view.animation_time = anim_time
        self.main_editor.level_view.do_redraw()

    def update_fps(self, value):
        self.fps = value

    def play_or_pause(self):
        #if self.main_editor.animation_menu.anim_editor is not None:
        #    self.main_editor.animation_menu.anim_editor.refresh_bck(reload_table=True)

        if self.main_editor.level_view.animation_running:
            self.main_editor.level_view.animation_running = False
            self.play_button.setText("Play")
        else:
            self.main_editor.level_view.animation_running = True
            self.play_button.setText("Pause")

    def pause(self):
        self.main_editor.level_view.animation_running = False

    def hierarchy_set_animated(self, animated):
        element = self.main_editor.get_selected()
        if element is not None:
            to_visit = [element]

            while len(to_visit) > 0:
                next = to_visit.pop(0)
                next.animated = animated
                if next.widget is not None:
                    next.widget.update_name()
                if next.child is not None:
                    for child in next.child.children:
                        to_visit.append(child)

            self.update_link_button()

    def link_or_unlink_bck(self):
        self.main_editor.level_view.do_redraw()
        element = self.main_editor.get_selected()
        if element is not None:
            if element.animated:
                element.animated = False
                self.apply_anim_button.setText("Link to BCK")
            else:
                element.animated = True
                self.apply_anim_button.setText("Unlink from BCK")

            if element.widget is not None:
                element.widget.update_name()


class BCKAnimationMenu(QMenu):
    #filter_update = pyqtSignal()

    def __init__(self, editor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor: LayoutEditor = editor
        #self.texture_handler = TextureHandler()

        self.setTitle("Animation")

        self.open_editor_action = QAction("Open BCK Editor", self)
        self.open_editor_action.triggered.connect(self.open_editor)
        self.addAction(self.open_editor_action)

        self.anim_editor: GenEditor = None

        #self.load_archive_action = QAction("Load From Archive", self)
        #self.load_archive_action.triggered.connect(self.load_archive)
        #self.addAction(self.load_archive_action)

        """self.save_file_action = QAction("Save To Folder", self)
        self.save_file_action.triggered.connect(self.save_to_folder)
        self.addAction(self.save_file_action)

        self.clean_up_action = QAction("Clean Up Current Archive", self)
        self.clean_up_action.triggered.connect(self.clean_up)
        self.addAction(self.clean_up_action)"""

    def handle_editor_closed(self):
        self.anim_editor.destroy()
        self.anim_editor = None

    def open_editor(self):
        self.anim_editor = GenEditor(self.editor)
        self.anim_editor.closing.connect(self.handle_editor_closed)
        self.anim_editor.table_display.cellChanged.connect(self.update_3d)
        self.anim_editor.show()

    def update_3d(self, x, y):
        self.editor.level_view.do_redraw()