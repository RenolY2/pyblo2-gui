import os
import json
from math import radians
from OpenGL.GL import *
from .model_rendering import (GenericObject, Model, TexturedModel,
                              GenericFlyer, GenericCrystallWall, GenericLongLegs, GenericChappy, GenericSnakecrow,
                              GenericSwimmer, Cube, PaneRender)
from lib.blo.readblo2 import ScreenBlo, Pane, Window, Textbox, Picture
from lib.vectors import Matrix4x4
import blo_editor_widgets

with open("lib/color_coding.json", "r") as f:
    colors = json.load(f)


class ObjectModels(object):
    def __init__(self):
        self.models = {}
        self.generic = GenericObject()
        self.generic_flyer = GenericFlyer()
        self.generic_longlegs = GenericLongLegs()
        self.generic_chappy = GenericChappy()
        self.generic_snakecrow = GenericSnakecrow()
        self.generic_swimmer = GenericSwimmer()
        self.cube = Cube()
        self.checkpointleft = Cube(colors["CheckpointLeft"])
        self.checkpointright = Cube(colors["CheckpointRight"])
        self.itempoint = Cube(colors["ItemRoutes"])
        self.enemypoint = Cube(colors["EnemyRoutes"])
        self.camera = GenericObject(colors["Camera"])
        self.areas = GenericObject(colors["Areas"])
        self.objects = GenericObject(colors["Objects"])
        self.respawn = GenericObject(colors["Respawn"])
        self.startpoints = GenericObject(colors["StartPoints"])
        #self.purplecube = Cube((0.7, 0.7, 1.0, 1.0))

        self.pane_render = PaneRender()

        genericmodels = {
            "Chappy": self.generic_chappy,
            "Flyer": self.generic_flyer,
            "Longlegs": self.generic_longlegs,
            "Snakecrow": self.generic_snakecrow,
            "Swimmer": self.generic_swimmer
        }

        with open("resources/enemy_model_mapping.json", "r") as f:
            mapping = json.load(f)
            for enemytype, enemies in mapping.items():
                if enemytype in genericmodels:
                    for name in enemies:
                        self.models[name.title()] = genericmodels[enemytype]

        with open("resources/unitsphere.obj", "r") as f:
            self.sphere = Model.from_obj(f, rotate=True)

        with open("resources/unitcylinder.obj", "r") as f:
            self.cylinder = Model.from_obj(f, rotate=True)

        with open("resources/unitcircle.obj", "r") as f:
            self.circle = Model.from_obj(f, rotate=True)

        with open("resources/unitcube_wireframe.obj", "r") as f:
            self.wireframe_cube = Model.from_obj(f, rotate=True)

        with open("resources/arrow_head.obj", "r") as f:
            self.arrow_head = Model.from_obj(f, rotate=True, scale=300.0)

    def init_gl(self):
        for dirpath, dirs, files in os.walk("resources/objectmodels"):
            for file in files:
                if file.endswith(".obj"):
                    filename = os.path.basename(file)
                    objectname = filename.rsplit(".", 1)[0]
                    self.models[objectname] = TexturedModel.from_obj_path(os.path.join(dirpath, file), rotate=True)
        for cube in (self.cube, self.checkpointleft, self.checkpointright, self.itempoint, self.enemypoint,
                     self.objects, self.areas, self.respawn, self.startpoints, self.camera):
            cube.generate_displists()

        self.generic.generate_displists()

        # self.generic_wall = TexturedModel.from_obj_path("resources/generic_object_wall2.obj", rotate=True, scale=20.0)

    def draw_arrow_head(self, frompos, topos):
        glPushMatrix()
        dir = topos-frompos
        dir.normalize()

        glMultMatrixf([dir.x, -dir.z, 0, 0,
                       -dir.z, -dir.x, 0, 0,
                       0, 0, 1, 0,
                       topos.x, -topos.z, topos.y, 1])
        self.arrow_head.render()
        glPopMatrix()
        #glBegin(GL_LINES)
        #glVertex3f(frompos.x, -frompos.z, frompos.y)
        #glVertex3f(topos.x, -topos.z, topos.y)
        #glEnd()

    def draw_sphere(self, position, scale):
        glPushMatrix()

        glTranslatef(position.x, -position.z, position.y)
        glScalef(scale, scale, scale)

        self.sphere.render()
        glPopMatrix()

    def draw_sphere_last_position(self, scale):
        glPushMatrix()

        glScalef(scale, scale, scale)

        self.sphere.render()
        glPopMatrix()

    def draw_cylinder(self,position, radius, height):
        glPushMatrix()

        glTranslatef(position.x, -position.z, position.y)
        glScalef(radius, height, radius)

        self.cylinder.render()
        glPopMatrix()

    def draw_wireframe_cube(self, position, rotation, scale):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        mtx = rotation.mtx
        glMultMatrixf(mtx)
        glScalef(-scale.z, scale.x, scale.y)
        self.wireframe_cube.render()
        glPopMatrix()

    def draw_cylinder_last_position(self, radius, height):
        glPushMatrix()

        glScalef(radius, radius, height)

        self.cylinder.render()
        glPopMatrix()

    def render_generic_position(self, position, selected):
        self._render_generic_position(self.cube, position, selected)

    def render_generic_position_colored(self, position, selected, cubename):
        self._render_generic_position(getattr(self, cubename), position, selected)

    def render_generic_position_rotation(self, position, rotation, selected):
        self._render_generic_position_rotation("generic", position, rotation, selected)

    def render_generic_position_rotation_colored(self, objecttype, position, rotation, selected):
        self._render_generic_position_rotation(objecttype, position, rotation, selected)

    def _render_generic_position_rotation(self, name, position, rotation, selected):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        mtx = rotation.mtx
        #glBegin(GL_LINES)
        #glVertex3f(0.0, 0.0, 0.0)
        #glVertex3f(mtx[0][0] * 2000, mtx[0][1] * 2000, mtx[0][2] * 2000)
        #glEnd()

        glMultMatrixf(mtx)

        glColor3f(0.0, 0.0, 0.0)
        glBegin(GL_LINE_STRIP)
        glVertex3f(0.0, 0.0, 750.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(1000.0, 0.0, 0.0)
        glEnd()


        #glMultMatrixf(rotation.mtx[])
        getattr(self, name).render(selected=selected)

        glPopMatrix()

    def _render_generic_position(self, cube, position, selected):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        cube.render(selected=selected)

        glPopMatrix()

    def render_generic_position_colored_id(self, position, id):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        self.cube.render_coloredid(id)

        glPopMatrix()

    def render_pane(self, pane, material, selected):
        self.pane_render.render_pane(pane, material, pane in selected)

    def render_node(self, node, materials, selected, vismenu, highlight_pass):
        for child in node.children:
            if isinstance(child, Pane):
                glPushMatrix()

                glTranslatef(child.p_offset_x, -child.p_offset_y, 0)
                glRotatef(child.p_rotation, 0, 0, 1)
                glScalef(child.p_scale_x, child.p_scale_y, 1.0)

                if highlight_pass and child in selected:
                    self.render_pane(child, materials, selected)
                elif not highlight_pass:
                    if (
                            ((child.name == "PAN2" and vismenu.panes.is_visible()) or
                            (child.name == "PIC2" and vismenu.pictures.is_visible()) or
                            (child.name == "TBX2" and vismenu.textboxes.is_visible()) or
                            (child.name == "WIN2" and vismenu.windows.is_visible())) and not child.hide
                    ):
                        self.render_pane(child, materials, selected)

                if child.child is not None:
                    self.render_node(child.child, materials, selected, vismenu, highlight_pass)

                glPopMatrix()

    def precompute_transforms(self, node, transform=None, transforms=None):
        if transforms is None:
            transforms = {}

        for child in node.children:
            if isinstance(child, Pane):
                matrix = Matrix4x4.from_j2d_srt(child.p_offset_x, child.p_offset_y,
                                                child.p_scale_x, child.p_scale_y,
                                                radians(child.p_rotation))
                if transform is not None:
                    matrix = transform.multiply_mat4(matrix)
                # print("Matrix for", child.p_panename, matrix)

                transforms[child] = matrix

                if child.child is not None:
                    self.precompute_transforms(child.child, matrix, transforms)

        return transforms

    def render_hierarchy(self, screen: ScreenBlo, selected, vismenu):
        self.render_node(screen.root, None, selected, vismenu, highlight_pass=False)
        self.render_node(screen.root, None, selected, vismenu, highlight_pass=True)

    def collision_detect_node(self, node, point, vismenu, transforms):#transform: Matrix4x4 = None):
        results = []

        for child in node.children:
            if isinstance(child, Pane):
                #matrix = Matrix4x4.from_j2d_srt(child.p_offset_x, child.p_offset_y,
                #                                child.p_scale_x, child.p_scale_y,
                #                                radians(child.p_rotation))
                #if transform is not None:
                #    matrix = transform.multiply_mat4(matrix)
                #print("Matrix for", child.p_panename, matrix)

                if child.child is not None:
                    more_results = self.collision_detect_node(child.child, point, vismenu, transforms)
                    results.extend(more_results)

                if (
                        (
                            (child.name == "PAN2" and vismenu.panes.is_selectable()) or
                            (child.name == "PIC2" and vismenu.pictures.is_selectable()) or
                            (child.name == "TBX2" and vismenu.textboxes.is_selectable()) or
                            (child.name == "WIN2" and vismenu.windows.is_selectable())
                        ) and not child.hide
                ):
                    if self.pane_render.point_lies_in_pane(child, point, transforms[child]):
                        results.append(child)

        return results

    def render_generic_position_rotation_colored_id(self, position, rotation, id):
        glPushMatrix()
        glTranslatef(position.x, -position.z, position.y)
        mtx = rotation.mtx
        #glMultMatrixf(rotation.mtx[])
        self.generic.render_coloredid(id)

        glPopMatrix()

    def render_line(self, pos1, pos2):
        pass

    def render_object(self, pikminobject, selected):
        glPushMatrix()

        glTranslatef(pikminobject.position.x, -pikminobject.position.z, pikminobject.position.y)
        if "mEmitRadius" in pikminobject.unknown_params and pikminobject.unknown_params["mEmitRadius"] > 0:
            self.draw_cylinder_last_position(pikminobject.unknown_params["mEmitRadius"]/2, 50.0)

        glRotate(pikminobject.rotation.x, 1, 0, 0)
        glRotate(pikminobject.rotation.y, 0, 0, 1)
        glRotate(pikminobject.rotation.z, 0, 1, 0)

        if pikminobject.name in self.models:
            self.models[pikminobject.name].render(selected=selected)
        else:
            glDisable(GL_TEXTURE_2D)
            self.generic.render(selected=selected)

        glPopMatrix()

    def render_object_coloredid(self, pikminobject, id):
        glPushMatrix()

        glTranslatef(pikminobject.position.x, -pikminobject.position.z, pikminobject.position.y)
        glRotate(pikminobject.rotation.x, 1, 0, 0)
        glRotate(pikminobject.rotation.y, 0, 0, 1)
        glRotate(pikminobject.rotation.z, 0, 1, 0)

        if pikminobject.name in self.models:
            self.models[pikminobject.name].render_coloredid(id)
        else:
            self.generic.render_coloredid(id)


        glPopMatrix()
