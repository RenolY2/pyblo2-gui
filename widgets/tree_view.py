from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from lib.libbol import BOL, get_full_name
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QAction, QMenu
from lib.blo.readblo2 import Information, Pane, Window, Textbox, Picture, ScreenBlo, MAT1, TextureNames, FontNames, Node




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


class NamedItemWithChildren(NamedItem):
    def remove_children(self):
        self.takeChildren()


class InformationItem(NamedItem):
    def __init__(self, bound_to: Information):
        super().__init__(None, "Information", bound_to, None)


class PaneItem(NamedItemWithChildren):
    def __init__(self, parent, name, bound_to: Pane=None, index=None):
        name = bound_to.name
        super().__init__(parent, "{0}: {1}".format(bound_to.name, bound_to.p_panename), bound_to, index)


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
    select_all = pyqtSignal(ObjectGroup)
    reverse = pyqtSignal(ObjectGroup)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.setMaximumWidth(600)
        self.resize(200, self.height())
        self.setColumnCount(1)
        self.setHeaderLabel("Track Data Entries")

        self.information = InformationItem(None)
        self.addTopLevelItem(self.information)
        self.material_list = NamedItemWithChildren(None, "Materials", None, None)
        self.texture_list = NamedItemWithChildren(None, "Textures", None, None)
        self.font_list = NamedItemWithChildren(None, "Fonts", None, None)
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

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.run_context_menu)"""

    def run_context_menu(self, pos):
        item = self.itemAt(pos)

        if not isinstance(item, (EnemyPointGroup, ObjectPointGroup, CheckpointGroup)):
            return

        context_menu = QMenu(self)
        select_all_action = QAction("Select All", self)
        reverse_action = QAction("Reverse", self)

        def emit_current_selectall():
            item = self.itemAt(pos)
            self.select_all.emit(item)

        def emit_current_reverse():
            item = self.itemAt(pos)
            self.reverse.emit(item)
        select_all_action.triggered.connect(emit_current_selectall)
        reverse_action.triggered.connect(emit_current_reverse)

        context_menu.addAction(select_all_action)
        context_menu.addAction(reverse_action)
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
                child_item = PaneItem(parent, child.p_panename, child, None)
                if child.child is not None:
                    self.set_node_objects(child.child, child_item)

    def set_objects(self, screen_data: ScreenBlo):
        self.reset()

        mat1: MAT1 = screen_data.root.materials

        for material in mat1.materials:
            material_item = NamedItem(self.material_list, material.name, material, None)

        textures: TextureNames = screen_data.root.textures
        for texture in textures.references:
            texture_item = NamedItem(self.texture_list, texture, texture, None)

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

    def sort_objects(self):
        self.objects.sort()
        """items = []
        for i in range(self.objects.childCount()):
            items.append(self.objects.takeChild(0))

        items.sort(key=lambda x: x.bound_to.objectid)

        for item in items:
            self.objects.addChild(item)"""