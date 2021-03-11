from OpenGL.GL import *  #glTranslatef, glPushMatrix, glPopMatrix, glColor3f, glScalef,
from lib.model_rendering import PaneRender
from lib.vectors import Vector3

RADIUS = 8.0
BORDER = 0.7


class BoxManipulator(object):
    TL = 1
    ML = 2
    BL = 3
    MB = 4
    BR = 5
    MR = 6
    TR = 7
    MT = 8

    def __init__(self, corner_model):
        self.visible = False
        self._bottom_left = Vector3(0, 0, 0)
        self._top_left = Vector3(0, 0, 0)
        self._top_right = Vector3(0, 0, 0)
        self._bottom_right = Vector3(0, 0, 0)

        self._middle_left = Vector3(0, 0, 0)
        self._middle_right = Vector3(0, 0, 0)
        self._middle_top = Vector3(0, 0, 0)
        self._middle_bottom = Vector3(0, 0, 0)
        self._transform = None

        self.corner = corner_model
        self._selected_corner = None

    def set_visible(self, state):
        self.visible = state

    def select(self, val):
        self._selected_corner = val

    def _draw_corner(self, pos, zoom, is_selected):
        glPushMatrix()
        glTranslatef(pos.x, pos.y, pos.z)
        scale = zoom*RADIUS
        glScalef(scale, scale, scale)
        if is_selected:
            glColor3f(1.0, 0.0, 0.0)
        else:
            glColor3f(0.0, 0.0, 0.0)
        self.corner.render()
        glScalef(BORDER, BORDER, BORDER)
        glColor3f(1.0, 1.0, 1.0)
        self.corner.render()
        glPopMatrix()

    def _draw_vector(self, origin, direction, zoom, is_selected):
        if is_selected:
            glColor3f(1.0, 0.0, 0.0)
        else:
            glColor3f(0.0, 1.0, 0.0)
        length = 50
        glBegin(GL_LINES)
        glVertex3f(origin.x, origin.y, origin.z)
        glVertex3f(origin.x+zoom*length*direction.x, (origin.y-zoom*length*direction.y), origin.z+zoom*length*direction.z)

        glEnd()

    def transform(self, vec):
        return self._transform.multiply_return_vec3(vec)

    def _set_corners(self, transform, pane):
        offset_x, offset_y = PaneRender.get_anchor_offset(pane)
        w, h = pane.p_size_x, pane.p_size_y

        self._bottom_left = transform.multiply_return_vec3(Vector3(0.0 + offset_x, 0.0 - offset_y, 1))
        self._top_left = transform.multiply_return_vec3(Vector3(0.0 + offset_x, -h - offset_y, 1))
        self._top_right = transform.multiply_return_vec3(Vector3(w + offset_x, -h - offset_y, 1))
        self._bottom_right = transform.multiply_return_vec3(Vector3(w + offset_x, 0 - offset_y, 1))

        #self._bottom_left = (Vector3(0.0 + offset_x, 0.0 - offset_y, 1))
        #self._top_left = (Vector3(0.0 + offset_x, -h - offset_y, 1))
        #self._top_right = (Vector3(w + offset_x, -h - offset_y, 1))
        #self._bottom_right = (Vector3(w + offset_x, 0 - offset_y, 1))

        self._middle_left = (self._bottom_left+self._top_left)*0.5
        self._middle_right = (self._bottom_right+self._top_right)*0.5
        self._middle_top = (self._top_right+self._top_left)*0.5
        self._middle_bottom = (self._bottom_left+self._bottom_right)*0.5

        self._transform = transform

    def render(self, transform, pane, zoom):
        self._set_corners(transform, pane)
        self._draw_corner(self._bottom_left, zoom, self._selected_corner == self.BL)
        self._draw_corner(self._bottom_right, zoom, self._selected_corner == self.BR)
        self._draw_corner(self._top_left, zoom, self._selected_corner == self.TL)
        self._draw_corner(self._top_right, zoom, self._selected_corner == self.TR)

        self._draw_corner(self._middle_bottom, zoom, self._selected_corner == self.MB)
        self._draw_corner(self._middle_right, zoom, self._selected_corner == self.MR)
        self._draw_corner(self._middle_left, zoom, self._selected_corner == self.ML)
        self._draw_corner(self._middle_top, zoom, self._selected_corner == self.MT)

        #x, y = pane._get_middle()
        #self._draw_corner(transform.multiply_return_vec3(Vector3(x-pane.p_offset_x, -y+pane.p_offset_y, 1)), zoom, False)

        for corner, val in ((self._bottom_left, self.BL),
                            (self._bottom_right, self.BR),
                            (self._top_left, self.TL),
                            (self._top_right, self.TR),
                            (self._middle_left, self.ML),
                            (self._middle_right, self.MR),
                            (self._middle_top, self.MT),
                            (self._middle_bottom, self.MB)
                            ):
            dir1, dir2 = self.get_corner_normals(val)
            self._draw_vector(corner, dir1, zoom, self._selected_corner == val)
            self._draw_vector(corner, dir2, zoom, self._selected_corner == val)

        #self._draw_corner(Vector3(x, -y, 1), zoom, False)

    def in_corner(self, x, y, scale):
        if not self.visible:
            return None
        else:
            for corner, val in ((self._bottom_left, self.BL),
                                (self._bottom_right, self.BR),
                                (self._top_left, self.TL),
                                (self._top_right, self.TR),
                                (self._middle_left, self.ML),
                                (self._middle_right, self.MR),
                                (self._middle_top, self.MT),
                                (self._middle_bottom, self.MB)
                                ):

                diff = (Vector3(x, y, 0) - corner)
                #print("corner:", corner, "mouse:", x, y)
                #print("Distance:", dist, "radius:", RADIUS, "scaled:", RADIUS*scale, "scale:", scale)
                if diff.x**2 + diff.y**2 < (RADIUS*scale)**2:
                    return val

        return None

    @staticmethod
    def get_corner_normals(corner):
        if corner == BoxManipulator.BL:
            return Vector3(-1, 0, 0), Vector3(0, -1, 0)
        elif corner == BoxManipulator.ML:
            return Vector3(-1, 0, 0), Vector3(0, 0, 0)
        elif corner == BoxManipulator.TL:
            return Vector3(-1, 0, 0), Vector3(0, 1, 0)
        elif corner == BoxManipulator.MB:
            return Vector3(0, 0, 0), Vector3(0, -1, 0)
        elif corner == BoxManipulator.MT:
            return Vector3(0, 0, 0), Vector3(0, 1, 0)
        elif corner == BoxManipulator.BR:
            return Vector3(1, 0, 0), Vector3(0, -1, 0)
        elif corner == BoxManipulator.MR:
            return Vector3(1, 0, 0), Vector3(0, 0, 0)
        elif corner == BoxManipulator.TR:
            return Vector3(1, 0, 0), Vector3(0, 1, 0)

        return None




