import traceback
import os
from timeit import default_timer
from copy import deepcopy
from io import TextIOWrapper, BytesIO, StringIO
from math import sin, cos, atan2
import json
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog, QSplitter,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QApplication, QStatusBar, QLineEdit)
from PyQt5.QtGui import QMouseEvent, QImage
import PyQt5.QtGui as QtGui

import opengltext
import py_obj

from widgets.editor_widgets import catch_exception
from widgets.editor_widgets import AddPikObjectWindow
from widgets.tree_view import LayoutDataTreeView
import widgets.tree_view as tree_view
from configuration import read_config, make_default_config, save_cfg

import mkdd_widgets # as mkddwidgets
from widgets.side_widget import PikminSideWidget
from widgets.editor_widgets import open_error_dialog, catch_exception_with_dialog
from mkdd_widgets import BolMapViewer, MODE_TOPDOWN
from lib.libbol import BOL, MGEntry, Route, get_full_name
import lib.libbol as libbol
from lib.rarc import Archive
from lib.BCOllider import RacetrackCollision
from lib.model_rendering import TexturedModel, CollisionModel, Minimap
from widgets.editor_widgets import ErrorAnalyzer
from lib.dolreader import DolFile, read_float, write_float, read_load_immediate_r0, write_load_immediate_r0, UnmappedAddress
from widgets.file_select import FileSelect
from PyQt5.QtWidgets import QTreeWidgetItem
from lib.bmd_render import clear_temp_folder, load_textured_bmd
from lib.blo.readblo2 import ScreenBlo

EDITOR_NAME = "BLO Layout Editor"


def get_treeitem(root: QTreeWidgetItem, obj):
    for i in range(root.childCount()):
        child = root.child(i)
        if child.bound_to == obj:
            return child
    return None


class LayoutEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.screen_file = ScreenBlo()

        self.setup_ui()

        try:
            self.configuration = read_config()
            print("Config file loaded")
        except FileNotFoundError as e:
            print("No config file found, creating default config...")
            self.configuration = make_default_config()

        self.level_view.screen_file = self.screen_file
        self.level_view.set_editorconfig(self.configuration["editor"])
        self.level_view.visibility_menu = self.visibility_menu

        self.pathsconfig = self.configuration["default paths"]
        self.editorconfig = self.configuration["editor"]
        self.current_gen_path = None

        self.current_coordinates = None
        self.editing_windows = {}
        self.add_object_window = None
        self.object_to_be_added = None

        self.history = EditorHistory(20)
        self.edit_spawn_window = None

        self._window_title = ""
        self._user_made_change = False
        self._justupdatingselectedobject = False

        self.addobjectwindow_last_selected = None

        self.loaded_archive = None
        self.loaded_archive_file = None
        self.last_position_clicked = []

        self.analyzer_window = None

        self._dontselectfromtree = False


    @catch_exception
    def reset(self):
        self.last_position_clicked = []
        self.loaded_archive = None
        self.loaded_archive_file = None
        self.history.reset()
        self.object_to_be_added = None
        self.level_view.reset(keep_collision=True)

        self.current_coordinates = None
        for key, val in self.editing_windows.items():
            val.destroy()

        self.editing_windows = {}

        if self.add_object_window is not None:
            self.add_object_window.destroy()
            self.add_object_window = None

        if self.edit_spawn_window is not None:
            self.edit_spawn_window.destroy()
            self.edit_spawn_window = None

        self.current_gen_path = None
        self.pik_control.reset_info()
        self.pik_control.button_add_object.setChecked(False)
        #self.pik_control.button_move_object.setChecked(False)
        self._window_title = ""
        self._user_made_change = False

        self.addobjectwindow_last_selected = None
        self.addobjectwindow_last_selected_category = None

    def set_base_window_title(self, name):
        self._window_title = name
        if name != "":
            self.setWindowTitle(EDITOR_NAME + " - " + name)
        else:
            self.setWindowTitle(EDITOR_NAME)

    def set_has_unsaved_changes(self, hasunsavedchanges):
        if hasunsavedchanges and not self._user_made_change:
            self._user_made_change = True

            if self._window_title != "":
                self.setWindowTitle(EDITOR_NAME + " [Unsaved Changes] - " + self._window_title)
            else:
                self.setWindowTitle(EDITOR_NAME + " [Unsaved Changes] ")
        elif not hasunsavedchanges and self._user_made_change:
            self._user_made_change = False
            if self._window_title != "":
                self.setWindowTitle(EDITOR_NAME + " - " + self._window_title)
            else:
                self.setWindowTitle(EDITOR_NAME)

    @catch_exception_with_dialog
    def do_goto_action(self, item, index):
        print(item, index)
        self.tree_select_object(item)
        print(self.level_view.selected_positions)
        if len(self.level_view.selected_positions) > 0:
            position = self.level_view.selected_positions[0]

            if self.level_view.mode == MODE_TOPDOWN:
                self.level_view.offset_z = -position.z
                self.level_view.offset_x = -position.x
            else:
                look = self.level_view.camera_direction.copy()

                pos = position.copy()
                fac = 5000
                self.level_view.offset_z = -(pos.z + look.y*fac)
                self.level_view.offset_x = pos.x - look.x*fac
                self.level_view.camera_height = pos.y - look.z*fac
            print("heyyy")
            self.level_view.do_redraw()

    def tree_select_arrowkey(self):
        current = self.layoutdatatreeview.selectedItems()
        if len(current) == 1:
            self.tree_select_object(current[0])

    def tree_select_object(self, item):
        """if self._dontselectfromtree:
            #print("hmm")
            #self._dontselectfromtree = False
            return"""

        print("Selected:", item)
        self.level_view.selected = []
        self.level_view.selected_positions = []
        self.level_view.selected_rotations = []

        if isinstance(item, (tree_view.PaneItem, )):
            self.level_view.selected = [item.bound_to]

        self.level_view.do_redraw()
        self.level_view.select_update.emit()
        return

        if isinstance(item, (tree_view.CameraEntry, tree_view.RespawnEntry, tree_view.AreaEntry, tree_view.ObjectEntry,
                             tree_view.KartpointEntry, tree_view.EnemyRoutePoint, tree_view.ObjectRoutePoint)):
            bound_to = item.bound_to
            self.level_view.selected = [bound_to]
            self.level_view.selected_positions = [bound_to.position]

            if hasattr(bound_to, "rotation"):
                self.level_view.selected_rotations = [bound_to.rotation]

        elif isinstance(item, tree_view.Checkpoint):
            bound_to = item.bound_to
            self.level_view.selected = [bound_to]
            self.level_view.selected_positions = [bound_to.start, bound_to.end]
        elif isinstance(item, (tree_view.EnemyPointGroup, tree_view.CheckpointGroup, tree_view.ObjectPointGroup)):
            self.level_view.selected = [item.bound_to]
        elif isinstance(item, tree_view.BolHeader) and self.level_file is not None:
            self.level_view.selected = [self.level_file]
        elif isinstance(item, (tree_view.LightParamEntry, tree_view.MGEntry)):
            self.level_view.selected = [item.bound_to]

        #self.level_view.gizmo.move_to_average(self.level_view.selected_positions)
        self.level_view.do_redraw()
        self.level_view.select_update.emit()

    def setup_ui(self):
        self.resize(1000, 800)
        self.set_base_window_title("")

        self.setup_ui_menubar()
        self.setup_ui_toolbar()

        #self.centralwidget = QWidget(self)
        #self.centralwidget.setObjectName("centralwidget")

        self.horizontalLayout = QSplitter()
        self.centralwidget = self.horizontalLayout
        self.setCentralWidget(self.horizontalLayout)
        self.layoutdatatreeview = LayoutDataTreeView(self.centralwidget)
        #self.leveldatatreeview.itemClicked.connect(self.tree_select_object)
        self.layoutdatatreeview.itemDoubleClicked.connect(self.do_goto_action)
        self.layoutdatatreeview.itemSelectionChanged.connect(self.tree_select_arrowkey)

        self.level_view = BolMapViewer(self.centralwidget)

        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.addWidget(self.layoutdatatreeview)
        self.horizontalLayout.addWidget(self.level_view)
        self.layoutdatatreeview.resize(200, self.layoutdatatreeview.height())
        spacerItem = QSpacerItem(10, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        #self.horizontalLayout.addItem(spacerItem)

        self.pik_control = PikminSideWidget(self)
        self.horizontalLayout.addWidget(self.pik_control)

        QtWidgets.QShortcut(Qt.Key_G, self).activated.connect(self.action_ground_objects)
        #QtWidgets.QShortcut(Qt.CTRL + Qt.Key_A, self).activated.connect(self.shortcut_open_add_item_window)
        self.statusbar = QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        self.connect_actions()

    @catch_exception_with_dialog
    def setup_ui_menubar(self):
        self.menubar = QMenuBar(self)
        self.file_menu = QMenu(self)
        self.file_menu.setTitle("File")

        save_file_shortcut = QtWidgets.QShortcut(Qt.CTRL + Qt.Key_S, self.file_menu)
        save_file_shortcut.activated.connect(self.button_save_level)
        #QtWidgets.QShortcut(Qt.CTRL + Qt.Key_O, self.file_menu).activated.connect(self.button_load_level)
        #QtWidgets.QShortcut(Qt.CTRL + Qt.Key_Alt + Qt.Key_S, self.file_menu).activated.connect(self.button_save_level_as)

        self.file_load_action = QAction("Load", self)
        self.save_file_action = QAction("Save", self)
        self.save_file_as_action = QAction("Save As", self)
        self.save_file_action.setShortcut("Ctrl+S")
        self.file_load_action.setShortcut("Ctrl+O")
        self.save_file_as_action.setShortcut("Ctrl+Alt+S")

        self.file_load_action.triggered.connect(self.button_load_level)
        self.save_file_action.triggered.connect(self.button_save_level)
        self.save_file_as_action.triggered.connect(self.button_save_level_as)

        self.file_menu.addAction(self.file_load_action)
        self.file_menu.addAction(self.save_file_action)
        self.file_menu.addAction(self.save_file_as_action)

        self.visibility_menu = mkdd_widgets.FilterViewMenu(self)
        self.visibility_menu.filter_update.connect(self.update_render)


        # ------ Collision Menu
        self.collision_menu = QMenu(self.menubar)
        self.collision_menu.setTitle("Geometry")
        self.collision_load_action = QAction("Load OBJ", self)
        self.collision_load_action.triggered.connect(self.button_load_collision)
        self.collision_menu.addAction(self.collision_load_action)
        self.collision_load_grid_action = QAction("Load BCO", self)
        self.collision_load_grid_action.triggered.connect(self.button_load_collision_bco)
        self.collision_menu.addAction(self.collision_load_grid_action)
        self.collision_load_bmd_action = QAction("Load BMD", self)
        self.collision_load_bmd_action.triggered.connect(self.button_load_collision_bmd)
        self.collision_menu.addAction(self.collision_load_bmd_action)

        self.minimap_menu = QMenu(self.menubar)
        self.minimap_menu.setTitle("Minimap")
        load_minimap = QAction("Load Minimap Image", self)
        load_coordinates_dol = QAction("Load Data from DOL", self)
        save_coordinates_dol = QAction("Save Data to DOL", self)
        load_coordinates_json = QAction("Load Data from JSON", self)
        save_coordinates_json = QAction("Save Data to JSON", self)


        load_minimap.triggered.connect(self.action_load_minimap_image)
        load_coordinates_dol.triggered.connect(self.action_load_dol)
        save_coordinates_dol.triggered.connect(self.action_save_to_dol)
        load_coordinates_json.triggered.connect(self.action_load_coordinates_json)
        save_coordinates_json.triggered.connect(self.action_save_coordinates_json)
        self.minimap_menu.addAction(load_minimap)
        self.minimap_menu.addAction(load_coordinates_dol)
        self.minimap_menu.addAction(save_coordinates_dol)
        self.minimap_menu.addAction(load_coordinates_json)
        self.minimap_menu.addAction(save_coordinates_json)

        # Misc
        self.misc_menu = QMenu(self.menubar)
        self.misc_menu.setTitle("Misc")
        #self.spawnpoint_action = QAction("Set startPos/Dir", self)
        #self.spawnpoint_action.triggered.connect(self.action_open_rotationedit_window)
        #self.misc_menu.addAction(self.spawnpoint_action)
        self.rotation_mode = QAction("Rotate Positions around Pivot", self)
        self.rotation_mode.setCheckable(True)
        self.rotation_mode.setChecked(True)
        #self.goto_action.triggered.connect(self.do_goto_action)
        #self.goto_action.setShortcut("Ctrl+G")
        self.misc_menu.addAction(self.rotation_mode)
        self.analyze_action = QAction("Analyze for common mistakes", self)
        self.analyze_action.triggered.connect(self.analyze_for_mistakes)
        self.misc_menu.addAction(self.analyze_action)

        self.change_to_topdownview_action = QAction("Topdown View", self)
        self.change_to_topdownview_action.triggered.connect(self.change_to_topdownview)
        self.misc_menu.addAction(self.change_to_topdownview_action)
        self.change_to_topdownview_action.setCheckable(True)
        self.change_to_topdownview_action.setChecked(True)
        self.change_to_topdownview_action.setShortcut("Ctrl+1")

        self.change_to_3dview_action = QAction("3D View", self)
        self.change_to_3dview_action.triggered.connect(self.change_to_3dview)
        self.misc_menu.addAction(self.change_to_3dview_action)
        self.change_to_3dview_action.setCheckable(True)
        self.change_to_3dview_action.setShortcut("Ctrl+2")

        self.choose_bco_area = QAction("Highlight Collision Area (BCO)")
        self.choose_bco_area.triggered.connect(self.action_choose_bco_area)
        self.misc_menu.addAction(self.choose_bco_area)
        self.choose_bco_area.setShortcut("Ctrl+3")

        self.menubar.addAction(self.file_menu.menuAction())
        self.menubar.addAction(self.visibility_menu.menuAction())
        self.menubar.addAction(self.collision_menu.menuAction())
        self.menubar.addAction(self.minimap_menu.menuAction())
        self.menubar.addAction(self.misc_menu.menuAction())
        self.setMenuBar(self.menubar)

        self.last_obj_select_pos = 0

    def action_load_minimap_image(self):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            self.pathsconfig["minimap_png"],
            "Image (*.png);;All files (*)")

        if filepath:
            self.level_view.minimap.set_texture(filepath)

            self.pathsconfig["minimap_png"] = filepath
            save_cfg(self.configuration)

    @catch_exception_with_dialog
    def action_load_dol(self, val):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            self.pathsconfig["dol"],
            "Game Executable (*.dol);;All files (*)")

        if filepath:
            with open("lib/minimap_locations.json", "r") as f:
                addresses_json = json.load(f)

            with open(filepath, "rb") as f:
                dol = DolFile(f)
                region = detect_dol_region(dol)

            addresses = addresses_json[region]

            item_list = ["None"]
            item_list.extend(addresses.keys())
            result, pos = FileSelect.open_file_list(self, item_list, "Select Track Slot")

            if result == "None":
                return

            corner1x, corner1z, corner2x, corner2z, orientation = addresses[result]
            with open(filepath, "rb") as f:
                dol = DolFile(f)

                dol.seek(int(orientation, 16))
                orientation = read_load_immediate_r0(dol)
                if orientation not in (0, 1, 2, 3):
                    raise RuntimeError("Wrong Address, orientation value in DOL isn't in 0-3 range: {0}. Maybe you are using"
                                       " a dol from a different version?".format(orientation))
                self.level_view.minimap.orientation = orientation
                dol.seek(int(corner1x, 16))
                self.level_view.minimap.corner1.x = read_float(dol)
                dol.seek(int(corner1z, 16))
                self.level_view.minimap.corner1.z = read_float(dol)
                dol.seek(int(corner2x, 16))
                self.level_view.minimap.corner2.x = read_float(dol)
                dol.seek(int(corner2z, 16))
                self.level_view.minimap.corner2.z = read_float(dol)

            self.pathsconfig["dol"] = filepath
            save_cfg(self.configuration)

    @catch_exception_with_dialog
    def action_save_to_dol(self, val):
        filepath, choosentype = QFileDialog.getSaveFileName(
            self, "Save to File",
            self.pathsconfig["dol"],
            "Game Executable (*.dol);;All files (*)")

        if filepath:
            with open("lib/minimap_locations.json", "r") as f:
                addresses_json = json.load(f)

            with open(filepath, "rb") as f:
                dol = DolFile(f)
                region = detect_dol_region(dol)

            addresses = addresses_json[region]

            item_list = ["None"]
            item_list.extend(addresses.keys())
            result, pos = FileSelect.open_file_list(self, item_list, "Select Track Slot")

            if result == "None":
                return

            corner1x, corner1z, corner2x, corner2z, orientation = addresses[result]
            with open(filepath, "rb") as f:
                dol = DolFile(f)

            orientation_val = self.level_view.minimap.orientation
            if orientation_val not in (0, 1, 2, 3):
                raise RuntimeError(
                    "Invalid Orientation value: Must be in the range 0-3 but is {0}".format(orientation_val))

            dol.seek(int(orientation, 16))
            orientation_val = read_load_immediate_r0(dol)
            if orientation_val not in (0, 1, 2, 3):
                raise RuntimeError(
                    "Wrong Address, orientation value in DOL isn't in 0-3 range: {0}. Maybe you are using"
                    " a dol from a different game version?".format(orientation_val))

            dol.seek(int(orientation, 16))
            write_load_immediate_r0(dol, self.level_view.minimap.orientation)
            dol.seek(int(corner1x, 16))
            write_float(dol, self.level_view.minimap.corner1.x)
            dol.seek(int(corner1z, 16))
            write_float(dol, self.level_view.minimap.corner1.z)
            dol.seek(int(corner2x, 16))
            write_float(dol, self.level_view.minimap.corner2.x)
            dol.seek(int(corner2z, 16))
            write_float(dol, self.level_view.minimap.corner2.z)

            with open(filepath, "wb") as f:
                dol.save(f)

            self.pathsconfig["dol"] = filepath
            save_cfg(self.configuration)

    @catch_exception_with_dialog
    def action_load_coordinates_json(self, val):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            self.pathsconfig["minimap_json"],
            "Json File (*.json);;All files (*)")

        if filepath:
            with open(filepath, "r") as f:
                data = json.load(f)
                self.level_view.minimap.corner1.x = data["Top Left Corner X"]
                self.level_view.minimap.corner1.z = data["Top Left Corner Z"]
                self.level_view.minimap.corner2.x = data["Bottom Right Corner X"]
                self.level_view.minimap.corner2.z = data["Bottom Right Corner Z"]
                self.level_view.minimap.orientation = data["Orientation"]

            self.pathsconfig["minimap_json"] = filepath
            save_cfg(self.configuration)

    @catch_exception_with_dialog
    def action_save_coordinates_json(self, val):
        filepath, choosentype = QFileDialog.getSaveFileName(
            self, "Save File",
            self.pathsconfig["minimap_json"],
            "Json File (*.json);;All files (*)")

        if filepath:
            data = {"Top Left Corner X": self.level_view.minimap.corner1.x,
                    "Top Left Corner Z": self.level_view.minimap.corner1.z,
                    "Bottom Right Corner X": self.level_view.minimap.corner2.x,
                    "Bottom Right Corner Z": self.level_view.minimap.corner2.z,
                    "Orientation": self.level_view.minimap.orientation}

            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)

            self.pathsconfig["minimap_json"] = filepath
            save_cfg(self.configuration)

    def action_choose_bco_area(self):
        areas = []
        if isinstance(self.level_view.alternative_mesh, CollisionModel):
            for area in self.level_view.alternative_mesh.meshes.keys():
                areas.append(str(hex(area)))
        areas.sort(key=lambda x: int(x, 16))
        areas.insert(0, "None")

        result, pos = FileSelect.open_file_list(self, areas, "Select Collision Area")
        if result != "None":
            self.level_view.highlight_colltype = int(result, 16)
        else:
            self.level_view.highlight_colltype = None

    def analyze_for_mistakes(self):
        if self.analyzer_window is not None:
            self.analyzer_window.destroy()
            self.analyzer_window = None

        self.analyzer_window = ErrorAnalyzer(self.level_file)
        self.analyzer_window.show()

    def update_render(self):
        self.level_view.do_redraw()

    def change_to_topdownview(self):
        self.level_view.change_from_3d_to_topdown()
        self.change_to_topdownview_action.setChecked(True)
        self.change_to_3dview_action.setChecked(False)

    def change_to_3dview(self):
        self.level_view.change_from_topdown_to_3d()
        self.change_to_topdownview_action.setChecked(False)
        self.change_to_3dview_action.setChecked(True)
        self.statusbar.clearMessage()

    def setup_ui_toolbar(self):
        # self.toolbar = QtWidgets.QToolBar("Test", self)
        # self.toolbar.addAction(QAction("TestToolbar", self))
        # self.toolbar.addAction(QAction("TestToolbar2", self))
        # self.toolbar.addAction(QAction("TestToolbar3", self))

        # self.toolbar2 = QtWidgets.QToolBar("Second Toolbar", self)
        # self.toolbar2.addAction(QAction("I like cake", self))

        # self.addToolBar(self.toolbar)
        # self.addToolBarBreak()
        # self.addToolBar(self.toolbar2)
        pass

    def connect_actions(self):
        self.level_view.select_update.connect(self.action_update_info)
        self.level_view.select_update.connect(self.select_from_3d_to_treeview)
        #self.pik_control.lineedit_coordinatex.textChanged.connect(self.create_field_edit_action("coordinatex"))
        #self.pik_control.lineedit_coordinatey.textChanged.connect(self.create_field_edit_action("coordinatey"))
        #self.pik_control.lineedit_coordinatez.textChanged.connect(self.create_field_edit_action("coordinatez"))

        #self.pik_control.lineedit_rotationx.textChanged.connect(self.create_field_edit_action("rotationx"))
        #self.pik_control.lineedit_rotationy.textChanged.connect(self.create_field_edit_action("rotationy"))
        #self.pik_control.lineedit_rotationz.textChanged.connect(self.create_field_edit_action("rotationz"))

        self.level_view.position_update.connect(self.action_update_position)

        self.level_view.customContextMenuRequested.connect(self.mapview_showcontextmenu)

        self.pik_control.button_add_object.pressed.connect(self.button_open_add_item_window)
        #self.pik_control.button_move_object.pressed.connect(self.button_move_objects)
        self.level_view.move_points.connect(self.action_move_objects)
        self.level_view.height_update.connect(self.action_change_object_heights)
        self.level_view.create_waypoint.connect(self.action_add_object)
        self.level_view.create_waypoint_3d.connect(self.action_add_object_3d)
        self.pik_control.button_ground_object.pressed.connect(self.action_ground_objects)
        self.pik_control.button_remove_object.pressed.connect(self.action_delete_objects)

        delete_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self.action_delete_objects)

        undo_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.CTRL + Qt.Key_Z), self)
        undo_shortcut.activated.connect(self.action_undo)

        redo_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.CTRL + Qt.Key_Y), self)
        redo_shortcut.activated.connect(self.action_redo)

        self.level_view.rotate_current.connect(self.action_rotate_object)
        self.layoutdatatreeview.select_all.connect(self.select_all_of_group)
        self.layoutdatatreeview.reverse.connect(self.reverse_all_of_group)

    def reverse_all_of_group(self, item):
        group = item.bound_to
        if isinstance(group, libbol.CheckpointGroup):
            group.points.reverse()
            for point in group.points:
                start = point.start
                point.start = point.end
                point.end = start
        elif isinstance(group, libbol.EnemyPointGroup):
            group.points.reverse()
        elif isinstance(group, libbol.Route):
            group.points.reverse()

        self.leveldatatreeview.set_objects(self.level_file)
        self.update_3d()

    def select_all_of_group(self, item):
        group = item.bound_to
        self.level_view.selected = []
        self.level_view.selected_positions = []
        self.level_view.selected_rotations = []
        for point in group.points:
            self.level_view.selected.append(point)

            if isinstance(group, libbol.CheckpointGroup):
                self.level_view.selected_positions.append(point.start)
                self.level_view.selected_positions.append(point.end)
            else:
                self.level_view.selected_positions.append(point.position)
        self.update_3d()

    def action_open_rotationedit_window(self):
        if self.edit_spawn_window is None:
            self.edit_spawn_window = mkdd_widgets.SpawnpointEditor()
            self.edit_spawn_window.position.setText("{0}, {1}, {2}".format(
                self.pikmin_gen_file.startpos_x, self.pikmin_gen_file.startpos_y, self.pikmin_gen_file.startpos_z
            ))
            self.edit_spawn_window.rotation.setText(str(self.pikmin_gen_file.startdir))
            self.edit_spawn_window.closing.connect(self.action_close_edit_startpos_window)
            self.edit_spawn_window.button_savetext.pressed.connect(self.action_save_startpos)
            self.edit_spawn_window.show()

    #@catch_exception
    def button_load_level(self):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            self.pathsconfig["bol"],
            "BLO files (*.blo);;Archived files (*.arc);;All files (*)")

        if filepath:
            print("Resetting editor")
            self.reset()
            print("Reset done")
            print("Chosen file type:", choosentype)
            if choosentype == "Archived files (*.arc)" or filepath.endswith(".arc"):
                with open(filepath, "rb") as f:
                    try:
                        self.loaded_archive = Archive.from_file(f)
                        root_name = self.loaded_archive.root.name
                        coursename = find_file(self.loaded_archive.root, "_course.bol")
                        bol_file = self.loaded_archive[root_name + "/" + coursename]
                        bol_data = BOL.from_file(bol_file)
                        self.setup_bol_file(bol_data, filepath)
                        self.leveldatatreeview.set_objects(bol_data)
                        self.current_gen_path = filepath
                        self.loaded_archive_file = coursename
                    except Exception as error:
                        print("Error appeared while loading:", error)
                        traceback.print_exc()
                        open_error_dialog(str(error), self)
                        self.loaded_archive = None
                        self.loaded_archive_file = None
                        return

                    try:
                        additional_files = []
                        bmdfile = get_file_safe(self.loaded_archive.root, "_course.bmd")
                        collisionfile = get_file_safe(self.loaded_archive.root, "_course.bco")

                        if bmdfile is not None:
                            additional_files.append(os.path.basename(bmdfile.name) + " (3D Model)")
                        if collisionfile is not None:
                            additional_files.append(os.path.basename(collisionfile.name) + " (3D Collision)")

                        if len(additional_files) > 0:
                            additional_files.append("None")
                            self.load_optional_3d_file_arc(additional_files, bmdfile, collisionfile, filepath)
                    except Exception as error:
                        print("Error appeared while loading:", error)
                        traceback.print_exc()
                        open_error_dialog(str(error), self)

            else:
                with open(filepath, "rb") as f:
                    try:
                        blo_file = ScreenBlo.from_file(f)

                        self.setup_blo_file(blo_file, filepath)
                        self.layoutdatatreeview.set_objects(blo_file)
                        self.current_gen_path = filepath

                        """if filepath.endswith("_course.bol"):
                            filepath_base = filepath[:-11]
                            additional_files = []
                            bmdfile = filepath_base+"_course.bmd"
                            collisionfile = filepath_base+"_course.bco"
                            if os.path.exists(bmdfile):
                                additional_files.append(os.path.basename(bmdfile) + " (3D Model)")
                            if os.path.exists(collisionfile):
                                additional_files.append(os.path.basename(collisionfile) + " (3D Collision)")

                            if len(additional_files) > 0:
                                additional_files.append("None")
                                self.load_optional_3d_file(additional_files, bmdfile, collisionfile)"""

                    except Exception as error:
                        print("Error appeared while loading:", error)
                        traceback.print_exc()
                        open_error_dialog(str(error), self)

    def load_optional_3d_file(self, additional_files, bmdfile, collisionfile):
        choice, pos = FileSelect.open_file_list(self, additional_files,
                                                "Select additional file to load", startat=0)

        if choice.endswith("(3D Model)"):
            alternative_mesh = load_textured_bmd(bmdfile)
            with open("lib/temp/temp.obj", "r") as f:
                verts, faces, normals = py_obj.read_obj(f)

            self.setup_collision(verts, faces, bmdfile, alternative_mesh)

        elif choice.endswith("(3D Collision)"):
            bco_coll = RacetrackCollision()
            verts = []
            faces = []

            with open(collisionfile, "rb") as f:
                bco_coll.load_file(f)

            for vert in bco_coll.vertices:
                verts.append(vert)

            for v1, v2, v3, collision_type, rest in bco_coll.triangles:
                faces.append(((v1 + 1, None), (v2 + 1, None), (v3 + 1, None)))
            model = CollisionModel(bco_coll)
            self.setup_collision(verts, faces, collisionfile, alternative_mesh=model)

    def load_optional_3d_file_arc(self, additional_files, bmdfile, collisionfile, arcfilepath):
        choice, pos = FileSelect.open_file_list(self, additional_files,
                                                "Select additional file to load", startat=0)

        if choice.endswith("(3D Model)"):
            with open("lib/temp/temp.bmd", "wb") as f:
                f.write(bmdfile.getvalue())

            bmdpath = "lib/temp/temp.bmd"
            alternative_mesh = load_textured_bmd(bmdpath)
            with open("lib/temp/temp.obj", "r") as f:
                verts, faces, normals = py_obj.read_obj(f)

            self.setup_collision(verts, faces, arcfilepath, alternative_mesh)

        elif choice.endswith("(3D Collision)"):
            bco_coll = RacetrackCollision()
            verts = []
            faces = []

            bco_coll.load_file(collisionfile)

            for vert in bco_coll.vertices:
                verts.append(vert)

            for v1, v2, v3, collision_type, rest in bco_coll.triangles:
                faces.append(((v1 + 1, None), (v2 + 1, None), (v3 + 1, None)))
            model = CollisionModel(bco_coll)
            self.setup_collision(verts, faces, arcfilepath, alternative_mesh=model)

    def setup_blo_file(self, blo_file:ScreenBlo, filepath):
        self.layout_file = blo_file
        self.level_view.layout_file = self.layout_file
        # self.pikmin_gen_view.update()
        self.level_view.do_redraw()

        print("File loaded")
        # self.bw_map_screen.update()
        # path_parts = path.split(filepath)
        self.set_base_window_title(filepath)
        self.pathsconfig["bol"] = filepath
        save_cfg(self.configuration)
        self.current_gen_path = filepath

    @catch_exception_with_dialog
    def button_save_level(self, *args, **kwargs):
        if self.current_gen_path is not None:
            if self.loaded_archive is not None:
                assert self.loaded_archive_file is not None
                root_name = self.loaded_archive.root.name
                file = self.loaded_archive[root_name + "/" + self.loaded_archive_file]
                file.seek(0)

                self.level_file.write(file)

                with open(self.current_gen_path, "wb") as f:
                    self.loaded_archive.write_arc(f)

                self.set_has_unsaved_changes(False)
                self.statusbar.showMessage("Saved to {0}".format(self.current_gen_path))

            else:
                with open(self.current_gen_path, "wb") as f:
                    self.level_file.write(f)
                    self.set_has_unsaved_changes(False)

                    self.statusbar.showMessage("Saved to {0}".format(self.current_gen_path))
        else:
            self.button_save_level_as()

    @catch_exception_with_dialog
    def button_save_level_as(self, *args, **kwargs):
        filepath, choosentype = QFileDialog.getSaveFileName(
            self, "Save File",
            self.pathsconfig["bol"],
            "MKDD Track Data (*.bol);;Archived files (*.arc);;All files (*)")
        if filepath:
            if choosentype == "Archived files (*.arc)" or filepath.endswith(".arc"):
                if self.loaded_archive is None or self.loaded_archive_file is None:
                    with open(filepath, "rb") as f:
                        self.loaded_archive = Archive.from_file(f)

                self.loaded_archive_file = find_file(self.loaded_archive.root, "_course.bol")
                root_name = self.loaded_archive.root.name
                file = self.loaded_archive[root_name + "/" + self.loaded_archive_file]
                file.seek(0)

                self.level_file.write(file)

                with open(filepath, "wb") as f:
                    self.loaded_archive.write_arc(f)

                self.set_has_unsaved_changes(False)
                self.statusbar.showMessage("Saved to {0}".format(filepath))
            else:
                with open(filepath, "wb") as f:
                    self.level_file.write(f)

                    self.set_has_unsaved_changes(False)

            self.current_gen_path = filepath
            self.pathsconfig["bol"] = filepath
            save_cfg(self.configuration)
            self.statusbar.showMessage("Saved to {0}".format(filepath))

    def button_load_collision(self):
        try:
            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.pathsconfig["collision"],
                "Collision (*.obj);;All files (*)")

            if not filepath:
                return

            with open(filepath, "r") as f:
                verts, faces, normals = py_obj.read_obj(f)
            alternative_mesh = TexturedModel.from_obj_path(filepath, rotate=True)

            self.setup_collision(verts, faces, filepath, alternative_mesh)

        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), self)

    def button_load_collision_bmd(self):
        try:
            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.pathsconfig["collision"],
                "Course Model (*.bmd);;Archived files (*.arc);;All files (*)")

            if not filepath:
                return
            bmdpath = filepath
            clear_temp_folder()
            if choosentype == "Archived files (*.arc)" or filepath.endswith(".arc"):
                with open(filepath, "rb") as f:
                    rarc = Archive.from_file(f)

                root_name = rarc.root.name
                bmd_filename = find_file(rarc.root, "_course.bmd")
                bmd = rarc[root_name][bmd_filename]
                with open("lib/temp/temp.bmd", "wb") as f:
                    f.write(bmd.getvalue())

                bmdpath = "lib/temp/temp.bmd"
                

            alternative_mesh = load_textured_bmd(bmdpath)
            with open("lib/temp/temp.obj", "r") as f:
                verts, faces, normals = py_obj.read_obj(f)

            self.setup_collision(verts, faces, filepath, alternative_mesh)

        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), self)

    def button_load_collision_bco(self):
        try:
            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.pathsconfig["collision"],
                "MKDD Collision (*.bco);;Archived files (*.arc);;All files (*)")
            if filepath:
                bco_coll = RacetrackCollision()
                verts = []
                faces = []

                if choosentype == "Archived files (*.arc)" or filepath.endswith(".arc"):
                    with open(filepath, "rb") as f:
                        rarc = Archive.from_file(f)


                    root_name = rarc.root.name
                    collision_file = find_file(rarc.root, "_course.bco")
                    bco = rarc[root_name][collision_file]
                    bco_coll.load_file(bco)
                else:
                    with open(filepath, "rb") as f:
                        bco_coll.load_file(f)

                for vert in bco_coll.vertices:
                    verts.append(vert)

                for v1, v2, v3, collision_type, rest in bco_coll.triangles:
                    faces.append(((v1+1, None), (v2+1, None), (v3+1, None)))
                model = CollisionModel(bco_coll)
                self.setup_collision(verts, faces, filepath, alternative_mesh=model)

        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), self)

    def setup_collision(self, verts, faces, filepath, alternative_mesh=None):
        self.level_view.set_collision(verts, faces, alternative_mesh)
        self.pathsconfig["collision"] = filepath
        save_cfg(self.configuration)

    def action_close_edit_startpos_window(self):
        self.edit_spawn_window.destroy()
        self.edit_spawn_window = None

    @catch_exception_with_dialog
    def action_save_startpos(self):
        pos, direction = self.edit_spawn_window.get_pos_dir()
        self.pikmin_gen_file.startpos_x = pos[0]
        self.pikmin_gen_file.startpos_y = pos[1]
        self.pikmin_gen_file.startpos_z = pos[2]
        self.pikmin_gen_file.startdir = direction

        #self.pikmin_gen_view.update()
        self.pikmin_gen_view.do_redraw()
        self.set_has_unsaved_changes(True)

    def button_open_add_item_window(self):
        if self.add_object_window is None:
            self.add_object_window = AddPikObjectWindow()
            self.add_object_window.button_savetext.pressed.connect(self.button_add_item_window_save)
            self.add_object_window.closing.connect(self.button_add_item_window_close)
            print("hmmm")
            if self.addobjectwindow_last_selected is not None:
                self.add_object_window.category_menu.setCurrentIndex(self.addobjectwindow_last_selected_category)
                self.add_object_window.template_menu.setCurrentIndex(self.addobjectwindow_last_selected)

            self.add_object_window.show()

        elif self.level_view.mousemode == mkdd_widgets.MOUSE_MODE_ADDWP:
            self.level_view.set_mouse_mode(mkdd_widgets.MOUSE_MODE_NONE)
            self.pik_control.button_add_object.setChecked(False)

    def shortcut_open_add_item_window(self):
        if self.add_object_window is None:
            self.add_object_window = AddPikObjectWindow()
            self.add_object_window.button_savetext.pressed.connect(self.button_add_item_window_save)
            self.add_object_window.closing.connect(self.button_add_item_window_close)
            print("object")
            if self.addobjectwindow_last_selected is not None:
                self.add_object_window.category_menu.setCurrentIndex(self.addobjectwindow_last_selected_category)
                self.add_object_window.template_menu.setCurrentIndex(self.addobjectwindow_last_selected)


            self.add_object_window.show()

    @catch_exception
    def button_add_item_window_save(self):
        print("ohai")
        if self.add_object_window is not None:
            self.object_to_be_added = self.add_object_window.get_content()
            if self.object_to_be_added is None:
                return

            obj = self.object_to_be_added[0]

            if isinstance(obj, (libbol.EnemyPointGroup, libbol.CheckpointGroup, libbol.Route,
                                                    libbol.LightParam, libbol.MGEntry)):
                if isinstance(obj, libbol.EnemyPointGroup):
                    self.level_file.enemypointgroups.groups.append(obj)
                elif isinstance(obj, libbol.CheckpointGroup):
                    self.level_file.checkpoints.groups.append(obj)
                elif isinstance(obj, libbol.Route):
                    self.level_file.routes.append(obj)
                elif isinstance(obj, libbol.LightParam):
                    self.level_file.lightparams.append(obj)
                elif isinstance(obj, libbol.MGEntry):
                    self.level_file.lightparams.append(obj)

                self.addobjectwindow_last_selected_category = self.add_object_window.category_menu.currentIndex()
                self.object_to_be_added = None
                self.add_object_window.destroy()
                self.add_object_window = None
                self.leveldatatreeview.set_objects(self.level_file)

            elif self.object_to_be_added is not None:
                self.addobjectwindow_last_selected_category = self.add_object_window.category_menu.currentIndex()
                self.pik_control.button_add_object.setChecked(True)
                #self.pik_control.button_move_object.setChecked(False)
                self.level_view.set_mouse_mode(mkdd_widgets.MOUSE_MODE_ADDWP)
                self.add_object_window.destroy()
                self.add_object_window = None
                #self.pikmin_gen_view.setContextMenuPolicy(Qt.DefaultContextMenu)

    @catch_exception
    def button_add_item_window_close(self):
        # self.add_object_window.destroy()
        print("Hmmm")
        self.add_object_window = None
        self.pik_control.button_add_object.setChecked(False)
        self.level_view.set_mouse_mode(mkdd_widgets.MOUSE_MODE_NONE)

    @catch_exception
    def action_add_object(self, x, z):
        y = 0
        object, group, position = self.object_to_be_added
        #if self.editorconfig.getboolean("GroundObjectsWhenAdding") is True:
        if isinstance(object, libbol.Checkpoint):
            y = object.start.y
        else:
            if self.level_view.collision is not None:
                y_collided = self.level_view.collision.collide_ray_downwards(x, z)
                if y_collided is not None:
                    y = y_collided

        self.action_add_object_3d(x, y, z)

    @catch_exception
    def action_add_object_3d(self, x, y, z):
        object, group, position = self.object_to_be_added
        if position is not None and position < 0:
            position = 99999999 # this forces insertion at the end of the list

        if isinstance(object, libbol.Checkpoint):
            if len(self.last_position_clicked) == 1:
                placeobject = deepcopy(object)

                x1, y1, z1 = self.last_position_clicked[0]
                placeobject.start.x = x1
                placeobject.start.y = y1
                placeobject.start.z = z1

                placeobject.end.x = x
                placeobject.end.y = y
                placeobject.end.z = z
                self.last_position_clicked = []
                self.level_file.checkpoints.groups[group].points.insert(position, placeobject)
                self.level_view.do_redraw()
                self.set_has_unsaved_changes(True)
                self.leveldatatreeview.set_objects(self.level_file)
            else:
                self.last_position_clicked = [(x, y, z)]

        else:
            placeobject = deepcopy(object)
            placeobject.position.x = x
            placeobject.position.y = y
            placeobject.position.z = z

            if isinstance(object, libbol.EnemyPoint):
                placeobject.group = group
                self.level_file.enemypointgroups.groups[group].points.insert(position, placeobject)
            elif isinstance(object, libbol.RoutePoint):
                self.level_file.routes[group].points.insert(position, placeobject)
            elif isinstance(object, libbol.MapObject):
                self.level_file.objects.objects.append(placeobject)
            elif isinstance(object, libbol.KartStartPoint):
                self.level_file.kartpoints.positions.append(placeobject)
            elif isinstance(object, libbol.JugemPoint):
                self.level_file.respawnpoints.append(placeobject)
            elif isinstance(object, libbol.Area):
                self.level_file.areas.areas.append(placeobject)
            elif isinstance(object, libbol.Camera):
                self.level_file.cameras.append(placeobject)
            else:
                raise RuntimeError("Unknown object type {0}".format(type(object)))

            self.level_view.do_redraw()
            self.leveldatatreeview.set_objects(self.level_file)
            self.set_has_unsaved_changes(True)



    @catch_exception
    def action_move_objects(self, deltax, deltay, deltaz):
        for i in range(len(self.level_view.selected_positions)):
            for j in range(len(self.level_view.selected_positions)):
                pos = self.level_view.selected_positions
                if i != j and pos[i] == pos[j]:
                    print("What the fuck")
        for pos in self.level_view.selected_positions:
            """obj.x += deltax
            obj.z += deltaz
            obj.x = round(obj.x, 6)
            obj.z = round(obj.z, 6)
            obj.position_x = obj.x
            obj.position_z = obj.z
            obj.offset_x = 0
            obj.offset_z = 0

            if self.editorconfig.getboolean("GroundObjectsWhenMoving") is True:
                if self.pikmin_gen_view.collision is not None:
                    y = self.pikmin_gen_view.collision.collide_ray_downwards(obj.x, obj.z)
                    obj.y = obj.position_y = round(y, 6)
                    obj.offset_y = 0"""
            pos.x += deltax
            pos.y += deltay
            pos.z += deltaz

        #if len(self.pikmin_gen_view.selected) == 1:
        #    obj = self.pikmin_gen_view.selected[0]
        #    self.pik_control.set_info(obj, obj.position, obj.rotation)

        #self.pikmin_gen_view.update()
        self.level_view.do_redraw()
        self.pik_control.update_info()
        self.set_has_unsaved_changes(True)


    @catch_exception
    def action_change_object_heights(self, deltay):
        for obj in self.pikmin_gen_view.selected:
            obj.y += deltay
            obj.y = round(obj.y, 6)
            obj.position_y = obj.y
            obj.offset_y = 0

        if len(self.pikmin_gen_view.selected) == 1:
            obj = self.pikmin_gen_view.selected[0]
            self.pik_control.set_info(obj, (obj.x, obj.y, obj.z), obj.get_rotation())

        #self.pikmin_gen_view.update()
        self.pikmin_gen_view.do_redraw()
        self.set_has_unsaved_changes(True)

    def keyPressEvent(self, event: QtGui.QKeyEvent):

        if event.key() == Qt.Key_Escape:
            self.level_view.set_mouse_mode(mkdd_widgets.MOUSE_MODE_NONE)
            self.pik_control.button_add_object.setChecked(False)
            #self.pik_control.button_move_object.setChecked(False)
            if self.add_object_window is not None:
                self.add_object_window.close()

        if event.key() == Qt.Key_Shift:
            self.level_view.shift_is_pressed = True
        elif event.key() == Qt.Key_R:
            self.level_view.rotation_is_pressed = True
        elif event.key() == Qt.Key_H:
            self.level_view.change_height_is_pressed = True

        if event.key() == Qt.Key_W:
            self.level_view.MOVE_FORWARD = 1
        elif event.key() == Qt.Key_S:
            self.level_view.MOVE_BACKWARD = 1
        elif event.key() == Qt.Key_A:
            self.level_view.MOVE_LEFT = 1
        elif event.key() == Qt.Key_D:
            self.level_view.MOVE_RIGHT = 1
        elif event.key() == Qt.Key_Q:
            self.level_view.MOVE_UP = 1
        elif event.key() == Qt.Key_E:
            self.level_view.MOVE_DOWN = 1

        if event.key() == Qt.Key_Plus:
            self.level_view.zoom_in()
        elif event.key() == Qt.Key_Minus:
            self.level_view.zoom_out()

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key_Shift:
            self.level_view.shift_is_pressed = False
        elif event.key() == Qt.Key_R:
            self.level_view.rotation_is_pressed = False
        elif event.key() == Qt.Key_H:
            self.level_view.change_height_is_pressed = False

        if event.key() == Qt.Key_W:
            self.level_view.MOVE_FORWARD = 0
        elif event.key() == Qt.Key_S:
            self.level_view.MOVE_BACKWARD = 0
        elif event.key() == Qt.Key_A:
            self.level_view.MOVE_LEFT = 0
        elif event.key() == Qt.Key_D:
            self.level_view.MOVE_RIGHT = 0
        elif event.key() == Qt.Key_Q:
            self.level_view.MOVE_UP = 0
        elif event.key() == Qt.Key_E:
            self.level_view.MOVE_DOWN = 0

    def action_rotate_object(self, deltarotation):
        #obj.set_rotation((None, round(angle, 6), None))
        for rot in self.level_view.selected_rotations:
            if deltarotation.x != 0:
                rot.rotate_around_y(deltarotation.x)
            elif deltarotation.y != 0:
                rot.rotate_around_z(deltarotation.y)
            elif deltarotation.z != 0:
                rot.rotate_around_x(deltarotation.z)

        if self.rotation_mode.isChecked():
            middle = self.level_view.gizmo.position

            for position in self.level_view.selected_positions:
                diff = position - middle
                diff.y = 0.0

                length = diff.norm()
                if length > 0:
                    diff.normalize()
                    angle = atan2(diff.x, diff.z)
                    angle += deltarotation.y
                    position.x = middle.x + length * sin(angle)
                    position.z = middle.z + length * cos(angle)

        """
        if len(self.pikmin_gen_view.selected) == 1:
            obj = self.pikmin_gen_view.selected[0]
            self.pik_control.set_info(obj, obj.position, obj.rotation)
        """
        #self.pikmin_gen_view.update()
        self.level_view.do_redraw()
        self.set_has_unsaved_changes(True)
        self.pik_control.update_info()

    def action_ground_objects(self):
        for pos in self.level_view.selected_positions:
            if self.level_view.collision is None:
                return None
            height = self.level_view.collision.collide_ray_closest(pos.x, pos.z, pos.y)

            if height is not None:
                pos.y = height

        self.pik_control.update_info()
        self.level_view.gizmo.move_to_average(self.level_view.selected_positions)
        self.set_has_unsaved_changes(True)
        self.level_view.do_redraw()

    def action_delete_objects(self):
        tobedeleted = []
        for obj in self.level_view.selected:
            if isinstance(obj, libbol.EnemyPoint):
                for group in self.level_file.enemypointgroups.groups:
                    if obj in group.points:
                        group.points.remove(obj)
                        break

            elif isinstance(obj, libbol.RoutePoint):
                for route in self.level_file.routes:
                    if obj in route.points:
                        route.points.remove(obj)
                        break

            elif isinstance(obj, libbol.Checkpoint):
                for group in self.level_file.checkpoints.groups:
                    if obj in group.points:
                        group.points.remove(obj)
                        break

            elif isinstance(obj, libbol.MapObject):
                self.level_file.objects.objects.remove(obj)
            elif isinstance(obj, libbol.KartStartPoint):
                self.level_file.kartpoints.positions.remove(obj)
            elif isinstance(obj, libbol.JugemPoint):
                self.level_file.respawnpoints.remove(obj)
            elif isinstance(obj, libbol.Area):
                self.level_file.areas.areas.remove(obj)
            elif isinstance(obj, libbol.Camera):
                self.level_file.cameras.remove(obj)
            elif isinstance(obj, libbol.CheckpointGroup):
                self.level_file.checkpoints.groups.remove(obj)
            elif isinstance(obj, libbol.EnemyPointGroup):
                self.level_file.enemypointgroups.groups.remove(obj)
            elif isinstance(obj, libbol.Route):
                self.level_file.routes.remove(obj)
            elif isinstance(obj, libbol.LightParam):
                self.level_file.lightparams.remove(obj)
            elif isinstance(obj, libbol.MGEntry):
                self.level_file.mgentries.remove(obj)
        self.level_view.selected = []
        self.level_view.selected_positions = []
        self.level_view.selected_rotations = []

        self.pik_control.reset_info()
        self.leveldatatreeview.set_objects(self.level_file)
        self.level_view.gizmo.hidden = True
        #self.pikmin_gen_view.update()
        self.level_view.do_redraw()
        self.set_has_unsaved_changes(True)

    @catch_exception
    def action_undo(self):
        res = self.history.history_undo()
        if res is None:
            return
        action, val = res

        if action == "AddObject":
            obj = val
            self.pikmin_gen_file.generators.remove(obj)
            if obj in self.editing_windows:
                self.editing_windows[obj].destroy()
                del self.editing_windows[obj]

            if len(self.pikmin_gen_view.selected) == 1 and self.pikmin_gen_view.selected[0] is obj:
                self.pik_control.reset_info()
            elif obj in self.pik_control.objectlist:
                self.pik_control.reset_info()
            if obj in self.pikmin_gen_view.selected:
                self.pikmin_gen_view.selected.remove(obj)
                self.pikmin_gen_view.gizmo.hidden = True

            #self.pikmin_gen_view.update()
            self.pikmin_gen_view.do_redraw()

        if action == "RemoveObjects":
            for obj in val:
                self.pikmin_gen_file.generators.append(obj)

            #self.pikmin_gen_view.update()
            self.pikmin_gen_view.do_redraw()
        self.set_has_unsaved_changes(True)

    @catch_exception
    def action_redo(self):
        res = self.history.history_redo()
        if res is None:
            return

        action, val = res

        if action == "AddObject":
            obj = val
            self.pikmin_gen_file.generators.append(obj)

            #self.pikmin_gen_view.update()
            self.pikmin_gen_view.do_redraw()

        if action == "RemoveObjects":
            for obj in val:
                self.pikmin_gen_file.generators.remove(obj)
                if obj in self.editing_windows:
                    self.editing_windows[obj].destroy()
                    del self.editing_windows[obj]

                if len(self.pikmin_gen_view.selected) == 1 and self.pikmin_gen_view.selected[0] is obj:
                    self.pik_control.reset_info()
                elif obj in self.pik_control.objectlist:
                    self.pik_control.reset_info()
                if obj in self.pikmin_gen_view.selected:
                    self.pikmin_gen_view.selected.remove(obj)
                    self.pikmin_gen_view.gizmo.hidden = True

            #self.pikmin_gen_view.update()
            self.pikmin_gen_view.do_redraw()
        self.set_has_unsaved_changes(True)

    def update_3d(self):
        self.level_view.gizmo.move_to_average(self.level_view.selected_positions)
        self.level_view.do_redraw()

    def select_from_3d_to_treeview(self):
        if self.level_file is not None:
            selected = self.level_view.selected
            if len(selected) == 1:
                currentobj = selected[0]
                item = None
                if isinstance(currentobj, libbol.EnemyPoint):
                    for i in range(self.leveldatatreeview.enemyroutes.childCount()):
                        child = self.leveldatatreeview.enemyroutes.child(i)
                        item = get_treeitem(child, currentobj)
                        if item is not None:
                            break

                    """elif isinstance(currentobj, libbol.Checkpoint):
                    for i in range(self.leveldatatreeview.checkpointgroups.childCount()):
                        child = self.leveldatatreeview.checkpointgroups.child(i)
                        item = get_treeitem(child, currentobj)
                        if item is not None:
                            break"""

                elif isinstance(currentobj, libbol.RoutePoint):
                    for i in range(self.leveldatatreeview.objectroutes.childCount()):
                        child = self.leveldatatreeview.objectroutes.child(i)
                        item = get_treeitem(child, currentobj)
                        if item is not None:
                            break

                elif isinstance(currentobj, libbol.MapObject):
                    item = get_treeitem(self.leveldatatreeview.objects, currentobj)
                elif isinstance(currentobj, libbol.Camera):
                    item = get_treeitem(self.leveldatatreeview.cameras, currentobj)
                elif isinstance(currentobj, libbol.Area):
                    item = get_treeitem(self.leveldatatreeview.areas, currentobj)
                elif isinstance(currentobj, libbol.JugemPoint):
                    item = get_treeitem(self.leveldatatreeview.respawnpoints, currentobj)
                elif isinstance(currentobj, libbol.KartStartPoint):
                    item = get_treeitem(self.leveldatatreeview.kartpoints, currentobj)

                #assert item is not None
                if item is not None:
                    #self._dontselectfromtree = True
                    self.leveldatatreeview.setCurrentItem(item)

    @catch_exception
    def action_update_info(self):
        if self.level_file is not None:
            selected = self.level_view.selected
            if len(selected) == 1:
                currentobj = selected[0]
                if isinstance(currentobj, Route):
                    objects = []
                    index = self.level_file.routes.index(currentobj)
                    for object in self.level_file.objects.objects:
                        if object.pathid == index:
                            objects.append(get_full_name(object.objectid))
                    for i, camera in enumerate(self.level_file.cameras):
                        if camera.route == index:
                            objects.append("Camera {0}".format(i))

                    self.pik_control.set_info(currentobj, self.update_3d, objects)
                else:
                    self.pik_control.set_info(currentobj, self.update_3d)

                self.pik_control.update_info()
            else:
                self.pik_control.reset_info("{0} objects selected".format(len(self.level_view.selected)))
                self.pik_control.set_objectlist(selected)

    @catch_exception
    def mapview_showcontextmenu(self, position):
        context_menu = QMenu(self)
        action = QAction("Copy Coordinates", self)
        action.triggered.connect(self.action_copy_coords_to_clipboard)
        context_menu.addAction(action)
        context_menu.exec(self.mapToGlobal(position))
        context_menu.destroy()

    def action_copy_coords_to_clipboard(self):
        if self.current_coordinates is not None:
            QApplication.clipboard().setText(", ".join(str(x) for x in self.current_coordinates))

    def action_update_position(self, event, pos):
        self.current_coordinates = pos
        self.statusbar.showMessage(str(pos))


class EditorHistory(object):
    def __init__(self, historysize):
        self.history = []
        self.step = 0
        self.historysize = historysize

    def reset(self):
        del self.history
        self.history = []
        self.step = 0

    def _add_history(self, entry):
        if self.step == len(self.history):
            self.history.append(entry)
            self.step += 1
        else:
            for i in range(len(self.history) - self.step):
                self.history.pop()
            self.history.append(entry)
            self.step += 1
            assert len(self.history) == self.step

        if len(self.history) > self.historysize:
            for i in range(len(self.history) - self.historysize):
                self.history.pop(0)
                self.step -= 1

    def add_history_addobject(self, pikobject):
        self._add_history(("AddObject", pikobject))

    def add_history_removeobjects(self, objects):
        self._add_history(("RemoveObjects", objects))

    def history_undo(self):
        if self.step == 0:
            return None

        self.step -= 1
        return self.history[self.step]

    def history_redo(self):
        if self.step == len(self.history):
            return None

        item = self.history[self.step]
        self.step += 1
        return item

def find_file(rarc_folder, ending):
    for filename in rarc_folder.files.keys():
        if filename.endswith(ending):
            return filename
    raise RuntimeError("No Course File found!")


def get_file_safe(rarc_folder, ending):
    for filename in rarc_folder.files.keys():
        if filename.endswith(ending):
            return rarc_folder.files[filename]
    return None


import sys
def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)



if __name__ == "__main__":
    #import sys
    import platform
    import argparse
    from PyQt5.QtCore import QLocale

    QLocale.setDefault(QLocale(QLocale.English))

    sys.excepthook = except_hook

    parser = argparse.ArgumentParser()
    parser.add_argument("--inputgen", default=None,
                        help="Path to generator file to be loaded.")
    parser.add_argument("--collision", default=None,
                        help="Path to collision to be loaded.")
    parser.add_argument("--waterbox", default=None,
                        help="Path to waterbox file to be loaded.")

    args = parser.parse_args()

    app = QApplication(sys.argv)

    if platform.system() == "Windows":
        import ctypes
        myappid = 'P2GeneratorsEditor'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    with open("log.txt", "w") as f:
        #sys.stdout = f
        #sys.stderr = f
        print("Python version: ", sys.version)
        pikmin_gui = LayoutEditor()
        pikmin_gui.setWindowIcon(QtGui.QIcon('resources/icon.ico'))

        if args.inputgen is not None:
            with open(args.inputgen, "r", encoding="shift_jis-2004", errors="backslashreplace") as f:
                pikmin_gen_file = PikminGenFile()
                pikmin_gen_file.from_file(f)

            pikmin_gui.setup_gen_file(pikmin_gen_file, args.inputgen)

        pikmin_gui.show()

        if args.collision is not None:
            if args.collision.endswith(".obj"):
                with open(args.collision, "r") as f:
                    verts, faces, normals = py_obj.read_obj(f)

            elif args.collision.endswith(".bin"):
                with open(args.collision, "rb") as f:
                    collision = py_obj.PikminCollision(f)
                verts = collision.vertices
                faces = [face[0] for face in collision.faces]

            elif args.collision.endswith(".szs") or args.collision.endswith(".arc"):
                with open(args.collision, "rb") as f:
                    archive = Archive.from_file(f)
                f = archive["text/grid.bin"]
                collision = py_obj.PikminCollision(f)

                verts = collision.vertices
                faces = [face[0] for face in collision.faces]

            else:
                raise RuntimeError("Unknown collision file type:", args.collision)

            pikmin_gui.setup_collision(verts, faces, args.collision)

        if args.waterbox is not None:
            if args.waterbox.endswith(".txt"):
                with open(args.waterbox, "r", encoding="shift_jis-2004", errors="backslashreplace") as f:
                    waterboxfile = WaterboxTxt()
                    waterboxfile.from_file(f)
            elif args.waterbox.endswith(".szs") or args.waterbox.endwith(".arc"):
                with open(args.waterbox, "rb") as f:
                    archive = Archive.from_file(f)
                    # try:
                    f = archive["text/waterbox.txt"]
                    # print(f.read())
                    f.seek(0)
                    waterboxfile = WaterboxTxt()
                    waterboxfile.from_file(TextIOWrapper(f, encoding="shift_jis-2004", errors="backslashreplace"))
            else:
                raise RuntimeError("Unknown waterbox file type:", args.waterbox)

            pikmin_gui.setup_waterboxes(waterboxfile)

        err_code = app.exec()

    sys.exit(err_code)