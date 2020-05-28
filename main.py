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
최소경로 인덱싱(최소경로신장트리?)
1개 초과의 blob을 가지는 경우가 아니면 diagonal과 rect 둘 중 하나로 환원가능하다(diag도 rect로 환원가능한듯)
"""

import wx
import wx.grid
import wx.lib.scrolledpanel
import wx.lib.inspection
import random
import time
import cython
# from numba import jit

from PIL import Image, ImageTk
import numpy as np

from shot import *
from hash import *
from geometric import *

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

chip_size = (8, 5)
chips = {}
chip_hash = {}


class MySheet(wx.grid.Grid):

    def __init__(self, *args, **kw):
        super(MySheet, self).__init__(*args, **kw)

        self.InitUI()

    def InitUI(self):
        nOfRows = 30000
        nOfCols = 2

        self.row = self.col = 0
        self.CreateGrid(nOfRows, nOfCols)

        self.SetColLabelSize(20)
        self.SetRowLabelSize(50)

        self.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.OnGridSelectCell)

        # for i in range(nOfRows):
        #     self.SetRowSize(i, 20)
        #
        for i in range(nOfCols):
            self.SetColSize(i, 75)

    def OnGridSelectCell(self, e):
        return
        self.row, self.col = e.GetRow(), e.GetCol()

        control = self.GetParent().GetParent().position
        value = self.GetColLabelValue(self.col) + self.GetRowLabelValue(self.row)
        control.SetValue(value)

        e.Skip()


class Example(wx.Frame):
    is_marking_layer_dirty = False
    is_left_down = False
    is_right_down = False
    is_middle_down = False
    drag_init_pos = (0, 0)
    cam_pos = (0, 0)
    cam_init_pos = (0, 0)
    queue_update_marker = []
    queue_update_shot_marker = []
    cursor_pos = (0, 0)
    cursor_pos_world = (0, 0)
    cursor_chip = None
    cursor_shot = None
    selected = set()

    para_shape = []
    para_tops = []
    map_bots = []
    shots = set()

    sb1 = None
    sb2 = None
    sb3 = None
    panel = None

    # for seamless drawing
    repeat_w = 0
    repeat_h = 0
    # for low-end hardware
    middle_down_offset = (0, 0)
    dirty_rect = None
    prev_dirty_rect = None

    coord_bmp = None
    wafermap_bmp = None
    ruler_vertical_bmp = None
    ruler_horizontal_bmp = None
    ruler_dummy_bmp = None
    hash_grid_bitmap = None
    marking_bitmap = None
    shot_bmp = None
    profile_bmp = None
    cached_bmp = None
    imsi_bmp = None

    prev_time = 0
    delta_time = 0

    hash_chip = None
    hash_shot = None

    chip_coord_x_min = 10000
    chip_coord_x_max = -10000
    chip_coord_y_min = 10000
    chip_coord_y_max = -10000

    # numpy things
    # np_chips = np.array()
    # np_paras = np.array()

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, size=(RW + 2 * RM, RH))
        self.font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL, False)
        self.paras = []
        with open("para.txt", 'r') as fi:
            self.para_shape = fi.read().splitlines()
            for i, s in enumerate(self.para_shape):
                self.para_shape[i] = list(s)
        self.para_tops = [-1000 for i in range(len(self.para_shape[0]))]
        # self.np_paras = np.asarray(self.para_shape, dtype=int)

        i = 1
        for y in range(len(self.para_shape)):
            for x in range(len(self.para_shape[0])):
                if self.para_shape[y][x]:
                    self.paras.append((x, y, i ** 2))
                    i += 1

        for x in range(len(self.para_shape[0])):
            top = -1000
            for y in range(len(self.para_shape)):
                if self.para_shape[y][x] == "1":
                    top = max(y, top)
                    break
            self.para_tops[x] = top

        print(self.para_tops)

        self.TOOLTIP_MARGIN = 35
        self.hash_grid_size = 15
        # for high end realtime drawing
        # self.repeat_w, self.repeat_h = (math.ceil(1200 / (chip_size[0] * 5)) * chip_size[0] * 5,
        #                                 math.ceil(700 / (chip_size[1] * 5)) * chip_size[1] * 5)
        # for low-end cached drawing
        self.repeat_w, self.repeat_h = (math.ceil(1980 / (chip_size[0] * 5)) * chip_size[0] * 5,
                                        math.ceil(1080 / (chip_size[1] * 5)) * chip_size[1] * 5)
        self.dirty_rect = wx.Rect(0, 0, 0, 0)
        self.prev_dirty_rect = wx.Rect(0, 0, 0, 0)
        self.hash_chip = Hash(self.hash_grid_size)
        self.hash_shot = Hash(self.hash_grid_size)
        self.CreateCoordGrid()
        self.CreateMap()
        self.CreateRuler()
        self.CreateHashGrid()
        self.CreateMarking()
        self.create_shot_bmp()
        self.create_profile_bmp()
        self.InitUI()

        self.timer = wx.Timer(self, 1)
        self.Bind(wx.EVT_TIMER, self.OnTimer)
        self.timer.Start()  # 1 second interval

        self.Bind(wx.EVT_IDLE, self.onIdle)

    def onIdle(self, e):
        return
        # self.delta_time = time.time() - self.prev_time
        # self.prev_time = time.time()
        # wx.IdleEvent.RequestMore(e)
        self.painter.Refresh()

    # def get_chip_key(self, pos):
    #     return pos[0]/[]

    def OnTimer(self, e):
        return
        mem_bmp = wx.Bitmap(PAINTER_W, 100)
        mem_dc = wx.MemoryDC(mem_bmp)
        mem_dc.DrawBitmap(self.profile_bmp, 1, 0)
        mem_dc.SetPen(wx.Pen(wx.WHITE, 1, wx.TRANSPARENT))
        # mem_dc.SetBrush(wx.Brush(wx.WHITE))
        val = random.randint(0, 100)
        mem_dc.DrawRectangle(0, 0, 1, val)
        del mem_dc
        self.profile_bmp = mem_bmp
        del mem_bmp
        self.painter.Refresh()

    def create_profile_bmp(self):
        self.profile_bmp = wx.Bitmap(PAINTER_W, 100)
        # self.shot_bmp.SetMaskColour(wx.BLACK)

    def create_shot_bmp(self):
        self.shot_bmp = wx.Bitmap(PAINTER_W, PAINTER_H)
        self.shot_bmp.SetMaskColour(wx.BLACK)

    def CreateMarking(self):
        self.marking_bitmap = wx.Bitmap(PAINTER_W, PAINTER_H)

    def CreateHashGrid(self):
        self.hash_grid_bitmap = wx.Bitmap(PAINTER_W, PAINTER_H)
        mem_dc = wx.MemoryDC(self.hash_grid_bitmap)
        mem_dc.SetPen(wx.Pen(wx.RED, 1, wx.SOLID))
        mem_dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        for i in range(1, PAINTER_W):
            if not (i % self.hash_grid_size):
                mem_dc.DrawLine(i, 0, i, PAINTER_H)
        for i in range(1, PAINTER_H):
            if not (i % self.hash_grid_size):
                mem_dc.DrawLine(0, i, PAINTER_W, i)
        del mem_dc
        self.hash_grid_bitmap.SetMaskColour(wx.BLACK)

    def CreateRuler(self):
        self.ruler_vertical_bmp = wx.Bitmap(35, self.repeat_h)
        mem_dc = wx.MemoryDC(self.ruler_vertical_bmp)
        # draw background
        # mem_dc.SetBackgroundMode(wx.TRANSPARENT)
        mem_dc.SetPen(wx.Pen('#777777', 1, wx.SOLID))
        mem_dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        mem_dc.DrawRectangle(0, 0, 35, self.repeat_h)
        # draw text
        mem_dc.SetPen(wx.Pen(RULER_FONT_COLOR, 1))
        # mem_dc.SetTextBackground(wx.WHITE)
        mem_dc.SetTextForeground(RULER_FONT_COLOR)
        mem_dc.SetFont(self.font)
        for i in range(1, self.repeat_h):
            if not (i % (chip_size[1] * 5)):
                mem_dc.DrawLine(0, i, 10, i)
                txt = str(int(i / chip_size[1]))
                w, h = mem_dc.GetTextExtent(txt)
                mem_dc.DrawText(txt, 1, i + 1)
        del mem_dc
        self.ruler_vertical_bmp.SetMaskColour(wx.BLACK)

        self.ruler_horizontal_bmp = wx.Bitmap(self.repeat_w, 35)
        mem_dc = wx.MemoryDC(self.ruler_horizontal_bmp)
        # draw background
        # mem_dc.SetBackgroundMode(wx.TRANSPARENT)
        mem_dc.SetPen(wx.Pen('#777777', 1, wx.SOLID))
        mem_dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        mem_dc.DrawRectangle(0, 0, self.repeat_w, 35)
        # draw text
        mem_dc.SetPen(wx.Pen(RULER_FONT_COLOR, 1))
        mem_dc.SetTextBackground(wx.BLACK)
        mem_dc.SetTextForeground(RULER_FONT_COLOR)
        mem_dc.SetFont(self.font)
        for i in range(1, self.repeat_w):
            if not (i % (chip_size[0] * 5)):
                mem_dc.DrawLine(i, 0, i, 10)
                txt = str(int(i / chip_size[0]))
                w, h = mem_dc.GetTextExtent(txt)
                mem_dc.DrawText(txt, i + 1, 1)
        del mem_dc
        self.ruler_horizontal_bmp.SetMaskColour(wx.BLACK)

        self.ruler_dummy_bmp = wx.Bitmap(35, 35)
        mem_dc = wx.MemoryDC(self.ruler_dummy_bmp)
        # draw background
        mem_dc.SetBackgroundMode(wx.TRANSPARENT)
        mem_dc.SetPen(wx.Pen(RULER_FONT_COLOR, 1, wx.SOLID))
        mem_dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        mem_dc.DrawRectangle(0, 0, 35, 35)
        del mem_dc
        self.ruler_dummy_bmp.SetMaskColour(wx.BLACK)

    def CreateCoordGrid(self):
        w, h = (math.ceil(1024 / (chip_size[0] * 5)) * chip_size[0] * 5,
                math.ceil(1024 / (chip_size[1] * 5)) * chip_size[1] * 5)
        self.coord_bmp = wx.Bitmap(w, h)
        mem_dc = wx.MemoryDC(self.coord_bmp)
        mem_dc.SetPen(wx.Pen('#777777', 0, wx.TRANSPARENT))
        mem_dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR, wx.SOLID))
        mem_dc.DrawRectangle(0, 0, w, h)
        mem_dc.SetPen(wx.Pen('#777777', 1, wx.DOT))
        mem_dc.SetBrush(wx.Brush(wx.BLACK, wx.TRANSPARENT))
        for i in range(0, w):
            if not (i % 5):
                mem_dc.DrawLine(i * chip_size[0], 0, i * chip_size[0], h)
        for i in range(0, h):
            if not (i % 5):
                mem_dc.DrawLine(0, i * chip_size[1], w, i * chip_size[1])
        del mem_dc
        self.coord_bmp.SetMaskColour(wx.BLACK)

    def CreateMap(self):
        self.hash_chip = Hash(self.hash_grid_size)

        self.wafermap_bmp = wx.Bitmap(PAINTER_W, PAINTER_H)
        mem_dc = wx.MemoryDC(self.wafermap_bmp)
        # draw background
        mem_dc.SetPen(wx.Pen(CHIP_LINE_COLOR, 0, wx.TRANSPARENT))
        mem_dc.SetBrush(wx.Brush(wx.BLACK))
        mem_dc.DrawRectangle(0, 0, PAINTER_W, PAINTER_H)

        # draw chip
        mem_dc.SetPen(wx.Pen(PAINTER_BACK_COLOR, 0, wx.SOLID))
        mem_dc.SetBrush(wx.Brush(CHIP_COLOR))
        for x in range(10, 250):
            for y in range(10, 250):
                if distance((x * chip_size[0], y * chip_size[1]), (100 * chip_size[0], 100 * chip_size[1])) < 400:
                    chip = Chip(x * chip_size[0],
                                y * chip_size[1],
                                x,
                                y)
                    chips[chip.Coord()] = chip
                    self.chip_coord_x_min = min(self.chip_coord_x_min, x)
                    self.chip_coord_x_max = max(self.chip_coord_x_max, x)
                    self.chip_coord_y_min = min(self.chip_coord_y_min, y)
                    self.chip_coord_y_max = max(self.chip_coord_y_max, y)
                    # self.listBox.Append(str(chip.x) + str(chip.y))
                    self.hash_chip.insert(chip)

                    mem_dc.DrawRectangle(chip.pos_x - chip_size[0] / 2,
                                         chip.pos_y - chip_size[1] / 2,
                                         chip_size[0],
                                         chip_size[1])

        del mem_dc
        self.wafermap_bmp.SetMaskColour(wx.BLACK)
        self.imsi_bmp = wx.Bitmap(PAINTER_W, PAINTER_H)

        #  50 is margin
        self.map_bots = [10000 for i in range(self.chip_coord_x_max + 1 + 50)]
        for c in chips.values():
            x, y = c.Coord()
            self.map_bots[x] = min(y, self.map_bots[x])

    def on_combo_select(self, e):
        self.print_debug("combo: " + self.combo_select.GetValue())

    def on_combo_wheel(self, e):
        self.print_debug("combo: " + str(e.GetWheelRotation()))
        if e.GetWheelRotation() > 0:
            self.combo_select.SetSelection(max(self.combo_select.GetSelection() - 1, 0))
        else:
            self.combo_select.SetSelection(self.combo_select.GetSelection() + 1)

    def on_chk01(self, e):
        self.painter.Refresh()

    def on_chk02(self, e):
        self.painter.Refresh()

    def on_btn_debug(self, e):
        self.cam_pos = (self.cam_pos[0] + 10, self.cam_pos[1] + 10)
        self.painter.Refresh()

    def run(self, e):

        self.shots.clear()
        for c in chips.values():
            c.set_contact_cnt(0)

        x_iter = 0
        y_iter = 0
        xrange = self.chip_coord_x_max + 1
        yrange = self.chip_coord_y_max + 1
        para_width = len(self.para_shape[0])
        y01 = self.spin_y01.GetValue()
        y02 = self.spin_y02.GetValue()
        x01 = self.spin_x01.GetValue()
        x02 = self.spin_x02.GetValue()
        xoffset = self.spin_xoffset.GetValue()

        t0 = time.time()

        x = xoffset
        while x < xrange:
            y = min(self.map_bots[x + i] - self.para_tops[i] for i in range(para_width))
            while y < yrange:
                contacted = 0
                weight_sum = 0
                for x_, y_, w_ in self.paras:
                    if (x + x_, y + y_) in chips:
                        contacted += 1
                        chips[(x + x_, y + y_)].contact_cnt += 1
                        weight_sum += w_
                if contacted:
                    shot = Shot(x * chip_size[0], y * chip_size[1], x, y)
                    shot.weight_sum = weight_sum
                    self.shots.add(shot)
                y += y01 if y_iter % 2 == 0 else y02
                y_iter += 1
            x += x01 if x_iter % 2 == 0 else x02
            x_iter += 1
        print(time.time() - t0)
        t0 = time.time()

        mem_dc = wx.MemoryDC(self.shot_bmp)
        mem_dc.SetPen(wx.Pen(wx.BLACK, 1, wx.SOLID))
        mem_dc.SetBrush(wx.Brush(wx.BLACK))
        mem_dc.DrawRectangle(0, 0, PAINTER_W, PAINTER_H)

        mem_dc.SetPen(wx.Pen(wx.BLACK, 1, wx.TRANSPARENT))
        mem_dc.SetBrush(wx.Brush('#9999ff', wx.SOLID))
        for k, c in chips.items():
            if c.get_contact_cnt() == 1:
                mem_dc.DrawRectangle(c.Pos()[0] - chip_size[0] / 2 + 1,
                                     c.Pos()[1] - chip_size[1] / 2 + 1,
                                     chip_size[0] - 2,
                                     chip_size[1] - 2)

        mem_dc.SetPen(wx.Pen(wx.BLACK, 1, wx.TRANSPARENT))
        mem_dc.SetBrush(wx.Brush('#DDAA00', wx.SOLID))
        for k, c in chips.items():
            if c.get_contact_cnt() == 2:
                mem_dc.DrawRectangle(c.Pos()[0] - chip_size[0] / 2 + 1,
                                     c.Pos()[1] - chip_size[1] / 2 + 1,
                                     chip_size[0] - 2,
                                     chip_size[1] - 2)

        mem_dc.SetPen(wx.Pen(wx.BLACK, 1, wx.TRANSPARENT))
        mem_dc.SetBrush(wx.Brush(wx.RED, wx.SOLID))
        for k, c in chips.items():
            if c.get_contact_cnt() >= 3:
                mem_dc.DrawRectangle(c.Pos()[0] - chip_size[0] / 2 + 1,
                                     c.Pos()[1] - chip_size[1] / 2 + 1,
                                     chip_size[0] - 2,
                                     chip_size[1] - 2)

        mem_dc.SetPen(wx.Pen('#000001', 1, wx.SOLID))
        mem_dc.SetBrush(wx.Brush(wx.BLACK, wx.TRANSPARENT))
        for i, s in enumerate(self.shots):
            mem_dc.DrawRectangle(s.Pos()[0] - chip_size[0] / 2,
                                 s.Pos()[1] - chip_size[1] / 2,
                                 chip_size[0],
                                 chip_size[1])
            dummy_digit_count = 4 - len(f'{s.weight_sum:x}') % 4
            dummy_digit = '#' + '0' * dummy_digit_count
            self.spread_sheet.GetPage(0).SetCellValue(i, 0, f'{i+1}')
            self.spread_sheet.GetPage(0).SetCellValue(i, 1, f'{dummy_digit}{s.weight_sum:x}')
        del mem_dc
        self.shot_bmp.SetMaskColour(wx.BLACK)

        # self.hash_shot = Hash(self.hash_grid_size)
        # for s in self.shots:
        #     self.hash_shot.insert(s)
        self.painter.Refresh()

    def InitUI(self):
        self.panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.pnl_info = wx.Panel(self.panel, name="pnl_info", style=wx.SIMPLE_BORDER, size=(250, 100))
        self.pnl_info.SetSizer(vbox)
        sizer.Add(self.pnl_info, 0, flag=wx.EXPAND | wx.ALL, border=5)

        self.pnl01 = wx.Panel(self.pnl_info, name="panel01", style=wx.SIMPLE_BORDER, size=(250, 100))
        vBox01 = wx.BoxSizer(wx.VERTICAL)
        self.pnl01.SetSizer(vBox01)
        self.spread_sheet = wx.Notebook(self.pnl01)
        sheet1 = MySheet(self.spread_sheet)
        sheet2 = MySheet(self.spread_sheet)
        sheet3 = MySheet(self.spread_sheet)
        sheet1.SetFocus()
        self.spread_sheet.AddPage(sheet1, 'Sheet1')
        self.spread_sheet.AddPage(sheet2, 'Sheet2')
        self.spread_sheet.AddPage(sheet3, 'Sheet3')
        vBox01.Add(self.spread_sheet, 1, flag=wx.EXPAND)
        self.pnl01.SetDoubleBuffered(True)
        vbox.Add(self.pnl01, 1, flag=wx.EXPAND | wx.ALL, border=5)

        self.pnl02 = wx.Panel(self.pnl_info, name="panel02", style=wx.SIMPLE_BORDER)
        vBox02 = wx.BoxSizer(wx.VERTICAL)
        self.pnl02.SetSizer(vBox02)
        self.btn_run = wx.Button(self.pnl02, label="Run")
        self.btn_run.Bind(wx.EVT_BUTTON, self.run)
        vBox02.Add(self.btn_run, flag=wx.EXPAND | wx.ALL, border=5)
        self.btn_debug = wx.Button(self.pnl02, label="Debug")
        self.btn_debug.Bind(wx.EVT_BUTTON, self.on_btn_debug)
        vBox02.Add(self.btn_debug, flag=wx.EXPAND | wx.ALL, border=5)
        choice = ['chip', 'shot']
        self.combo_select = wx.ComboBox(self.pnl02, choices=choice)
        self.combo_select.Bind(wx.EVT_COMBOBOX, self.on_combo_select)
        self.combo_select.Bind(wx.EVT_MOUSEWHEEL, self.on_combo_wheel)
        vBox02.Add(self.combo_select, flag=wx.EXPAND | wx.ALL, border=5)
        self.combo_select.SetSelection(1)
        self.ckBox01 = wx.CheckBox(self.pnl02, label="grid")
        self.ckBox01.Bind(wx.EVT_CHECKBOX, self.on_chk01)
        vBox02.Add(self.ckBox01, flag=wx.EXPAND | wx.ALL, border=5)
        self.ckBox02 = wx.CheckBox(self.pnl02, label="shot")
        self.ckBox02.SetValue(True)
        self.ckBox02.Bind(wx.EVT_CHECKBOX, self.on_chk02)
        vBox02.Add(self.ckBox02, flag=wx.EXPAND | wx.ALL, border=5)
        hbox01 = wx.BoxSizer(wx.HORIZONTAL)
        hbox02 = wx.BoxSizer(wx.HORIZONTAL)
        hbox03 = wx.BoxSizer(wx.HORIZONTAL)
        hbox04 = wx.BoxSizer(wx.HORIZONTAL)
        hbox05 = wx.BoxSizer(wx.HORIZONTAL)

        self.pnl_x = wx.Panel(self.pnl02, name="pnl_x")
        self.pnl_x.SetSizer(hbox01)
        vBox02.Add(self.pnl_x, flag=wx.EXPAND | wx.ALL, border=5)
        hbox01.Add(wx.StaticText(self.pnl_x, label="X1:"), 0, flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_x01 = wx.SpinCtrl(self.pnl_x, initial=2, min=1, size=(50,20))
        hbox01.Add(self.spin_x01, 1, flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_x01.Bind(wx.EVT_SPINCTRL, self.run)
        hbox01.Add(wx.StaticText(self.pnl_x, label="X2:"), 0, flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_x02 = wx.SpinCtrl(self.pnl_x, initial=2, min=1, size=(50,20))
        hbox01.Add(self.spin_x02, 1, flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_x02.Bind(wx.EVT_SPINCTRL, self.run)

        self.pnl_y = wx.Panel(self.pnl02, name="pnl_y")
        self.pnl_y.SetSizer(hbox02)
        vBox02.Add(self.pnl_y, flag=wx.EXPAND | wx.ALL, border=5)
        hbox02.Add(wx.StaticText(self.pnl_y, label="Y1:"),0, flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_y01 = wx.SpinCtrl(self.pnl_y, initial=2, min=1, size=(50,20))
        hbox02.Add(self.spin_y01,1, flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_y01.Bind(wx.EVT_SPINCTRL, self.run)
        hbox02.Add(wx.StaticText(self.pnl_y, label="Y2:"),0, flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_y02 = wx.SpinCtrl(self.pnl_y, initial=2, min=1, size=(50,20))
        hbox02.Add(self.spin_y02,1, flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_y02.Bind(wx.EVT_SPINCTRL, self.run)

        self.pnl_offset = wx.Panel(self.pnl02, name="pnl_offset")
        self.pnl_offset.SetSizer(hbox03)
        vBox02.Add(self.pnl_offset, flag=wx.EXPAND | wx.ALL, border=5)
        hbox03.Add(wx.StaticText(self.pnl_offset, label="Xoffset:"), flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_xoffset = wx.SpinCtrl(self.pnl_offset, initial=0, max=50)
        hbox03.Add(self.spin_xoffset, flag=wx.RIGHT | wx.ALIGN_CENTER, border=5)
        self.spin_xoffset.Bind(wx.EVT_SPINCTRL, self.run)
        vbox.Add(self.pnl02, 1, flag=wx.EXPAND | wx.ALL, border=5)


        self.painter = wx.Panel(self.panel, name="painter_panel", style=wx.SIMPLE_BORDER)
        sizer.Add(self.painter, 4, flag=wx.EXPAND | wx.TOP | wx.BOTTOM | wx.RIGHT, border=5)
        self.painter.SetDoubleBuffered(True)
        self.cam_pos = (0, 0)

        self.pnl03 = wx.Panel(self.panel, name="panel03", style=wx.SIMPLE_BORDER)
        sizer.Add(self.pnl03, 0, flag=wx.EXPAND | wx.TOP | wx.BOTTOM | wx.RIGHT, border=5)
        self.vBox03 = wx.BoxSizer(wx.VERTICAL)
        self.pnl03.SetSizer(self.vBox03)
        self.debugText = wx.StaticText(self.pnl03, label="", style=wx.ALIGN_LEFT, size=(100, 100))
        self.vBox03.Add(self.debugText)
        self.pnl03.SetDoubleBuffered(True)

        # sizer.AddGrowableRow(1)
        # sizer.AddGrowableCol(1)

        # self.Bind(wx.EVT_PAINT, self.OnPaint)
        # self.Bind(wx.EVT_SIZING, self.refresh_all())
        self.painter.Bind(wx.EVT_PAINT, self.OnPaint)
        self.painter.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.painter.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.painter.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.painter.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.painter.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.painter.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDown)
        self.painter.Bind(wx.EVT_MIDDLE_UP, self.OnMiddleUP)
        self.panel.SetSizer(sizer)
        # sizer.Fit(self)

        self.CreateStatusBar()
        self.Layout()
        self.Centre()

        self.Show(True)

        # self.Fit()

        # for i, (cod, chip) in enumerate(chips.items()):
        #     self.spread_sheet.GetPage(0).SetCellValue(i, 0, str(cod))
        #     self.spread_sheet.GetPage(0).SetCellValue(i, 1, str(chip.get_contact_cnt()))
        self.Refresh()

    def refresh_all(self):
        self.Refresh()

    def OnPaint(self, e):

        pos_offset = (-self.cam_pos[0], -self.cam_pos[1])
        cursor_pos_world = self.cursor_pos + self.cam_pos

        dc = wx.PaintDC(self.painter)
        dc.SetFont(self.font)

        # for low-end hardware
        if self.is_middle_down:
            dc.DrawBitmap(self.cached_bmp, self.middle_down_offset[0] + 35, self.middle_down_offset[1] + 35)
            # draw ruler simple
            dc.DrawBitmap(self.ruler_vertical_bmp, -1, pos_offset[1], True)
            dc.DrawBitmap(self.ruler_horizontal_bmp, pos_offset[0], -1, True)
            # dc.DrawBitmap(wx.Bitmap('img/imsi2.png'), 100*math.sin(time.time()*10), 0)
            # dc.DrawBitmap(self.ruler_dummy_bmp, -1, -1, True)
            return

        # draw coord grid
        dc.SetBrush(wx.Brush(self.coord_bmp))
        for i in range(-1, 2):
            for j in range(-1, 2):
                dc.DrawBitmap(self.coord_bmp,
                              pos_offset[0] % self.coord_bmp.GetSize()[0] + i * self.coord_bmp.GetSize()[0],
                              pos_offset[1] % self.coord_bmp.GetSize()[1] + j * self.coord_bmp.GetSize()[1], False)

        # draw wafer map
        for i in range(1):
            dc.DrawBitmap(self.wafermap_bmp, pos_offset[0], pos_offset[1], True)

        # dc.DrawBitmap(wx.Bitmap('img/imsi2.png'), 100 * math.sin(time.time() * 10), 0)
        # draw ruler seamess
        # for i in range(-1, 2):
        #     dc.DrawBitmap(self.ruler_vertical_bmp, 0, pos_offset[1] % self.repeat_h + i * self.repeat_h, True)
        # for i in range(-1, 2):
        #     dc.DrawBitmap(self.ruler_horizontal_bmp, pos_offset[0] % self.repeat_w + i * self.repeat_w, 0, True)
        # dc.DrawBitmap(self.ruler_dummy_bmp, 0, 0, True)

        # draw shot
        if self.ckBox02.GetValue():
            dc.DrawBitmap(self.shot_bmp, pos_offset[0], pos_offset[1], True)

        # draw ruler simple
        dc.DrawBitmap(self.ruler_vertical_bmp, -1, pos_offset[1], False)
        dc.DrawBitmap(self.ruler_horizontal_bmp, pos_offset[0], -1, False)
        # dc.DrawBitmap(self.ruler_dummy_bmp, 0, 0, False)

        # draw hash grid
        if self.ckBox01.GetValue():
            dc.DrawBitmap(self.hash_grid_bitmap, pos_offset[0], pos_offset[1], True)

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

        # draw select helper
        if self.combo_select.GetValue() == "chip":
            if self.cursor_chip:
                dc.SetPen(wx.Pen(wx.BLACK, 2, wx.SOLID))
                dc.SetBrush(wx.Brush('#333333', wx.TRANSPARENT))
                dc.DrawRectangle(self.cursor_chip.Pos()[0] + pos_offset[0] - chip_size[0] / 2 - 2,
                                 self.cursor_chip.Pos()[1] + pos_offset[1] - chip_size[1] / 2 - 2,
                                 chip_size[0] + 5,
                                 chip_size[1] + 5)
        elif self.combo_select.GetValue() == "shot":
            if self.cursor_shot:
                dc.SetPen(wx.Pen(wx.BLACK, 2, wx.SOLID))
                dc.SetBrush(wx.Brush('#333333', wx.TRANSPARENT))
                dc.DrawRectangle(self.cursor_shot.Pos()[0] + pos_offset[0] - chip_size[0] / 2 - 2,
                                 self.cursor_shot.Pos()[1] + pos_offset[1] - chip_size[1] / 2 - 2,
                                 chip_size[0] + 5,
                                 chip_size[1] + 5)

        # draw marker
        mem_dc = wx.MemoryDC(self.marking_bitmap)
        if self.queue_update_marker:
            for c in self.queue_update_marker:
                # print("update marker: "+str(c.Coord()))
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
        dc.DrawBitmap(self.marking_bitmap, pos_offset[0], pos_offset[1], True)

        # draw tooltip
        if self.combo_select.GetValue() == "chip":
            if self.cursor_chip:
                txt = str(str(self.cursor_chip.x).zfill(3) + "," + str(self.cursor_chip.y).zfill(3))
                txt = "CHIP\n" + txt
                txt += '\n' + "contact_count:" + str(self.cursor_chip.get_contact_cnt())
                w = max(dc.GetTextExtent(i)[0] for i in txt.splitlines())
                h = dc.GetTextExtent(txt.splitlines()[0])[1] * len(txt.splitlines())
                w += self.TOOLTIP_MARGIN
                h += self.TOOLTIP_MARGIN
                # draw background
                dc.SetPen(wx.Pen(wx.RED, 0, wx.TRANSPARENT))
                dc.SetBrush(wx.Brush(wx.BLACK))
                dc.DrawRectangle(
                    self.cursor_chip.Pos()[0] + pos_offset[0] - self.TOOLTIP_MARGIN / 2 + self.TOOLTIP_MARGIN,
                    self.cursor_chip.Pos()[1] + pos_offset[1] - self.TOOLTIP_MARGIN / 2 + self.TOOLTIP_MARGIN,
                    w,
                    h)
                dc.SetTextForeground(wx.WHITE)
                w, h = dc.GetTextExtent(txt)
                dc.DrawText(txt,
                            self.cursor_chip.Pos()[0] + pos_offset[0] + self.TOOLTIP_MARGIN,
                            self.cursor_chip.Pos()[1] + pos_offset[1] + self.TOOLTIP_MARGIN)

        elif self.combo_select.GetValue() == "shot":
            if self.cursor_shot:
                txt = str(str(self.cursor_shot.x).zfill(3) + "," + str(self.cursor_shot.y).zfill(3))
                txt = "SHOT\n" + txt
                w = max(dc.GetTextExtent(i)[0] for i in txt.splitlines())
                h = dc.GetTextExtent(txt.splitlines()[0])[1] * len(txt.splitlines())
                w += self.TOOLTIP_MARGIN
                h += self.TOOLTIP_MARGIN

                # draw background
                dc.SetPen(wx.Pen(wx.RED, 0, wx.TRANSPARENT))
                dc.SetBrush(wx.Brush(wx.BLACK))
                dc.DrawRectangle(
                    self.cursor_shot.Pos()[0] + pos_offset[0] - self.TOOLTIP_MARGIN / 2 + self.TOOLTIP_MARGIN,
                    self.cursor_shot.Pos()[1] + pos_offset[1] - self.TOOLTIP_MARGIN / 2 + self.TOOLTIP_MARGIN,
                    w,
                    h)
                dc.SetTextForeground(wx.WHITE)
                w, h = dc.GetTextExtent(txt)
                dc.DrawText(txt,
                            self.cursor_shot.Pos()[0] + pos_offset[0] + self.TOOLTIP_MARGIN,
                            self.cursor_shot.Pos()[1] + pos_offset[1] + self.TOOLTIP_MARGIN)

        # dc.DrawBitmap(self.profile_bmp, 0, 0)
        # dc.DrawBitmap(self.imsi_bmp, 0, 0, True)

        # draw painter border
        # dc.SetPen(wx.Pen(RULER_FONT_COLOR, 1, wx.SOLID))
        # dc.SetBrush(wx.Brush(wx.BLACK, wx.TRANSPARENT))
        # dc.DrawRectangle(0, 0, self.painter.GetSize()[0], self.painter.GetSize()[1])

    def OnMiddleDown(self, e):
        self.cached_bmp = wx.Bitmap((self.painter.GetSize()[0] - 2 - 35, self.painter.GetSize()[1] - 2 - 35))
        wdc = wx.WindowDC(self.painter)
        mem_dc = wx.MemoryDC(self.cached_bmp)
        mem_dc.SetPen(wx.Pen('#000001', 1, wx.TRANSPARENT))
        mem_dc.Blit(0, 0, self.painter.GetSize()[0] - 2 - 35, self.painter.GetSize()[1] - 2 - 35, wdc, 1 + 35, 1 + 35)
        del mem_dc
        self.is_middle_down = True
        self.cam_init_pos = self.cam_pos
        self.drag_init_pos = e.GetPosition()
        self.middle_down_offset = (0, 0)
        self.cached_bmp.SetMaskColour(wx.BLACK)

    def OnMiddleUP(self, e):
        self.is_middle_down = False
        self.painter.Refresh()

    def OnLeftDown(self, e):
        self.is_left_down = True
        self.UpdateCursorAndChip(e)
        self.UpdateSelect()
        self.painter.Refresh()
        # self.SetCursor(wx.Cursor(wx.CURSOR_SPRAYCAN))

    def OnLeftUp(self, e):
        self.is_left_down = False

    def OnRightDown(self, e):
        self.is_right_down = True
        self.UpdateCursorAndChip(e)
        self.UpdateSelect()
        self.painter.Refresh()
        # self.Close()

    def OnRightUp(self, e):
        self.is_right_down = False

    def OnMouseMove(self, e):
        # delta_time = time.time() - self.prev_time
        # print(1/delta_time)
        # self.prev_time = time.time()
        if self.is_middle_down:
            self.middle_down_offset = (
                e.GetPosition()[0] - self.drag_init_pos[0], e.GetPosition()[1] - self.drag_init_pos[1])
            self.cam_pos = (
                self.cam_init_pos[0] - self.middle_down_offset[0], self.cam_init_pos[1] - self.middle_down_offset[1])
        self.UpdateCursorAndChip(e)
        self.UpdateSelect()
        self.dirty_rect = wx.Rect(e.GetPosition()[0] - 50, e.GetPosition()[1] - 50, 250, 200)
        if self.is_middle_down:
            self.painter.Refresh()
        else:
            self.painter.RefreshRect(self.dirty_rect.Union(self.prev_dirty_rect))
        self.prev_dirty_rect = self.dirty_rect

    def UpdateSelect(self):
        if self.combo_select.GetValue() == "chip":
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
        elif self.combo_select.GetValue() == "shot":
            pass
            # if self.cursor_shot:
            #     if self.is_left_down:
            # self.selected.add(self.cursor_chip)
            # self.queue_update_marker.append(self.cursor_chip)
            # self.cursor_chip.set_selected(True)
            # if self.is_right_down:
            # if self.cursor_chip in self.selected:
            # self.selected.remove(self.cursor_chip)
            # self.queue_update_marker.append(self.cursor_chip)
            # self.cursor_chip.set_selected(False)

    def UpdateCursorAndChip(self, e):
        self.cursor_pos = e.GetPosition()
        self.cursor_pos_world = (self.cursor_pos[0] + self.cam_pos[0], self.cursor_pos[1] + self.cam_pos[1])
        self.cursor_chip = None
        self.cursor_shot = None
        # find current chip
        cs = self.hash_chip.query(self.cursor_pos_world)
        min_dist = 1000
        if cs:
            for c in cs:
                dist = distance(c.Pos(), self.cursor_pos_world)
                if dist < min_dist:
                    min_dist = dist
                    self.cursor_chip = c
        if self.cursor_chip:
            if not is_point_in_rect(self.cursor_pos_world, self.cursor_chip.Pos()[0] - chip_size[0] / 2,
                                    self.cursor_chip.Pos()[0] + chip_size[0] / 2,
                                    self.cursor_chip.Pos()[1] - chip_size[1] / 2,
                                    self.cursor_chip.Pos()[1] + chip_size[1] / 2):
                self.cursor_chip = None
        # find current shot
        ss = self.hash_shot.query(self.cursor_pos_world)
        min_dist = 1000
        if ss:
            for s in ss:
                dist = distance(s.Pos(), self.cursor_pos_world)
                if dist < min_dist:
                    min_dist = dist
                    self.cursor_shot = s
        if self.cursor_shot:
            if not is_point_in_rect(self.cursor_pos_world, self.cursor_shot.Pos()[0] - chip_size[0] / 2,
                                    self.cursor_shot.Pos()[0] + chip_size[0] / 2,
                                    self.cursor_shot.Pos()[1] - chip_size[1] / 2,
                                    self.cursor_shot.Pos()[1] + chip_size[1] / 2):
                self.cursor_shot = None

    def print_debug(self, txt):
        # return
        self.debugText.SetLabelText(txt)
        # self.Refresh()


def main():
    app = wx.App()
    ex = Example(None)
    ex.Show()
    # wx.lib.inspection.InspectionTool().Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
