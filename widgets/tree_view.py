from functools import partial
from copy import deepcopy

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView
from lib.libbol import BOL, get_full_name
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDropEvent, QDragEnterEvent
from PyQt5.QtWidgets import QAction, QMenu, QMessageBox
from lib.blo.readblo2 import Information, Pane, Window, Textbox, Picture, ScreenBlo, MAT1, TextureNames, FontNames, Node


def open_error_dialog(errormsg, self):
    errorbox = QMessageBox()
    errorbox.critical(self, "Error", errormsg)
    errorbox.setFixedSize(500, 200)


class ObjectGroup(QTreeWidgetItem):
    def __init__(self, name, parent=None, bound_to=None):
        if parent is None:
            super().__init__()
        else:
            super().__init__(parent)
        self.setText(0, name)
        self.bound_to = bound_to

    def remove_children(self):
        self.takeChildren()


class ObjectGroupObjects(ObjectGroup):
    def sort(self):
        """items = []
        for i in range(self.childCount()):
            items.append(self.takeChild(0))

        items.sort(key=lambda x: x.bound_to.objectid)

        for item in items:
            self.addChild(item)"""
        self.sortChildren(0, 0)


# Groups
class EnemyPointGroup(ObjectGroup):
    def __init__(self, parent, bound_to):
        super().__init__("Enemy point group", parent=parent, bound_to=bound_to)
        self.update_name()

    def update_name(self):
        index = self.parent().indexOfChild(self)
        self.setText(0, "Enemy point group {0} (ID: {1})".format(index, self.bound_to.id))


class CheckpointGroup(ObjectGroup):
    def __init__(self, parent, bound_to):
        super().__init__("Checkpoint group", parent=parent, bound_to=bound_to)
        self.update_name()

    def update_name(self):
        index = self.parent().indexOfChild(self)
        self.setText(0, "Checkpoint group {0}".format(index))


class ObjectPointGroup(ObjectGroup):
    def __init__(self, parent, bound_to):
        super().__init__("Object point group", parent=parent, bound_to=bound_to)
        self.update_name()

    def update_name(self):
        index = self.parent().indexOfChild(self)
        self.setText(0, "Object point group {0}".format(index))


# Entries in groups or entries without groups
class NamedItem(QTreeWidgetItem):
    def __init__(self, parent, name, bound_to=None, index=None):
        super().__init__(parent)
        self.setText(0, name)
        self.bound_to = bound_to
        self.index = index
        self.update_name()

    def update_name(self):
        pass


class Texture(NamedItem):
    pass


class Material(NamedItem):
    pass


class InformationItem(NamedItem):
    def __init__(self, bound_to: Information):
        super().__init__(None, "Information", bound_to, None)


class NamedItemWithChildren(NamedItem):
    def remove_children(self):
        self.takeChildren()


class TextureList(NamedItemWithChildren):
    pass


class MaterialList(NamedItemWithChildren):
    pass


class FontList(NamedItemWithChildren):
    pass


class PaneItem(NamedItemWithChildren):
    def __init__(self, parent, name, bound_to: Pane=None, index=None):
        name = bound_to.name
        bound_to.widget = self
        super().__init__(parent, "{0}: {1}".format(bound_to.name, bound_to.p_panename), bound_to, index)
        self.update_name()

    def update_name(self):
        print("updating name", self.bound_to.p_panename)
        name = "{0}: {1}".format(self.bound_to.name, self.bound_to.p_panename)
        if self.bound_to.hide:
            name += " (H)"
        self.setText(0, name)




class TextboxItem(PaneItem):
    pass


class PictureItem(PaneItem):
    pass


class WindowItem(PaneItem):
    pass



"""
class EnemyRoutePoint(NamedItem):
    def update_name(self):
        group_item = self.parent()
        group = group_item.bound_to

        index = group.points.index(self.bound_to)

        self.setText(0, "Enemy Route Point {0}".format(index))


class Checkpoint(NamedItem):
    def update_name(self):
        offset = 0
        group_item = self.parent()
        groups_item = group_item.parent()
        for i in range(groups_item.childCount()):
            other_group_item = groups_item.child(i)
            if other_group_item == group_item:
                break
            else:
                print("Hmmm,",other_group_item.text(0), len(other_group_item.bound_to.points), offset)
                group_object = other_group_item.bound_to
                offset += len(group_object.points)

        group = group_item.bound_to

        index = group.points.index(self.bound_to)

        self.setText(0, "Checkpoint {0} (pos={1})".format(index+1+offset, index))


class ObjectRoutePoint(NamedItem):
    def update_name(self):
        group_item = self.parent()
        group = group_item.bound_to

        index = group.points.index(self.bound_to)

        self.setText(0, "Object Route Point {0}".format(index))


class ObjectEntry(NamedItem):
    def __init__(self, parent, name, bound_to):
        super().__init__(parent, name, bound_to)
        bound_to.widget = self

    def update_name(self):
        self.setText(0, get_full_name(self.bound_to.objectid))

    def __lt__(self, other):
        return self.bound_to.objectid < other.bound_to.objectid


class KartpointEntry(NamedItem):
    def update_name(self):
        playerid = self.bound_to.playerid
        if playerid == 0xFF:
            result = "All"
        else:
            result = "ID:{0}".format(playerid)
        self.setText(0, "Kart Start Point {0}".format(result))


class AreaEntry(NamedItem):
    def update_name(self):
        self.setText(0, "Area (Type: {0})".format(self.bound_to.area_type))


class CameraEntry(NamedItem):
    def update_name(self):
        self.setText(0, "Camera {0} (Type: {1})".format(self.index, self.bound_to.camtype))


class RespawnEntry(NamedItem):
    def update_name(self):
        self.setText(0, "Respawn Point (ID: {0})".format(self.bound_to.respawn_id))


class LightParamEntry(NamedItem):
    def update_name(self):
        self.setText(0, "LightParam {0}".format(self.index))


class MGEntry(NamedItem):
    def update_name(self):
        self.setText(0, "MG")
"""



class LayoutDataTreeView(QTreeWidget):
    #select_all = pyqtSignal(ObjectGroup)
    #reverse = pyqtSignal(ObjectGroup)
    add_item = pyqtSignal(PaneItem)
    add_material = pyqtSignal(MaterialList)
    add_texture = pyqtSignal(TextureList)

    delete_item = pyqtSignal(PaneItem)
    delete_material = pyqtSignal(MaterialList)
    delete_texture = pyqtSignal(Texture)

    copy_item = pyqtSignal(PaneItem)
    paste_item = pyqtSignal(PaneItem)

    rebuild_tree = pyqtSignal()

    def __init__(self, main_editor, *args, **kwargs):
        super().__init__(*args)
        self.main_editor = main_editor
        self.setMaximumWidth(600)
        self.resize(200, self.height())
        self.setColumnCount(1)
        self.setHeaderLabel("Track Data Entries")

        self.information = InformationItem(None)
        self.addTopLevelItem(self.information)
        self.material_list = MaterialList(None, "Materials", None, None)
        self.texture_list = TextureList(None, "Textures", None, None)
        self.font_list = FontList(None, "Fonts", None, None)
        self.layout = NamedItemWithChildren(None, "Layout", None, None)

        for item in (self.texture_list, self.material_list, self.font_list, self.layout):
            self.addTopLevelItem(item)

        """self.enemyroutes = self._add_group("Enemy point groups")
        self.checkpointgroups = self._add_group("Checkpoint groups")
        self.objectroutes = self._add_group("Object point groups")
        self.objects = self._add_group("Objects", ObjectGroupObjects)
        self.kartpoints = self._add_group("Kart start points")
        self.areas = self._add_group("Areas")
        self.cameras = self._add_group("Cameras")
        self.respawnpoints = self._add_group("Respawn points")
        self.lightparams = self._add_group("Light param entries")
        self.mgentries = self._add_group("MG entries")
        """
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.run_context_menu)

        self._copied_object = None
        self._moving = False
        self.blo: ScreenBlo = None

        self.setSelectionMode(self.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setAnimated(True)

    def mimedataToItem(self):
        mimedata_to_item = {}
        widgets = []
        next = [self.layout]

        while len(next) > 0:
            curr = next.pop(0)
            mimedata = self.mimeData([curr])
            mimedata_to_item[mimedata.data('application/x-qabstractitemmodeldatalist')] = curr
            #print(mimedata, curr)

            for i in range(curr.childCount()):
                next.append(curr.child(i))

        return mimedata_to_item

    def dragEnterEvent(self, e: QDragEnterEvent):
        data = e.mimeData().data('application/x-qabstractitemmodeldatalist')
        mimedata_to_item = self.mimedataToItem()
        if data in mimedata_to_item:
            widget = mimedata_to_item[data]
            if widget.parent() is not None and widget.parent() != self.layout:
                e.acceptProposedAction()

    def item_is_ancestor_of(self, item, child):
        while child is not None:
            if item == child:
                return True
            child = child.parent()
        return False

    def dropEvent(self, e: QDropEvent):
        #, 'baseact', QtCore.Qt.CopyAction)
        # if e.keyboardModifiers() & QtCore.Qt.AltModifier:
        #     #e.setDropAction(QtCore.Qt.CopyAction)
        #     print('copy')
        # else:
        #     #e.setDropAction(QtCore.Qt.MoveAction)
        #     print("drop")
        data = e.mimeData().data('application/x-qabstractitemmodeldatalist')
        mimedata_to_item = self.mimedataToItem()
        widget = mimedata_to_item[data]
        index = self.indexAt(e.pos())
        parent = index.parent()
        print("Dropping", widget)
        print(e.source())
        print("Row/Column", index.row(),  index.column(), parent.row(), parent.column())

        parent_item = self.itemFromIndex(parent)
        item_drop = self.itemFromIndex(index)
        print(self.item_is_ancestor_of(widget, item_drop))
        if item_drop in mimedata_to_item.values():
            blo_item = widget.bound_to
            blo_item.parent.child.children.remove(blo_item)
            if item_drop.parent() == self.layout:
                new_blo_item = item_drop.bound_to
                new_blo_item.child.children.insert(0, blo_item)
                blo_item.parent = new_blo_item
            else:
                new_blo_item = parent_item.bound_to
                new_blo_item.child.children.insert(index.row(), blo_item)
                blo_item.parent = new_blo_item
            self.rebuild_tree.emit()
            e.acceptProposedAction()
        """ 
        print(e.dropAction())
        # super(Tree, self).dropEvent(e)
        index = self.indexAt(e.pos())
        parent = index.parent()
        print('in', index.row())
        print(e.mimeData().text())
        print(e.mimeData().formats())
        print(e.mimeData().data('application/x-qabstractitemmodeldatalist'))
        text = e.mimeData().data('application/x-qabstractitemmodeldatalist')
        self.model().dropMimeData(e.mimeData(), e.dropAction(), index.row(), index.column(), parent)"""
        #e.reject()

    def emit_add_item(self, pos):
        item = self.itemAt(pos)
        if isinstance(item, (PaneItem, )):
            self.add_item.emit(item)

    def emit_delete_item(self, pos):
        item = self.itemAt(pos)
        if isinstance(item, (PaneItem, )):
            self.delete_item.emit(item)

    def handle_add_new_texture(self):
        existing_textures = [x.lower() for x in self.blo.root.textures.references]

        new_name = "NewTexture.bti"
        i = 1
        while new_name.lower() in existing_textures:
            new_name = "NewTexture({0}).bti".format(i)
            i += 1

        self.blo.root.textures.references.append(new_name)
        self.rebuild_tree.emit()

    def handle_copy_item_with_children(self, pos):
        item = self.itemAt(pos)
        if isinstance(item, (PaneItem,)):
            self._copied_object = item.bound_to.copy(children=True)

    def handle_copy_item_without_children(self, pos):
        item = self.itemAt(pos)
        if isinstance(item, (PaneItem,)):
            self._copied_object = item.bound_to.copy(children=False)

    def handle_paste_item(self, pos):
        item = self.itemAt(pos)
        if isinstance(item, (PaneItem,)):
            item.bound_to.add_child(self._copied_object.copy(children=True))
            self.rebuild_tree.emit()

    def handle_add_item(self, pos, itemcls):
        item = self.itemAt(pos)
        if isinstance(item, (PaneItem,)):
            item.bound_to.add_child(itemcls.new())
            self.rebuild_tree.emit()

    def handle_duplicate(self, pos):
        item = self.itemAt(pos)
        if isinstance(item, (Material, )):
            mat = item.bound_to.copy()

            num = 0
            new_name = "{0}({1})".format(mat.name, num)
            while self.blo.root.materials.get_mat_index(new_name) is not None:
                num += 1
                new_name = "{0}({1})".format(mat.name, num)

            mat.name = new_name

            self.blo.root.materials.materials.append(mat)
            self.rebuild_tree.emit()

    def handle_delete_texture(self, delete_file, pos):
        item = self.itemAt(pos)

        if isinstance(item, (Texture,)):
            index = self.blo.root.textures.references.index(item.bound_to)
            mats_used = self.blo.root.materials.list_materials_that_use_texture(index)
            result = [x.name for x in mats_used]
            if len(result) == 0:

                if delete_file:
                    result = QMessageBox.question(self, "Texture Deletion",
                                                  ("The texture file will be removed when you save the textures. "
                                                   "A texture might be used by other BLO files. "
                                                   "Are you sure you want to delete the texture?"),
                                                  QMessageBox.Yes | QMessageBox.No)
                    if result == QMessageBox.Yes:
                        self.delete_texture.emit(item)
                        self.blo.root.textures.references.pop(index)
                        self.blo.root.materials.remove_texture_index(index)
                        self.rebuild_tree.emit()
                else:

                    self.blo.root.textures.references.pop(index)
                    self.blo.root.materials.remove_texture_index(index)
                    self.rebuild_tree.emit()



            else:
                if len(result) > 5:
                    show = result[0:5]
                    error = ("Cannot delete, texture is used by following materials: \n"
                             "{0} and {1} more".format(", ".join(show), len(result) - 5))
                else:
                    if len(result) == 0:
                        ending = ""
                    else:
                        ending = "s"
                    error = ("Cannot delete, texture is used by following material{1}: \n"
                             "{0}".format(", ".join(result), ending))
                open_error_dialog(error, self)


    def handle_delete(self, pos):
        item = self.itemAt(pos)

        if isinstance(item, (Material,)):
            mat = item.bound_to
            assert mat in self.blo.root.materials.materials

            result = self.blo.find_elements_that_use_material(mat)
            if len(result) == 0:
                self.blo.root.materials.materials.remove(mat)
                self.rebuild_tree.emit()
            else:
                result = list(map(lambda x: x.strip("\x00"), result))
                if len(result) > 5:
                    show = result[0:5]
                    error = ("Cannot delete, material is used by following element: \n"
                            "{0} and {1} more".format(", ".join(show), len(result)-5))
                else:
                    if len(result) == 0:
                        ending = ""
                    else:
                        ending = "s"
                    error = ("Cannot delete, material is used by following element{1}: \n"
                             "{0}".format(", ".join(result), ending))

                open_error_dialog(error, self)

    def run_context_menu(self, pos):
        item = self.itemAt(pos)
        if isinstance(item, (TextureList, )):
            context_menu = QMenu(self)
            add_texture_entry = QAction("Add Texture Entry")
            add_texture_entry.triggered.connect(self.handle_add_new_texture)
            context_menu.addAction(add_texture_entry)

            context_menu.exec(self.mapToGlobal(pos))
            context_menu.destroy()
            del context_menu

        elif isinstance(item, (Texture, )):
            context_menu = QMenu(self)
            remove_texture_entry = QAction("Remove Texture Entry")
            remove_texture_entry.triggered.connect(partial(self.handle_delete_texture, False, pos))
            context_menu.addAction(remove_texture_entry)

            context_menu.addSeparator()

            delete_texture_entry = QAction("Delete Texture")
            delete_texture_entry.triggered.connect(partial(self.handle_delete_texture, True, pos))
            context_menu.addAction(delete_texture_entry)

            if item.bound_to.lower() not in self.main_editor.texture_menu.texture_handler.textures:
                delete_texture_entry.setEnabled(False)

            context_menu.exec(self.mapToGlobal(pos))
            context_menu.destroy()
            del context_menu

        elif isinstance(item, (Material, )):
            context_menu = QMenu(self)

            duplicate_material = QAction("Duplicate")
            remove_material = QAction("Remove")
            context_menu.addAction(duplicate_material)
            duplicate_material.triggered.connect(partial(self.handle_duplicate, pos))
            context_menu.addSeparator()
            context_menu.addAction(remove_material)
            remove_material.triggered.connect(partial(self.handle_delete, pos))

            context_menu.exec(self.mapToGlobal(pos))

            context_menu.destroy()
            del context_menu

        elif isinstance(item, (PaneItem, )):

            is_not_root = True
            if isinstance(item, (PaneItem, )) and item.bound_to.parent is None:
                is_not_root = False

            add_item_menu = QMenu("Add Item", self)
            add_pane = QAction("[PAN2] Pane")
            add_pic = QAction("[PIC2] Picture")
            add_tbx = QAction("[TBX2] Textbox")
            add_win = QAction("[WIN2] Window")

            add_pane.triggered.connect(partial(self.handle_add_item, pos, Pane))
            add_pic.triggered.connect(partial(self.handle_add_item, pos, Picture))
            add_tbx.triggered.connect(partial(self.handle_add_item, pos, Textbox))
            add_win.triggered.connect(partial(self.handle_add_item, pos, Window))

            if self._copied_object is not None:
                add_copied = QAction("{0}: {1}".format(self._copied_object.name, self._copied_object.p_panename))
                add_copied.triggered.connect(partial(self.handle_paste_item, pos))
                add_copied.setDisabled(False)
            else:
                add_copied = QAction("--------")
                add_copied.setDisabled(True)



            add_item_menu.addAction(add_pane)
            add_item_menu.addAction(add_pic)
            add_item_menu.addAction(add_tbx)
            add_item_menu.addAction(add_win)
            add_item_menu.addAction(add_copied)

            copy_item_menu = QMenu("Copy Item", self)

            copy_without_children = QAction("Without Children")
            copy_with_children = QAction("With Children")
            copy_with_children.triggered.connect(partial(self.handle_copy_item_with_children, pos))
            copy_without_children.triggered.connect(partial(self.handle_copy_item_without_children, pos))
            copy_item_menu.addAction(copy_without_children)
            copy_item_menu.addAction(copy_with_children)


            context_menu = QMenu(self)


            #add_action = QAction("Add Item", self)
            #add_action.triggered.connect(partial(self.emit_add_item, pos))
            context_menu.addMenu(add_item_menu)

            if is_not_root:
                copy_action = QAction("Copy Item", self)
                #delet_action.triggered.connect(partial(self.emit_delete_item, pos))
                context_menu.addMenu(copy_item_menu)
                context_menu.addSeparator()

                delete_action = QAction("Delete Item", self)
                delete_action.triggered.connect(partial(self.emit_delete_item, pos))
                context_menu.addAction(delete_action)



            context_menu.exec(self.mapToGlobal(pos))
            context_menu.destroy()
            del context_menu

    def _add_group(self, name, customgroup=None):
        if customgroup is None:
            group = ObjectGroup(name)
        else:
            group = customgroup(name)
        self.addTopLevelItem(group)
        return group

    def reset(self):
        self.material_list.remove_children()
        self.texture_list.remove_children()
        self.layout.remove_children()
        self.font_list.remove_children()

    def set_node_objects(self, node, parent=None):
        for child in node.children:
            if not isinstance(child, (TextureNames, MAT1, FontNames)):
                assert not isinstance(child, Node)
                assert child.name in ("PAN2", "WIN2", "PIC2", "TBX2")

                if child.name == "PAN2":
                    child_item = PaneItem(parent, child.p_panename, child, None)
                elif child.name == "WIN2":
                    child_item = WindowItem(parent, child.p_panename, child, None)
                elif child.name == "PIC2":
                    child_item = PictureItem(parent, child.p_panename, child, None)
                elif child.name == "TBX2":
                    child_item = TextboxItem(parent, child.p_panename, child, None)

                if child.child is not None:
                    self.set_node_objects(child.child, child_item)

    def get_item_for_obj(self, obj, root: PaneItem=None):
        if self.layout.childCount() == 0:
            return None

        if root is None:
            return self.get_item_for_obj(obj, self.layout.child(0))
        else:
            if root.bound_to == obj:
                return root
            else:
                for i in range(root.childCount()):
                    child = root.child(i)
                    result = self.get_item_for_obj(obj, child)
                    if result is not None:
                        return result
        return None

    def set_objects(self, screen_data: ScreenBlo):
        self.reset()
        self.blo = screen_data
        mat1: MAT1 = screen_data.root.materials

        for material in mat1.materials:
            material_item = Material(self.material_list, material.name, material, None)

        textures: TextureNames = screen_data.root.textures
        for texture in textures.references:
            texture_item = Texture(self.texture_list, texture, texture, None)

        self.set_node_objects(screen_data.root, self.layout)

        """
        for group in boldata.enemypointgroups.groups:
            group_item = EnemyPointGroup(self.enemyroutes, group)

            for point in group.points:
                point_item = EnemyRoutePoint(group_item, "Enemy Route Point", point)

        for group in boldata.checkpoints.groups:
            group_item = CheckpointGroup(self.checkpointgroups, group)

            for point in group.points:
                point_item = Checkpoint(group_item, "Checkpoint", point)

        for route in boldata.routes:
            route_item = ObjectPointGroup(self.objectroutes, route)

            for point in route.points:
                point_item = ObjectRoutePoint(route_item, "Object route point", point)

        for object in boldata.objects.objects:
            object_item = ObjectEntry(self.objects, "Object", object)

        self.sort_objects()"""

        """for kartpoint in boldata.kartpoints.positions:
            item = KartpointEntry(self.kartpoints, "Kartpoint", kartpoint)

        for area in boldata.areas.areas:
            item = AreaEntry(self.areas, "Area", area)

        for respawn in boldata.respawnpoints:
            item = RespawnEntry(self.respawnpoints, "Respawn", respawn)

        for i, camera in enumerate(boldata.cameras):
            item = CameraEntry(self.cameras, "Camera", camera, i)

        for i, lightparam in enumerate(boldata.lightparams):
            item = LightParamEntry(self.lightparams, "LightParam", lightparam, i)

        for mg in boldata.mgentries:
            item = MGEntry(self.mgentries, "MG", mg)"""

    def save_expand_status(self, expand, child: NamedItemWithChildren):
        if child.isExpanded():
            expand[child.bound_to] = True

        for i in range(child.childCount()):
            self.save_expand_status(expand, child.child(i))

    def restore_expand_status(self, expand, child: NamedItemWithChildren):
        expanded = False
        if child.bound_to in expand:
            expanded = expand[child.bound_to]

        child.setExpanded(expanded)

        for i in range(child.childCount()):
            self.restore_expand_status(expand, child.child(i))

    def set_objects_remember_expanded(self, screen_data: ScreenBlo):
        matlist_expanded = self.material_list.isExpanded()
        texlist_expanded = self.texture_list.isExpanded()
        layout_expanded = self.layout.isExpanded()

        layout_children_expanded = {}

        self.save_expand_status(layout_children_expanded, self.layout)

        self.set_objects(screen_data)

        self.material_list.setExpanded(matlist_expanded)
        self.texture_list.setExpanded(texlist_expanded)
        self.layout.setExpanded(layout_expanded)
        self.restore_expand_status(layout_children_expanded, self.layout)

    def sort_objects(self):
        self.objects.sort()
        """items = []
        for i in range(self.objects.childCount()):
            items.append(self.objects.takeChild(0))

        items.sort(key=lambda x: x.bound_to.objectid)

        for item in items:
            self.objects.addChild(item)"""