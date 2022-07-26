from io import BytesIO
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt, QRect, QModelIndex, pyqtSignal

from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog, QSplitter, QCheckBox, QDialog,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QApplication, QStatusBar, QLineEdit, QComboBox,
                             QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem, QActionGroup)

from PyQt5.QtGui import QMouseEvent, QImage, QIcon
import PyQt5.QtGui as QtGui

import widgets.bckwidget.j3d_animation_editor.animations.general_animation as j3d

import widgets.bckwidget.j3d_animation_editor.widgets.create_anim as create_widget
import widgets.bckwidget.j3d_animation_editor.widgets.tree_view as tree_view
import widgets.bckwidget.j3d_animation_editor.widgets.tree_item as tree_item
import widgets.bckwidget.j3d_animation_editor.widgets.add_frames as frames_widget
import widgets.bckwidget.j3d_animation_editor.widgets.mass_edit as maedit_widget
import widgets.bckwidget.j3d_animation_editor.widgets.open_folder as folder_widget
import widgets.bckwidget.j3d_animation_editor.widgets.select_model as select_widget
import widgets.bckwidget.j3d_animation_editor.widgets.sound_editor as sounds_widget
from widgets.bckwidget.j3d_animation_editor.widgets.theme_handler import themed_window
import glob
from os import path
from configparser import ConfigParser
import json, csv
from widgets.bckwidget.bck import BCKFile
from widgets.bckwidget.j3d_animation_editor.widgets.tree_item import JointItem
from widgets.editor_widgets import open_error_dialog, catch_exception_with_dialog
from widgets.file_select import FileSelect

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from blo_editor import LayoutEditor


class GenEditor(QMainWindow, themed_window):
    closing = pyqtSignal()

    def __init__(self, blo_editor):
    
        super().__init__()

        self.blo_editor: LayoutEditor = blo_editor

        self.copied_values = []
        self.curr_index = 0
        self.prev_index = 0
        self.is_remove = False
        
        self.create_window = None
        self.frames_window = None
        self.maedit_window = None
        self.folder_window = None
        self.sounds_window = None
        
        self.create_box = None
        self.frames_box = None
        self.maedit_box = None
        self.sounds_box = None
        
        self.sound_enabled = False
        
        self.compression = 0
        
        self.popout = True
        self.theme = "default"
        self.include_subdirs = False
        self.load_model = False
        
        self.bvh_as_bca = False
         
        self.setAcceptDrops(True)
        self.setup_ui()

        self.animation = None

        self.archive_loaded_file = None

    def setup_ui(self):
        self.resize(1280, 720)
        self.resize_mw=QAction()
        
        self.setWindowTitle("j3d animation editor")
        self.setup_ui_menubar()
        self.setup_ui_main()
        self.edit_gui()
        self.read_settings_ini()
        
        
        self.show()
    
    def setup_ui_menubar(self):
        
        #file stuff
        self.menubar = QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 200, 50))
        self.menubar.setObjectName("menubar")
        
        #file menu
        self.file_menu = QMenu(self)
        self.file_menu.setTitle("File")

        save_file_shortcut = QtWidgets.QShortcut(Qt.CTRL + Qt.Key_S, self.file_menu)

        
        self.file_load_action = QAction("Load", self)
        self.file_load_archive = QAction("Load from Current Archive", self)
        self.save_file_parent = QMenu("Save...", self)
        
        self.save_file_action = QAction("Save", self)
        self.save_file_as_action = QAction("Save As", self)
        self.save_file_all_action = QAction("Save All", self)
        
        self.save_file_parent.addAction(self.save_file_action)
        self.save_file_parent.addAction(self.save_file_as_action)
        self.save_file_parent.addAction(self.save_file_all_action)
        
        
        self.create_animation = QAction("Create Animation", self)
        #self.combine_animations = QAction("Combine Animations", self)
        self.disable_compression_menu = QMenu("Set Compression Level", self)
        self.compression_group = QActionGroup(self)
        self.compression_group.setExclusive(True)
        
        self.auto_compression = QAction("Auto Compression", self, checkable = True)
        self.auto_compression.setChecked(True);
        self.no_compression = QAction("No Compression", self, checkable = True)
        self.low_compression = QAction("Little Compression", self, checkable = True)
        self.mid_compression = QAction("Moderate Compression", self, checkable = True)
        self.high_compression = QAction("Maximum Compression", self, checkable = True)
        
        self.disable_compression_menu.addAction(self.auto_compression)
        self.disable_compression_menu.addSeparator()
        self.disable_compression_menu.addAction(self.no_compression)
        self.disable_compression_menu.addAction(self.low_compression)
        self.disable_compression_menu.addAction(self.mid_compression)
        self.disable_compression_menu.addAction(self.high_compression)
        
        self.compression_group.addAction(self.auto_compression)
        self.compression_group.addAction(self.no_compression)
        self.compression_group.addAction(self.low_compression)
        self.compression_group.addAction(self.mid_compression)
        self.compression_group.addAction(self.high_compression)
        

        self.save_file_action.setShortcut("Ctrl+S")
        self.file_load_action.setShortcut("Ctrl+O")
        self.file_load_archive.setShortcut("Shift+Ctrl+O")
        self.save_file_as_action.setShortcut("Ctrl+Alt+S")
        self.save_file_all_action.setShortcut("Shift+Ctrl+S")
        self.create_animation.setShortcut("Ctrl+N")

        self.file_load_action.triggered.connect(self.button_load_level)
        self.file_load_archive.triggered.connect(self.button_load_from_arc)
        self.save_file_action.triggered.connect(self.button_save_level)
        self.save_file_as_action.triggered.connect(self.button_save_as)
        self.save_file_all_action.triggered.connect(self.button_save_all)
        self.create_animation.triggered.connect(lambda: self.create_new(one_time = True))
        
        self.auto_compression.triggered.connect(lambda: self.set_compression_level(0))
        self.no_compression.triggered.connect(lambda: self.set_compression_level(1))
        self.low_compression.triggered.connect(lambda: self.set_compression_level(2))
        self.mid_compression.triggered.connect(lambda: self.set_compression_level(3))
        self.high_compression.triggered.connect(lambda: self.set_compression_level(4))
          
        
        
        #self.combine_animations.triggered.connct(self.combine_anims)

        self.file_menu.addAction(self.file_load_action)
        self.file_menu.addAction(self.file_load_archive)
        self.file_menu.addMenu(self.save_file_parent)
        #self.file_menu.addAction(self.save_file_action)
        #self.file_menu.addAction(self.save_file_as_action) 
        #self.file_menu.addAction(self.save_file_all_action)
        self.file_menu.addAction(self.create_animation)
        #self.file_menu.addAction(self.combine_animations)
        self.file_menu.addSeparator()
        self.file_menu.addMenu(self.disable_compression_menu)
 
        self.menubar.addAction(self.file_menu.menuAction())
        self.setMenuBar(self.menubar)    
        
        #view menu
        
        self.view_menu = QMenu(self)
        self.view_menu.setTitle("View")
        
        self.toggle_dark_theme_menu = QMenu("Choose Theme", self) # give different theme options
        
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        
        self.normal_theme = QAction("Default Theme (Light)", self, checkable = True)
        self.dark_theme = QAction("Dark Theme", self, checkable = True)
        self.fall_theme = QAction("Fall Theme", self, checkable = True)
        self.toadette_theme = QAction("Toadette Theme", self, checkable = True)
        self.peaches_theme = QAction("Peaches and Plums", self, checkable = True)
        self.toggle_dark_theme_menu.addAction(self.normal_theme)
        self.toggle_dark_theme_menu.addAction(self.dark_theme)
        self.toggle_dark_theme_menu.addAction(self.fall_theme)
        self.toggle_dark_theme_menu.addAction(self.toadette_theme)
        self.toggle_dark_theme_menu.addAction(self.peaches_theme)
        
        self.theme_group.addAction(self.normal_theme)
        self.theme_group.addAction(self.dark_theme)
        self.theme_group.addAction(self.fall_theme)
        self.theme_group.addAction(self.toadette_theme)
        self.theme_group.addAction(self.peaches_theme)
 
        self.normal_theme.triggered.connect(lambda: self.toggle_dark_theme() )
        self.dark_theme.triggered.connect(lambda: self.toggle_theme("./themes/dark.qss") )
        self.fall_theme.triggered.connect(lambda: self.toggle_theme("./themes/fall.qss") )
        self.toadette_theme.triggered.connect(lambda: self.toggle_theme("./themes/toadette.qss") )
        self.peaches_theme.triggered.connect(lambda: self.toggle_theme("./themes/peaches and plums.qss") )
        
        self.sep_window = QAction("Pop Out Windows", self, checkable = True)
        #self.sep_window.setChecked(True)
        self.sep_window.triggered.connect( self.set_popout)
        
        self.show_widget = QMenu("Show Feature")
        self.show_widget.menuAction().setStatusTip("Requires Pop Out Windows to be turned off")
        
        self.show_create = QAction("Create Animation", self, checkable = True)
        self.show_frames = QAction("Frames Editor", self, checkable = True)
        self.show_maedit = QAction("Mass Animation Editor", self, checkable = True)

        self.show_create.triggered.connect( self.toggle_show_create )
        self.show_frames.triggered.connect( self.toggle_show_frames )
        self.show_maedit.triggered.connect( self.toggle_show_maedit )
        
        self.show_widget.addAction( self.show_create )
        self.show_widget.addAction( self.show_frames )
        self.show_widget.addAction( self.show_maedit )
       
        self.view_menu.addMenu(self.toggle_dark_theme_menu) # add the button to the view menu
        self.view_menu.addAction(self.sep_window)
        self.view_menu.addMenu(self.show_widget)
        
        
        self.menubar.addAction(self.view_menu.menuAction() )
        
        #edit menu
        
        self.edit_menu = QMenu(self)
        self.edit_menu.setTitle("Edit")

        self.copy_cells_action = QAction("Copy Selected Cells", self)
        self.paste_cells_action = QAction("Paste Selected Cells", self)  
        self.clear_cells_action = QAction("Clear Selected Cells", self)
        self.select_all_action = QAction("Select All Cells", self)
        self.select_all_action = QAction("Select All Cells", self)
        self.remove_dups_action = QAction("Remove Duplicate Frames", self)
        self.flip_poster = QAction("Flip Poster-Like", self)
        
        self.copy_cells_action.triggered.connect(self.emit_copy_cells)
        self.paste_cells_action.triggered.connect(self.emit_paste_cells)
        self.clear_cells_action.triggered.connect(self.emit_clear_cells)
        self.select_all_action.triggered.connect(self.emit_select_all)
        self.remove_dups_action.triggered.connect(self.emit_remove_dups)
        
        self.copy_cells_action.setShortcut("Ctrl+C")
        self.paste_cells_action.setShortcut("Ctrl+V")
        self.clear_cells_action.setShortcut("Delete")
        self.select_all_action.setShortcut("Ctrl+A")
        
        
        self.remove_row_end = QAction("Remove Row from End", self)
        self.remove_row_end.triggered.connect(self.rem_row)
        
        self.remove_row_here = QAction("Remove Current Row", self)
        self.remove_row_here.triggered.connect(self.rem_row_here)
        
        self.add_row_end = QAction("Add Row to End", self)
        self.add_row_end.triggered.connect(self.add_row)
        
        self.add_row_next = QAction("Add Row Here", self)
        self.add_row_next.triggered.connect(self.add_row_here)
        
      
        self.edit_menu.addAction(self.copy_cells_action)
        self.edit_menu.addAction(self.paste_cells_action)
        self.edit_menu.addAction(self.clear_cells_action)
        self.edit_menu.addAction(self.select_all_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.add_row_end)
        self.edit_menu.addAction(self.add_row_next)
        self.edit_menu.addAction(self.remove_row_end)
        self.edit_menu.addAction(self.remove_row_here)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.remove_dups_action)
        
        
        
        
        
        self.menubar.addAction(self.edit_menu.menuAction())
        
        #convert menu
        self.convert = QMenu(self)
        self.convert.setTitle("Convert")
        
        self.convert_to_key = QAction("Save as .bck / .blk", self)
        self.convert_to_all = QAction("Save as .bca / .bla", self)
        
        self.import_csv = QAction("Import .csv", self)
        self.export_csv = QAction("Export .csv", self)
        
        
        self.convert_to_key.triggered.connect(self.convert_to_k)
        self.convert_to_all.triggered.connect(self.convert_to_a)
        
        self.import_csv.triggered.connect(self.import_csv_file)
        self.export_csv.triggered.connect(self.export_csv_file)
        
        
        self.convert_to_key.setShortcut("Ctrl+K")
        
        self.convert.addAction(self.convert_to_key)
        self.convert.addAction(self.convert_to_key)
        self.convert.addAction(self.convert_to_all)
        
        self.convert_to_key.setDisabled(True)
        self.convert_to_all.setDisabled(True)
        
        
        self.menubar.addAction(self.convert.menuAction())
        
        
        #mass edit
        self.mass_edit = QMenu(self)
        self.mass_edit.setTitle("Mass Editing")
        #self.mass_edit.triggered.connect(lambda: self.maedit_dialogue(one_time = True))
        
        self.mass_edit_action = QAction(self)
        self.mass_edit_action.setText("Mass Animation Editor")
        self.mass_edit_action.triggered.connect(lambda: self.maedit_dialogue(one_time = True))
        self.mass_edit_action.setShortcut("Ctrl + M")
        
        self.mass_edit_file = QAction(self)
        self.mass_edit_file.setText("Mass Edit from File")
        self.mass_edit_file.triggered.connect( self.maedit_file )
        self.mass_edit_file.setShortcut("Shift + Ctrl + M")
        
        self.mass_edit.addAction(self.mass_edit_action)
        self.mass_edit.addAction(self.mass_edit_file)
        
        self.menubar.addMenu(self.mass_edit)
        
    def setup_ui_main(self):
        #main splitter
        
        self.horizontalLayout = QSplitter()
        self.centralwidget = self.horizontalLayout
        self.setCentralWidget(self.horizontalLayout)
        
        #left sidebar
        self.workaroundl = QWidget(self)
        self.left_vbox = QVBoxLayout(self.workaroundl)
        
        #tree view
        
        self.anim_bar = tree_view.animation_bar(self.workaroundl)      
        self.anim_bar.set_main_editor(self)
        self.anim_bar.itemSelectionChanged.connect(self.selected_animation_changed) 
   
        self.left_vbox.addWidget(self.anim_bar)
        
        #middle table
        
      
        
        #bottom bar
        
        self.workaround = QWidget(self)
        self.workaround.setObjectName("white_bg")
        self.bottom_actions = QGridLayout(self.workaround)
        self.workaround.setGeometry(50, 50, 50, 50)
        #self.bottom_actions.setGeometry(QRect(800, 0, self.width(), self.height()) )            
        
        self.bt_addc_here = QPushButton(self)
        self.bt_addc_here.setText("Add Column Next")
        self.bt_addc_here.clicked.connect(self.add_col_here)
        
        self.bt_add_col = QPushButton(self)
        self.bt_add_col.setText("Add Column To End")
        self.bt_add_col.clicked.connect(self.add_column)
        
        self.bt_remc_here = QPushButton(self)
        self.bt_remc_here.setText("Rem. Current Column")
        self.bt_remc_here.clicked.connect(self.rem_col_here)
        
        self.bt_rm_col = QPushButton(self)
        self.bt_rm_col.setText("Remove Column")
        self.bt_rm_col.clicked.connect(self.rem_column)
        
       #necessary row operations: add material / bone, remove material / bone, remove empty
        
        """
        self.bt_add_row = QPushButton(self)
        self.bt_add_row.setText("Add Row To End")
        self.bt_add_row.clicked.connect(self.add_row)
        
        self.bt_addr_here = QPushButton(self)
        self.bt_addr_here.setText("Add Row Next")
        self.bt_addr_here.clicked.connect(self.add_row_here)  
        """  
        self.bt_rm_row = QPushButton(self)
        self.bt_rm_row.setText("Remove Empty Rows")
        self.bt_rm_row.clicked.connect(self.rem_empty_rows) 

        self.bt_remmat_here = QPushButton(self)
        self.bt_remmat_here.setText("Remove Material / Bone")
        self.bt_remmat_here.clicked.connect(self.rem_material)

        self.bt_add_material = QPushButton(self)
        self.bt_add_material.setText("Add Material / Bone")
        self.bt_add_material.clicked.connect(self.add_material)
        
        self.bt_add_frames_adv = QPushButton(self)
        self.bt_add_frames_adv.setText("Add Frames Dialogue")
        self.bt_add_frames_adv.clicked.connect(lambda: self.frames_dialogue(one_time = True) )
        
        self.bottom_actions.addWidget(self.bt_addc_here, 0, 0)       
        #self.bottom_actions.addWidget(self.bt_addr_here, 0, 1)
        self.bottom_actions.addWidget(self.bt_add_col, 1 ,0)
        #self.bottom_actions.addWidget(self.bt_add_row, 1, 1)
        self.bottom_actions.addWidget(self.bt_remc_here, 2, 0)
        self.bottom_actions.addWidget(self.bt_remmat_here, 1, 1)
        self.bottom_actions.addWidget(self.bt_rm_col, 3, 0)
        self.bottom_actions.addWidget(self.bt_rm_row, 2, 1)
        self.bottom_actions.addWidget(self.bt_add_material, 0, 1)
        self.bottom_actions.addWidget(self.bt_add_frames_adv, 3, 1)
               
        self.workaround.setDisabled(True)       
        
        self.left_vbox.addWidget(self.workaround)
        
        
        self.workaroundm = QWidget(self)
        self.workaroundm.resize(1600, self.height())
        self.middle_vbox = QVBoxLayout(self.workaroundm)
        
        self.workaroundmt = QWidget(self)
        self.workaroundmt_layout = QHBoxLayout(self.workaroundmt)
        
        self.loop_label = QLabel(self.workaroundmt)
        self.loop_label.setText("Loop Mode:")
        
        self.loop_box = QComboBox(self.workaroundmt)
        self.loop_box.addItems(j3d.loop_mode)
        
        self.duration_label = QLabel(self.workaroundmt)
        self.duration_label.setText("Duration:")
        
        self.duration_box = QLineEdit(self.workaroundmt)
        
        self.tantype_label = QLabel(self.workaroundmt)
        self.tantype_label.setText("Tangent Type:")
        
        self.tantype_box = QComboBox(self.workaroundmt)
        self.tantype_box.addItems(j3d.tan_type)
        
        self.workaroundmt_layout.addWidget(self.loop_label)
        self.workaroundmt_layout.addWidget(self.loop_box)
        self.workaroundmt_layout.addWidget(self.duration_label)
        self.workaroundmt_layout.addWidget(self.duration_box)
        self.workaroundmt_layout.addWidget(self.tantype_label)
        self.workaroundmt_layout.addWidget(self.tantype_box)
        
        
        self.table_display = QTableWidget(self)
        self.table_display.resize(1600, self.height())
        self.table_display.setColumnCount(4)
        self.table_display.setRowCount(4)
        for i in range(self.table_display.rowCount()): # iterate through our initial rows
            self.table_display.setRowHeight(i, 20) # make them thinner       
        self.table_display.setGeometry(400, 50, self.width(), self.height())
        self.table_display.cellClicked.connect(self.cell_clicked)
        
        self.middle_vbox.addWidget(self.workaroundmt)
        self.middle_vbox.addWidget(self.table_display)

        
        
        #self.table_display.currentItemChanged.connect(self.display_info_changes)
        
        
        self.workaroundr = QWidget(self)
        self.right_vbox = QVBoxLayout(self.workaroundr)
        
        
        #self.horizontalLayout.addWidget(self.anim_bar)
        self.horizontalLayout.addWidget(self.workaroundl)
        self.horizontalLayout.addWidget(self.workaroundm)  
        self.horizontalLayout.addWidget(self.workaroundr)

        self.table_display.cellChanged.connect(self.resort_table)
        self.do_refresh = False

    def find_joint(self, index):
        cell_row = index*9 + 1
        if cell_row > self.table_display.rowCount():
            return None
        else:
            return cell_row

    def set_or_add_keyframe(self, frame, joint, translation_x=None, translation_y=None, scale_x=None, scale_y=None, rotation=None):
        row = self.find_joint(joint)

        if row is not None:
            self.do_refresh = False
            for column in range(3, self.table_display.columnCount()):
                item = self.table_display.item(0, column)
                split = item.text().split(" ")
                if len(split) > 1:
                    currframe = int(split[1])
                    column_to_modify = None
                    if currframe == frame:
                        # set frame values
                        column_to_modify = column
                    elif frame < currframe:
                        # Insert new frame
                        self.add_col_here(column+1)
                        self.do_refresh = False  # add_col_here resets it to True but we are not done yet
                        item = self.table_display.item(0, column)
                        item.setText("Frame {0}".format(frame))
                        column_to_modify = column

                    if column_to_modify is not None:
                        if scale_x is not None:
                            self.table_display.item(row+0, column).setText(str(scale_x))
                        if scale_y is not None:
                            self.table_display.item(row+2, column).setText(str(scale_y))
                        if rotation is not None:
                            self.table_display.item(row+4, column).setText(str(rotation))
                        if translation_x is not None:
                            self.table_display.item(row+6, column).setText(str(translation_x))
                        if translation_y is not None:
                            self.table_display.item(row+8, column).setText(str(translation_y))
                        break


            #self.refresh_bck()
            self.do_refresh = True

    def closeEvent(self, event):
        self.closing.emit()

    def read_settings_ini(self):
        #read ini settings
        
        #theme
        self.set_ini_theme()
        configur = ConfigParser()
        configur.read('settings.ini')
        comp_level = configur.get('menu options', 'compression')
        comp_level = comp_level.lower()
        
        #compression level
        if comp_level == "auto":
            self.set_compression_level(0)
            self.auto_compression.setChecked(True)
        elif comp_level == "none": 
            self.set_compression_level(1)
            self.no_compression.setChecked(True)
        elif comp_level in [ "low", "fast"]: 
            self.set_compression_level(2)
            self.low_compression.setChecked(True)
        elif comp_level == "mid": 
            self.set_compression_level(3)
            self.mid_compression.setChecked(True)
        elif comp_level in [ "high", "slow" ]: 
            self.set_compression_level(4)
            self.high_compression.setChecked(True)
            
        #right sidebar stuff
        
        #whether or not to even show stuff on the side
        popout_or_not = configur.get('menu options',  'popup_additional_windows'  )
        popout_or_not = popout_or_not.lower()
        popout_or_not = (popout_or_not == "true")
        
        self.popout = (popout_or_not)
        self.sep_window.setChecked( popout_or_not )
        self.show_widget.setDisabled( popout_or_not )
        
        if self.popout:
            self.workaroundr.hide()

        #save stuff
        self.save_unedited = False
        save_unedited = configur.get('menu options',  'save_unedited'  )
        self.save_unedited = save_unedited.lower() == "true"
 
        #specific editors
        show_create = configur.get('menu options',  'show_create_animation_maker'  )
        show_create = show_create.lower() == "true"
        if show_create:
            self.show_create.setChecked(True)
            self.create_new()
            
            
        show_maedit = configur.get('menu options',  'show_mass_animation_editor'  )
        show_maedit = show_maedit.lower() == "true"
        if show_maedit:
            self.show_maedit.setChecked(True)
            self.maedit_dialogue()
            
            
        show_frames = configur.get('menu options',  'show_frames_adder'  )
        show_frames = show_frames.lower() == "true"
        if show_frames:
            self.show_frames.setChecked(True)
            self.frames_dialogue()
            
            
        show_sounds = configur.get('menu options',  'show_sound_editor'  )
        show_sounds = show_sounds.lower() == "true"
        if show_sounds:
            self.show_sounds.setChecked(True)
            self.sounds_dialogue()
           
        include_subdirs = configur.get('folder load options', 'include_subdirectories')
        self.include_subdirs = include_subdirs.lower() == "true"
        load_model = configur.get('folder load options', 'load_model_file')
        self.load_model = load_model.lower() == "true"
        

        main_game = configur.get('sound options', 'main_game')
        if main_game.lower() in ["tww", "wind waker", "the wind waker", "tp", "twilight princess"]:
            self.sound_enabled = True
        else:
            self.show_widget.removeAction(self.show_sounds)
            self.show_sounds.setParent(None)
            if main_game.lower() in ["mkdd", "double dash", "mario kart double dash", "mario kart: double dash!!"]:
                self.bvh_as_bca = True
                #print('mkdd baybee')
        
        debug_csv = configur.get('menu options', 'debug_csv')
        if debug_csv.lower() == "true":
            self.convert.addAction(self.import_csv)
            self.convert.addAction(self.export_csv)
        
    def write_settings_ini(self, setting):
        configur = ConfigParser()
        configur.read('settings.ini')
        configur[setting[0]][setting[1]] = str(setting[2])
        
        with open('settings.ini', 'w') as f:
            configur.write(f)
            
    def edit_gui(self, filename = None):
        are_no_anims = self.anim_bar.topLevelItemCount() == 0
        self.save_file_parent.setDisabled(are_no_anims)
        self.mass_edit.setDisabled(are_no_anims)
        self.workaround.setDisabled(are_no_anims)
        self.workaroundr.setDisabled(are_no_anims)
        self.edit_menu.setDisabled(are_no_anims)
        
        if self.anim_bar.topLevelItemCount() == 0:
            #if there are no animations, disable everything
            return
        else:
            if filename is None:
                extension = self.anim_bar.currentItem().filepath[-4:]
            else:
                extension = filename[-4:]
                
            if extension == ".bck":
                self.convert_to_all.setDisabled(False)
                self.convert_to_key.setDisabled(True)
            else:
                self.convert_to_key.setDisabled(True)
                self.convert_to_all.setDisabled(True)

    def refresh_bck(self, reload_table=False):
        self.do_refresh = False
        bck = self.bck_save_and_return()
        tmp = BytesIO()
        bck.write_bck(tmp)
        tmp.seek(0)

        if reload_table:
            pos_vertical = self.table_display.verticalScrollBar().value()
            pos_horizontal = self.table_display.horizontalScrollBar().value()
            self.anim_bar.emit_close_all()
            self.open_file_obj(bck, ".bck")

            self.table_display.verticalScrollBar().setValue(pos_vertical)
            self.table_display.horizontalScrollBar().setValue(pos_horizontal)
        self.animation = BCKFile.from_file(tmp)

        del tmp
        del bck
        self.do_refresh = True

    def resort_table(self, x, y):
        if self.do_refresh:
            self.refresh_bck(reload_table=True)

    def button_load_from_arc(self):
        if self.blo_editor.loaded_archive is not None:
            root = self.blo_editor.loaded_archive.root
            try:
                print(root.files, root.subdirs)
                scrn_dir = root["scrn"]
            except FileNotFoundError:
                open_error_dialog("'scrn' directory not found, archive probably has no BCK files for BLO.", self)
            else:
                filepaths = list(filter(lambda x: x.endswith(".bck"), [x for x in scrn_dir.files.keys()]))
                filepaths.sort()
                file, lastpos = FileSelect.open_file_list(self, filepaths, title="Select file")

                self.do_refresh = False
                self.anim_bar.emit_close_all()
                self.open_file_from_obj(BytesIO(scrn_dir[file].getvalue()), file)
                self.refresh_bck()
                self.archive_loaded_file = file
                self.do_refresh = True

    #file stuff
    def button_load_level(self):
        self.do_refresh = False
        filter =  "All Supported Files(*.bck)"
        filepath, choosentype = QFileDialog.getOpenFileName(self, "Open File", "", filter)

        if filepath:
            self.archive_loaded_file = None
            self.anim_bar.emit_close_all()
            self.open_file(filepath)
            self.refresh_bck()

        self.do_refresh = True

    def button_load_folder(self):
        if self.folder_window == None:
            self.folder_window = folder_widget.folder_dia(self.include_subdirs, self.load_model)
            
            if self.folder_window.exec_() == QDialog.Accepted:
                directory = self.folder_window.selectedUrls()[0].toLocalFile() 
                print(directory)
                
                if self.folder_window.isChecked() != self.include_subdirs:
                    self.write_settings_ini(['folder load options', 'include_subdirectories', self.folder_window.isChecked()])
                if self.folder_window.load_model() != self.load_model:
                    self.write_settings_ini(['folder load options', 'load_model_file', self.folder_window.load_model()]) 
                
                self.include_subdirs = self.folder_window.isChecked()
                self.load_model = self.folder_window.load_model()
                self.open_folder(directory)
            
                
            self.folder_window = None
    
    def open_folder(self, directory ):
        subdirs = self.include_subdirs
        models = self.load_model
        files = []
        types = ("*.bca", "*.bck", "*.bla", "*.blk", "*.bpk", "*.brk", "*.btk", "*.btp", "*.bva")  
        if subdirs:
            for exten in types:
                files.extend(glob.glob(directory+"/**/"+exten, recursive = True ) )
        else:
            for exten in types:
                files.extend(glob.glob(directory+"/"+exten ) )
        
        #print (files)
        
        for file in files:
            animation_object = j3d.sort_file(file)               
            self.new_animation_from_object(animation_object, file)
            
        if models:
            model_files = []
            model_types = ("*.bmd", "*.bdl")
            
            if subdirs:
                for exten in model_types:
                    model_files.extend(glob.glob(directory+"/**/"+exten, recursive = True ) )
            else:
                for exten in model_types:
                    model_files.extend(glob.glob(directory+"/"+exten ) )
            
           
            if len(model_files) == 1:
                self.load_bone_names_all_file(model_files[0])
            elif len(model_files) > 0:
                load_model = select_widget.model_select( model_files)
                load_model.setWindowModality(QtCore.Qt.ApplicationModal)
                load_model.exec_()
                model_filepath = load_model.selected
                if model_filepath is not None:
                    self.load_bone_names_all_file(model_filepath)

    def get_current_item(self):
        item = self.anim_bar.currentItem()
        if isinstance(item, JointItem):
            item = item.parent()

        return item

    def bck_save_and_return(self):
        current_item = self.get_current_item()
        current_item.header_info = self.get_header()
        current_item.display_info = self.get_on_screen()
        bck = current_item.save_animation_return("", compress_dis=self.compression)
        return bck
        print("done saving")

    def universal_save(self, filepath = ""):
        
        current_item = self.anim_bar.currentItem()
        current_item.header_info = self.get_header()
        current_item.display_info = self.get_on_screen()
        if current_item.filepath.endswith(".bck") and self.sounds_box is not None:
            current_item.sound_data = self.sounds_box.get_info()
        current_item.save_animation(filepath, compress_dis = self.compression)
        print("done saving")
        
    def button_save_level(self):
        self.universal_save()
            
    def button_save_as(self):         
        filter =  "All Supported Files(*.bca *.bck *.bla *.blk *.bpk *.brk *.btk *.btp *.bva)"
        filepath, choosentype = QFileDialog.getSaveFileName(self, "Save File", self.anim_bar.currentItem().filepath, filter)
        if filepath:
            self.universal_save(filepath)
        
    def button_save_all(self):
        current_item = self.anim_bar.currentItem()
        
        curr_display_info = self.get_on_screen()
        curr_header_info = self.get_header()
        
        if current_item.display_info != curr_display_info:
            current_item.changed = True
            current_item.display_info = curr_display_info
        if current_item.display_info != curr_header_info:
            current_item.changed = True
            current_item.header_info = curr_header_info
        
        if current_item.filepath.endswith(".bck") and self.sounds_box is not None:
            current_item.sound_data = self.sounds_box.get_info()
            
        
        #current_item.save_animation()
        for i in range( self.anim_bar.topLevelItemCount() ):
            # read the of save_unedited
            item = self.anim_bar.topLevelItem(i);

            item.save_animation(compress_dis = self.compression, save_all = not self.save_unedited);
        
    def create_new(self, one_time = False):
        if self.popout and self.create_window is None:
            #if you want to pop stuff out and there is not current window, create it
    
            self.create_window = create_widget.create_window(self.theme)
            self.create_window.setWindowModality(QtCore.Qt.ApplicationModal)
            self.create_window.exec_()
            
            created_info = self.create_window.get_info() 
            self.create_new_from_bar(created_info, False)
            self.create_window = None
        elif not self.popout and self.create_box is None:
            #if you want it on the right bar and it is currently not there, create it. 
            self.create_box = create_widget.create_box(self, one_time)
            self.right_vbox.addWidget(self.create_box)
    
    def create_new_from_bar(self, created_info, one_time):
        if created_info is not None:
            table = j3d.create_empty( created_info )

            filepath = created_info[0]
            
            self.new_animation_from_array(table, filepath, 1)
        if one_time:
            self.create_box.setParent(None)
            self.right_vbox.removeWidget(self.create_box)
            self.create_box = None
                 
    def combine_anims(self):
        import widgets.quick_change as quick_change
            
        quick_change_window = quick_change.quick_editor()  
        quick_change_window.setWindowModality(QtCore.Qt.ApplicationModal)            
        quick_change_window.exec_()
    
    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls:
            url = mime_data.urls()[0]
            filepath = url.toLocalFile()
            exten = filepath[filepath.rfind("."):].lower()
            if exten in [ ".bca", ".bck", ".bla", ".blk", ".bpk", ".brk", ".btk", ".btp", ".bva", ".anim", ".fbx", ".txt", ".bvh", ".csv" ]:
                event.acceptProposedAction()
            if exten in [".bmd", ".bdl"]:
                anim_exten = self.anim_bar.currentItem().filepath
                anim_exten = anim_exten[anim_exten.rfind("."):].lower()
                if anim_exten in [".bca", ".bck"]:
                    event.acceptProposedAction()
          
    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls:
            url = mime_data.urls()[0]
            filepath = url.toLocalFile()
            exten = filepath[filepath.rfind("."):].lower()
            if exten in [ ".bca", ".bck", ".bla", ".blk", ".bpk", ".brk", ".btk", ".btp", ".bva" ]:
                self.open_file(filepath)
            elif exten == ".anim": 
                self.import_anim_file(filepath)
            elif exten == ".fbx":
                self.import_fbx_file(filepath)
            elif exten in [".bmd", ".bdl"]:
                self.load_bone_names(filepath)
            elif exten == ".txt":
                self.maedit_file(filepath)
            elif exten == ".bvh":
                self.import_bvh_file(filepath)
            elif exten == ".csv":
                self.import_csv_file(filepath)
        
    def open_file(self, filepath):
        animation_object = j3d.sort_file(filepath)               
        self.new_animation_from_object(animation_object, filepath)

    def open_file_from_obj(self, f, filename):
        animation_object = j3d.sort_file_obj(f)
        self.new_animation_from_object(animation_object, filename, check_for_compression=False)

    def open_file_obj(self, animation_object, fname):
        self.new_animation_from_object(animation_object, fname)

    def set_compression_level(self, level):
        self.compression = level
        levels = ["auto", "none", "low", "mid", "high"]
        self.write_settings_ini(["menu options", "compression", levels[level] ])
   
    #view menu functions
    
    def toggle_theme(self, filepath):
        #print("toggle theme")
        self.toggle_dark_theme(filepath)
        if self.create_box is not None:
            self.create_box.main_widget.toggle_dark_theme(filepath)
        if self.frames_box is not None:
            self.frames_box.main_widget.toggle_dark_theme(filepath)
        if self.maedit_box is not None:
            self.maedit_box.main_widget.toggle_dark_theme(filepath)
        if self.sounds_box is not None:
            self.sounds_box.main_widget.toggle_dark_theme(filepath)
            
        if self.create_window is not None:
            self.create_window.toggle_dark_theme(filepath)
        if self.frames_window is not None:
            self.frames_window.toggle_dark_theme(filepath)
        if self.maedit_window is not None:
            self.maedit_window.toggle_dark_theme(filepath)
        if self.sounds_window is not None:
            self.sounds_window.toggle_dark_theme(filepath)
            
        #print( filepath[filepath.rfind("/") + 1:filepath.rfind(".qss")] )
        self.write_settings_ini(["menu options", "theme", filepath[filepath.rfind("/") + 1:filepath.rfind(".qss")] ])
          
    def set_popout(self):
        self.popout = self.sep_window.isChecked()
        if self.sep_window.isChecked():
            self.workaroundr.hide()
            self.show_widget.setDisabled(True)
        else:
            self.workaroundr.show()
            self.show_widget.setDisabled(False)
        self.write_settings_ini(["menu options", "popup_additional_windows", self.sep_window.isChecked() ] )

    def toggle_show_create(self):
        if self.show_create.isChecked():
            self.create_new()
        else:
            self.create_box.setParent(None)
            self.right_vbox.removeWidget(self.create_box)
            self.create_box = None
        self.write_settings_ini(["menu options", "show_create_animation_maker", self.show_create.isChecked() ] )
    
    def toggle_show_frames(self):
        if self.show_frames.isChecked():
            self.frames_dialogue()
        else:
            self.frames_box.setParent(None)
            self.right_vbox.removeWidget(self.frames_box)
            self.frames_box = None   
        self.write_settings_ini(["menu options", "show_frames_adder", self.show_frames.isChecked() ] )
        
    def toggle_show_maedit(self):
        if self.show_maedit.isChecked():
            self.maedit_dialogue()
        else:
            self.maedit_box.setParent(None)
            self.right_vbox.removeWidget(self.maedit_box)
            self.maedit_box = None 
        self.write_settings_ini(["menu options", "show_mass_animation_editor", self.show_maedit.isChecked() ] )

   #convert print

    
    def convert_to_k(self):
        current_item = self.get_current_item()
        current_item.header_info = self.get_header()
        current_item.display_info = self.get_on_screen()
        current_item.convert_to_k()
        
    def convert_to_a(self):
        current_item = self.get_current_item()
        current_item.header_info = self.get_header()
        current_item.display_info = self.get_on_screen()
        current_item.convert_to_a()
    
    def import_anim_file(self, filepath = None):
        if filepath is None or filepath == False:
            filepath, choosentype = QFileDialog.getOpenFileName( self, "Open File","" ,
        ".anim files(*.anim)" )
        if filepath:
            bck = j3d.import_anim_file(filepath)
            filepath = filepath[0:-5] + ".bck"
            self.new_animation_from_object(bck, filepath)
    
    def export_anim_file(self):
        current_item = self.get_current_item()
        current_item.header_info = self.get_header()
        current_item.display_info = self.get_on_screen()
        current_item.export_anim()
       
    def import_csv_file(self, filepath = None):
        if filepath is None or filepath == False:
            filepath, choosentype = QFileDialog.getOpenFileName( self, "Open .csv file","" ,".csv files(*.csv)" )
        if filepath:
            with open(filepath, "r", newline='') as f:
                csv_reader = csv.reader(f)
                info = list(csv_reader)
                info[0][0] = int(info[0][0])
                info[0][2] = int(info[0][2])
                filepath = filepath[ : len(filepath) - 4] + "." + info[0][3]
                self.new_animation_from_array(info, filepath, False, None)
        
    def export_csv_file(self):
        filepath, choosentype = QFileDialog.getSaveFileName(self, "Save as .csv File", self.get_current_item().filepath + ".csv", ".csv files(*.csv)")
        if filepath:
            header = self.get_header()
            header.append(self.get_current_item().get_animtype())
            info = j3d.fix_array(header, self.get_on_screen())
            print(info)
            with open(filepath, 'w+', newline='') as f:
                writer = csv.writer(f)
                for row in info:
                    writer.writerow(row)
       
    def new_animation_from_object(self, actual_animation_object, filepath, check_for_compression=True):
        #deal with compression and keep track of whether or not to compress it
        compressed = 1
        if check_for_compression:
            try:
                with open(filepath, "rb") as f:
                    header = f.read(4)

                    if header == b"Yaz0":
                        compressed = 4
            except:
                pass
         
        #tree view stuff
        display_info = actual_animation_object.get_loading_information()
      
        sound_data = None
        anim_type = str(type(actual_animation_object)) 
        if anim_type.find('bck') != -1:
            sound_data = actual_animation_object.sound
        
        #self.anim_bar.addTopLevelItem(loaded_animation)
             
        """
        print("loaded animation display info")
        print(loaded_animation.display_info[0])
        print("index of loaded animation in tree view")
        print(self.anim_bar.indexOfTopLevelItem(loaded_animation) )
        """
        
        loaded_animation = self.new_animation_from_array(display_info, filepath, compressed, sound_data)
        
        loaded_animation.add_children( actual_animation_object.get_children_names() )
        
        #print("end of new animation from object")
    
    #bmd stuff
    def new_animation_from_array(self, array, filepath, compressed, sound_data = None):
        #store back old values
        if self.anim_bar.topLevelItemCount() > 0:
            #print( "this is not the first loaded animation " ) 
            #print( "the old index is " + str(self.anim_bar.curr_index) )
            #print("load in the current table to index " + str(self.anim_bar.curr_index) )
            #self.anim_bar.itemAt(self.anim_bar.curr_index,0).display_info = self.get_on_screen()
           
            
            #add something for the header
            self.anim_bar.currentItem().header_info = self.get_header()
            self.anim_bar.currentItem().display_info = self.get_on_screen()
            #print(self.anim_bar.currentItem().text(0) )
            #print( self.anim_bar.currentItem().display_info[0])
        #print(self.anim_bar.topLevelItemCount())
        if self.anim_bar.topLevelItemCount() == 0:
            loaded_animation = tree_item.tree_item(self.anim_bar)    
            self.anim_bar.curr_item = loaded_animation
            #print("curr_item set " + str( self.anim_bar.curr_item))
        else:
            loaded_animation = tree_item.tree_item(self.anim_bar)  
        
        #loaded animation is a tree item
        loaded_animation.set_values( array, filepath, compressed )
        loaded_animation.set_sound(sound_data) 

        #process sound
        if filepath.endswith(".bck"):
            if self.anim_bar.curr_item is not None and self.sounds_box is not None:
                self.anim_bar.curr_item.sound_data = self.sounds_box.get_info()
            if self.sounds_box is not None:         
                self.sounds_box.main_widget.sound_data = sound_data
                self.sounds_box.main_widget.setup_sound_data()

        # deal with the various ui stuff
        self.edit_gui(filepath)
        self.setWindowTitle("j3d animation editor - " + filepath)

            
        #do the adding
        self.is_remove = True  
        self.anim_bar.curr_item = loaded_animation
        self.anim_bar.setCurrentItem(loaded_animation)
        
        #load to the table
        self.load_animation_to_middle(loaded_animation)
     
        self.is_remove = False
        
        return loaded_animation

    def set_header(self, header_info):
        self.loop_box.setCurrentIndex( header_info[0] ) 
        self.duration_box.setText( str(header_info[1]) )
        
        if header_info[2] == -1:
            self.tantype_box.setDisabled(True)
        else:
            self.tantype_box.setDisabled(False)
            self.tantype_box.setCurrentIndex( header_info[2] )
    
    def get_header(self):
        header_info = []
        header_info.append( self.loop_box.currentIndex() )
        header_info.append( self.duration_box.text() )
        
        header_info.append( self.tantype_box.currentIndex() )
        
        return header_info

    # mass editor
    def maedit_dialogue(self, one_time = False): 
        if self.popout and self.maedit_window is None:
        
            self.maedit_window = maedit_widget.maedit_window(self.theme)
            self.maedit_window.setWindowModality(QtCore.Qt.ApplicationModal)
            self.maedit_window.exec_()
            maedit_info = self.maedit_window.get_info() 
            self.maedit_from_bar(maedit_info, False)
            self.maedit_window = None
        elif not self.popout and self.maedit_box is None:
            self.maedit_box = maedit_widget.maedit_box(self, one_time)
            self.right_vbox.addWidget(self.maedit_box)

    def maedit_from_bar(self, maedit_info, one_time, model = None):
        print("going to maedit")
        if maedit_info is not None:
            for maedit_entry in maedit_info:
                print(maedit_entry)
                anim_type = maedit_entry[0]
                #anim_name = maedit_entry[2]
                         

                look_col = 2
                if maedit_entry[0] in[ ".bla" ,".blk", ".bva", ".btp"]:
                    look_col = 0
                elif maedit_entry[0] == ".bpk":
                    look_col = 1
                self.anim_bar.currentItem().display_info = self.get_on_screen()
                
                for j in range( self.anim_bar.topLevelItemCount() ):
                    item = self.anim_bar.topLevelItem(j)

    
                    model_test = (model is None) or ( (item.bmd_file is not None) and item.bmd_file.endswith(model) )
                    if model_test and (item.filepath.endswith(maedit_entry[0])) :
                        #print("passed", maedit_entry)
                        
                        info = item.display_info
                        #print(info[1])
                        
                        new_table = self.find_and_edit(info, maedit_entry[1], maedit_entry[2], look_col, maedit_entry[0])
                        #print(new_table[1])
                        #print(item.display_info[1])
                        
                        item.display_info = new_table
                       
                        item.changed = True
                        del info
                    del item

                self.load_animation_to_middle(self.anim_bar.currentItem() )
        if one_time:
            self.maedit_box.setParent(None)
            self.right_vbox.removeWidget(self.maedit_box)
            self.maedit_box = None
    
    def maedit_file(self, filepath = None):
        if filepath is None:
            filter =  "Mass Editing Text File(*.txt)"
            filepath, choosentype = QFileDialog.getOpenFileName( self, "Open File","" , filter )
            
        if filepath: 
            with open(filepath, "r") as f:
                lines = f.read().splitlines()
            
            lines = [ line for line in lines if line != ""]
            lines = [ line.strip() for line in lines]
            #print(lines)
            
            anim_type = lines[0].lower()
            if not anim_type.startswith("."):
                anim_type = "." + anim_type
            model_name = None
            #print (anim_type)
            if anim_type in [".btk", ".brk", ".bck" , ".btp", ".bca", ".bpk", ".bla", ".blk", ".bva" ]:
                if lines[1].startswith("file:"):
                    model_name = lines[1][5:].strip()
                   
                
                maedit_info = []
                
                i = 1
                if model_name is not None:
                    i = 2
                while i < len(lines):            
                    bone_name = lines[i]
                   
                    maedit_array = [ anim_type, bone_name]
                    values = []
                    i += 1
                    #iterate until you get an ending line
                    
                    while i < len(lines) and lines[i] not in ["end", "]", "}", ")"] :
                        #print("some transform - check if valid at line " + str(i) )
                        #print ("next line " + lines [i] )
                        if lines[i].startswith("//"):
                            i = i + 1
                            continue

                        new_transform =  self.handle_transform_regex(anim_type, lines[i])
                        if new_transform is not None:
                            values.append(new_transform)
                        i = i + 1
                        
                    # optimize values
                    
                        
                    if len(values) > 0:
                        
                        maedit_array.append(values)
                        maedit_info.append(maedit_array)
                    i = i + 1
                    del maedit_array
                #print(maedit_info)
                
                self.maedit_from_bar(maedit_info, False, model_name)
                                 
    def handle_transform_regex( self, file_type, line):
        import re
        ending_part = "\s*:?\s*(\+|\-|\*|/|avg|set|)\s*(\d*.\d*)"
        if file_type in [".bck", ".bca"]:
            regex = "(scale|rot\w*|trans\w*)\s([xyz])" + ending_part
            m = re.match( regex, line, re.IGNORECASE)
            if m is not None:
                #print("got a match")
                this_transform = []
                comp = ""
                if m.group(0).lower().startswith("s"):
                    comp += "Scale "
                elif m.group(0).lower().startswith("r"):
                    comp += "Rotation "
                elif m.group(0).lower().startswith("t"):
                    comp += "Translation "
                comp += m.group(2).upper()
                
                comp += ":"
                
                ops = ["+", "-", "*", "/", "avg", "set"]
                try:
                    op_code = ops.index( m.group(3) )
                    if op_code == 5:
                        op_code = 4
                except:
                    op_code = 4
                
                this_transform.append(comp)
                this_transform.append(op_code )
                this_transform.append(m.group(4) )
                #print(this_transform)
                return this_transform

    def find_and_edit(self, info, name, values, look_col, exten = None):
            def operations( array, operation ) :
                #print("operation " + str(operation ), array)
                
                if array[1] == "":
                    return array[0]
                if operation == 0:
                    
                    return array[0] + array[1]
                elif operation == 1:
                    
                    return array[0] - array[1]
                elif operation == 2:
                    
                    return array[0] * array[1]
                elif operation == 3:
                    
                    return array[0] / array[1]
                elif operation == 4:
                    #print( array[1] )
                    if array[1] == "":
                        try:
                            if array[1].strip() != "" and float(array[1]):
                                return float(array[1])                 
                        except:
                            pass
                        finally:
                            sum = 0
                            for val in array:
                                sum += val
                            return sum / len(array)
                    else:
                        return array[1]
            
            def operations_bva (array, operation):
                #print( "operation "  + str(operation) + " " + str (array) )
                if array[1] == "": #assume switch has a 0 case 
                    if array[0] == 1:
                        return 0
                    else: 
                        return 1
                return array[1]
            
            def change_row(info, i, look_col, values):
                for j in range( look_col + 1 , len( info[i ]) ):
                    item = info[i][j]
                    if item != "":
                        if values[2] != "":
                            values[2] = float(values[2])
                        if exten == ".bva":
                            new_val = operations_bva( [float(item), values[2] ], values[1] )
                        else:
                            new_val = operations( [float(item), values[2] ], values[1] )
                        if exten == ".btp" or exten == ".bva":
                            new_val = int(round(new_val))
                        info[i][j] = str(new_val) 
            #print(info, name, values, look_col, exten)
            for i in range(1, len(info)):
                item = info[i][0] 
                
                #print(item, name)
                if item is not None and item.lower() == name.lower():
                    print(values)
                    #single line animation
                    if exten == [ ".bla" ,".blk", ".bva", ".btp"]:
                        look_col += 1
                        if exten == ".blk":
                            look_col -= 1
                        #print(look_col)
                        change_row(info, i, look_col, values[0])

                    else:
                        curr_row = i
                        for j in range( len(values) ):
                            if values[j][2] != "" or values[j][1] == 4:
                                curr_row = self.find_row_2(info, look_col, curr_row, values[j][0])
                                change_row(info, curr_row, look_col, values[j]) 
                    break
            return info
    
    def find_row_2(self, table, look_col, row, value):
        found_row = row
        stop_row =  self.table_display.rowCount()
        found = False
        while found == False and found_row > 0 and found_row < stop_row:
            item = self.table_display.item(found_row, look_col)
            #print("find row 2", item.text(), value)
            if item is not None and item.text().lower() == value.lower():
                found = True
            else:
                found_row += 1
        
        if not found:
            return None
        else:
            return found_row
     
    #table view stuff
    def contextMenuEvent(self, event):
        
        if  self.anim_bar.topLevelItemCount() < 1:
            return
            
        quick_change_action = QAction("Quick Edit Menu", self)
        
        def operations( array, operation ) :
            if operation == 0:
                return array[0] + array[1]
            elif operation == 1:
                return array[0] - array[1]
            elif operation == 2:
                return array[0] * array[1]
            elif operation == 3:
                return array[0] / array[1]
            elif operation == 4:
                sum = 0
                for val in array:
                    sum += val
                return sum / len(array)
        
        def emit_quick_change():
            import widgets.bckwidget.j3d_animation_editor.widgets.quick_change as quick_change
            
            quick_change_window = quick_change.quick_editor()  
            quick_change_window.setWindowModality(QtCore.Qt.ApplicationModal)            
            quick_change_window.exec_()
            
            info = quick_change_window.get_info() 
            if info is not None :
                 
                
                list = self.table_display.selectedIndexes()
                
                avg_array = []
                for cell in list:
                    
                    item = self.table_display.item(cell.row(), cell.column())
                    frames_row = cell.row() == 1
                    if isinstance(item, QTableWidgetItem):
                        if info[0] < 4:
                            try:
                                if frames_row and not item.text().isnumeric():
                                   base_value = float( item.text()[6:] )
                                else:
                                    base_value =  float(item.text())
                                new_value = operations( [ base_value , float(info[1])], info[0] )
                                index = self.anim_bar.currentIndex().row()   
                                exten = self.anim_bar.currentItem().filepath[-4:]
                                if exten in [".bva", ".btp", ".brk", ".bpk"] :
                                    new_value = int( new_value )
                                    new_value = max( 0, new_value)
                                    if exten in [".brk", ".bpk"]:
                                        
                                        new_value = min( new_value, 255)
                                    elif exten == ".bva":
                                        new_value = min(1, new_value)
                                
                                if frames_row:
                                    new_value = "Frame " + str(int(new_value)) 
                                    item.setText(new_value )
                                else:
                                    item.setText(str( new_value) )
                                #print(new_value)
                            except Exception as e:
                                print(e)
                                print( "error with " +  item.text())
                        else:
                            print("added")
                            try:
                                avg_array.append( float(item.text()) )
                                
                            except:
                                print("not a numeric value - will be ignored" )
                
                print( len( avg_array) )
                if info[0] >= 4:
                    average = operations(avg_array, info[0] )
                    for cell in list: 
                        item = self.table_display.item(cell.row(), cell.column())
                        try:
                            float(item.text())
                            item.setText( str(average) )
                        except:
                            pass
                            
            del quick_change_window
            
        
        quick_change_action.triggered.connect(emit_quick_change)
        
        context_menu = QMenu(self.anim_bar)
        
        context_menu.addAction(self.copy_cells_action)
        context_menu.addAction(self.paste_cells_action)
        context_menu.addAction(self.clear_cells_action)
        context_menu.addAction(quick_change_action)
        
        context_menu.exec(self.mapToGlobal(event.pos()))
        context_menu.destroy()
        del context_menu
    
    def emit_copy_cells(self):
        list = self.table_display.selectedIndexes()
        self.copied_values = []
        #print( list.column() )
        lowest_row = list[0].row()
        lowest_col = list[0].column()
        
        
        
        for cell in list:
            item = self.table_display.item(cell.row(), cell.column())
            
            if isinstance(item, QTableWidgetItem):
                self.copied_values.append( [item.text(), cell.row(), cell.column(), item.icon() ] )                  
            else:
                self.copied_values.append( ["", cell.row(), cell.column(), QIcon() ] )
                           
            lowest_row = min(lowest_row, cell.row())
            lowest_col = min(lowest_col, cell.column())
            
        #print( len( self.copied_values) )
        
        for cell in self.copied_values:
            cell[1] -= lowest_row
            cell[2] -= lowest_col
                     
    def emit_paste_cells(self):
        list = self.table_display.selectedIndexes()
    
        row = list[0].row()
        col = list[0].column()
        
        max_row_length = self.table_display.columnCount()
        
        for cell in self.copied_values:
            eff_row = cell[1] + row
            eff_col = cell[2] + col
            if eff_col < max_row_length:
            
                self.table_display.setItem(eff_row, eff_col, QTableWidgetItem(cell[3], cell[0] ))

    def emit_clear_cells(self):
        list = self.table_display.selectedIndexes()
        
        for cell in list:
            item = self.table_display.item(cell.row(), cell.column())
            
            if isinstance(item, QTableWidgetItem):
                item.setText("")
                item.setIcon( QIcon() )
            """else:
                self.table_display.setItem(cell.row(), cell.column(), QTableWidgetItem( "" )) """

    def emit_select_all(self):
        
        
        for i in range( self.table_display.rowCount() ):
            for j in range( self.table_display.columnCount() ) :
                item = self.table_display.item(i, j)
                if isinstance(item, QTableWidgetItem):
                    self.table_display.item(i, j).setSelected(True)
        
    def get_vertical_headers(self, information):
        col_count = max( len(information[0]), len(information[1]))
        first_vals = []
        first_vals.append( information[0][0] )
        first_vals.append( information[1][0] )
        for i in range(2, len(information)):
            col_count = max(col_count, len( information [i] ) )
            
            for j in range( len(information[i] )):          
   
                if not information[i][j] in ["LLLL", "SSSS", "Texture Index", "Center", "Register", "Constant", "Linear", "Smooth"]:
                   
                    if not str(information[i][j]).isnumeric() and information[i][j] != "":
                      
                        if not str(information[i][j]).startswith("("):
                   
                            first_vals.append(str(information[i][j]))
                            break
        return (first_vals, col_count)

    #table info stuff
    
    def fix_table(self, information, col_count):
        for row in range(len(information)):
            for col in range(col_count):
                if len( information[row] ) > col:
                    if information[row][col] == "LLLL" or ( col == 1 and information[row][col] == "Linear"):
                        icon = QIcon("icons/linear.png")
                        item = QTableWidgetItem(icon, "Linear")
                        item.setWhatsThis("The tanget interpolation mode")
                    elif information[row][col] == "SSSS" or ( col == 1 and information[row][col] == "Smooth"):
                        icon = QIcon("icons/smooth.png")
                        item = QTableWidgetItem(icon, "Smooth")
                    else:
                        item = QTableWidgetItem(str(information[row][col]) )
                    self.table_display.setItem(row, col, item)
    
    #ONLY loads what it is given, backup MUST be done before calling this
    def load_animation_to_middle(self, treeitem):      
        
        #print("beginning of load animation to middle")
        
        self.table_display.clearContents()
        
        #print("new loaded animation")
        #print(treeitem)
        
        information = treeitem.display_info
        
        #print(information[0] )
        
        header_info = treeitem.header_info
        filepath = treeitem.filepath
        
        first_vals, col_count = self.get_vertical_headers(information)

        self.table_display.setColumnCount(col_count)
        self.table_display.setRowCount(len(information))

        for i in range(self.table_display.rowCount()): # interate through all the rows of the middle table
            self.table_display.setRowHeight(i, 20) # make each row thinner
                
        self.fix_table(information, col_count)
                      
        self.table_display.setHorizontalHeaderLabels(information[0])
        self.table_display.setVerticalHeaderLabels(first_vals)
        
        
        self.set_header(header_info)
        
        self.setWindowTitle("j3d animation editor - " + filepath)
        self.edit_gui(filepath)
        
        

        #print("end of load animation to middle")
    
    def selected_animation_changed(self):
        if isinstance(self.anim_bar.currentItem(), JointItem):
            index = self.anim_bar.currentItem().get_index()
            row = self.find_joint(index)
            if row is not None:
                width = self.table_display.horizontalScrollBar().value()
                item = self.table_display.item(row, 0)
                item2 = self.table_display.item(row+8, 0)
                self.table_display.scrollToItem(item2)
                self.table_display.scrollToItem(item)

                self.table_display.horizontalScrollBar().setValue(width)
        if False:
            if self.is_remove:
                return

            if self.anim_bar.topLevelItemCount()  > 0:
                #load in previous values
                #print("load in previous value")
                #print(self.anim_bar.curr_item.text(0))
                curr_header_info = self.get_header()
                curr_display_info = self.get_on_screen()

                if self.anim_bar.curr_item.display_info != curr_display_info:
                    self.anim_bar.curr_item.changed = True
                    #print( "display info changed ")
                elif self.anim_bar.curr_item.header_info != curr_header_info:
                    self.anim_bar.curr_item.changed = True


                self.anim_bar.curr_item.display_info = curr_display_info
                self.anim_bar.curr_item.header_info = curr_header_info
                if self.anim_bar.curr_item.filepath.endswith(".bck") and self.sounds_box is not None:

                    curr_sound_data = self.sounds_box.get_info()

                    if self.anim_bar.curr_item.sound_data != curr_sound_data:
                        self.anim_bar.curr_item.chanaged = True
                        #print("sound data changed")

                    self.anim_bar.curr_item.sound_data = curr_sound_data
                    #print("get on screen result")
                    #print( self.anim_bar.curr_item.sound_data)
                    #print( "new data" )
                    #print( self.anim_bar.currentItem().sound_data)
                    self.sounds_box.main_widget.sound_data = self.anim_bar.currentItem().sound_data
                    self.sounds_box.main_widget.setup_sound_data()



                self.anim_bar.curr_item = self.anim_bar.currentItem()




                """
                print("updated curr item")
                print(self.anim_bar.curr_item.text(0))
                print( "new selected index is " + str(self.anim_bar.curr_item ) )
                print( self.anim_bar.currentItem().display_info )
                """
                self.load_animation_to_middle(self.anim_bar.currentItem() )
             
    def get_on_screen(self):
    
        collected_info = []
        
        
        for i in range( self.table_display.rowCount() ):
            row_info = []
               
            for j in range (self.table_display.columnCount() ):
                item = self.table_display.item(i, j)
                if isinstance(item, QTableWidgetItem):
                    row_info.append(item.text())
                else:
                    row_info.append("")
    
            collected_info.append(row_info)
        return collected_info
                             
    def cell_clicked(self, row, column):
        item = self.table_display.item(row, column)
        
        if isinstance(item, QTableWidgetItem):
            icon = item.icon()
            
            if not item.icon().isNull() and column <= 1:
                if item.text().startswith("L"):
                    item.setText("Smooth")
                    icon = QIcon("icons/smooth.png")
                else:
                    item.setText("Linear")
                    icon = QIcon("icons/linear.png")
                item.setIcon(icon)
            elif column == 0:
                if item.text() == "Register":
                    item.setText("Constant")
                elif item.text() == "Constant":
                    item.setText("Register")
            elif row == 0 and column > 0:
                setting = self.table_display.item(row, column - 1).text()
                value = self.table_display.item(row, column).text()
                if setting.startswith("Loop"):
                    options = j3d.loop_mode
                elif setting.startswith("Tan"):
                    options = j3d.tan_type
                else:
                    return
                    
                if value == "" or value not in options:
                    position = -1
                else:
                    position = options.index(value)           
                self.table_display.item(row, column).setText(options[( position + 1) % len(options)])

    #table button stuff   
   
    def add_column(self):
        self.table_display.setColumnCount(self.table_display.columnCount() + 1)
        if self.anim_bar.topLevelItemCount() > 0:
            minimum = len (self.get_current_item().display_info[0] )
            if self.table_display.columnCount() > minimum:
                self.bt_rm_col.setDisabled(False)
        
    def rem_column(self):
        if self.anim_bar.topLevelItemCount() > 0:
            vals = self.get_current_item().display_info[0]
            
            minimum = 0;
            
            for i in vals:
                if i != "":
                    minimum += 1
            if self.table_display.columnCount() > minimum:
                self.table_display.setColumnCount(self.table_display.columnCount() - 1)
        else:
            self.table_display.setColumnCount(self.table_display.columnCount() - 1)
    
    def add_col_here(self, col_index = None):
        self.do_refresh = False
        if col_index == None or col_index == False:
            curcol = self.table_display.currentColumn() + 2
        else:
            curcol = col_index
        #print(self.table_display.currentColumn())
        self.add_column()
        if curcol > 2:
            #print("at least 2")
            for i in range( 0, self.table_display.rowCount() ):
                for j in reversed( range( curcol, self.table_display.columnCount() ) ):
                    old = self.table_display.item(i, j-1)
                    try:
                        new = QTableWidgetItem(old.text())
                        old.setText("")
                    except:
                        new = QTableWidgetItem("")
                        self.table_display.setItem(i, j-1, QTableWidgetItem(""))
                    self.table_display.setItem(i, j, new)

        self.do_refresh = True

    def rem_col_here(self):
        self.do_refresh = False
        curcol = self.table_display.currentColumn() + 1
        #print(curcol)
        if self.anim_bar.topLevelItemCount() > 0:          
            vals = self.get_current_item().display_info[0]
            
            minimum = 0;
            
            for i in vals:
                if i != "":
                    minimum += 1
            
            #print(minimum)
            
            #print("removing column")
            for i in range( 0, self.table_display.rowCount() ):
                for j in range( curcol, self.table_display.columnCount() ):
                    old = self.table_display.item(i, j)
                    try:
                        new = QTableWidgetItem(old.text())
                        old.setText("")
                    except:
                        new = QTableWidgetItem("")
                        self.table_display.setItem(i, j, QTableWidgetItem(""))
                    self.table_display.setItem(i, j - 1, new)
            
            
            if self.table_display.columnCount() > minimum: #if you can remove a col            
                self.rem_column()
        else:
            self.rem_column()

        self.do_refresh = True

    def add_row(self, value = None):
        self.table_display.setRowCount(self.table_display.rowCount() + 1)
        self.table_display.setRowHeight(self.table_display.rowCount() - 1, 20)
        
        self.bt_rm_row.setDisabled(self.table_display.rowCount() <= 2)
        print(value)
        if value is not None and value is not False:
            
            for i in range(len (value)):
                new_item = QTableWidgetItem( str(value[i] ))
                self.table_display.setItem(self.table_display.rowCount() - 1, i, new_item)

    def rem_empty_rows(self):
        #print("column count " + str( self.table_display.columnCount() ) )
        if self.anim_bar.topLevelItemCount() > 0:
            for i in reversed(range( 2, self.table_display.rowCount() )):
                is_empty = True
                j = 0
                while is_empty and j < self.table_display.columnCount():
                    item = self.table_display.item(i, j)
                    if item is not None and item.text() != "":
                        is_empty = False
                    j += 1
                if is_empty:
                    #print( "removing row " + str(i) )
                    self.rem_row_here(i)
                    i -= 1
                     
    def rem_row(self):
        if self.table_display.rowCount() > 2:
            self.table_display.setRowCount(self.table_display.rowCount() - 1)
        if self.table_display.rowCount() == 2:
            self.bt_rm_row.setDisabled(True)
    
    def add_row_here(self, currow):
        self.do_refresh = False
        if currow is not False and currow is not None:
            currow += 1
        else:
            currow = self.table_display.currentRow()
        #currow = self.table_display.currentRow() + 1
        
        self.add_row()
        if currow > 2:
            for i in reversed( range( currow, self.table_display.rowCount() ) ):
                for j in range( 0, self.table_display.columnCount() ):
                    if i != currow:
                        old = self.table_display.item(i - 1, j)
                        
                        
                        if old is not None:
                            self.table_display.setItem(i, j, old.clone())
                    else:
                        self.table_display.setItem(i, j, QTableWidgetItem(""))
                    """
                    except:
                        new = QTableWidgetItem("")
                        self.table_display.setItem(i - 1, j, QTableWidgetItem(""))
                    #self.table_display.setItem(i, j, new)
                    self.table_display.setItem(i, j, old.clone())
                    """
        self.do_refresh = True

    def find_row(self, step, look_col, start, end):
        row = self.table_display.currentRow()
        stop_row =  self.table_display.rowCount()
        found = False
        while found == False and row > 1 and row < stop_row:
            item = self.table_display.item(row, look_col)
            if item is not None and item.text().lower().startswith(start) and item.text().lower().endswith(end):
                found = True
            else:
                row += step
        
        if not found:
            return None
        else:
            return row
      
    def rem_material(self):
        if self.anim_bar.topLevelItemCount() > 0:
            extension = self.anim_bar.currentItem().filepath
            extension = extension[-4:]
            if extension in [ ".bla" ,".blk", ".bva", ".btp"]:
                self.rem_row_here()
            else:
                look_col = 2
                top_row  = self.table_display.currentRow()
                bot_row = self.table_display.currentRow()
                if extension in [".bca", ".bck"]:
                    # look for scalex and to transz
                    
                    top_row = self.find_row(-1, look_col, "scale", "x:")
                    if top_row is None:
                        return 
                    bot_row = self.find_row(1, look_col, "trans", "z:" )
                    if bot_row is None:
                        return

                    #print(top_row, bot_row)
                
                    
                elif extension == ".btk":
                    top_row = self.find_row(-1, look_col, "scale", "u:")
                    if top_row is None:
                        return 
                    bot_row = self.find_row(1, look_col, "trans", "w:" )
                    if bot_row is None:
                        return

                    #print(top_row, bot_row)
                elif extension in [".brk", ".bpk"]:
                    if extension == ".bpk":
                        look_col = 1
                    top_row = self.find_row(-1, look_col, "re", "d:")
                    if top_row is None:
                        return 
                    bot_row = self.find_row(1, look_col, "alp", "ha:" )
                    if bot_row is None:
                        return
                    # look for red and alpha
                for i in range(top_row, bot_row + 1):
                    self.rem_row_here(top_row)
                information = self.get_on_screen()
                first_vals, col_count = self.get_vertical_headers(information)
                self.table_display.setVerticalHeaderLabels(first_vals)
                self.fix_table(information, col_count)
                
    def rem_row_here(self, currow = None):
        if currow is None or currow == False:
            currow = self.table_display.currentRow()
        if currow == 0:
            self.rem_row()
        elif self.anim_bar.topLevelItemCount() > 0:       
            currow += 1
            for i in range( currow, self.table_display.rowCount() ):
                for j in range( 0, self.table_display.columnCount() ):
                    old = self.table_display.item(i, j)
                    try:
                        new = QTableWidgetItem(old.text())
                        old.setText("")
                    except:
                        new = QTableWidgetItem("")
                        self.table_display.setItem(i, j, QTableWidgetItem(""))
                    self.table_display.setItem(i - 1, j, new)
            self.rem_row()
        else:
            self.rem_row()
            
    def add_material(self):
        if self.anim_bar.topLevelItemCount() > 0:
            extension = self.anim_bar.currentItem().filepath
            extension = extension[-4:]
            
            rows_to_add = 0
            
            
            
            if extension == ".bla" or extension == ".blk":
                self.add_row(["Cluster #"])
            elif extension == ".btp":
                self.add_row(["Material Name"])
            elif extension == ".bva":
                self.add_row(["Mesh #"])
            else:
                single_mat = j3d.get_single_mat(extension)
                for i in range( len(single_mat)):
                    self.add_row(single_mat[i])
           
            
            for i in range( rows_to_add ):
                self.add_row()
            
            information = self.get_on_screen()
            first_vals, col_count = self.get_vertical_headers(information)
            self.table_display.setVerticalHeaderLabels(first_vals)
            self.fix_table(information, col_count)
               
    def frames_dialogue(self, one_time = False):
        if self.popout and self.frames_window is None:
            self.frames_window = frames_widget.frames_window(self.theme)
            self.frames_window.setWindowModality(QtCore.Qt.ApplicationModal)
            self.frames_window.exec_()
    
            frames_to_add = self.frames_window.get_info() 
            self.frames_from_bar( frames_to_add, False) 
            self.frames_window = None
        elif not self.popout and self.frames_box is None:
            self.frames_box = frames_widget.frames_box(self, one_time)
            self.right_vbox.addWidget(self.frames_box)
            
    def frames_from_bar(self, frames_to_add, one_time):
        if frames_to_add is not None:
        
            extension = self.anim_bar.currentItem().filepath
            info = self.get_on_screen()
            extension = extension[-4:]
            
            register_index = -1
            constant_index = -1
            duration = int( self.duration_box.text() )
           
            if len(frames_to_add) >= 3 and frames_to_add[2] == "duration":              
                frames_to_add = [ *range(frames_to_add[1], duration + 1, frames_to_add[0]) ]
           
            frames_column = 2
            if extension in [".bca", ".bck", ".btk", ".brk"]:
                frames_column = 3
            elif extension == ".blk":
                frames_column = 1
            
         
            if frames_to_add[-1] > duration:
                new = QTableWidgetItem(str(frames_to_add[-1]))
                duration = frames_to_add[-1]
                self.duration_box.setText( str(duration) )
                if extension in [".btk", ".bca", ".bck"]:
                    self.table_display.setItem(0, 5, new)
                else:
                    self.table_display.setItem(0, 3, new)
            
            keyframes = []
            
            frames_row = 0
            before_adding = [0, frames_column]

            if len(frames_to_add) == 0:
                return

            for i in range( frames_column, len(info[frames_row]) ):
                cell_text = info[frames_row][i].strip()
                if cell_text != "":
                    if not cell_text.isnumeric():
                        cell_text = cell_text[6:]
                            
                    cell_text = int(cell_text)
                    if cell_text in frames_to_add:
                        frames_to_add.remove(cell_text)      
                    
                    if cell_text <= frames_to_add[0] and cell_text > before_adding[0]:
                        before_adding = [cell_text, i]
                        
                    
                    if cell_text > frames_to_add[0]:
                        keyframes.append( (cell_text, i) )
            #assume keyframes are sorted
            """
            print(before_adding)
            print (keyframes)
            print(frames_to_add)
            print("-")
            """
            frames_added = 0
            keyframes_passed = 0
            
            for frame in frames_to_add:

                
                if len(keyframes) == 0:
                    insertion_column = before_adding[1] + keyframes_passed
                    print("len is zero")
                    #before_adding[1] += 1
                elif frame < keyframes[0][0]:
                    insertion_column = keyframes[0][1] -1
                    print("frame " + str(frame) + " is less than first keyframe ", end = "")
                elif frame > keyframes[0][0]:
                    insertion_column = keyframes[0][1]
                    keyframes.pop(0)
                    keyframes_passed += 1
                    print("frame " + str(frame)+ " is greater than first keyframe ", end = "")
                
                insertion_column += frames_added + 2
                print(insertion_column) 
                self.add_col_here(insertion_column)
                frames_added += 1
                
                new = QTableWidgetItem("Frame " + str(frame))
                self.table_display.setItem(frames_row, insertion_column - 1, new)
                
        
        self.table_display.setHorizontalHeaderLabels(self.get_on_screen()[1])
        
        if one_time:
            self.frames_box.setParent(None)
            self.right_vbox.removeWidget(self.frames_box)
            self.frames_box = None

    def emit_remove_dups(self):
        if self.anim_bar.currentItem() is None:
            return
            
        filepath = self.anim_bar.currentItem().filepath[-4:]
        stop_row =  self.table_display.columnCount()
        look_col = 2
        if filepath in [".bck", ".bca", ".brk"]:
            look_col = 3
        elif filepath == ".blk":
            look_col = 1
        CUTOFF = .01
        for i in range(1, self.table_display.rowCount() ) :
            
            local_look = look_col
            ini_item = self.table_display.item(i, local_look)
            
            while local_look < stop_row and (ini_item is None or ini_item.text().strip()) == "":
                local_look += 1
                ini_item = self.table_display.item(i, local_look)
            
            if abs( float(ini_item.text() )) < CUTOFF:
                ini_item.setText("0.0")
            
            #print("initial col " + str(local_look))
            if local_look < stop_row:
                curr_value = float(ini_item.text())
                local_look += 1
                
                for j in range( local_look, stop_row):
                    item = self.table_display.item(i, j)
                    
                    #print (item.text() + " at " + str(i) + " " + str(j) )
                    if item is not None and item.text().strip() != "":
                        
                        try:
                            if abs( float(item.text() )) < CUTOFF:
                                item.setText("0.0")
                            if abs( float(item.text()) - curr_value) < CUTOFF:
                                item.setText("")
                            else:
                                curr_value = float(item.text())
                        except:
                            item.setText("")

    # sound stuff - kill me
    def sounds_dialogue(self, one_time = False):
        if self.popout and self.sounds_window is None:
            self.sounds_window = sounds_widget.sounds_window(self.theme, self.anim_bar.currentItem().sound_data)
            self.sounds_window.setWindowModality(QtCore.Qt.ApplicationModal)
            self.sounds_window.exec_()
            
            new_sound_data = self.sound_window.get_info()
            
            self.sounds_from_bar(new_sound_data, False)
            self.sounds_window = None
            
        elif not self.popout and self.sounds_box is None:
            if self.anim_bar.topLevelItemCount() > 0:
                self.sounds_box = sounds_widget.sounds_box(self, one_time, self.anim_bar.currentItem().sound_data)
            else:
                self.sounds_box = sounds_widget.sounds_box(self, one_time, None)
            self.right_vbox.addWidget(self.sounds_box)
                
    def sounds_from_bar(self, new_sound_data, one_time):
        self.anim_bar.currentItem().set_sound(new_sound_data)
        #print("sounds from bar")
        #print(new_sound_data)
        if one_time:
            self.sounds_box.setParent( None)
            self.right_vbox.removeWidget(self.sounds_box)
            self.sounds_box = None
                
                
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
    parser.add_argument("input", default = None,  nargs = '?')

    args = parser.parse_args()

    app = QApplication(sys.argv)
    
    

    pikmin_gui = GenEditor()
    pikmin_gui.clipboard = app.clipboard() # we can put stuff on the clipboard with this
    pikmin_gui.show()
    
    if len(sys.argv) > 1 and path.exists(sys.argv[1]):
        if path.isfile(sys.argv[1]):
            #provided a file
            filepath = sys.argv[1][-4:]
            if filepath in [".bck", ".bca", ".btk", ".brk", ".btp", ".bpk", ".bla", ".blk", ".bva" ]:
            
                pikmin_gui.open_file(sys.argv[1])
            elif filepath == "anim":
                pikmin_gui.import_anim_file(sys.argv[1])
            elif filepath == ".fbx":
                pikmin_gui.import_fbx_file(sys.argv[1])
            elif filepath == ".gItf":
                pikmin_gui.import_bvh_file( sys.argv[1])
        elif path.isdir(sys.argv[1] ):
            pikmin_gui.open_folder(sys.argv[1] )
    
    err_code = app.exec()

    sys.exit(err_code)
