import os
import json

from collections import OrderedDict
from PyQt5.QtWidgets import QScrollArea, QSizePolicy, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox, QLineEdit, QComboBox, QSizePolicy
from PyQt5.QtGui import QIntValidator, QDoubleValidator, QValidator, QPainter, QColor
from math import inf
from lib.libbol import (EnemyPoint, EnemyPointGroup, CheckpointGroup, Checkpoint, Route, RoutePoint,
                        MapObject, KartStartPoint, Area, Camera, BOL, JugemPoint, MapObject,
                        LightParam, MGEntry, OBJECTNAMES, REVERSEOBJECTNAMES, MUSIC_IDS, REVERSE_MUSIC_IDS)
from lib.vectors import Vector3
from lib.model_rendering import Minimap
from PyQt5.QtCore import pyqtSignal, QSize, QRect
from lib.blo import readblo2
from widgets import tree_view
#from blo_editor import LayoutEditor


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


class DataEditor(QWidget):
    emit_3d_update = pyqtSignal()

    def __init__(self, parent, bound_to):
        super().__init__(parent)
        self.main_editor = parent
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

    def catch_text_update(self):
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

    def add_integer_input(self, attribute, text, min_val, max_val):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        line_edit.setValidator(PythonIntValidator(min_val, max_val, line_edit))

        def input_edited():
            print("Hmmmm")
            text = line_edit.text()
            print("input:", text)

            setattr(self.bound_to, attribute, int(text))

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

    def add_decimal_input(self, attribute, text, min_val, max_val):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        line_edit.setValidator(QDoubleValidator(min_val, max_val, 6, self))

        def input_edited():
            text = line_edit.text()
            print("input:", text)
            self.catch_text_update()
            setattr(self.bound_to, attribute, float(text))

        line_edit.editingFinished.connect(input_edited)

        self.vbox.addLayout(layout)

        return line_edit

    def add_text_input(self, attribute, text, maxlength, pad=" "):
        line_edit = QLineEdit(self)
        layout = self.create_labeled_widget(self, text, line_edit)

        line_edit.setMaxLength(maxlength)

        def input_edited():
            print("edited AAAAaaa", line_edit.text())
            text = line_edit.text()
            text = text.rjust(maxlength, pad)
            setattr(self.bound_to, attribute, text)

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

    def add_dropdown_input(self, attribute, text, keyval_dict):
        combobox = QComboBox(self)
        for val in keyval_dict:
            combobox.addItem(val)

        layout = self.create_labeled_widget(self, text, combobox)

        def item_selected(item):
            val = keyval_dict[item]
            print("selected", item)
            setattr(self.bound_to, attribute, val)

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

    def add_updater(self, func, attr, *args, **kwargs):
        preprocess_func = None
        if "preprocess_func" in kwargs:
            preprocess_func = kwargs["preprocess_func"]
            del kwargs["preprocess_func"]

        #print(args, kwargs)
        widget = func(attr, *args, **kwargs)

        if preprocess_func is None:
            def update_text(editor: DataEditor):
                widget.setText(str(getattr(editor.bound_to, attr)))
        else:
            def update_text(editor: DataEditor):
                widget.setText(str(preprocess_func(getattr(editor.bound_to, attr))))

        self.field_updaters.append(update_text)
        return widget

    def add_combobox_updater(self, func, attr, *args, **kwargs):
        preprocess_func = None
        if "preprocess_func" in kwargs:
            preprocess_func = kwargs["preprocess_func"]
            del kwargs["preprocess_func"]

        #print(args, kwargs)
        widget = func(attr, *args, **kwargs)

        if preprocess_func is None:
            def update_text(editor: DataEditor):
                widget.setCurrentIndex(getattr(editor.bound_to, attr))
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
        return PaneEdit  # TODO
    elif isinstance(obj, readblo2.Textbox):
        return PaneEdit  # TODO
    elif isinstance(obj, readblo2.Picture):
        return PictureEdit
    elif isinstance(obj, readblo2.Pane):
        return PaneEdit
    elif isinstance(obj, tree_view.Texture):
        return Texture
    elif isinstance(obj, EnemyPoint):
        return EnemyPointEdit
    elif isinstance(obj, EnemyPointGroup):
        return EnemyPointGroupEdit
    elif isinstance(obj, CheckpointGroup):
        return CheckpointGroupEdit
    elif isinstance(obj, MapObject):
        return ObjectEdit
    elif isinstance(obj, Checkpoint):
        return CheckpointEdit
    elif isinstance(obj, Route):
        return ObjectRouteEdit
    elif isinstance(obj, RoutePoint):
        return ObjectRoutePointEdit
    elif isinstance(obj, BOL):
        return BOLEdit
    elif isinstance(obj, KartStartPoint):
        return KartStartPointEdit
    elif isinstance(obj, Area):
        return AreaEdit
    elif isinstance(obj, Camera):
        return CameraEdit
    elif isinstance(obj, JugemPoint):
        return RespawnPointEdit
    elif isinstance(obj, LightParam):
        return LightParamEdit
    elif isinstance(obj, MGEntry):
        return MGEntryEdit
    elif isinstance(obj, Minimap):
        return MinimapEdit
    else:
        return None

        self.p_anchor = None
        self.p_size_x = None
        self.p_size_y = None
        self.p_scale_x = None
        self.p_scale_y = None
        self.p_offset_x = None
        self.p_offset_y = None
        self.p_rotation = None
        self.p_panename = None
        self.p_secondaryname = None


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
        print("hiii")
        p = self.p
        p.begin(self)
        h = self.height()
        w = self.width()
        """print(w,h)
        p.setBrush(QColor("white"))
        p.drawRect(0, 0, w - 1, h - 1)"""
        if self.img is not None:
            ratio = self.img.width()/self.img.height()

            new_h = w//ratio
            new_w = w

            if new_h > h:
                new_h = h
                new_w = new_h*w

            p.drawImage(QRect(0, 0, new_w, new_h), self.img)

            """if w < h:
                p.drawImage(QRect(0, 0, w, w//ratio), self.img)
            else:
                new_w = h*ratio
                new_h = h
                if w < new_w:
                    new_w = w
                    new_h = w//ratio
                p.drawImage(QRect(0, 0, new_w, new_h), self.img)"""
        p.end()


class Texture(DataEditor):
    def setup_widgets(self):
        self.tex = self.add_texture_widget()
        self.a = self.add_label("Dimensions:")

    def update_data(self):
        super().update_data()
        #self.main_editor: LayoutEditor
        self.bound_to: tree_view.Texture

        name = self.bound_to.bound_to
        print(name)

        img = self.main_editor.parent.texture_menu.texture_handler.get_texture_image(name)
        if img is not None:
            self.tex.set_image(img)

        self.a.setText("Dimensions: {0}x{1}".format(img.width(), img.height()))

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


class PictureColorEditor(QWidget):
    def __init__(self, color, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.unk1 = self.add_integer_input(dict_setter_int(self.color, "unk1"),
                                           "Unk 1", -MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.unk2 = self.add_integer_input(dict_setter_int(self.color, "unk2"),
                                           "Unk 2", -MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)

        self.unknowns = self.add_multiple_integer_input_list(
            [dict_setter_int_list(self.color, "unknowns", i) for i in range(4)], 4,
            "Unknowns", -MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)

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


class PaneEdit(DataEditor):
    def setup_widgets(self):
        readblo2.Pane
        self.name = self.add_updater(self.add_text_input,
                                     "p_panename", "Name", maxlength=8, pad="\x00",
                                     preprocess_func=lambda x: x.lstrip("\x00"))
        self.name.editingFinished.connect(self.update_name)
        self.secondaryname = self.add_updater(self.add_text_input,
                                              "p_secondaryname", "Secondary Name", maxlength=8, pad="\x00",
                                              preprocess_func=lambda x: x.lstrip("\x00"))
        self.enable = self.add_checkbox_updater(self.add_checkbox, "p_enabled", "Enable", 0, 1)
        self.hide = self.add_checkbox_updater(self.add_checkbox, "hide", "Hide (Editor only)", 0, 1)
        self.hide.stateChanged.connect(self.catch_text_update)
        self.hide.stateChanged.connect(self.update_name)
        self.anchor = self.add_combobox_updater(self.add_dropdown_input,
                                       "p_anchor", "Anchor", keyval_dict=anchor_dropdown)

        self.anchor.currentIndexChanged.connect(self.catch_text_update)
        self.offset_x = self.add_updater(self.add_decimal_input, "p_offset_x", "X Offset", -inf, +inf)
        self.offset_y = self.add_updater(self.add_decimal_input, "p_offset_y", "Y Offset", -inf, +inf)
        self.size_x = self.add_updater(self.add_decimal_input, "p_size_x", "X Size", -inf, +inf)
        self.size_y = self.add_updater(self.add_decimal_input, "p_size_y", "Y Size", -inf, +inf)
        self.scale_x = self.add_updater(self.add_decimal_input, "p_scale_x", "X Scale", -inf, +inf)
        self.scale_y = self.add_updater(self.add_decimal_input, "p_scale_y", "Y Scale", -inf, +inf)

        self.rotation = self.add_updater(self.add_decimal_input, "p_rotation", "Rotation", -inf, +inf)
        self.unk1 = self.add_updater(self.add_integer_input, "p_unk1", "Unknown 1", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk2 = self.add_updater(self.add_decimal_input, "p_unk4", "Unknown 4", -inf, +inf)


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


class PictureEdit(PaneEdit):
    def setup_widgets(self):
        super().setup_widgets()
        self.size = self.add_updater(self.add_integer_input, "size", "Size", -MIN_UNSIGNED_SHORT, +MAX_UNSIGNED_SHORT)
        self.unk_index = self.add_updater(self.add_decimal_input, "unk_index", "Unk Index", -inf, +inf)


        #self.material = self.add_updater(self.add_text_input_unlimited, "material", "Material")
        self.material = QComboBox(self)
        self.vbox.addWidget(self.material)
        blo: readblo2.ScreenBlo = self.main_editor.parent.layout_file

        self.mat_dict = OrderedDict()
        matpairs = []
        for material in blo.root.materials.materials:
            matpairs.append((material.name, material))

        matpairs.sort(key=lambda x: x[0])
        for matname, mat in matpairs:
            self.mat_dict[matname] = mat

            self.material.addItem(matname)

        self.material.currentTextChanged.connect(self._change_material)

        self.add_label("Color Top")
        self.color_1 = self.add_widget(PictureColorEditor(self.bound_to.color1))

        self.add_label("Color Bottom")
        self.color_2 = self.add_widget(PictureColorEditor(self.bound_to.color2))

    def _change_material(self, text):
        self.bound_to._material = self.mat_dict[text]
        self.bound_to.material = text
        self.emit_3d_update.emit()


    def update_data(self):
        super().update_data()
        self.color_1.update()
        self.color_2.update()

        for i in range(self.material.count()):
            if self.bound_to._material.name == self.material.itemText(i):
                self.material.setCurrentIndex(i)
                break

    def update_name(self):
        super().update_name()


class EnemyPointGroupEdit(DataEditor):
    def setup_widgets(self):
        self.groupid = self.add_integer_input("Group ID", "id", MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)

    def update_data(self):
        self.groupid.setText(str(self.bound_to.id))


class EnemyPointEdit(DataEditor):
    def setup_widgets(self, group_editable=False):
        self.position = self.add_multiple_decimal_input("Position", "position", ["x", "y", "z"],
                                                        -inf, +inf)
        self.pointsetting = self.add_integer_input("Point Setting", "pointsetting",
                                                    MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.link = self.add_integer_input("Link", "link",
                                           MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.scale = self.add_decimal_input("Scale", "scale", -inf, inf)
        self.groupsetting = self.add_integer_input("Group Setting", "groupsetting",
                                                   MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.group = self.add_integer_input("Group", "group",
                                            MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        if not group_editable:
            self.group.setDisabled(True)

        self.pointsetting2 = self.add_integer_input("Point Setting 2", "pointsetting2",
                                                    MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.unk1 = self.add_integer_input("Unknown 1", "unk1",
                                           MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.unk2 = self.add_integer_input("Unknown 2", "unk2",
                                           MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)

        for widget in self.position:
            widget.editingFinished.connect(self.catch_text_update)

    def update_data(self):
        obj: EnemyPoint = self.bound_to
        self.position[0].setText(str(round(obj.position.x, 3)))
        self.position[1].setText(str(round(obj.position.y, 3)))
        self.position[2].setText(str(round(obj.position.z, 3)))
        self.pointsetting.setText(str(obj.pointsetting))
        self.link.setText(str(obj.link))
        self.scale.setText(str(obj.scale))
        self.groupsetting.setText(str(obj.groupsetting))
        self.group.setText(str(obj.group))
        self.pointsetting2.setText(str(obj.pointsetting2))
        self.unk1.setText(str(obj.unk1))
        self.unk2.setText(str(obj.unk2))


class CheckpointGroupEdit(DataEditor):
    def setup_widgets(self):
        self.grouplink = self.add_integer_input("Group Link", "grouplink",
                                                MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.prevgroup = self.add_multiple_integer_input_list("Previous Groups", "prevgroup",
                                                              MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.nextgroup = self.add_multiple_integer_input_list("Next Groups", "nextgroup",
                                                              MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)

    def update_data(self):
        obj = self.bound_to
        self.grouplink.setText(str(obj.grouplink))
        for i, widget in enumerate(self.prevgroup):
            widget.setText(str(obj.prevgroup[i]))
        for i, widget in enumerate(self.nextgroup):
            widget.setText(str(obj.nextgroup[i]))


class CheckpointEdit(DataEditor):
    def setup_widgets(self):
        self.start = self.add_multiple_decimal_input("Start", "start", ["x", "y", "z"],
                                                        -inf, +inf)
        self.end = self.add_multiple_decimal_input("End", "end", ["x", "y", "z"],
                                                     -inf, +inf)

        self.unk1 = self.add_integer_input("Unknown", "unk1",
                                           MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.unk2 = self.add_checkbox("Unknown Flag", "unk2",
                                      0, 1)
        self.unk3 = self.add_checkbox("Unknown Flag 2", "unk3",
                                           0, 1)

    def update_data(self):
        obj: Checkpoint = self.bound_to
        self.start[0].setText(str(round(obj.start.x, 3)))
        self.start[1].setText(str(round(obj.start.y, 3)))
        self.start[2].setText(str(round(obj.start.z, 3)))

        self.end[0].setText(str(round(obj.end.x, 3)))
        self.end[1].setText(str(round(obj.end.y, 3)))
        self.end[2].setText(str(round(obj.end.z, 3)))

        self.unk1.setText(str(obj.unk1))
        self.unk2.setChecked(obj.unk2 != 0)
        self.unk3.setChecked(obj.unk3 != 0)


class ObjectRouteEdit(DataEditor):
    def setup_widgets(self):
        self.unk1 = self.add_integer_input("Unknown 1", "unk1",
                                           MIN_UNSIGNED_INT, MAX_UNSIGNED_INT)
        self.unk2 = self.add_integer_input("Unknown 2", "unk2",
                                           MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)

    def update_data(self):
        obj: Route = self.bound_to
        self.unk1.setText(str(obj.unk1))
        self.unk2.setText(str(obj.unk2))


class ObjectRoutePointEdit(DataEditor):
    def setup_widgets(self):
        self.position = self.add_multiple_decimal_input("Position", "position", ["x", "y", "z"],
                                                        -inf, +inf)
        self.unknown = self.add_integer_input("Object Action", "unk",
                                              MIN_UNSIGNED_INT, MAX_UNSIGNED_INT)

    def update_data(self):
        obj: RoutePoint = self.bound_to
        self.position[0].setText(str(round(obj.position.x, 3)))
        self.position[1].setText(str(round(obj.position.y, 3)))
        self.position[2].setText(str(round(obj.position.z, 3)))
        self.unknown.setText(str(obj.unk))


ROLL_OPTIONS = OrderedDict()
ROLL_OPTIONS["Disabled"] = 0
ROLL_OPTIONS["Only Sky+Items"] = 1
ROLL_OPTIONS["Entire Track"] = 2


class BOLEdit(DataEditor):
    def setup_widgets(self):
        self.roll = self.add_dropdown_input("Tilt", "roll", ROLL_OPTIONS)
        self.rgb_ambient = self.add_multiple_integer_input("RGB Ambient", "rgb_ambient", ["r", "g", "b"],
                                                           MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.rgba_light = self.add_multiple_integer_input("RGBA Light", "rgba_light", ["r", "g", "b", "a"],
                                                          MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.lightsource = self.add_multiple_decimal_input("Light Position", "lightsource", ["x", "y", "z"],
                                                           -inf, +inf)
        self.lap_count = self.add_integer_input("Lap Count", "lap_count",
                                                MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)

        self.music_id = self.add_dropdown_input("Music ID", "music_id",
                                                REVERSE_MUSIC_IDS)
        self.fog_type = self.add_integer_input("Fog Type", "fog_type",
                                               MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.fog_color = self.add_multiple_integer_input("Fog Color", "fog_color", ["r", "g", "b"],
                                                         MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.fog_startz = self.add_decimal_input("Fog Near Z", "fog_startz",
                                                 -inf, +inf)
        self.fog_endz = self.add_decimal_input("Fog Far Z", "fog_endz",
                                               -inf, +inf)
        self.unk1 = self.add_integer_input("Unknown 1", "unk1",
                                           MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.unk2 = self.add_checkbox("Sherbet Land Env. Effects", "unk2",
                                           off_value=0, on_value=1)
        self.unk3 = self.add_integer_input("Unknown 3", "unk3",
                                           MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.shadow_color = self.add_multiple_integer_input("Shadow Color", "shadow_color", ["r", "g", "b"],
                                                            MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.unk4 = self.add_integer_input("Unknown 4", "unk4",
                                           MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.unk5 = self.add_integer_input("Unknown 5", "unk5",
                                           MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.unk6 = self.add_integer_input("Unknown 6", "unk6",
                                           MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)

    def update_data(self):
        obj: BOL = self.bound_to
        #self.roll.setText(str(obj.roll))
        self.roll.setCurrentIndex(obj.roll)
        self.rgb_ambient[0].setText(str(obj.rgb_ambient.r))
        self.rgb_ambient[1].setText(str(obj.rgb_ambient.g))
        self.rgb_ambient[2].setText(str(obj.rgb_ambient.b))
        self.rgba_light[0].setText(str(obj.rgba_light.r))
        self.rgba_light[1].setText(str(obj.rgba_light.g))
        self.rgba_light[2].setText(str(obj.rgba_light.b))
        self.rgba_light[3].setText(str(obj.rgba_light.a))
        self.lightsource[0].setText(str(round(obj.lightsource.x, 3)))
        self.lightsource[1].setText(str(round(obj.lightsource.y, 3)))
        self.lightsource[2].setText(str(round(obj.lightsource.z, 3)))
        self.lap_count.setText(str(obj.lap_count))
        self.fog_type.setText(str(obj.fog_type))
        self.fog_color[0].setText(str(obj.fog_color.r))
        self.fog_color[1].setText(str(obj.fog_color.g))
        self.fog_color[2].setText(str(obj.fog_color.b))
        self.fog_startz.setText(str(obj.fog_startz))
        self.fog_endz.setText(str(obj.fog_endz))
        self.unk1.setText(str(obj.unk1))
        self.unk2.setChecked(obj.unk2 != 0)
        self.unk3.setText(str(obj.unk3))
        self.unk4.setText(str(obj.unk4))
        self.unk5.setText(str(obj.unk5))
        self.unk6.setText(str(obj.unk6))
        self.shadow_color[0].setText(str(obj.shadow_color.r))
        self.shadow_color[1].setText(str(obj.shadow_color.g))
        self.shadow_color[2].setText(str(obj.shadow_color.b))

        if obj.music_id not in MUSIC_IDS:
            name = "INVALID"
        else:
            name = MUSIC_IDS[obj.music_id]
        index = self.music_id.findText(name)
        self.music_id.setCurrentIndex(index)


class ObjectEdit(DataEditor):
    def setup_widgets(self):
        self.position = self.add_multiple_decimal_input("Position", "position", ["x", "y", "z"],
                                                        -inf, +inf)
        self.scale = self.add_multiple_decimal_input("Scale", "scale", ["x", "y", "z"],
                                                    -inf, +inf)
        self.rotation = self.add_rotation_input()
        self.objectid = self.add_dropdown_input("Object Type", "objectid", REVERSEOBJECTNAMES)

        self.pathid = self.add_integer_input("Path ID", "pathid",
                                             MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)

        self.unk_28 = self.add_integer_input("Unknown 0x28", "unk_28",
                                             MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)

        self.unk_2a = self.add_integer_input("Path Point ID", "unk_2a",
                                             MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.presence_filter = self.add_integer_input("Presence Mask", "presence_filter",
                                                      MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.presence = self.add_integer_input("Presence", "presence",
                                               MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.flag = self.add_checkbox("Collision", "unk_flag",
                                      off_value=0, on_value=1)
        self.unk_2f = self.add_integer_input("Unknown 0x2F", "unk_2f",
                                             MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)

        self.userdata = []
        for i in range(8):
            self.userdata.append(
                self.add_integer_input_index("Obj Data {0}".format(i+1), "userdata", i,
                                             MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
            )

        self.objectid.currentTextChanged.connect(self.update_name)

        for widget in self.position:
            widget.editingFinished.connect(self.catch_text_update)

        self.objectid.currentTextChanged.connect(self.rename_object_parameters)

        self.assets = self.add_label("Required Assets: Unknown")
        self.assets.setWordWrap(True)
        hint = self.assets.sizePolicy()
        hint.setVerticalPolicy(QSizePolicy.Minimum)
        self.assets.setSizePolicy(hint)

    def rename_object_parameters(self, current):
        parameter_names, assets = load_parameter_names(current)
        if parameter_names is None:
            for i in range(8):
                self.userdata[i][0].setText("Obj Data {0}".format(i+1))
                self.userdata[i][0].setVisible(True)
                self.userdata[i][1].setVisible(True)
            self.assets.setText("Required Assets: Unknown")
        else:
            for i in range(8):
                if parameter_names[i] == "Unused":
                    self.userdata[i][0].setVisible(False)
                    self.userdata[i][1].setVisible(False)
                    if self.bound_to.userdata[i] != 0:
                        Warning("Parameter with index {0} in object {1} is marked as Unused but has value {2}".format(
                            i, current, self.bound_to.userdata[i]
                        ))
                else:
                    self.userdata[i][0].setVisible(True)
                    self.userdata[i][1].setVisible(True)
                    self.userdata[i][0].setText(parameter_names[i])
            if len(assets) == 0:
                self.assets.setText("Required Assets: None")
            else:
                self.assets.setText("Required Assets: {0}".format(", ".join(assets)))

    def update_name(self):
        if self.bound_to.widget is None:
            return
        self.bound_to.widget.update_name()
        self.bound_to.widget.parent().sort()
        self.bound_to.widget.setSelected(True)

    def update_data(self):
        obj: MapObject = self.bound_to
        self.position[0].setText(str(round(obj.position.x, 3)))
        self.position[1].setText(str(round(obj.position.y, 3)))
        self.position[2].setText(str(round(obj.position.z, 3)))

        self.scale[0].setText(str(round(obj.scale.x, 3)))
        self.scale[1].setText(str(round(obj.scale.y, 3)))
        self.scale[2].setText(str(round(obj.scale.z, 3)))

        self.update_rotation(*self.rotation)

        if obj.objectid not in OBJECTNAMES:
            name = "INVALID"
        else:
            name = OBJECTNAMES[obj.objectid]
        index = self.objectid.findText(name)
        self.objectid.setCurrentIndex(index)

        self.pathid.setText(str(obj.pathid))
        self.unk_28.setText(str(obj.unk_28))
        self.unk_2a.setText(str(obj.unk_2a))
        self.unk_2f.setText(str(obj.unk_2f))
        self.presence_filter.setText(str(obj.presence_filter))
        self.presence.setText(str(obj.presence))
        self.flag.setChecked(obj.unk_flag != 0)
        for i in range(8):
            self.userdata[i][1].setText(str(obj.userdata[i]))


class KartStartPointEdit(DataEditor):
    def setup_widgets(self):
        self.position = self.add_multiple_decimal_input("Position", "position", ["x", "y", "z"],
                                                        -inf, +inf)
        self.rotation = self.add_rotation_input()
        self.scale = self.add_multiple_decimal_input("Scale", "scale", ["x", "y", "z"],
                                                     -inf, +inf)

        options = OrderedDict()
        options["Left"] = 0
        options["Right"] = 1
        self.poleposition = self.add_dropdown_input("Pole Position", "poleposition",
                                                    options)
        self.playerid = self.add_integer_input("Player ID", "playerid",
                                               MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.unknown = self.add_integer_input("Unknown", "unknown",
                                              MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)

    def update_data(self):
        obj: KartStartPoint = self.bound_to
        self.position[0].setText(str(round(obj.position.x, 3)))
        self.position[1].setText(str(round(obj.position.y, 3)))
        self.position[2].setText(str(round(obj.position.z, 3)))

        self.update_rotation(*self.rotation)

        self.scale[0].setText(str(obj.scale.x))
        self.scale[1].setText(str(obj.scale.y))
        self.scale[2].setText(str(obj.scale.z))

        self.poleposition.setCurrentIndex(obj.poleposition)
        self.playerid.setText(str(obj.playerid))
        self.unknown.setText(str(obj.unknown))


class AreaEdit(DataEditor):
    def setup_widgets(self):
        self.position = self.add_multiple_decimal_input("Position", "position", ["x", "y", "z"],
                                                        -inf, +inf)
        self.scale = self.add_multiple_decimal_input("Scale", "scale", ["x", "y", "z"],
                                                     -inf, +inf)
        self.rotation = self.add_rotation_input()
        self.check_flag = self.add_integer_input("Check Flag", "check_flag",
                                                 MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.area_type = self.add_integer_input("Area Type", "area_type",
                                                MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.camera_index = self.add_integer_input("Camera Index", "camera_index",
                                                   MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.unk1 = self.add_integer_input("Unknown 1", "unk1",
                                           MIN_UNSIGNED_INT, MAX_UNSIGNED_INT)
        self.unk2 = self.add_integer_input("Unknown 2", "unk2",
                                           MIN_UNSIGNED_INT, MAX_UNSIGNED_INT)
        self.unkfixedpoint = self.add_integer_input("Unknown 3 Fixed Point", "unkfixedpoint",
                                                    MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.unkshort = self.add_integer_input("Unknown 4", "unkshort",
                                               MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.shadow_id = self.add_integer_input("Shadow ID", "shadow_id",
                                                MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.lightparam_index = self.add_integer_input("LightParam Index", "lightparam_index",
                                                       MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)

    def update_data(self):
        obj: Area = self.bound_to
        self.position[0].setText(str(round(obj.position.x, 3)))
        self.position[1].setText(str(round(obj.position.y, 3)))
        self.position[2].setText(str(round(obj.position.z, 3)))

        self.scale[0].setText(str(round(obj.scale.x, 3)))
        self.scale[1].setText(str(round(obj.scale.y, 3)))
        self.scale[2].setText(str(round(obj.scale.z, 3)))

        self.update_rotation(*self.rotation)

        self.check_flag.setText(str(obj.check_flag))
        self.area_type.setText(str(obj.area_type))
        self.camera_index.setText(str(obj.camera_index))
        self.unk1.setText(str(obj.unk1))
        self.unk2.setText(str(obj.unk2))
        self.unkfixedpoint.setText(str(obj.unkfixedpoint))
        self.unkshort.setText(str(obj.unkshort))
        self.shadow_id.setText(str(obj.shadow_id))
        self.lightparam_index.setText(str(obj.lightparam_index))


class CameraEdit(DataEditor):
    def setup_widgets(self):
        self.position = self.add_multiple_decimal_input("Position", "position", ["x", "y", "z"],
                                                        -inf, +inf)
        self.position2 = self.add_multiple_decimal_input("End Point", "position2", ["x", "y", "z"],
                                                        -inf, +inf)
        self.position3 = self.add_multiple_decimal_input("Start Point", "position3", ["x", "y", "z"],
                                                        -inf, +inf)
        self.rotation = self.add_rotation_input()
        self.unkbyte = self.add_integer_input("Unknown 1", "unkbyte",
                                              MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.camtype = self.add_integer_input("Camera Type", "camtype",
                                              MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.startzoom = self.add_integer_input("Start Zoom", "startzoom",
                                                MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.camduration = self.add_integer_input("Camera Duration", "camduration",
                                                  MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.startcamera = self.add_integer_input("Start Camera", "startcamera",
                                                  MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.unk2 = self.add_integer_input("Unknown 2", "unk2",
                                           MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.unk3 = self.add_integer_input("Unknown 3", "unk3",
                                           MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.route = self.add_integer_input("Path ID", "route",
                                            MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.routespeed = self.add_integer_input("Route Speed", "routespeed",
                                                 MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.endzoom = self.add_integer_input("End Zoom", "endzoom",
                                              MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.nextcam = self.add_integer_input("Next Cam", "nextcam",
                                              MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.name = self.add_text_input("Camera Name", "name", 4)

    def update_data(self):
        obj: Camera = self.bound_to
        self.position[0].setText(str(round(obj.position.x, 3)))
        self.position[1].setText(str(round(obj.position.y, 3)))
        self.position[2].setText(str(round(obj.position.z, 3)))

        self.position2[0].setText(str(round(obj.position2.x, 3)))
        self.position2[1].setText(str(round(obj.position2.y, 3)))
        self.position2[2].setText(str(round(obj.position2.z, 3)))

        self.position3[0].setText(str(round(obj.position3.x, 3)))
        self.position3[1].setText(str(round(obj.position3.y, 3)))
        self.position3[2].setText(str(round(obj.position3.z, 3)))

        self.update_rotation(*self.rotation)

        self.unkbyte.setText(str(obj.unkbyte))
        self.camtype.setText(str(obj.camtype))
        self.startzoom.setText(str(obj.startzoom))
        self.camduration.setText(str(obj.camduration))
        self.startcamera.setText(str(obj.startcamera))
        self.unk2.setText(str(obj.unk2))
        self.unk3.setText(str(obj.unk3))
        self.route.setText(str(obj.route))
        self.routespeed.setText(str(obj.routespeed))
        self.endzoom.setText(str(obj.endzoom))
        self.nextcam.setText(str(obj.nextcam))
        self.name.setText(obj.name)


class RespawnPointEdit(DataEditor):
    def setup_widgets(self):
        self.position = self.add_multiple_decimal_input("Position", "position", ["x", "y", "z"],
                                                        -inf, +inf)
        self.rotation = self.add_rotation_input()
        self.respawn_id = self.add_integer_input("Respawn ID", "respawn_id",
                                                 MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.unk1 = self.add_integer_input("Next Enemy Point", "unk1",
                                           MIN_UNSIGNED_SHORT, MAX_UNSIGNED_SHORT)
        self.unk2 = self.add_integer_input("Unknown 2", "unk2",
                                           MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.unk3 = self.add_integer_input("Unknown 3", "unk3",
                                           MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)

    def update_data(self):
        obj: JugemPoint = self.bound_to
        self.position[0].setText(str(round(obj.position.x, 3)))
        self.position[1].setText(str(round(obj.position.y, 3)))
        self.position[2].setText(str(round(obj.position.z, 3)))
        self.update_rotation(*self.rotation)
        self.respawn_id.setText(str(obj.respawn_id))
        self.unk1.setText(str(obj.unk1))
        self.unk2.setText(str(obj.unk2))
        self.unk3.setText(str(obj.unk3))


class LightParamEdit(DataEditor):
    def setup_widgets(self):
        self.color1 = self.add_multiple_integer_input("RGBA 1", "color1", ["r", "g", "b", "a"],
                                                        MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)
        self.unkvec = self.add_multiple_decimal_input("Vector", "unkvec", ["x", "y", "z"],
                                                      -inf, +inf)
        self.color2 = self.add_multiple_integer_input("RGBA 2", "color2", ["r", "g", "b", "a"],
                                                      MIN_UNSIGNED_BYTE, MAX_UNSIGNED_BYTE)

    def update_data(self):
        obj: LightParam = self.bound_to
        self.color1[0].setText(str(obj.color1.r))
        self.color1[1].setText(str(obj.color1.g))
        self.color1[2].setText(str(obj.color1.b))
        self.color1[3].setText(str(obj.color1.a))

        self.color2[0].setText(str(obj.color2.r))
        self.color2[1].setText(str(obj.color2.g))
        self.color2[2].setText(str(obj.color2.b))
        self.color2[3].setText(str(obj.color2.a))

        self.unkvec[0].setText(str(obj.unkvec.x))
        self.unkvec[1].setText(str(obj.unkvec.y))
        self.unkvec[2].setText(str(obj.unkvec.z))


class MGEntryEdit(DataEditor):
    def setup_widgets(self):
        self.unk1 = self.add_integer_input("Unknown 1", "unk1",
                                           MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.unk2 = self.add_integer_input("Unknown 2", "unk2",
                                           MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.unk3 = self.add_integer_input("Unknown 3", "unk3",
                                           MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)
        self.unk4 = self.add_integer_input("Unknown 4", "unk4",
                                           MIN_SIGNED_SHORT, MAX_SIGNED_SHORT)

    def update_data(self):
        obj: MGEntry = self.bound_to
        self.unk1.setText(str(obj.unk1))
        self.unk2.setText(str(obj.unk2))
        self.unk3.setText(str(obj.unk3))
        self.unk4.setText(str(obj.unk4))


class MinimapEdit(DataEditor):
    def setup_widgets(self):
        self.topleft = self.add_multiple_decimal_input("TopLeft", "corner1", ["x", "y", "z"],
                                                       -inf, +inf)
        self.bottomright = self.add_multiple_decimal_input("BottomRight", "corner2", ["x", "y", "z"],
                                                           -inf, +inf)
        self.orientation = self.add_integer_input("Orientation", "orientation",
                                                  0, 3)

    def update_data(self):
        obj: Minimap = self.bound_to
        self.topleft[0].setText(str(round(obj.corner1.x, 3)))
        self.topleft[1].setText(str(round(obj.corner1.y, 3)))
        self.topleft[2].setText(str(round(obj.corner1.z, 3)))
        self.bottomright[0].setText(str(round(obj.corner2.x, 3)))
        self.bottomright[1].setText(str(round(obj.corner2.y, 3)))
        self.bottomright[2].setText(str(round(obj.corner2.z, 3)))

        self.orientation.setText(str(obj.orientation))