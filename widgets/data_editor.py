import os
import json
from functools import partial
from collections import OrderedDict
from PyQt5.QtWidgets import QFileDialog, QPushButton, QMessageBox, QScrollArea, QSizePolicy, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox, QLineEdit, QComboBox, QSizePolicy
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QIntValidator, QDoubleValidator, QValidator, QPainter, QColor
from math import inf
from lib.libbol import (EnemyPoint, EnemyPointGroup, CheckpointGroup, Checkpoint, Route, RoutePoint,
                        MapObject, KartStartPoint, Area, Camera, BOL, JugemPoint, MapObject,
                        LightParam, MGEntry, OBJECTNAMES, REVERSEOBJECTNAMES, MUSIC_IDS, REVERSE_MUSIC_IDS)
from lib.vectors import Vector3
from lib.model_rendering import Minimap
from PyQt5.QtCore import pyqtSignal, QSize, QRect, Qt
from lib.blo import readblo2
from widgets import tree_view
from lib.blo.tex.texture_utils import ImageFormat, PaletteFormat
#from blo_editor import LayoutEditor


def open_error_dialog(errormsg, self):
    errorbox = QMessageBox()
    errorbox.critical(self, "Error", errormsg)
    errorbox.setFixedSize(500, 200)


def load_parameter_names(objectname):
    try:
        with open(os.path.join("object_parameters", objectname+".json"), "r") as f:
            data = json.load(f)
            parameter_names = data["Object Parameters"]
            assets = data["Assets"]
            if len(parameter_names) != 8:
                raise RuntimeError("Not enough or too many parameters: {0} (should be 8)".format(len(parameter_names)))
            return parameter_names, assets
    except Exception as err:
        print(err)
        return None, None


class PythonIntValidator(QValidator):
    def __init__(self, min, max, parent):
        super().__init__(parent)
        self.min = min
        self.max = max

    def validate(self, p_str, p_int):
        if p_str == "" or p_str == "-":
            return QValidator.Intermediate, p_str, p_int

        try:
            result = int(p_str)
        except:
            return QValidator.Invalid, p_str, p_int

        if self.min <= result <= self.max:
            return QValidator.Acceptable, p_str, p_int
        else:
            return QValidator.Invalid, p_str, p_int

    def fixup(self, s):
        pass


# Combobox variant that prevents accidental
# scrolling when mouse hovers
class NonScrollQComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, *args, **kwargs):
        if self.hasFocus():
            return super().wheelEvent(*args, **kwargs)


class DataEditor(QWidget):
    emit_3d_update = pyqtSignal()

    def __init__(self, parent, bound_to, editor):
        super().__init__(parent)
        self.main_editor = editor
        self.bound_to = bound_to
        self.vbox = QVBoxLayout(self)
        self.setLayout(self.vbox)

        self.description = self.add_label("Object")

        self.field_updaters = []

        self.setup_widgets()

    def add_widget(self, widget):
        self.vbox.addWidget(widget)
        return widget

    def add_texture_widget(self):
        tex = TextureView(self)
        self.vbox.addWidget(tex)
        return tex

    def catch_text_update(self, *args):
        self.emit_3d_update.emit()

    def setup_widgets(self):
        pass

    def update_data(self):
        for update_field in self.field_updaters:
            update_field(self)

    def create_label(self, text):
        label = QLabel(self)
        label.setText(text)
        return label

    def add_label(self, text):
        label = self.create_label(text)
        self.vbox.addWidget(label)
        return label

    def create_labeled_widget(self, parent, text, widget):
        layout = QHBoxLayout(parent)
        label = self.create_label(text)
        label.setText(text)
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout

    def create_labeled_widgets(self, parent, text, widgetlist):
        layout = QHBoxLayout(parent)
        label = self.create_label(text)
        label.setText(text)
        layout.addWidget(label)
        for widget in widgetlist:
            layout.addWidget(widget)
        return layout

    def add_checkbox(self, attribute, text, off_value, on_value):
        checkbox = QCheckBox(self)
        layout = self.create_labeled_widget(self, text, checkbox)

        def checked(state):
            if state == 0:
                setattr(self.bound_to, attribute, off_value)
            else:
                setattr(self.bound_to, attribute, on_value)

        checkbox.stateChanged.connect(checked)
        self.vbox.addLayout(layout)

        return checkbox

    def add_integer_input(self, obj, attribute, text, min_val, max_val):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        line_edit.setValidator(PythonIntValidator(min_val, max_val, line_edit))

        def input_edited():
            print("Hmmmm")
            text = line_edit.text()
            print("input:", text)

            setattr(obj, attribute, int(text))

        line_edit.editingFinished.connect(input_edited)

        self.vbox.addLayout(layout)
        print("created for", text, attribute)
        return line_edit

    def add_integer_input_index(self, attribute, text, index, min_val, max_val):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        line_edit.setValidator(QIntValidator(min_val, max_val, self))

        def input_edited():
            text = line_edit.text()
            print("input:", text)
            mainattr = getattr(self.bound_to, attribute)
            mainattr[index] = int(text)

        line_edit.editingFinished.connect(input_edited)
        label = layout.itemAt(0).widget()
        self.vbox.addLayout(layout)

        return label, line_edit

    def add_decimal_input(self, bound_to, attribute, text, min_val, max_val):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        line_edit.setValidator(QDoubleValidator(min_val, max_val, 6, self))

        def input_edited():
            text = line_edit.text()
            print("input:", text)
            self.catch_text_update()
            setattr(bound_to, attribute, float(text))

        line_edit.editingFinished.connect(input_edited)

        self.vbox.addLayout(layout)

        return line_edit

    def add_text_input(self, bound_to, attribute, text, maxlength, pad=" "):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        line_edit.setMaxLength(maxlength)

        def input_edited():
            print("edited AAAAaaa", line_edit.text())
            text = line_edit.text()
            text = text.rjust(maxlength, pad)
            setattr(bound_to, attribute, text)

        line_edit.editingFinished.connect(input_edited)
        self.vbox.addLayout(layout)

        return line_edit

    def add_text_input_unlimited(self, attribute, text):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        #line_edit.setMaxLength(maxlength)

        def input_edited():
            print("edited AAAAaaa", line_edit.text())
            text = line_edit.text()
            #text = text.rjust(maxlength, pad)
            setattr(self.bound_to, attribute, text)

        line_edit.editingFinished.connect(input_edited)
        self.vbox.addLayout(layout)

        return line_edit

    def add_dropdown_input(self, obj, attribute, text, keyval_dict):
        combobox = NonScrollQComboBox(self)
        for val in keyval_dict:
            combobox.addItem(val)

        layout = self.create_labeled_widget(self, text, combobox)

        def item_selected(item):
            val = keyval_dict[item]
            print("selected", item)
            setattr(obj, attribute, val)

        combobox.currentTextChanged.connect(item_selected)
        self.vbox.addLayout(layout)

        return combobox

    def add_multiple_integer_input(self, attribute, subattributes, text, min_val, max_val):
        line_edits = []
        for subattr in subattributes:
            line_edit = QLineEdit(self)

            if max_val <= MAX_UNSIGNED_BYTE:
                line_edit.setMaximumWidth(30)

            line_edit.setValidator(QIntValidator(min_val, max_val, self))

            input_edited = create_setter(line_edit, self.bound_to, attribute, subattr, self.catch_text_update, isFloat=False)

            line_edit.editingFinished.connect(input_edited)
            line_edits.append(line_edit)

        layout = self.create_labeled_widgets(self, text, line_edits)
        self.vbox.addLayout(layout)


        return line_edits

    def add_multiple_decimal_input(self, attribute, subattributes, text, min_val, max_val):
        line_edits = []
        for subattr in subattributes:
            line_edit = QLineEdit(self)

            line_edit.setValidator(QDoubleValidator(min_val, max_val, 6, self))

            input_edited = create_setter(line_edit, self.bound_to, attribute, subattr, self.catch_text_update, isFloat=True)
            line_edit.editingFinished.connect(input_edited)
            line_edits.append(line_edit)

        layout = self.create_labeled_widgets(self, text, line_edits)
        self.vbox.addLayout(layout)

        return line_edits

    def add_multiple_integer_input_list(self, attribute, text, min_val, max_val):
        line_edits = []
        fieldlist = getattr(self.bound_to, attribute)
        for i in range(len(fieldlist)):
            line_edit = QLineEdit(self)
            line_edit.setMaximumWidth(30)

            line_edit.setValidator(QIntValidator(min_val, max_val, self))

            input_edited = create_setter_list(line_edit, self.bound_to, attribute, i)
            line_edit.editingFinished.connect(input_edited)
            line_edits.append(line_edit)

        layout = self.create_labeled_widgets(self, text, line_edits)
        self.vbox.addLayout(layout)

        return line_edits

    def update_rotation(self, forwardedits, upedits):
        rotation = self.bound_to.rotation
        forward, up, left = rotation.get_vectors()

        for attr in ("x", "y", "z"):
            if getattr(forward, attr) == 0.0:
                setattr(forward, attr, 0.0)

        for attr in ("x", "y", "z"):
            if getattr(up, attr) == 0.0:
                setattr(up, attr, 0.0)

        forwardedits[0].setText(str(round(forward.x, 4)))
        forwardedits[1].setText(str(round(forward.y, 4)))
        forwardedits[2].setText(str(round(forward.z, 4)))

        upedits[0].setText(str(round(up.x, 4)))
        upedits[1].setText(str(round(up.y, 4)))
        upedits[2].setText(str(round(up.z, 4)))
        self.catch_text_update()

    def add_rotation_input(self):
        rotation = self.bound_to.rotation
        forward_edits = []
        up_edits = []

        for attr in ("x", "y", "z"):
            line_edit = QLineEdit(self)
            validator = QDoubleValidator(-1.0, 1.0, 9999, self)
            validator.setNotation(QDoubleValidator.StandardNotation)
            line_edit.setValidator(validator)

            forward_edits.append(line_edit)

        for attr in ("x", "y", "z"):
            line_edit = QLineEdit(self)
            validator = QDoubleValidator(-1.0, 1.0, 9999, self)
            validator.setNotation(QDoubleValidator.StandardNotation)
            line_edit.setValidator(validator)

            up_edits.append(line_edit)

        def change_forward():
            forward, up, left = rotation.get_vectors()

            newforward = Vector3(*[float(v.text()) for v in forward_edits])
            if newforward.norm() == 0.0:
                newforward = left.cross(up)
            newforward.normalize()
            up = newforward.cross(left)
            up.normalize()
            left = up.cross(newforward)
            left.normalize()

            rotation.set_vectors(newforward, up, left)
            self.update_rotation(forward_edits, up_edits)

        def change_up():
            print("finally changing up")
            forward, up, left = rotation.get_vectors()
            newup = Vector3(*[float(v.text()) for v in up_edits])
            if newup.norm() == 0.0:
                newup = forward.cross(left)
            newup.normalize()
            forward = left.cross(newup)
            forward.normalize()
            left = newup.cross(forward)
            left.normalize()

            rotation.set_vectors(forward, newup, left)
            self.update_rotation(forward_edits, up_edits)

        for edit in forward_edits:
            edit.editingFinished.connect(change_forward)
        for edit in up_edits:
            edit.editingFinished.connect(change_up)

        layout = self.create_labeled_widgets(self, "Forward dir", forward_edits)
        self.vbox.addLayout(layout)
        layout = self.create_labeled_widgets(self, "Up dir", up_edits)
        self.vbox.addLayout(layout)
        return forward_edits, up_edits

    def set_value(self, field, val):
        field.setText(str(val))

    def add_updater(self, func, bound_to, attr, *args, **kwargs):
        preprocess_func = None
        if "preprocess_func" in kwargs:
            preprocess_func = kwargs["preprocess_func"]
            del kwargs["preprocess_func"]

        #print(args, kwargs)
        widget = func(bound_to, attr, *args, **kwargs)

        if preprocess_func is None:
            def update_text(editor: DataEditor):
                widget.setText(str(getattr(bound_to, attr)))
        else:
            def update_text(editor: DataEditor):
                widget.setText(str(preprocess_func(getattr(bound_to, attr))))

        self.field_updaters.append(update_text)
        return widget

    def add_combobox_updater(self, func, bound_to, attr, *args, **kwargs):
        preprocess_func = None
        if "preprocess_func" in kwargs:
            preprocess_func = kwargs["preprocess_func"]
            del kwargs["preprocess_func"]

        #print(args, kwargs)
        widget = func(bound_to, attr, *args, **kwargs)

        if preprocess_func is None:
            def update_text(editor: DataEditor):
                widget.setCurrentIndex(getattr(bound_to, attr))
        else:
            def update_text(editor: DataEditor):
                widget.setCurrentIndex(preprocess_func(getattr(editor.bound_to, attr)))

        self.field_updaters.append(update_text)
        return widget

    def add_checkbox_updater(self, func, attr, *args, **kwargs):
        preprocess_func = None
        if "preprocess_func" in kwargs:
            preprocess_func = kwargs["preprocess_func"]
            del kwargs["preprocess_func"]

        #print(args, kwargs)
        widget = func(attr, *args, **kwargs)

        if preprocess_func is None:
            def update_text(editor: DataEditor):
                widget.setChecked(getattr(editor.bound_to, attr) != 0)
        else:
            def update_text(editor: DataEditor):
                widget.setChecked(preprocess_func(getattr(editor.bound_to, attr)))

        self.field_updaters.append(update_text)
        return widget

    def add_material_combobox(self):
        material_widget = self.add_widget(NonScrollQComboBox(self))
        blo: readblo2.ScreenBlo = self.main_editor.parent.layout_file

        mat_dict = OrderedDict()
        matpairs = []
        for material in blo.root.materials.materials:
            matpairs.append((material.name, material))

        matpairs.sort(key=lambda x: x[0])
        for matname, mat in matpairs:
            mat_dict[matname] = mat

            material_widget.addItem(matname)

        material_widget.currentTextChanged.connect(partial(self._change_material, mat_dict))

        return material_widget, mat_dict

    def _change_material(self, mat_dict, text):
        self.bound_to._material = mat_dict[text]
        self.bound_to.material = text
        self.emit_3d_update.emit()


def create_setter_list(lineedit, bound_to, attribute, index):
    def input_edited():
        text = lineedit.text()
        mainattr = getattr(bound_to, attribute)
        mainattr[index] = int(text)

    return input_edited


def create_setter(lineedit, bound_to, attribute, subattr, update3dview, isFloat):
    if isFloat:
        def input_edited():
            text = lineedit.text()
            mainattr = getattr(bound_to, attribute)

            setattr(mainattr, subattr, float(text))
            update3dview()
        return input_edited
    else:
        def input_edited():
            text = lineedit.text()
            mainattr = getattr(bound_to, attribute)

            setattr(mainattr, subattr, int(text))
            update3dview()
        return input_edited


MIN_SIGNED_BYTE = -128
MAX_SIGNED_BYTE = 127
MIN_SIGNED_SHORT = -2**15
MAX_SIGNED_SHORT = 2**15 - 1
MIN_SIGNED_INT = -2**31
MAX_SIGNED_INT = 2**31 - 1

MIN_UNSIGNED_BYTE = MIN_UNSIGNED_SHORT = MIN_UNSIGNED_INT = 0
MAX_UNSIGNED_BYTE = 255
MAX_UNSIGNED_SHORT = 2**16 - 1
MAX_UNSIGNED_INT = 2**32 - 1


def choose_data_editor(obj):
    print("acoo", type(obj), obj)
    if isinstance(obj, readblo2.Window):
        return WindowEditor  # TODO
    elif isinstance(obj, readblo2.Textbox):
        return TextboxEditor  # TODO
    elif isinstance(obj, readblo2.Picture):
        return PictureEdit
    elif isinstance(obj, readblo2.Pane):
        return PaneEdit
    elif isinstance(obj, tree_view.Texture):
        return Texture
    elif isinstance(obj, tree_view.Material):
        return MaterialEditor
    else:
        return None


class TextureView(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.img = None
        self.p = QPainter(self)
        self.setMinimumSize(QSize(100, 256))
        print("did get initialized")

    def set_image(self, img):
        self.img = img

    def paintEvent(self, event):
        p = self.p
        p.begin(self)
        h = self.height()
        w = self.width()
        if self.img is not None:
            ratio = self.img.width()/self.img.height()

            new_h = w//ratio
            new_w = w

            if new_h > h:
                new_h = h
                new_w = new_h*ratio

            p.drawImage(QRect(0, 0, new_w, new_h), self.img)
        p.end()


FORMATS = OrderedDict()
FORMATS["I4"]       = ImageFormat.I4
FORMATS["I8"]       = ImageFormat.I8
FORMATS["IA4"]      = ImageFormat.IA4
FORMATS["IA8"]      = ImageFormat.IA8
FORMATS["RGB565"]   = ImageFormat.RGB565
FORMATS["RGB5A3"]   = ImageFormat.RGB5A3
FORMATS["RGBA32"]   = ImageFormat.RGBA32
FORMATS["C4"]       = ImageFormat.C4
FORMATS["C8"]       = ImageFormat.C8
FORMATS["C14X2"]    = ImageFormat.C14X2
FORMATS["CMPR"]     = ImageFormat.CMPR

PALETTE_FORMATS = OrderedDict()
PALETTE_FORMATS["IA8"]     = PaletteFormat.IA8
PALETTE_FORMATS["RGB565"]  = PaletteFormat.RGB565
PALETTE_FORMATS["RGB5A3"]  = PaletteFormat.RGB5A3


class Texture(DataEditor):
    def setup_widgets(self):
        self.tex = self.add_texture_widget()
        self.load_texture = QPushButton("Import Texture", self)
        self.load_texture.pressed.connect(self.handle_load_texture)
        self.vbox.addWidget(self.load_texture)
        self.a = self.add_label("Dimensions:")
        self.line_edit = QLineEdit(self)
        # line_edit.setValidator(PythonSameNameValidator())
        layout = self.create_labeled_widget(self, "Name", self.line_edit)
        texture = self.bound_to.bound_to
        old_text = texture
        textures = self.main_editor.parent.layout_file.root.textures.references
        index = textures.index(texture)
        # line_edit.setMaxLength(maxlength)

        def input_edited():
            print("edited AAAAaaa", self.line_edit.text())
            text = self.line_edit.text()
            # text = text.rjust(maxlength, pad)
            if text.lower() == self.bound_to.bound_to.lower():
                pass
            elif text.lower() in [x.lower() for x in textures]:
                open_error_dialog("Cannot use name, name already in use!", self)
            else:
                textures[index] = text
                self.bound_to.bound_to = text
                self.bound_to.setText(0, text)
                if self.main_editor.parent.texture_menu.texture_handler.exists(old_text):
                    self.main_editor.parent.texture_menu.texture_handler.rename(old_text, text)
                #mat.name = text
            # setattr(self.bound_to, attribute, text)

        self.line_edit.editingFinished.connect(input_edited)
        self.vbox.addLayout(layout)

        bti = self.main_editor.parent.texture_menu.texture_handler.get_bti(texture)

        if bti is not None:
            self.alphasetting = self.add_integer_input(bti, "alpha_setting", "Alpha Setting", MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
            self.format = self.add_dropdown_input(bti, "image_format", "Image Format", FORMATS)
            self.format.currentIndexChanged.connect(self.update_dirty_status)

    def update_dirty_status(self):
        texture = self.bound_to.bound_to
        self.main_editor.parent.texture_menu.texture_handler.update_format(texture)

    def handle_load_texture(self):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            "",
            "Image (*.png;*.jpg;*.jfif;);;All files (*)")

        if filepath:
            name = self.bound_to.bound_to
            self.main_editor.parent.texture_menu.texture_handler.replace_from_path(filepath, name)

    def update_data(self):
        super().update_data()
        #self.main_editor: LayoutEditor
        self.bound_to: tree_view.Texture

        name = self.bound_to.bound_to
        print(name)
        self.line_edit.setText(name)

        img = self.main_editor.parent.texture_menu.texture_handler.get_texture_image(name)
        if img is not None:
            self.tex.set_image(img)

            self.a.setText("Dimensions: {0}x{1}".format(img.width(), img.height()))
        bti = self.main_editor.parent.texture_menu.texture_handler.get_bti(name)
        if bti is not None:
            self.alphasetting.setText(str(bti.alpha_setting))
            for i, v in enumerate(FORMATS.values()):
                if bti.image_format == v:
                    self.format.setCurrentIndex(i)


anchor_dropdown = OrderedDict()
anchor_dropdown["Top-Left"] = 0
anchor_dropdown["Center-Top"] = 1
anchor_dropdown["Top-Right"] = 2
anchor_dropdown["Center-Left"] = 3
anchor_dropdown["Center"] = 4
anchor_dropdown["Center-Right"] = 5
anchor_dropdown["Bottom-Left"] = 6
anchor_dropdown["Center-Bottom"] = 7
anchor_dropdown["Bottom-Right"] = 8


def dict_setter_int(var, field):
    def setter(x):
        var[field] = int(x)

    return setter


def dict_setter_int_list(var, field, i):
    def setter(x):
        var[field][i] = int(x)

    return setter


def color_setter_int(var, field):
    def setter(x):
        setattr(var, field, x)

    return setter


class SubEditor(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

    def create_labeled_widgets(self, parent, text, widgetlist):
        layout = QHBoxLayout(parent)
        label = self.create_label(text)
        label.setText(text)
        layout.addWidget(label)
        for widget in widgetlist:
            layout.addWidget(widget)
        return layout

    def add_integer_input(self, setter, text, min_val, max_val):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        line_edit.setValidator(PythonIntValidator(min_val, max_val, line_edit))

        def input_edited():
            print("Hmmmm")
            text = line_edit.text()
            print("input:", text)

            #setattr(self.bound_to, attribute, int(text))
            #self.bound_to
            setter(text)

        line_edit.editingFinished.connect(input_edited)

        self.layout.addLayout(layout)
        return line_edit

    def add_text_input(self, setter, text, min_val, max_val):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        line_edit.setValidator(PythonIntValidator(min_val, max_val, line_edit))

        def input_edited():
            print("Hmmmm")
            text = line_edit.text()
            print("input:", text)

            #setattr(self.bound_to, attribute, int(text))
            #self.bound_to
            setter(text)

        line_edit.editingFinished.connect(input_edited)

        self.layout.addLayout(layout)
        return line_edit

    def add_multiple_integer_input_list(self, setter_list, length, text, min_val, max_val):
        line_edits = []

        for i in range(length):
            line_edit = QLineEdit(self)
            line_edit.setMaximumWidth(30)

            line_edit.setValidator(QIntValidator(min_val, max_val, self))

            def create_input_edited(i, line_edit):
                def input_edited():
                    print("Hmmmm", i, line_edit)
                    text = line_edit.text()
                    print("input:", text)

                    # setattr(self.bound_to, attribute, int(text))
                    # self.bound_to
                    setter_list[i](text)
                return input_edited

            line_edit.editingFinished.connect(create_input_edited(i, line_edit))
            line_edits.append(line_edit)

        layout = self.create_labeled_widgets(self, text, line_edits)
        self.layout.addLayout(layout)

        return line_edits

    def create_label(self, text):
        label = QLabel(self)
        label.setText(text)
        return label

    def add_label(self, text):
        label = self.create_label(text)
        self.layout.addWidget(label)
        return label

    def create_labeled_widget(self, parent, text, widget):
        layout = QHBoxLayout(parent)
        label = self.create_label(text)
        label.setText(text)
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout


class PythonSameNameValidator(QValidator):
    def __init__(self, materials, parent):
        super().__init__(parent)
        self.materials = materials

    def validate(self, p_str, p_int):
        if p_str == "" :
            return QValidator.Intermediate, p_str, p_int

        if p_str in [mat.name for mat in self.materials]:
            return QValidator.Invalid, p_str, p_int
        else:
            return QValidator.Acceptable, p_str, p_int

    def fixup(self, s):
        pass


class MaterialEditor(DataEditor):
    def setup_widgets(self):
        super().setup_widgets()

        self.line_edit = QLineEdit(self)
        #line_edit.setValidator(PythonSameNameValidator())
        layout = self.create_labeled_widget(self, "Name", self.line_edit)
        mat = self.bound_to.bound_to
        materials = self.main_editor.parent.layout_file.root.materials.materials

        # line_edit.setMaxLength(maxlength)

        def input_edited():
            print("edited AAAAaaa", self.line_edit.text())
            text = self.line_edit.text()
            # text = text.rjust(maxlength, pad)
            if text == self.bound_to.bound_to.name:
                pass
            elif text in [x.name for x in materials]:
                open_error_dialog("Cannot use name, name already in use!", self)
            else:
                mat.name = text
            #setattr(self.bound_to, attribute, text)

        self.line_edit.editingFinished.connect(input_edited)
        self.line_edit.editingFinished.connect(self.update_name)
        self.vbox.addLayout(layout)

        self.texture_edits = []

        self.textures = OrderedDict()
        texture_list = []
        for i, tex in enumerate(self.main_editor.parent.layout_file.root.textures.references):
            texture_list.append((tex, i))
        texture_list.sort(key=lambda x: x[1])

        for tex, i in texture_list:
            self.textures[tex] = i

        for i in range(8):
            self.add_texture_edit(i)

    def add_texture_edit(self, i):
        combobox = NonScrollQComboBox(self)
        combobox.addItem("--None--")
        for texture in self.textures:
            combobox.addItem(texture)

        combobox.currentTextChanged.connect(partial(self.set_texture, i))
        combobox.currentTextChanged.connect(self.catch_text_update)
        self.vbox.addLayout(self.create_labeled_widget(self, "Tex {0}".format(i+1), combobox))
        self.texture_edits.append(combobox)

    def set_texture(self, pos, name):
        if self.texture_edits[pos].currentIndex() == 0:
            self.bound_to.bound_to.textures[pos] = None
        else:
            index = self.textures[name]
            self.bound_to.bound_to.textures[pos] = index

    def update_data(self):
        self.line_edit.setText(self.bound_to.bound_to.name)
        for i in range(8):
            for j, v in enumerate(self.textures.items()):
                tex, index = v
                if self.bound_to.bound_to.textures[i] == index:
                    self.texture_edits[i].setCurrentIndex(j+1)

    def update_name(self):
        self.bound_to.setText(0, self.bound_to.bound_to.name)


class PictureColorEditor(SubEditor):
    def __init__(self, color, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color

        self.unk1 = self.add_integer_input(dict_setter_int(self.color, "unk1"),
                                           "Unk 1", -MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.unk2 = self.add_integer_input(dict_setter_int(self.color, "unk2"),
                                           "Unk 2", -MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)

        self.unknowns = self.add_multiple_integer_input_list(
            [dict_setter_int_list(self.color, "unknowns", i) for i in range(4)], 4,
            "UV Coordinates (L/R)", -MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)

        self.color1 = self.add_multiple_integer_input_list(
            [dict_setter_int_list(self.color, "col1", i) for i in range(4)], 4,
            "Color Left", -MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)

        self.color2 = self.add_multiple_integer_input_list(
            [dict_setter_int_list(self.color, "col2", i) for i in range(4)], 4,
            "Color Right", -MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)

    def update(self):
        self.unk1.setText(str(self.color["unk1"]))
        self.unk2.setText(str(self.color["unk2"]))

        for i in range(4):
            self.unknowns[i].setText(str(self.color["unknowns"][i]))

        for i in range(4):
            self.color1[i].setText(str(self.color["col1"][i]))

        for i in range(4):
            self.color2[i].setText(str(self.color["col2"][i]))


class ColorEdit(SubEditor):
    def __init__(self, color, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color
        self.color_input = self.add_multiple_integer_input_list(
            [color_setter_int(self.color, x) for x in ("r", "g", "b", "a")], 4,
            name, MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)

    def update(self):
        self.color_input[0].setText(str(self.color.r))
        self.color_input[1].setText(str(self.color.g))
        self.color_input[2].setText(str(self.color.b))
        self.color_input[3].setText(str(self.color.a))

class WindowSubSettingEdit(SubEditor):
    def __init__(self, subdata, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subdata = subdata
        self.parent = parent
        self.main_editor = parent.main_editor

        self.sub_unk2 = self.add_integer_input(dict_setter_int(self.subdata, "sub_unk2"),
                                           "Unk 2", -MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)

        self.sub_unk3 = self.add_integer_input(dict_setter_int(self.subdata, "sub_unk3"),
                                               "Unk 3", -MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)

        self.material, mat_dict = self.add_material_combobox()

    def add_material_combobox(self):
        material_widget = NonScrollQComboBox(self)
        self.layout.addWidget(material_widget)
        blo: readblo2.ScreenBlo = self.main_editor.parent.layout_file

        mat_dict = OrderedDict()
        matpairs = []
        for material in blo.root.materials.materials:
            matpairs.append((material.name, material))

        matpairs.sort(key=lambda x: x[0])
        for matname, mat in matpairs:
            mat_dict[matname] = mat

            material_widget.addItem(matname)

        material_widget.currentTextChanged.connect(partial(self._change_material, mat_dict))

        return material_widget, mat_dict

    def _change_material(self, mat_dict, text):
        #self.bound_to._material = mat_dict[text]
        self.subdata["material"] = text
        self.parent.emit_3d_update.emit()

    def update_data(self):
        self.sub_unk2.setText(str(self.subdata["sub_unk2"]))
        self.sub_unk3.setText(str(self.subdata["sub_unk3"]))

        for i in range(self.material.count()):
            if self.subdata["material"] == self.material.itemText(i):
                self.material.setCurrentIndex(i)
                break


class PaneEdit(DataEditor):
    def setup_widgets(self):
        readblo2.Pane
        self.name = self.add_updater(self.add_text_input, self.bound_to,
                                     "p_panename", "Name", maxlength=8, pad="\x00",
                                     preprocess_func=lambda x: x.lstrip("\x00"))
        self.name.editingFinished.connect(self.update_name)
        self.secondaryname = self.add_updater(self.add_text_input, self.bound_to,
                                              "p_secondaryname", "Secondary Name", maxlength=8, pad="\x00",
                                              preprocess_func=lambda x: x.lstrip("\x00"))
        self.enable = self.add_checkbox_updater(self.add_checkbox, "p_enabled", "Enable", 0, 1)
        self.hide = self.add_checkbox_updater(self.add_checkbox, "hide", "Hide (Editor only)", 0, 1)
        self.hide.stateChanged.connect(self.catch_text_update)
        self.hide.stateChanged.connect(self.update_name)
        self.anchor = self.add_combobox_updater(self.add_dropdown_input, self.bound_to,
                                       "p_anchor", "Anchor", keyval_dict=anchor_dropdown)

        self.anchor.currentIndexChanged.connect(self.catch_text_update)
        self.offset_x = self.add_updater(self.add_decimal_input, self.bound_to, "p_offset_x", "X Offset", -inf, +inf)
        self.offset_y = self.add_updater(self.add_decimal_input, self.bound_to, "p_offset_y", "Y Offset", -inf, +inf)
        self.size_x = self.add_updater(self.add_decimal_input, self.bound_to, "p_size_x", "X Size", -inf, +inf)
        self.size_y = self.add_updater(self.add_decimal_input, self.bound_to, "p_size_y", "Y Size", -inf, +inf)
        self.scale_x = self.add_updater(self.add_decimal_input, self.bound_to, "p_scale_x", "X Scale", -inf, +inf)
        self.scale_y = self.add_updater(self.add_decimal_input, self.bound_to, "p_scale_y", "Y Scale", -inf, +inf)

        self.rotation = self.add_updater(self.add_decimal_input, self.bound_to, "p_rotation", "Rotation", -inf, +inf)
        self.unk1 = self.add_updater(self.add_integer_input, self.bound_to, "p_bckindex", "BCK Animation Index", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk2 = self.add_updater(self.add_decimal_input, self.bound_to, "p_unk4", "Unknown 4", -inf, +inf)

    def update_data(self):
        super().update_data()
        self.bound_to: readblo2.Pane
        bound_to = self.bound_to

        #self.name.setText(bound_to.p_panename.lstrip("\x00"))
        """self.secondaryname.setText(bound_to.p_secondaryname.lstrip("\x00"))
        self.anchor.setCurrentIndex(bound_to.p_anchor)
        self.offset_x.setText(str(bound_to.p_offset_x))
        self.offset_y.setText(str(bound_to.p_offset_y))
        self.size_x.setText(str(bound_to.p_size_x))
        self.size_y.setText(str(bound_to.p_size_y))
        self.scale_x.setText(str(bound_to.p_scale_x))
        self.scale_y.setText(str(bound_to.p_scale_y))
        self.rotation.setText(str(bound_to.p_rotation))"""

    def update_name(self):
        if self.bound_to.widget is None:
            return
        self.bound_to.widget.update_name()


class WindowEditor(PaneEdit):
    def setup_widgets(self):
        super().setup_widgets()
        #self.size = self.add_updater(self.add_integer_input, self.bound_to, "size", "Size",
        #                             -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)

        self.unkbyte1 = self.add_updater(self.add_integer_input, self.bound_to, "unkbyte1", "Unk 1",
                                     -MIN_UNSIGNED_BYTE, +MAX_UNSIGNED_BYTE)

        self.unkbyte2 = self.add_updater(self.add_integer_input, self.bound_to, "unkbyte2", "Unk 2",
                                         -MIN_UNSIGNED_BYTE, +MAX_UNSIGNED_BYTE)

        self.unk3 = self.add_updater(self.add_integer_input, self.bound_to, "unk3", "Unk 3",
                                         -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk4 = self.add_updater(self.add_integer_input, self.bound_to, "unk4", "Unk 4",
                                     -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk5 = self.add_updater(self.add_integer_input, self.bound_to, "unk5", "Unk 5",
                                     -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk6 = self.add_updater(self.add_integer_input, self.bound_to, "unk6", "Unk 6",
                                     -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk7 = self.add_updater(self.add_integer_input, self.bound_to, "unk7", "Unk 7",
                                     -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)

        self.material, mat_dict = self.add_material_combobox()
        self.subs = []

        for i in range(4):
            self.add_label("Corner {0}".format(i+1))
            sub = self.add_widget(WindowSubSettingEdit(self.bound_to.subdata[i], self))
            self.subs.append(sub)

    def update_data(self):
        super().update_data()

        for i in range(self.material.count()):
            if self.bound_to.material == self.material.itemText(i):
                self.material.setCurrentIndex(i)
                break

        for sub in self.subs:
            sub.update_data()


class TextboxEditor(PaneEdit):
    def setup_widgets(self):
        super().setup_widgets()
        #self.size = self.add_updater(self.add_integer_input, self.bound_to, "size", "Size", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk_1 = self.add_updater(self.add_integer_input, self.bound_to, "unk1", "Unk 1", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.material, self.mat_dict = self.add_material_combobox()
        self.signedunk3 = self.add_updater(self.add_integer_input, self.bound_to, "signedunk3", "Unk 3", MIN_SIGNED_SHORT, +MAX_SIGNED_SHORT)
        self.signedunk4 = self.add_updater(self.add_integer_input, self.bound_to, "signedunk4", "Unk 4", MIN_SIGNED_SHORT, +MAX_SIGNED_SHORT)


        self.unk5 = self.add_updater(self.add_integer_input, self.bound_to, "unk5", "Font Width", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk6 = self.add_updater(self.add_integer_input, self.bound_to, "unk6", "Font Height", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk7 = self.add_updater(self.add_integer_input, self.bound_to, "unk7byte", "Unk 7", -MIN_UNSIGNED_BYTE, +MAX_UNSIGNED_BYTE)
        self.unk8 = self.add_updater(self.add_integer_input, self.bound_to, "unk8byte", "Unk 8", -MIN_UNSIGNED_BYTE, +MAX_UNSIGNED_BYTE)

        self.color_top = self.add_widget(ColorEdit(self.bound_to.color_top, "Color Top"))
        self.color_bottom = self.add_widget(ColorEdit(self.bound_to.color_bottom, "Color Bottom"))



        self.unk11 = self.add_updater(self.add_integer_input, self.bound_to, "unk11", "Unk 11", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.text_cutoff = self.add_updater(self.add_integer_input, self.bound_to, "text_cutoff", "Text Cutoff", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.text = self.add_text_input_unlimited("text", "Text")

    def update_data(self):
        super().update_data()

        self.color_top.update()
        self.color_bottom.update()

        self.text.setText(self.bound_to.text)

        for i in range(self.material.count()):
            if self.bound_to.material == self.material.itemText(i):
                self.material.setCurrentIndex(i)
                break


class PictureEdit(PaneEdit):
    def setup_widgets(self):
        super().setup_widgets()
        #self.size = self.add_updater(self.add_integer_input, self.bound_to, "size", "Size", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk_index = self.add_updater(self.add_integer_input, self.bound_to, "unk_index", "Unk Index", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)


        #self.material = self.add_updater(self.add_text_input_unlimited, "material", "Material")
        self.material, self.mat_dict = self.add_material_combobox()

        self.add_label("Top Settings")
        self.color_1 = self.add_widget(PictureColorEditor(self.bound_to.color1))

        self.add_label("Bottom Settings")
        self.color_2 = self.add_widget(PictureColorEditor(self.bound_to.color2))

    def update_data(self):
        super().update_data()
        self.color_1.update()
        self.color_2.update()

        if self.bound_to._material is not None:
            for i in range(self.material.count()):
                if self.bound_to._material.name == self.material.itemText(i):
                    self.material.setCurrentIndex(i)
                    break

    def update_name(self):
        super().update_name()
