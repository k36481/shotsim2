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
from node import *

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


class Example(wx.Frame):
    sb1 = None
    sb2 = None
    sb3 = None
    panel = None

    nodes = set()

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, size=(RW + 2 * RM, RH))
        self.font = wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL, False, 'Segoe UI')

        self.InitUI()


    def run(self, e):
        self.nodes.add(Node())
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
        vBox02 = wx.BoxSizer(wx.HORIZONTAL)
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

        dc.SetPen(wx.Pen(RULER_FONT_COLOR, 1, wx.SOLID))
        dc.SetBrush(wx.Brush(PAINTER_BACK_COLOR))
        for n in self.nodes:
            dc.DrawRoundedRectangle(n.get_pos()[0],n.get_pos()[1], n.get_size()[0], n.get_size()[1], 10)
            if n.active:
                dc.SetPen(wx.Pen(RULER_FONT_COLOR, 2, wx.SOLID))
                dc.DrawRoundedRectangle(n.get_pos()[0], n.get_pos()[1], n.get_size()[0], n.get_size()[1], 10)

        # draw painter border
        dc.SetPen(wx.Pen(RULER_FONT_COLOR, 1, wx.SOLID))
        dc.SetBrush(wx.Brush(wx.BLACK, wx.TRANSPARENT))
        dc.DrawRectangle(0, 0, self.painter.GetSize()[0], self.painter.GetSize()[1])

    def OnLeftDown(self, e):
        self.is_left_down = True
        for n in self.nodes:
            if n.is_overlap(e.GetPosition()):
                n.active = True
        self.Refresh()

    def OnMouseMove(self, e):
        # return
        self.Refresh()

    def OnLeftUp(self, e):
        self.is_left_down = False

    def OnRightDown(self, e):
        print("wewwe")
        self.Refresh()

    def OnRightUp(self, e):
        self.is_right_down = False

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
