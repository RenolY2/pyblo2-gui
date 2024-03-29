import traceback
import os
from time import sleep
from timeit import default_timer
from io import StringIO
from math import sin, cos, atan2, radians, degrees, pi, tan, ceil
import json
import numpy

from OpenGL.GL import *
from OpenGL.GLU import *

from PyQt5.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QFont, QFontMetrics, QPolygon, QImage, QPixmap, QKeySequence
from PyQt5.QtWidgets import (QWidget, QListWidget, QListWidgetItem, QDialog, QMenu, QLineEdit,
                            QMdiSubWindow, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit, QAction, QShortcut)
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt5.QtCore import Qt


from helper_functions import calc_zoom_in_factor, calc_zoom_out_factor
from lib.collision import Collision
from widgets.editor_widgets import catch_exception, catch_exception_with_dialog

from opengltext import draw_collision
from lib.vectors import Matrix4x4, Vector3, Line, Plane, Triangle

from lib.model_rendering import TexturedPlane, Model, Grid, GenericObject, Material, Minimap
from lib.object_models import ObjectModels
from editor_controls import UserControl
from lib.libpath import Paths
from lib.blo.readblo2 import ScreenBlo, Pane
from lib.control.box_manipulator import BoxManipulator
from gizmo import Gizmo2D

MOUSE_MODE_NONE = 0
MOUSE_MODE_MOVEWP = 1
MOUSE_MODE_ADDWP = 2
MOUSE_MODE_CONNECTWP = 3

MODE_TOPDOWN = 0
MODE_3D = 1

#colors = [(1.0, 0.0, 0.0), (0.0, 0.5, 0.0), (0.0, 0.0, 1.0), (1.0, 1.0, 0.0)]
colors = [(0.0,191/255.0,255/255.0), (30/255.0,144/255.0,255/255.0), (0.0,0.0,255/255.0), (0.0,0.0,139/255.0)]

with open("lib/color_coding.json", "r") as f:
    colors_json = json.load(f)
    colors_selection = colors_json["SelectionColor"]
    colors_area  = colors_json["Areas"]


class SelectionQueue(list):
    def __init__(self):
        super().__init__()

    def queue_selection(self, x, y, width, height, shift_pressed, do_gizmo=False):
        if do_gizmo:
            for i in self:
                if i[-1] is True:
                    return
        self.append((x, y, width, height, shift_pressed, do_gizmo))

    def clear(self):
        tmp = [x for x in self]
        for val in tmp:
            if tmp[-1] is True:
                self.remove(tmp)

    def queue_pop(self):
        if len(self) > 0:
            return self.pop(0)

        else:
            return None


class BolMapViewer(QtWidgets.QOpenGLWidget):
    mouse_clicked = pyqtSignal(QMouseEvent)
    entity_clicked = pyqtSignal(QMouseEvent, str)
    mouse_dragged = pyqtSignal(QMouseEvent)
    mouse_released = pyqtSignal(QMouseEvent)
    mouse_wheel = pyqtSignal(QWheelEvent)
    position_update = pyqtSignal(QMouseEvent, tuple)
    height_update = pyqtSignal(float)
    select_update = pyqtSignal()
    move_points = pyqtSignal(float, float, float)
    connect_update = pyqtSignal(int, int)
    create_waypoint = pyqtSignal(float, float)
    create_waypoint_3d = pyqtSignal(float, float, float)

    rotate_current = pyqtSignal(Vector3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._zoom_factor = 80
        self.setFocusPolicy(Qt.ClickFocus)

        self.SIZEX = 1024#768#1024
        self.SIZEY = 1024#768#1024

        self.canvas_width, self.canvas_height = self.width(), self.height()
        self.resize(600, self.canvas_height)
        #self.setMinimumSize(QSize(self.SIZEX, self.SIZEY))
        #self.setMaximumSize(QSize(self.SIZEX, self.SIZEY))
        self.setObjectName("bw_map_screen")

        self.origin_x = self.SIZEX//2
        self.origin_z = self.SIZEY//2

        self.offset_x = 0
        self.offset_z = 0

        self.left_button_down = False
        self.mid_button_down = False
        self.right_button_down = False
        self.drag_last_pos = None

        self.selected = []
        self.selected_positions = []
        self.selected_rotations = []

        #self.p = QPainter()
        #self.p2 = QPainter()
        # self.show_terrain_mode = SHOW_TERRAIN_REGULAR

        self.selectionbox_start = None
        self.selectionbox_end = None

        self.visualize_cursor = None

        self.click_mode = 0

        self.collision = None

        self.highlighttriangle = None

        self.setMouseTracking(True)

        self.layout_file: ScreenBlo = None
        self.waterboxes = []

        self.mousemode = MOUSE_MODE_NONE

        self.overlapping_wp_index = 0
        self.editorconfig = None
        self.visibility_menu = None

        #self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.spawnpoint = None
        self.alternative_mesh = None
        self.highlight_colltype = None

        self.shift_is_pressed = False
        self.rotation_is_pressed = False
        self.last_drag_update = 0
        self.change_height_is_pressed = False
        self.last_mouse_move = None

        self.timer = QtCore.QTimer()
        self.timer.setInterval(2)
        self.timer.timeout.connect(self.render_loop)
        self.timer.start()
        self._lastrendertime = 0
        self._lasttime = 0

        self._frame_invalid = False

        self.MOVE_UP = 0
        self.MOVE_DOWN = 0
        self.MOVE_LEFT = 0
        self.MOVE_RIGHT = 0
        self.MOVE_FORWARD = 0
        self.MOVE_BACKWARD = 0
        self.SPEEDUP = 0

        self._wasdscrolling_speed = 1
        self._wasdscrolling_speedupfactor = 3

        self.main_model = None
        self.buffered_deltas = []

        # 3D Setup
        self.mode = MODE_TOPDOWN
        self.camera_horiz = pi*(1/2)
        self.camera_vertical = -pi*(1/4)
        self.camera_height = 1000
        self.last_move = None
        self.backgroundcolor = (255, 255, 255, 255)

        #self.selection_queue = []
        self.selectionqueue = SelectionQueue()

        self.selectionbox_projected_start = None
        self.selectionbox_projected_end = None

        #self.selectionbox_projected_2d = None
        self.selectionbox_projected_origin = None
        self.selectionbox_projected_up = None
        self.selectionbox_projected_right = None
        self.selectionbox_projected_coords = None
        self.last_position_update = 0
        self.move_collision_plane = Plane(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0))

        self.paths = Paths()
        self.usercontrol = UserControl(self)

        # Initialize some models
        #with open("resources/gizmo.obj", "r") as f:
        #    self.gizmo = Gizmo.from_obj(f, rotate=True)

        #self.generic_object = GenericObject()
        self.models = ObjectModels()
        self.grid = Grid(100000, 100000, 10000)

        self.modelviewmatrix = None
        self.projectionmatrix = None

        self.arrow = None
        self.minimap = Minimap(Vector3(-1000.0, 0.0, -1000.0), Vector3(1000.0, 0.0, 1000.0), 0,
                               None)
        self.last_selected = None
        self.last_selected_candidates = None
        self.box_manipulator = BoxManipulator(self.models.circle)
        self.gizmo2d = Gizmo2D()
        self.transforms = {}

        self.texture_handler = None

        self.animation_time = 0.0
        self.animation_duration = 1000.0
        self.animation_running = False

    @catch_exception_with_dialog
    def initializeGL(self):
        self.rotation_visualizer = glGenLists(1)
        glNewList(self.rotation_visualizer, GL_COMPILE)
        glColor4f(0.0, 0.0, 1.0, 1.0)

        glBegin(GL_LINES)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 40.0, 0.0)
        glEnd()
        glEndList()

        self.models.init_gl()
        self.arrow = Material(texturepath="resources/arrow.png")

        self.minimap = Minimap(Vector3(-1000.0, 0.0, -1000.0), Vector3(1000.0, 0.0, 1000.0), 0,
                               "resources/arrow.png")


    def resizeGL(self, width, height):
        # Called upon window resizing: reinitialize the viewport.
        # update the window size
        self.canvas_width, self.canvas_height = width, height
        # paint within the whole window
        glEnable(GL_DEPTH_TEST)
        glViewport(0, 0, self.canvas_width, self.canvas_height)

    @catch_exception
    def set_editorconfig(self, config):
        self.editorconfig = config
        self._wasdscrolling_speed = config.getfloat("wasdscrolling_speed")
        self._wasdscrolling_speedupfactor = config.getfloat("wasdscrolling_speedupfactor")
        backgroundcolor = config["3d_background"].split(" ")
        self.backgroundcolor = (int(backgroundcolor[0])/255.0,
                                int(backgroundcolor[1])/255.0,
                                int(backgroundcolor[2])/255.0,
                                1.0)

    def change_from_topdown_to_3d(self):
        if self.mode == MODE_3D:
            return
        else:
            self.mode = MODE_3D

            if self.mousemode == MOUSE_MODE_NONE:
                self.setContextMenuPolicy(Qt.DefaultContextMenu)

            # This is necessary so that the position of the 3d camera equals the middle of the topdown view
            self.offset_x *= -1
            self.do_redraw()

    def change_from_3d_to_topdown(self):
        if self.mode == MODE_TOPDOWN:
            return
        else:
            self.mode = MODE_TOPDOWN
            if self.mousemode == MOUSE_MODE_NONE:
                self.setContextMenuPolicy(Qt.CustomContextMenu)

            self.offset_x *= -1
            self.do_redraw()

    @catch_exception
    def render_loop(self):
        now = default_timer()

        diff = now-self._lastrendertime
        timedelta = now-self._lasttime

        if self.mode == MODE_TOPDOWN:
            self.handle_arrowkey_scroll(timedelta)
        else:
            self.handle_arrowkey_scroll_3d(timedelta)

        if self.animation_running:
            self.do_redraw()
            self.animation_time += timedelta
            bckmenu = self.main_program.animation_menu

            if bckmenu.anim_editor is not None and bckmenu.anim_editor.animation is not None:
                duration = bckmenu.anim_editor.animation.duration
            else:
                duration = 1000
            fps = self.main_program.pik_control.bckcontrols.fps
            if self.animation_time*fps > duration:
                self.animation_time = 0.0
                self.main_program.pik_control.bckcontrols.frame_count.setValue(0)

        if diff > 1 / 60.0:
            if self.animation_running:
                fps = self.main_program.pik_control.bckcontrols.fps
                frameval = int(self.animation_time * fps)

                self.main_program.pik_control.bckcontrols.frame_count.setValue(frameval)

            if self._frame_invalid:
                self.update()
                self._lastrendertime = now
                self._frame_invalid = False
        self._lasttime = now

    def handle_arrowkey_scroll(self, timedelta):
        if self.selectionbox_projected_coords is not None:
            return

        diff_x = diff_y = 0
        #print(self.MOVE_UP, self.MOVE_DOWN, self.MOVE_LEFT, self.MOVE_RIGHT)
        speedup = 1

        if self.shift_is_pressed:
            speedup = self._wasdscrolling_speedupfactor

        if self.MOVE_FORWARD == 1 and self.MOVE_BACKWARD == 1:
            diff_y = 0
        elif self.MOVE_FORWARD == 1:
            diff_y = 1*speedup*self._wasdscrolling_speed*timedelta
        elif self.MOVE_BACKWARD == 1:
            diff_y = -1*speedup*self._wasdscrolling_speed*timedelta

        if self.MOVE_LEFT == 1 and self.MOVE_RIGHT == 1:
            diff_x = 0
        elif self.MOVE_LEFT == 1:
            diff_x = 1*speedup*self._wasdscrolling_speed*timedelta
        elif self.MOVE_RIGHT == 1:
            diff_x = -1*speedup*self._wasdscrolling_speed*timedelta

        if diff_x != 0 or diff_y != 0:
            if self.zoom_factor > 1.0:
                self.offset_x += diff_x * (1.0 + (self.zoom_factor - 1.0) / 2.0)
                self.offset_z += diff_y * (1.0 + (self.zoom_factor - 1.0) / 2.0)
            else:
                self.offset_x += diff_x
                self.offset_z += diff_y
            # self.update()

            self.do_redraw()

    def handle_arrowkey_scroll_3d(self, timedelta):
        if self.selectionbox_projected_coords is not None:
            return

        diff_x = diff_y = diff_height = 0
        #print(self.MOVE_UP, self.MOVE_DOWN, self.MOVE_LEFT, self.MOVE_RIGHT)
        speedup = 1

        forward_vec = Vector3(cos(self.camera_horiz), sin(self.camera_horiz), 0)
        sideways_vec = Vector3(sin(self.camera_horiz), -cos(self.camera_horiz), 0)

        if self.shift_is_pressed:
            speedup = self._wasdscrolling_speedupfactor

        if self.MOVE_FORWARD == 1 and self.MOVE_BACKWARD == 1:
            forward_move = forward_vec*0
        elif self.MOVE_FORWARD == 1:
            forward_move = forward_vec*(1*speedup*self._wasdscrolling_speed*timedelta)
        elif self.MOVE_BACKWARD == 1:
            forward_move = forward_vec*(-1*speedup*self._wasdscrolling_speed*timedelta)
        else:
            forward_move = forward_vec*0

        if self.MOVE_LEFT == 1 and self.MOVE_RIGHT == 1:
            sideways_move = sideways_vec*0
        elif self.MOVE_LEFT == 1:
            sideways_move = sideways_vec*(-1*speedup*self._wasdscrolling_speed*timedelta)
        elif self.MOVE_RIGHT == 1:
            sideways_move = sideways_vec*(1*speedup*self._wasdscrolling_speed*timedelta)
        else:
            sideways_move = sideways_vec*0

        if self.MOVE_UP == 1 and self.MOVE_DOWN == 1:
            diff_height = 0
        elif self.MOVE_UP == 1:
            diff_height = 1*speedup*self._wasdscrolling_speed*timedelta
        elif self.MOVE_DOWN == 1:
            diff_height = -1 * speedup * self._wasdscrolling_speed * timedelta

        if not forward_move.is_zero() or not sideways_move.is_zero() or diff_height != 0:
            #if self.zoom_factor > 1.0:
            #    self.offset_x += diff_x * (1.0 + (self.zoom_factor - 1.0) / 2.0)
            #    self.offset_z += diff_y * (1.0 + (self.zoom_factor - 1.0) / 2.0)
            #else:
            self.offset_x += (forward_move.x + sideways_move.x)
            self.offset_z += (forward_move.y + sideways_move.y)
            self.camera_height += diff_height
            # self.update()

            self.do_redraw()

    def set_arrowkey_movement(self, up, down, left, right):
        self.MOVE_UP = up
        self.MOVE_DOWN = down
        self.MOVE_LEFT = left
        self.MOVE_RIGHT = right

    def do_redraw(self, force=False):
        self._frame_invalid = True
        if force:
            self._lastrendertime = 0
            self.update()

    def reset(self, keep_collision=False):
        self.highlight_colltype = None
        self.overlapping_wp_index = 0
        self.shift_is_pressed = False
        self.SIZEX = 1024
        self.SIZEY = 1024
        self.origin_x = self.SIZEX//2
        self.origin_z = self.SIZEY//2
        self.last_drag_update = 0

        self.left_button_down = False
        self.mid_button_down = False
        self.right_button_down = False
        self.drag_last_pos = None

        self.selectionbox_start = None
        self.selectionbox_end = None

        self.selected = []

        if not keep_collision:
            # Potentially: Clear collision object too?
            self.level_image = None
            self.offset_x = 0
            self.offset_z = 0
            self._zoom_factor = 80
            #self._zoom_i
            #self._zoom_i
            #self.waterboxes = []

        self.pikmin_generators = None

        self.mousemode = MOUSE_MODE_NONE
        self.spawnpoint = None
        self.rotation_is_pressed = False

        self._frame_invalid = False

        self.MOVE_UP = 0
        self.MOVE_DOWN = 0
        self.MOVE_LEFT = 0
        self.MOVE_RIGHT = 0
        self.SPEEDUP = 0

    def set_collision(self, verts, faces, alternative_mesh):
        self.collision = Collision(verts, faces)

        if self.main_model is None:
            self.main_model = glGenLists(1)

        self.alternative_mesh = alternative_mesh

        glNewList(self.main_model, GL_COMPILE)
        #glBegin(GL_TRIANGLES)
        draw_collision(verts, faces)
        #glEnd()
        glEndList()

    def set_mouse_mode(self, mode):
        assert mode in (MOUSE_MODE_NONE, MOUSE_MODE_ADDWP, MOUSE_MODE_CONNECTWP, MOUSE_MODE_MOVEWP)

        self.mousemode = mode

        if self.mousemode == MOUSE_MODE_NONE and self.mode == MODE_TOPDOWN:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
        else:
            self.setContextMenuPolicy(Qt.DefaultContextMenu)

    @property
    def zoom_factor(self):
        return self._zoom_factor/100.0

    def zoom(self, fac):
        if self._zoom_factor <= 60:
            mult = 40.0
        elif self._zoom_factor >= 600:
            mult = 200.0
        else:
            mult = 100.0

        MIN = 1
        MAX = 1500

        print(self.zoom_factor, self._zoom_factor)

        if True:#MIN < (self._zoom_factor + fac*mult) <= MAX:
            if fac > 0:
                change = max(fac*mult/10, 1)
            else:
                change = min(fac*mult/10, 1)
            self._zoom_factor += change

            if self._zoom_factor < MIN:
                self._zoom_factor = MIN
            elif self._zoom_factor > MAX:
                self._zoom_factor = MAX
            #self.update()
            self.do_redraw()

    def mouse_coord_to_world_coord(self, mouse_x, mouse_y):
        zf = self.zoom_factor
        width, height = self.canvas_width, self.canvas_height
        camera_width = width * zf
        camera_height = height * zf

        topleft_x = -camera_width / 2 - self.offset_x
        topleft_y = camera_height / 2 + self.offset_z

        relx = mouse_x / width
        rely = mouse_y / height
        res = (topleft_x + relx*camera_width, topleft_y - rely*camera_height)

        return res

    def mouse_coord_to_world_coord_transform(self, mouse_x, mouse_y):
        mat4x4 = Matrix4x4.from_opengl_matrix(*glGetFloatv(GL_PROJECTION_MATRIX))
        width, height = self.canvas_width, self.canvas_height
        result = mat4x4.multiply_vec4(mouse_x-width/2, mouse_y-height/2, 0, 1)

        return result

    #@catch_exception_with_dialog
    #@catch_exception
    def paintGL(self):
        self.texture_handler.update_gl()

        start = default_timer()
        offset_x = self.offset_x
        offset_z = self.offset_z

        #start = default_timer()
        glClearColor(1.0, 1.0, 1.0, 0.0)
        #glClearColor(*self.backgroundcolor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        width, height = self.canvas_width, self.canvas_height
        glLineWidth(1.0)

        if self.mode == MODE_TOPDOWN:
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            zf = self.zoom_factor
            #glOrtho(-6000.0, 6000.0, -6000.0, 6000.0, -3000.0, 2000.0)
            camera_width = width*zf
            camera_height = height*zf

            glOrtho(-camera_width / 2 - offset_x, camera_width / 2 - offset_x,
                    -camera_height / 2 + offset_z, camera_height / 2 + offset_z, -120000.0, 80000.0)

            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
        else:
            #glEnable(GL_CULL_FACE)
            # set yellow color for subsequent drawing rendering calls

            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(75, width / height, 256.0, 160000.0)

            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            look_direction = Vector3(cos(self.camera_horiz), sin(self.camera_horiz), sin(self.camera_vertical))
            # look_direction.unify()
            fac = 1.01 - abs(look_direction.z)
            # print(fac, look_direction.z, look_direction)

            gluLookAt(self.offset_x, self.offset_z, self.camera_height,
                      self.offset_x + look_direction.x * fac, self.offset_z + look_direction.y * fac,
                      self.camera_height + look_direction.z,
                      0, 0, 1)

            self.camera_direction = Vector3(look_direction.x * fac, look_direction.y * fac, look_direction.z)

            #print(self.camera_direction)

        self.modelviewmatrix = numpy.transpose(numpy.reshape(glGetFloatv(GL_MODELVIEW_MATRIX), (4, 4)))
        self.projectionmatrix = numpy.transpose(numpy.reshape(glGetFloatv(GL_PROJECTION_MATRIX), (4, 4)))
        self.mvp_mat = numpy.dot(self.projectionmatrix, self.modelviewmatrix)
        self.modelviewmatrix_inv = numpy.linalg.inv(self.modelviewmatrix)

        campos = Vector3(self.offset_x, self.camera_height, -self.offset_z)
        self.campos = campos

        if self.mode == MODE_TOPDOWN:
            gizmo_scale = 3*zf
        else:
            gizmo_scale = (self.gizmo.position - campos).norm() / 130.0


        self.gizmo_scale = gizmo_scale

        #print(self.gizmo.position, campos)
        vismenu: FilterViewMenu = self.visibility_menu

        #del self.transforms
        if self.layout_file is not None:
            bckmenu = self.main_program.animation_menu
            if bckmenu.anim_editor is not None and bckmenu.anim_editor.animation is not None:
                bck = bckmenu.anim_editor.animation
                fps = self.main_program.pik_control.bckcontrols.fps
                if fps == 0:
                    fps = 1
                frame_time = int(self.animation_time * fps)
                element_transforms, anim_transforms = self.models.precompute_transforms(self.layout_file.root,
                                                                                        bck, frame_time)
            else:
                element_transforms, anim_transforms = self.models.precompute_transforms(self.layout_file.root,
                                                                                        None, 0)




            self.transforms = element_transforms

        """
        bckmenu = self.main_program.animation_menu
        if bckmenu.anim_editor is not None and bckmenu.anim_editor.animation is not None:

            for pane in self.transforms.keys():
                if pane.animated:
                    if pane.p_bckindex < len(bck.animations):
                        anim = bck.animations[pane.p_bckindex]
                        values = anim.interpolate(frame_time)
                        self.transforms[pane] = Matrix4x4.from_j2d_srt(*values)"""


        while len(self.selectionqueue) > 0:
            print(len(self.selectionqueue))
            glClearColor(1.0, 1.0, 1.0, 1.0)
            #
            click_x, click_y, clickwidth, clickheight, shiftpressed, do_gizmo = self.selectionqueue.queue_pop()
            world_x, world_y = self.mouse_coord_to_world_coord(click_x, click_y)
            click_y = height - click_y
            hit = 0xFF


            glClearColor(1.0, 1.0, 1.0, 1.0)

            if self.layout_file is not None:# and hit == 0xFF and not do_gizmo:
                #objects = self.pikmin_generators.generators
                glDisable(GL_TEXTURE_2D)
                #print("select time taken", default_timer() - start)
                #print("result:", selected)
                selected_candidates = self.models.collision_detect_node(
                    self.layout_file.root, Vector3(world_x, world_y, 1),
                    self.visibility_menu,
                    element_transforms)

                if not selected_candidates:
                    self.last_selected = None
                    self.last_selected_candidates = selected_candidates

                elif self.last_selected_candidates != selected_candidates:
                    self.last_selected = selected_candidates[0]
                    self.last_selected_candidates = selected_candidates
                else:
                    if self.last_selected is None or self.last_selected not in selected_candidates:
                        self.last_selected = selected_candidates[0]
                    else:
                        pos = selected_candidates.index(self.last_selected)
                        if pos+1 < len(selected_candidates):
                            self.last_selected = selected_candidates[pos+1]
                        else:
                            self.last_selected = selected_candidates[0]

                if self.last_selected is None:
                    selected = []
                else:
                    selected = [self.last_selected]
                #selected = [x for x in selected.keys()]
                if not shiftpressed:
                    self.selected = selected
                    #self.selected_positions = selected_positions
                    #self.selected_rotations = selected_rotations
                    self.select_update.emit()

                else:
                    for obj in selected:
                        if obj not in self.selected:
                            self.selected.append(obj)
                    """for pos in selected_positions:
                        if pos not in self.selected_positions:
                            self.selected_positions.append(pos)

                    for rot in selected_rotations:
                        if rot not in self.selected_rotations:
                            self.selected_rotations.append(rot)"""

                    self.select_update.emit()

        #print("gizmo status", self.gizmo.was_hit_at_all)
        #glClearColor(1.0, 1.0, 1.0, 0.0)
        glClearColor(*self.backgroundcolor)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        if self.main_model is not None:
            if self.alternative_mesh is None:
                glCallList(self.main_model)
            else:
                glPushMatrix()
                glScalef(1.0, -1.0, 1.0)
                self.alternative_mesh.render(selectedPart=self.highlight_colltype)
                glPopMatrix()

        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        #self.grid.render()
        if self.mode == MODE_TOPDOWN:
            glClear(GL_DEPTH_BUFFER_BIT)


        #else:
        #    if self.minimap is not None and vismenu.minimap.is_visible():
        #        self.minimap.render()
        #    glDisable(GL_DEPTH_TEST)

        glEnable(GL_ALPHA_TEST)
        glAlphaFunc(GL_GEQUAL, 0.5)

        if self.layout_file is not None:
            selected = self.selected
            positions = self.selected_positions

            select_optimize = self.selected#x: True for x in selected}
            #for x in selected:
            #    if isinstance(x, (Pane, )):
            #        select_optimize
            #objects = self.pikmin_generators.generators

            #for pikminobject in objects:
            #    self.models.render_object(pikminobject, pikminobject in selected)

            vismenu = self.visibility_menu

            self.models.render_hierarchy(self.layout_file, select_optimize, vismenu, self.texture_handler,
                                         anim_transforms)

            #glDisable(GL_TEXTURE_2D)



        glColor3f(0.0, 0.0, 0.0)
        glDisable(GL_TEXTURE_2D)
        if len(self.selected) == 1 and isinstance(self.selected[0], (Pane, )):
            element = self.selected[0]
            self.box_manipulator.set_visible(True)
            self.box_manipulator.render(element_transforms[element], element, self.zoom_factor)
            self.gizmo2d.visible = True

            offsetx, offsety = element.get_anchor_offset()

            self.gizmo2d.position = element_transforms[element].multiply_return_vec3(Vector3(0, 0, 1))

        else:
            self.box_manipulator.set_visible(False)
            self.gizmo2d.visible = False

        glColor4f(0.0, 1.0, 0.0, 1.0)
        rendered = {}
        glColor4f(0.0, 1.0, 1.0, 1.0)
        """for points in self.paths.wide_paths:
            glBegin(GL_LINE_LOOP)
            for p in points:
                glVertex3f(p.x, -p.z, p.y + 5)

            glEnd()"""

        #self.gizmo.render_scaled(gizmo_scale, is3d=self.mode == MODE_3D)
        self.gizmo2d.render(self.zoom_factor)
        glDisable(GL_DEPTH_TEST)
        if self.selectionbox_start is not None and self.selectionbox_end is not None:
            #print("drawing box")
            startx, startz = self.selectionbox_start
            endx, endz = self.selectionbox_end
            glColor4f(1.0, 0.0, 0.0, 1.0)
            glLineWidth(2.0)
            glBegin(GL_LINE_LOOP)
            glVertex3f(startx, startz, 0)
            glVertex3f(startx, endz, 0)
            glVertex3f(endx, endz, 0)
            glVertex3f(endx, startz, 0)

            glEnd()

        if self.selectionbox_projected_origin is not None and self.selectionbox_projected_coords is not None:
            #print("drawing box")
            origin = self.selectionbox_projected_origin
            point2, point3, point4 = self.selectionbox_projected_coords
            glColor4f(1.0, 0.0, 0.0, 1.0)
            glLineWidth(2.0)

            point1 = origin

            glBegin(GL_LINE_LOOP)
            glVertex3f(point1.x, point1.y, point1.z)
            glVertex3f(point2.x, point2.y, point2.z)
            glVertex3f(point3.x, point3.y, point3.z)
            glVertex3f(point4.x, point4.y, point4.z)
            glEnd()

        glEnable(GL_DEPTH_TEST)
        glFinish()
        now = default_timer() - start
        #print("Frame time:", now, 1/now, "fps")

    @catch_exception
    def mousePressEvent(self, event):
        self.usercontrol.handle_press(event)

    @catch_exception
    def mouseMoveEvent(self, event):
        self.usercontrol.handle_move(event)

    @catch_exception
    def mouseReleaseEvent(self, event):
        self.usercontrol.handle_release(event)

    def wheelEvent(self, event):
        wheel_delta = event.angleDelta().y()

        if self.editorconfig is not None:
            invert = self.editorconfig.getboolean("invertzoom")
            if invert:
                wheel_delta = -1*wheel_delta

        if wheel_delta < 0:
            self.zoom_out()

        elif wheel_delta > 0:
            self.zoom_in()

    def zoom_in(self):
        current = self.zoom_factor

        fac = calc_zoom_out_factor(current)

        self.zoom(fac)

    def zoom_out(self):
        current = self.zoom_factor
        fac = calc_zoom_in_factor(current)

        self.zoom(fac)

    def create_ray_from_mouseclick(self, mousex, mousey, yisup=False):
        self.camera_direction.normalize()
        height = self.canvas_height
        width = self.canvas_width

        view = self.camera_direction.copy()

        h = view.cross(Vector3(0, 0, 1))
        v = h.cross(view)

        h.normalize()
        v.normalize()

        rad = 75 * pi / 180.0
        vLength = tan(rad / 2) * 1.0
        hLength = vLength * (width / height)

        v *= vLength
        h *= hLength

        x = mousex - width / 2
        y = height - mousey- height / 2

        x /= (width / 2)
        y /= (height / 2)
        camerapos = Vector3(self.offset_x, self.offset_z, self.camera_height)

        pos = camerapos + view * 1.0 + h * x + v * y
        dir = pos - camerapos

        if yisup:
            tmp = pos.y
            pos.y = -pos.z
            pos.z = tmp

            tmp = dir.y
            dir.y = -dir.z
            dir.z = tmp

        return Line(pos, dir)


class ObjectViewSelectionToggle(object):
    def __init__(self, name, menuparent):
        self.name = name
        self.menuparent = menuparent

        self.action_view_toggle = QAction("{0} visible".format(name), menuparent)
        self.action_select_toggle = QAction("{0} selectable".format(name), menuparent)
        self.action_view_toggle.setCheckable(True)
        self.action_view_toggle.setChecked(True)
        self.action_select_toggle.setCheckable(True)
        self.action_select_toggle.setChecked(True)

        self.action_view_toggle.triggered.connect(self.handle_view_toggle)
        self.action_select_toggle.triggered.connect(self.handle_select_toggle)

        menuparent.addAction(self.action_view_toggle)
        menuparent.addAction(self.action_select_toggle)

    def handle_view_toggle(self, val):
        if not val:
            self.action_select_toggle.setChecked(False)
        else:
            self.action_select_toggle.setChecked(True)

    def handle_select_toggle(self, val):
        if val:
            self.action_view_toggle.setChecked(True)

    def is_visible(self):
        return self.action_view_toggle.isChecked()

    def is_selectable(self):
        return self.action_select_toggle.isChecked()


class FilterViewMenu(QMenu):
    filter_update = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTitle("Filter View")

        self.show_all = QAction("Show All", self)
        self.show_all.triggered.connect(self.handle_show_all)
        self.addAction(self.show_all)

        self.hide_all = QAction("Hide All", self)
        self.hide_all.triggered.connect(self.handle_hide_all)
        self.addAction(self.hide_all)

        self.panes = ObjectViewSelectionToggle("Panes", self)
        self.pictures = ObjectViewSelectionToggle("Pictures", self)
        self.windows = ObjectViewSelectionToggle("Windows", self)
        self.textboxes = ObjectViewSelectionToggle("Textboxes", self)

        self.all_toggles = (self.panes, self.pictures, self.windows, self.textboxes)

        for action in self.all_toggles:
            action.action_view_toggle.triggered.connect(self.emit_update)
            action.action_select_toggle.triggered.connect(self.emit_update)

    def handle_show_all(self):
        for action in self.all_toggles:
            action.action_view_toggle.setChecked(True)
            action.action_select_toggle.setChecked(True)
        self.filter_update.emit()

    def handle_hide_all(self):
        for action in self.all_toggles:
            action.action_view_toggle.setChecked(False)
            action.action_select_toggle.setChecked(False)
        self.filter_update.emit()

    def emit_update(self, val):
        self.filter_update.emit()

    def mouseReleaseEvent(self, e):
        try:
            action = self.activeAction()
            if action and action.isEnabled():
                action.trigger()
            else:
                QMenu.mouseReleaseEvent(self, e)
        except:
            traceback.print_exc()

