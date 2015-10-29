#!/usr/bin/env python

import pcbnew
import csv
import re
import sys

class RefBuilder:
    ''' RefBuilder use to re-build the module referrence number
    Step 1:  use rb = RefBuilder() to create a RefBuilder object
    Step 2:  use rb.collect(ref) to collect current exist reference
    Step 3:  usb newRef = rb.build(oldRef) to build new ref, if oldRef already built
             use the last oldRef's new Ref
    '''
    def  __init__(self, init_ref = None):
        self.patten = re.compile(r'([a-zA-Z]+)\s*(\d+)')
        self.refMap = {}
        self.builtMap = {}
        if init_ref:
            self.refMap = init_ref
    def collect(self, ref):
        m = re.match(r'([a-zA-Z]+)\s*(\d+)', ref)
        if m:
            if not self.refMap.has_key(m.group(1)):
                self.refMap[m.group(1)] = m.group(2)
            else:
                max = self.refMap[m.group(1)]
                if int(m.group(2)) > int(max):
                    self.refMap[m.group(1)] = m.group(2)
    def collects(self, refs):
        for ref in refs:
            self.collect(ref)
    def build(self, oldRef):
        m = re.match(r'([a-zA-Z]+)\s*(\d+)',oldRef)
        if not m:
            print 'Ref is invalid %s'%oldRef
            return None
        if self.builtMap.has_key(oldRef):
            return self.builtMap[oldRef]
        newRef = ''
        if not self.refMap.has_key(m.group(1)):
            self.refMap[m.group(1)] = m.group(2)
            newRef = oldRef
        else:
            max = int(self.refMap[m.group(1)])
            max = max + 1
            self.refMap[m.group(1)] = str(max)
            newRef = m.group(1) + str(max)
        self.builtMap[oldRef] = newRef
        return newRef
    def Show(self):
        print self.refMap
        
def testRefBuilder():
    rb = RefBuilder()
    rb.collects(['R1','R2','R14', 'R10', 'D1', 'D2', 'U3', 'U2', 'U1'])
    rb.show()
    print 'R1 -> %s'%rb.build('R1')
    print 'R2 -> %s'%rb.build('R2')
    print 'R3 -> %s'%rb.build('R3')
    print 'U1 -> %s'%rb.build('U1')
    print 'U2 -> %s'%rb.build('U2')
    print 'X2 -> %s'%rb.build('X2')
    print 'X1 -> %s'%rb.build('X1')
    print 'R? -> %s'%rb.build('R?')
    print 'R1 -> %s'%rb.build('R1')
    print 'R2 -> %s'%rb.build('R2')
    print 'X2 -> %s'%rb.build('X2')
    rb.show()

# Get Board Bounding rect by the margin layer element
def GetBoardArea(brd = None, marginLayer = pcbnew.Margin):
  if not brd:
    brd = pcbnew.GetBoard()
  rect = None
  for dwg in brd.GetDrawings():
    if dwg.GetLayer() == marginLayer:
        # Margin layer
        box = dwg.GetBoundingBox()
        if rect:
            rect.Merge(box)
        else:
            rect = box
  rect.SetX(rect.GetX() + 100001)
  rect.SetY(rect.GetY() + 100001)
  rect.SetWidth(rect.GetWidth() - 200002)
  rect.SetHeight(rect.GetHeight() - 200002)
  #print rect.GetX(), rect.GetY(), rect.GetWidth(), rect.GetHeight()
  return rect

class BoardItems:
    '''  Class to hold all interest board items
         Use Collect method to get all board items
   
    '''
    def __init__(self):
        self.rb = RefBuilder()
        self.orgItems = []
        self.rect = None
    def ItemValid(self, item):
        ''' Check the item is in the rect or not'''
        return item.HitTest(self.rect, False)
    def Collect(self, brd = None, rect = None):
        ''' Collect board items in specify rect'''
        if not brd:
            brd = pcbnew.GetBoard()
        if not rect:
            rect = GetBoardArea(brd)
        self.rect = rect
        for mod in brd.GetModules():
            if self.ItemValid(mod):
                self.orgItems.append(mod)
                self.rb.collect(mod.GetReference())
        for track in brd.GetTracks():
            if self.ItemValid(track):
                self.orgItems.append(track)
        for dwg in brd.GetDrawings():
            if self.ItemValid(dwg):
                self.orgItems.append(dwg)
            #print dwg.GetLayer()
        area_cnt = brd.GetAreaCount()
        for i in range(area_cnt):
            area = brd.GetArea(i)
            if self.ItemValid(area):
                self.orgItems.append(area)
        self.brd = brd
        #self.rb.Show()
    def Mirror(self):
        rotPt = pcbnew.wxPoint(self.rect.GetX() + self.rect.GetWidth()/2, self.rect.GetY() + self.rect.GetHeight()/2)
        for item in self.orgItems:
            item.Flip(rotPt)
            item.Rotate(rotPt, 1800)
    def Rotate(self, angle = 90):
        rotPt = pcbnew.wxPoint(self.rect.GetX() + self.rect.GetWidth()/2, self.rect.GetY() + self.rect.GetHeight()/2)
        for item in self.orgItems:
            item.Rotate(rotPt, angle * 10)
    def MoveToMM(self, x, y):
        self.MoveTo(pcbnew.wxPointMM(x,y))
    def MoveTo(self, pos):
        off = pcbnew.wxPoint( pos.x - self.rect.GetX(), pos.y - self.rect.GetY() )
        #print 'org is:', self.x, ',', self.y
        #print 'off is:', off
        for item in self.orgItems:
            item.Move(off)
        self.rect.Move(off)
    def Clone(self, brd = None):
        if not brd:
            brd = self.brd
        newBI = BoardItems()
        newBI.rect = self.rect
        for item in self.orgItems:
            newItem = item.Duplicate()
            newBI.orgItems.append(newItem)
            brd.Add(newItem)
        newBI.brd = brd
        return newBI
    def Remove(self):
        for item in self.orgItems:
            self.brd.Remove(item)
    def UpdateRef(self, rb):
        ''' Update items reference with specify ref builder'''
        for item in self.orgItems:
            if isinstance(item,pcbnew.MODULE):
                newRef = rb.build(item.GetReference())
                if newRef:
                    item.SetReference(newRef)
    def ChangeBrd(self, brd = None):
        if not brd:
            brd = pcbnew.GetBoard()
        if brd == self.brd:
            print 'Same board, do nothing'
        for item in self.orgItems:
            self.brd.Remove(item)
            brd.Add(item)

def test2():
    # load board to be panelized
    #b1 = pcbnew.LoadBoard(r'test1.kicad_pcb')
    b2 = pcbnew.LoadBoard(r'test2.kicad_pcb')
    # Get current work borad, must be a empty board
    brd = pcbnew.GetBoard()
    # Collect items
    bi1 = BoardItems()
    bi2 = BoardItems()
    bi1.Collect(brd)
    bi2.Collect(b2)
    #bi1 = bi1.Clone(brd)
    #bi2 = bi2.Clone(brd)
    # Clone items in board 1
    bb1 = bi1.Clone()
    # Change the module reference 
    bi2.UpdateRef(bi1.rb)
    # Clone items in board 2
    bb2 = bi2.Clone()
    # Copy board items to current board
    #bi1.ChangeBrd(brd)
    #bb1.ChangeBrd(brd)
    bi2.ChangeBrd(brd)
    bb2.ChangeBrd(brd)
    # Move them
    bi2.MoveToMM(0,0)
    bi2.Rotate(180)
    
    bb1.Mirror()
    bb2.Rotate(180)
    bb2.Mirror()
    
    bb1.MoveToMM(54, -59)
    bb2.MoveToMM(54, -59)

def GetPad1(mod):
    '''Get the first pad of a module'''
    padx = None
    for pad in mod.Pads():
        if not padx:
            padx = pad
        if pad.GetPadName() == '1':
            return pad
    print 'Pad 1 not found, use the first pad instead'
    return padx
def IsSMD(mod):
    for pad in mod.Pads():
        if pad.GetAttribute() != pcbnew.PAD_SMD:
            return False
    return True

class BOMItem:
    def __init__(self, ref, footprint, value, pincount):
        self.refs = [ref]
        self.fp = footprint
        self.value = value
        self.pincount = pincount
    def Output(self, out = None):
        refs = ''
        for r in self.refs:
           refs += r + ','
        if not out:
            out = csv.writer(sys.stdout, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_ALL)
        out.writerow([self.value, 'Desc', refs, self.fp, 'LibRef', str(self.pincount), str(len(self.refs))])
    def AddRef(self, ref):
        self.refs.append(ref)

def OutputBOMHeader(out = None):
    if not out:
        out = csv.writer(sys.stdout, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_ALL)
    out.writerow(['Comment','Description','Designator','Footprint','LibRef','Pins','Quantity','Number'])

def GenBOM(brd = None, layer = pcbnew.F_Cu, type = 1):
    if not brd:
        brd = pcbnew.GetBoard()
    bomList = {}
    for mod in brd.GetModules():
        needOutput = False
        if mod.GetLayer() == layer:
            needOutput = IsSMD(mod) == (type == 1)
        if needOutput:
            v = mod.GetValue()
            f = mod.GetFPID().GetFootprintName().Cast_to_CChar()
            r = mod.GetReference()
            vf = v + f
            if bomList.has_key(vf):
                bomList[vf].AddRef(r)
            else:
                bomList[vf] = BOMItem(r,f,v, mod.GetPadCount())
    print 'there are ', len(bomList), ' items'
    return bomList

def layerName(layerId):
    if layerId == pcbnew.F_Cu:
       return 'T'
    if layerId == pcbnew.B_Cu:
       return 'B'
    return 'X'
def toMM(v):
    return str(v/1000000.0) + 'mm'
class POSItem:
    def __init__(self, mod):
        self.MidX = toMM(mod.GetPosition().x)
        self.MidY = toMM(mod.GetPosition().y)
        self.RefX = toMM(mod.GetPosition().x)
        self.RefY = toMM(mod.GetPosition().y)
        pad = GetPad1(mod)
        if pad:
            self.PadX = toMM(pad.GetPosition().x)
            self.PadY = toMM(pad.GetPosition().y)
        else:
            print 'Pad1 not found for mod'
            self.PadX = self.MidX
            self.PadY = self.MidY
        self.rot = int(mod.GetOrientation()/10)
        self.ref = mod.GetReference()
        self.val = mod.GetValue()
        self.layer = layerName(mod.GetLayer())
        self.fp = mod.GetFPID().GetFootprintName().Cast_to_CChar()
    def Output(self, out = None):
        if not out:
            out = csv.writer(sys.stdout, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_ALL)
        out.writerow([self.ref, self.fp, str(self.MidX), str(self.MidY),
                     str(self.RefX), str(self.RefY), str(self.PadX), str(self.PadY),
                     self.layer, str(self.rot), self.val])

def GenPos(brd = None, layer = pcbnew.F_Cu, type = 1):
    if not brd:
        brd = pcbnew.GetBoard()
    posList = []
    for mod in brd.GetModules():
        needOutput = False
        if mod.GetLayer() == layer:
            needOutput = IsSMD(mod) == (type == 1)
        if needOutput:
            posList.append(POSItem(mod))
    return posList
def OutputPosHeader(out = None):
    if not out:
        out = csv.writer(sys.stdout, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_ALL)
    out.writerow(['Designator','Footprint','Mid X','Mid Y','Ref X','Ref Y','Pad X','Pad Y','Layer','Rotation','Comment'])
def PrintBOM(boms):
    OutputBOMHeader()
    i = 1
    for bom in boms:
       print 'BOM items for BOM', i
       i = i + 1
       for k,v in bom.items():
           v.Output()
def PrintPOS(Poses):
    OutputPosHeader()
    i = 1
    for pos in Poses:
       print 'Pos items ', i
       i = i+ 1
       for v in pos:
           v.Output()
    
    
    
