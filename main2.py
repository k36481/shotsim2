#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ZetCode wxPython tutorial

This program creates a ruler.

author: Jan Bodnar
website: zetcode.com
last edited: May 2018
"""

"""
NinePatchRect
커서를 대면 박스가 표시
spatial hashing -> quad tree(cluster가 많은경우)
spatial hashing / rect select / select similar / select edge
node based working
"""

import sys
import wx
import wx.lib.inspection

from chip import *
from shot import *
from hash import *
from  geometric import *

RW = 1001  # ruler width
RM = 10  # ruler margin
RH = 900  # ruler height

PAINTER_W = 1920
PAINTER_H = 1080
PAINTER_HELPER_WH = 10

RULER_FONT_COLOR = '#000001'
PAINTER_BACK_COLOR = '#f0f0f0'
PANEL_COLOR_01 = '#202531'
PANEL_COLOR_02 = '#262c3b'
PANEL_COLOR_03 = '#333b4f'

CHIP_COLOR = '#78c431'
CHIP_LINE_COLOR = '#c4f09c'

chip_size = (8, 6)
chips = {}
chip_hash = {}


class Example(wx.Frame):
    is_marking_layer_dirty = False
    is_left_down = False
    is_right_down = False
    queue_update_marker = []
    queue_update_shot_marker = []
    cursor_chip = None
    cursor_chip_pos = (0, 0)
    cursor_pos = (0, 0)
    selected = set()

    shot_shape = [[1, 1],
                  [1, 1],
                  [1, 1],
                  [1, 1]]
    shots = set()

    sb1 = None
    sb2 = None
    sb3 = None
    panel = None

    wafer_map_bitmap = None
    ruler_bitmap = None
    cursor_bitmap = None
    hash_grid_bitmap = None
    marking_bitmap = None
    shot_bmp = None

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, size=(RW + 2 * RM, RH))
        self.font = wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL, False, 'Segoe UI')
        # self.SetBackgroundColour(PANEL_COLOR_01)
        self.TOOLTIP_MARGIN = 20
        self.hash_grid_size = 20
        self.CreateMap()
        self.CreateRuler()
        self.CreateMarking()
        self.create_shot_bmp()
        self.InitUI()

    def create_shot_bmp(self):
        self.shot_bmp = wx.Bitmap(PAINTER_W, PAINTER_H)
        self.shot_bmp.SetMaskColour(wx.BLACK)

    def CreateMarking(self):
        self.marking_bitmap = wx.Bitmap(PAINTER_W, PAINTER_H)

    def CreateRuler(self):
        self.ruler_bitmap = wx.Bitmap(PAINTER_W, PAINTER_H)
        mem_dc = wx.MemoryDC(self.ruler_bitmap)
        # draw background
        mem_dc.SetBackgroundMode(wx.TRANSPARENT)
        mem_dc.SetPen(wx.Pen(RULER_FONT_COLOR, 0, wx.TRANSPARENT))
        mem_dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        mem_dc.DrawRectangle(0, 0, PAINTER_W, 35)
        mem_dc.DrawRectangle(0, 0, 35, PAINTER_H)
        # draw text
        mem_dc.SetPen(wx.Pen(RULER_FONT_COLOR))
        mem_dc.SetTextBackground(wx.WHITE)
        mem_dc.SetTextForeground(RULER_FONT_COLOR)
        mem_dc.SetFont(self.font)
        for i in range(1, PAINTER_W):
            if not (i % (chip_size[0] * 5)):
                mem_dc.DrawLine(i, 0, i, 10)
                txt = str(int(i / chip_size[0]))
                w, h = mem_dc.GetTextExtent(txt)
                mem_dc.DrawText(txt, i - w / 2, 10)
        for i in range(1, PAINTER_H):
            if not (i % (chip_size[1] * 5)):
                mem_dc.DrawLine(0, i, 10, i)
                txt = str(int(i / chip_size[1]))
                w, h = mem_dc.GetTextExtent(txt)
                mem_dc.DrawText(txt, 10, i - h / 2)
        del mem_dc
        self.ruler_bitmap.SetMaskColour(wx.BLACK)

    def CreateMap(self):
        self.hash = Hash(self.hash_grid_size)

        self.wafer_map_bitmap = wx.Bitmap(PAINTER_W, PAINTER_H)
        mem_dc = wx.MemoryDC(self.wafer_map_bitmap)
        # draw background
        mem_dc.SetPen(wx.Pen(CHIP_LINE_COLOR, 0, wx.TRANSPARENT))
        mem_dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        mem_dc.DrawRectangle(0, 0, PAINTER_W, PAINTER_H)

        # draw grid
        mem_dc.SetPen(wx.Pen(RULER_FONT_COLOR, 1, wx.DOT))
        # mem_dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        for i in range(1, PAINTER_W):
            if not (i % 5):
                mem_dc.DrawLine(i * chip_size[0], 0, i * chip_size[0], PAINTER_H)
        for i in range(1, PAINTER_H):
            if not (i % 5):
                mem_dc.DrawLine(0, i * chip_size[1], PAINTER_W, i * chip_size[1])

        # draw chip
        mem_dc.SetPen(wx.Pen(PAINTER_BACK_COLOR, 0, wx.SOLID))
        mem_dc.SetBrush(wx.Brush(CHIP_COLOR))
        for x in range(10, 150):
            for y in range(10, 150):
                if distance((x * chip_size[0], y * chip_size[1]), (50 * chip_size[0], 50 * chip_size[1])) < 200:
                    chip = Chip(x * chip_size[0],
                                y * chip_size[1],
                                x,
                                y)
                    chips[chip.Coord()] = chip
                    # self.listBox.Append(str(chip.x) + str(chip.y))
                    self.hash.insert(chip)

                    mem_dc.DrawRectangle(chip.pos_x - chip_size[0] / 2,
                                         chip.pos_y - chip_size[1] / 2,
                                         chip_size[0],
                                         chip_size[1])

        del mem_dc
        # draw hash grid
        # mem_dc.SetPen(wx.Pen(wx.RED))
        # for i in range(PAINTER_W):
        #     if not (i % self.hash_grid_size):
        #         mem_dc.DrawLine(i, 0, i, PAINTER_H)
        # for i in range(PAINTER_H):
        #     if not (i % self.hash_grid_size):
        #         mem_dc.DrawLine(0, i, PAINTER_W, i)
        # del mem_dc

    # def on_check_box(self, e):
    #     for c in chips:
    #         self.selected.add(c)
    #         self.queue_add_marker.append(c)
    #     self.Refresh()

    def run(self, e):
        # for k,c in chips.items():
        #     print(c.Pos())
        iter = 0
        x = 0
        while x < 100:
            y = 0
            while y < 100:
                dut_cnt = 0
                for x_ in range(len(self.shot_shape[0])):
                    for y_ in range(len(self.shot_shape)):
                        if self.shot_shape[y_][x_] == 1 and (x + x_, y + y_) in chips:
                            dut_cnt += 1
                            chips[(x + x_, y + y_)].set_contact_cnt(chips[(x + x_, y + y_)].get_contact_cnt() + 1)
                            self.print_debug(str(chips[(x + x_, y + y_)].Pos()))
                if dut_cnt:
                    self.shots.add(Shot(x * chip_size[0], y * chip_size[1], x, y))
                y += 4
                iter += 1
                if iter > 1000000:
                    print("long loop")
                    return
            x += 1

        mem_dc = wx.MemoryDC(self.shot_bmp)
        # if self.shots:
        for k, c in chips.items():
            if c.get_contact_cnt() == 0:
                pass
            elif c.get_contact_cnt() == 1:
                mem_dc.SetPen(wx.Pen(wx.BLACK, 1, wx.SOLID))
                mem_dc.SetBrush(wx.Brush(wx.BLUE, wx.SOLID))
                mem_dc.DrawRectangle(c.Pos()[0] - chip_size[0] / 2,
                                     c.Pos()[1] - chip_size[1] / 2,
                                     chip_size[0],
                                     chip_size[1])
            elif c.get_contact_cnt() == 2:
                mem_dc.SetPen(wx.Pen(wx.BLACK, 1, wx.SOLID))
                mem_dc.SetBrush(wx.Brush('#ccaa00', wx.SOLID))
                # for s in self.shots:
                mem_dc.DrawRectangle(c.Pos()[0] - chip_size[0] / 2,
                                     c.Pos()[1] - chip_size[1] / 2,
                                     chip_size[0],
                                     chip_size[1])
            else:
                mem_dc.SetPen(wx.Pen(wx.BLACK, 1, wx.SOLID))
                mem_dc.SetBrush(wx.Brush(wx.RED, wx.SOLID))
                # for s in self.shots:
                mem_dc.DrawRectangle(c.Pos()[0] - chip_size[0] / 2,
                                     c.Pos()[1] - chip_size[1] / 2,
                                     chip_size[0],
                                     chip_size[1])
        del mem_dc
        self.shot_bmp.SetMaskColour(wx.BLACK)

        self.Refresh()

    def InitUI(self):
        self.panel = wx.Panel(self)
        sizer = wx.GridBagSizer(5, 5)

        self.pnl01 = wx.Panel(self.panel, name="panel01")
        sizer.Add(self.pnl01, pos=(0, 0), span=(5, 1), flag=wx.EXPAND | wx.ALL, border=5)
        vBox01 = wx.BoxSizer(wx.VERTICAL)
        self.pnl01.SetSizer(vBox01)
        # text = wx.StaticText(self.pnl01, label="Name")
        # vBox01.Add(text, 0)
        self.listBox = wx.ListBox(self.pnl01, style=wx.LB_ALWAYS_SB)
        # self.listBox.SetBackgroundColour(PANEL_COLOR_02)
        vBox01.Add(self.listBox, 1, flag=wx.EXPAND)
        self.pnl01.SetDoubleBuffered(True)

        self.pnl02 = wx.Panel(self.panel, name="panel02")
        sizer.Add(self.pnl02, pos=(0, 1), span=(1, 1), flag=wx.EXPAND | wx.ALL, border=5)
        vBox02 = wx.BoxSizer(wx.VERTICAL)
        self.pnl02.SetSizer(vBox02)
        self.btn_run = wx.Button(self.pnl02, label="Run")
        self.btn_run.Bind(wx.EVT_BUTTON, self.run)
        vBox02.Add(self.btn_run)

        self.painter = wx.Panel(self.panel, name="painter_panel")
        sizer.Add(self.painter, pos=(1, 1), span=(4, 1), flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT | wx.BOTTOM,
                  border=5)
        self.painter.SetDoubleBuffered(True)
        self.painter.camera_pos = (0, 0)

        self.pnl03 = wx.Panel(self.panel, name="panel03")
        sizer.Add(self.pnl03, pos=(0, 2), span=(5, 1), flag=wx.EXPAND | wx.ALL, border=5)
        self.vBox03 = wx.BoxSizer(wx.VERTICAL)
        self.pnl03.SetSizer(self.vBox03)
        self.text2 = wx.StaticText(self.pnl03, label="dddd", style = wx.ALIGN_LEFT, size=(100,100))
        self.vBox03.Add(self.text2)
        self.pnl03.SetDoubleBuffered(True)

        sizer.AddGrowableRow(1)
        sizer.AddGrowableCol(1)

        # self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.painter.Bind(wx.EVT_PAINT, self.OnPaint)
        self.painter.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.painter.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.painter.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.painter.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.painter.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.panel.SetSizer(sizer)
        # sizer.Fit(self)

        self.Centre()
        self.Show(True)
        self.Refresh()

    def OnPaint(self, e):
        cam_offset = (-self.painter.camera_pos[0], -self.painter.camera_pos[1])

        dc = wx.PaintDC(self.painter)

        # draw background
        dc.SetPen(wx.Pen(RULER_FONT_COLOR, 1, wx.SOLID))
        dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        dc.DrawRectangle(0, 0, self.GetClientSize()[0], self.GetClientSize()[1])

        # draw wafer map
        dc.SetPen(wx.Pen(RULER_FONT_COLOR, 0, wx.TRANSPARENT))
        dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        dc.DrawBitmap(self.wafer_map_bitmap, cam_offset[0], cam_offset[1])

        # draw ruler
        dc.DrawBitmap(self.ruler_bitmap, 0, 0, True)

        # draw mag-glass
        # bmp = wx.Bitmap(32, 32)
        # mem_dc = wx.MemoryDC(bmp)
        # mem_dc.Blit(0, 0, 32, 32, dc, self.cursor_pos[0], self.cursor_pos[1])
        # del mem_dc
        # bmp = bmp.ConvertToImage().Rescale(32 * 8, 32 * 8).ConvertToBitmap()
        # dc.DrawBitmap(bmp, self.cursor_pos[0], self.cursor_pos[1] + 50)
        # dc.SetPen(wx.Pen(wx.BLACK, 1, wx.SOLID))
        # dc.SetBrush(wx.Brush('#333333', wx.TRANSPARENT))
        # dc.DrawRectangle(self.cursor_pos[0],self.cursor_pos[1] + 50,32 * 8,32 * 8)

        # draw shot
        dc.DrawBitmap(self.shot_bmp, 0, 0, True)

        # draw select helper
        if self.cursor_chip:
            dc.SetPen(wx.Pen(wx.BLACK, 2, wx.SOLID))
            dc.SetBrush(wx.Brush('#333333', wx.TRANSPARENT))
            dc.DrawRectangle(self.cursor_chip_pos[0] - chip_size[0] / 2 - 2,
                             self.cursor_chip_pos[1] - chip_size[1] / 2 - 2,
                             chip_size[0] + 5,
                             chip_size[1] + 5)

        # draw marker
        mem_dc = wx.MemoryDC(self.marking_bitmap)
        if self.queue_update_marker:
            for c in self.queue_update_marker:
                if c.get_selected():
                    mem_dc.SetPen(wx.Pen('#000001', 1, wx.SOLID))
                    mem_dc.SetBrush(wx.Brush('#333333', wx.TRANSPARENT))
                    mem_dc.DrawRectangle(c.Pos()[0] - chip_size[0] / 2,
                                         c.Pos()[1] - chip_size[1] / 2,
                                         chip_size[0],
                                         chip_size[1])
                    c.SetMarked(True)
                else:
                    mem_dc.SetPen(wx.Pen('#000000', 1, wx.SOLID))
                    mem_dc.SetBrush(wx.Brush('#333333', wx.TRANSPARENT))
                    mem_dc.DrawRectangle(c.Pos()[0] - chip_size[0] / 2,
                                         c.Pos()[1] - chip_size[1] / 2,
                                         chip_size[0],
                                         chip_size[1])
                    c.SetMarked(False)
            self.queue_update_marker = []
        del mem_dc
        self.marking_bitmap.SetMaskColour(wx.BLACK)
        dc.DrawBitmap(self.marking_bitmap, 0, 0, True)
        # self.is_marking_layer_dirty = False

        # draw tooltip
        if self.cursor_chip:
            txt = str(str(self.cursor_chip.x).zfill(3) + "," + str(self.cursor_chip.y).zfill(3))
            w, h = dc.GetTextExtent(txt)
            h *= 3
            w += self.TOOLTIP_MARGIN
            h += self.TOOLTIP_MARGIN

            txt = "CELL\n" + txt
            txt += '\n' + str(self.cursor_chip.get_contact_cnt())

            # draw background
            dc.SetPen(wx.Pen(wx.RED, 0, wx.TRANSPARENT))
            dc.SetBrush(wx.Brush(wx.BLACK))
            dc.DrawRectangle(self.cursor_chip_pos[0] + 20 - self.TOOLTIP_MARGIN / 2,
                             self.cursor_chip_pos[1] - 55 - self.TOOLTIP_MARGIN / 2,
                             w,
                             h)
            dc.SetTextForeground(wx.WHITE)
            dc.SetFont(self.font)
            w, h = dc.GetTextExtent(txt)
            dc.DrawText(txt,
                        self.cursor_chip_pos[0] + 20,
                        self.cursor_chip_pos[1] - 55)

        # draw painter border
        dc.SetPen(wx.Pen(RULER_FONT_COLOR, 1, wx.SOLID))
        dc.SetBrush(wx.Brush(wx.BLACK, wx.TRANSPARENT))
        dc.DrawRectangle(0, 0, self.painter.GetSize()[0], self.painter.GetSize()[1])

    def OnLeftDown(self, e):
        self.is_left_down = True
        self.UpdateCursorAndChip(e)
        self.UpdateSelect()
        self.Refresh()
        # self.SetCursor(wx.Cursor(wx.CURSOR_SPRAYCAN))

    def OnMouseMove(self, e):
        self.UpdateCursorAndChip(e)
        self.UpdateSelect()
        self.Refresh()

    def UpdateSelect(self):
        if self.cursor_chip:
            if self.is_left_down:
                self.selected.add(self.cursor_chip)
                self.queue_update_marker.append(self.cursor_chip)
                self.cursor_chip.set_selected(True)
            if self.is_right_down:
                if self.cursor_chip in self.selected:
                    self.selected.remove(self.cursor_chip)
                    self.queue_update_marker.append(self.cursor_chip)
                    self.cursor_chip.set_selected(False)

    def OnLeftUp(self, e):
        self.is_left_down = False

    def OnRightDown(self, e):
        self.is_right_down = True
        self.UpdateCursorAndChip(e)
        self.UpdateSelect()
        self.Refresh()
        # self.Close()

    def OnRightUp(self, e):
        self.is_right_down = False

    def UpdateCursorAndChip(self, e):
        self.cursor_chip = None
        self.cursor_pos = e.GetPosition()
        cs = self.hash.query(self.cursor_pos)
        min_dist = 1000
        if cs:
            for c in cs:
                dist = distance(c.Pos(), self.cursor_pos)
                if dist < min_dist:
                    min_dist = dist
                    self.cursor_chip_pos = c.Pos()
                    self.cursor_chip = c

    def print_debug(self, txt):
        # return
        self.text2.SetLabelText( txt)
        # self.Refresh()


def main():
    app = wx.App()
    ex = Example(None)
    ex.Show()
    # wx.lib.inspection.InspectionTool().Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
