#!/usr/bin/env python

import pcbnew
import csv
import re
import sys
import os

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
        m = self.patten.match(ref)
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
    rb.Show()
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
    rb.Show()

# Get Board Bounding rect by the margin layer element
#def GetBoardArea(brd = None, marginLayer = pcbnew.Margin):
#  if not brd:
#    brd = pcbnew.GetBoard()
#  rect = None
#  for dwg in brd.GetDrawings():
#    if dwg.GetLayer() == marginLayer:
#        box = dwg.GetBoundingBox()
#        if rect:
#            rect.Merge(box)
#        else:
#            rect = box
#  rect.SetX(rect.GetX() + 100001)
#  rect.SetY(rect.GetY() + 100001)
#  rect.SetWidth(rect.GetWidth() - 200002)
#  rect.SetHeight(rect.GetHeight() - 200002)
#  #print rect.GetX(), rect.GetY(), rect.GetWidth(), rect.GetHeight()
#  return rect

def GetBoardBound(brd = None, marginLayer = pcbnew.Edge_Cuts):
    ''' Calculate board edge from the margin layer, the default margin layer is Edge_Cuts
        enum all the draw segment on the specified layer, and merge their bound rect
    '''
    if not brd:
        brd = pcbnew.GetBoard()
    rect = None
    l = None
    r = None
    t = None
    b = None
    for dwg in brd.GetDrawings():
        if dwg.GetLayer() == marginLayer:
            if hasattr(dwg, 'Cast_to_DRAWSEGMENT'):
                d = dwg.Cast_to_DRAWSEGMENT()
            else:
                d = pcbnew.Cast_to_DRAWSEGMENT(dwg)
            w = d.GetWidth()
            box = d.GetBoundingBox()
            box.SetX(box.GetX() + w/2)
            box.SetY(box.GetY() + w/2)
            box.SetWidth(box.GetWidth() - w)
            box.SetHeight(box.GetHeight() - w)
            if rect:
                rect.Merge(box)
            else:
                rect = box
    w = 2
    rect.SetX(rect.GetX() + w/2)
    rect.SetY(rect.GetY() + w/2)
    rect.SetWidth(rect.GetWidth() - w)
    rect.SetHeight(rect.GetHeight() - w)
    return rect

def GetOtherBoard(brd):
    r = brd
    curbrd = pcbnew.GetBoard()
    s = curbrd.GetFileName()
    if not brd:
        brd = curbrd
    elif type(brd) == str:
        if os.path.exists(brd):
            brd = pcbnew.LoadBoard(brd)
        elif os.path.exists(s[0:s.rfind('/')] + '/' + brd):
            brd = pcbnew.LoadBoard(s[0:s.rfind('/')] + '/' + brd)
        else:
            return None
    else:
        return brd
    return brd
    
class BoardItems:
    '''  Class to hold all interest board items
         Use Collect method to get all board items
   
    '''
    def __init__(self):
        self.rb = RefBuilder()
        self.orgItems = []
        self.mods = []
        self.rect = None
    def ItemValid(self, item):
        ''' Check the item is in the rect or not'''
        return item.HitTest(self.rect, False)
    def Collect(self, brd = None, rect = None):
        ''' Collect board items in specify rect'''
        brd = GetOtherBoard(brd)
        #if not brd:
        #    brd = pcbnew.GetBoard()
        if not rect:
            rect = GetBoardBound(brd)
        self.rect = rect
        for mod in brd.GetModules():
            if self.ItemValid(mod):
                self.orgItems.append(mod)
                self.mods.append(mod)
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
    def ShowRect(self):
        r = '('
        r += str(self.rect.GetX()/1000000) + ','
        r += str(self.rect.GetY()/1000000) + ','
        r += str(self.rect.GetWidth()/1000000) + ','
        r += str(self.rect.GetHeight()/1000000) + ')'
        return r
    def MoveTo(self, pos):
        off = pcbnew.wxPoint( pos.x - self.rect.GetX(), pos.y - self.rect.GetY() )
        #print 'org is:', self.x, ',', self.y
        #print 'off is:', off
        for item in self.orgItems:
            item.Move(off)
        print 'Move item in ', self.ShowRect(), 'off = (', off.x/1000000, ',' ,off.y/1000000,')'
        self.rect.Move(off)
        print 'Result is ', self.ShowRect()
        
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
        self.brd = brd
    def HideValue(self, hide = True):
        for m in self.mods:
            if hide:
                m.Value().SetVisible(False)
            else:
                m.Value().SetVisible(True)

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
        attr_smd = pcbnew.PAD_SMD if hasattr(pcbnew,'PAD_SMD') else pcbnew.PAD_ATTRIB_SMD
        if pad.GetAttribute() != attr_smd:
            return False
    return True
def footPrintName(mod):
    fid = mod.GetFPID()
    f = fid.GetFootprintName().Cast_to_CChar() if hasattr(fid, 'GetFootprintName') else fid.GetLibItemName().Cast_to_CChar()
    return f

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
    out.writerow(['Comment','Description','Designator','Footprint','LibRef','Pins','Quantity','\xb1\xe0\xba\xc5'])

def IsModExclude(mod, ExcludeRefs = [], ExcludeValues = []):
    r = mod.GetReference()
    v = mod.GetValue()
    for pat in ExcludeRefs:
        if pat.match(r):
            return True
    for pat in ExcludeValues:
        if pat.match(v):
            return True
    return False
    
def GenBOM(brd = None, layer = pcbnew.F_Cu, type = 1, ExcludeRefs = [], ExcludeValues = []):
    if not brd:
        brd = pcbnew.GetBoard()
    bomList = {}
    for mod in brd.GetModules():
        needOutput = False
        if (mod.GetLayer() == layer) and (not IsModExclude(mod, ExcludeRefs, ExcludeValues)):
            needOutput = IsSMD(mod) == (type == 1)
        if needOutput:
            v = mod.GetValue()
            f = footPrintName(mod)
            r = mod.GetReference()
            vf = v + f
            if bomList.has_key(vf):
                bomList[vf].AddRef(r)
            else:
                bomList[vf] = BOMItem(r,f,v, mod.GetPadCount())
    print 'there are ', len(bomList), ' items at layer ', layer
    return sorted(bomList.values(), key = lambda item: item.refs[0])

def layerName(layerId):
    if layerId == pcbnew.F_Cu:
       return 'T'
    if layerId == pcbnew.B_Cu:
       return 'B'
    return 'X'
def toMM(v):
    return str(v/1000000.0) + 'mm'
class POSItem:
    def __init__(self, mod, offx = 0, offy = 0):
        self.MidX = toMM(mod.GetPosition().x-offx)
        self.MidY = toMM(offy - mod.GetPosition().y)
        self.RefX = toMM(mod.GetPosition().x-offx)
        self.RefY = toMM(offy - mod.GetPosition().y)
        pad = GetPad1(mod)
        if pad:
            self.PadX = toMM(pad.GetPosition().x-offx)
            self.PadY = toMM(offy - pad.GetPosition().y)
        else:
            print 'Pad1 not found for mod'
            self.PadX = self.MidX
            self.PadY = self.MidY
        self.rot = int(mod.GetOrientation()/10)
        self.ref = mod.GetReference()
        self.val = mod.GetValue()
        self.layer = layerName(mod.GetLayer())
        self.fp = footPrintName(mod)
    def Output(self, out = None):
        if not out:
            out = csv.writer(sys.stdout, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_ALL)
        out.writerow([self.ref, self.fp, str(self.MidX), str(self.MidY),
                     str(self.RefX), str(self.RefY), str(self.PadX), str(self.PadY),
                     self.layer, str(self.rot), self.val])

def GenPos(brd = None, layer = pcbnew.F_Cu, type = 1, ExcludeRefs = [], ExcludeValues = []):
    if not brd:
        brd = pcbnew.GetBoard()
    posList = []
    pt_org = brd.GetAuxOrigin()
    for mod in brd.GetModules():
        needOutput = False
        if (mod.GetLayer() == layer) and (not IsModExclude(mod, ExcludeRefs, ExcludeValues)):
            needOutput = IsSMD(mod) == (type == 1)
        if needOutput:
            posList.append(POSItem(mod, pt_org.x, pt_org.y))
    posList = sorted(posList, key = lambda item: item.ref)
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
def CollectItemByName(filename = None):
    try:
        brd = pcbnew.LoadBoard(filename)
    except IOError:
        print 'Can not open ', filename
        filename = os.path.split(pcbnew.GetBoard().GetFileName())[0] + '\\' + filename
        print 'Try to open ', filename
    try:
        brd = pcbnew.LoadBoard(filename)
    except IOError:
        print 'Can not open ', filename
        return None
    bi = BoardItems()
    bi.Collect(brd)
    return bi

def CollectItem(brd = None):
    if not brd:
        brd = pcbnew.GetBoard()
    bi = BoardItems()
    bi.Collect(brd)
    return bi
    
def CopyItemTo(boardItem, x, y):
    newBI = boardItem.Clone()
    newBI.MoveToMM(x, y)
    return newBI

def MirrorItemTo(boardItem, x, y):
    newBI = boardItem.Clone()
    newBI.MoveToMM(x, y)
    newBI.Mirror()
    return newBI
    
def OpenCSV(fileName):
    try:
        f = open(fileName, 'w+')
    except IOError:
        e = "Can't open output file for writing: " + fileName
        print( __file__, ":", e, sys.stderr )
        f = sys.stdout
    out = csv.writer( f, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_MINIMAL )
    return out

def PreCompilePattenList(pattenList):
    res = []
    for pat in pattenList:
        res.append(re.compile(pat))
    return res
    
def GenMFDoc(SplitTopAndBottom = False, ExcludeRef = [], ExcludeValue = [], brd = None):
    if not brd:
        brd = pcbnew.GetBoard()
    bound = GetBoardBound(brd)
    org_pt = pcbnew.wxPoint( bound.GetLeft(), bound.GetBottom())
    brd.SetAuxOrigin(org_pt)
    print "set board aux origin to left bottom point, at", org_pt
    fName = brd.GetFileName()
    path = os.path.split(fName)[0]
    fName = os.path.split(fName)[1]
    bomName = fName.rsplit('.',1)[0]
    
    excludeRefs = PreCompilePattenList(ExcludeRef)
    excludeValues = PreCompilePattenList(ExcludeValue)

    bomSMDTop = GenBOM(brd, pcbnew.F_Cu, 1, excludeRefs, excludeValues)
    bomHoleTop = GenBOM(brd, pcbnew.F_Cu, 0, excludeRefs, excludeValues)
    
    bomSMDBot = GenBOM(brd, pcbnew.B_Cu, 1, excludeRefs, excludeValues)
    bomHoleBot = GenBOM(brd, pcbnew.B_Cu, 0, excludeRefs, excludeValues)
    
    posSMDTop = GenPos(brd, pcbnew.F_Cu, 1, excludeRefs, excludeValues)
    posHoleTop = GenPos(brd, pcbnew.F_Cu, 0, excludeRefs, excludeValues)
    
    posSMDBot = GenPos(brd, pcbnew.B_Cu, 1, excludeRefs, excludeValues)
    posHoleBot = GenPos(brd, pcbnew.B_Cu, 0, excludeRefs, excludeValues)
    
    if SplitTopAndBottom:
        fName = bomName
        bomName = path + '/' + fName + '_BOM_TOP.csv'
        posName = path + '/' + fName + '_POS_TOP.csv'
        # Generate BOM for Top layer
        print 'Genertate BOM file ', bomName
        csv = OpenCSV(bomName)
        OutputBOMHeader(csv)
        for v in bomSMDTop:
           v.Output(csv)
        if len(bomHoleTop)>0:
            csv.writerow(['Through Hole Items '])
            for v in bomHoleTop:
                v.Output(csv)
        
        # Generate POS for Top layer
        print 'Genertate POS file ', posName
        csv = OpenCSV(posName)
        OutputPosHeader(csv)
        for v in posSMDTop:
           v.Output(csv)
        if len(posHoleTop)>0:
            csv.writerow(['Through Hole Items '])
            for v in posHoleTop:
               v.Output(csv)
           
        bomName = path + '/' + fName + '_BOM_BOT.csv'
        posName = path + '/' + fName + '_POS_BOT.csv'
        # Generate BOM for Bottom layer
        print 'Genertate BOM file ', bomName
        csv = OpenCSV(bomName)
        OutputBOMHeader(csv)
        for  v in bomSMDBot:
           v.Output(csv)
        if len(bomHoleBot)>0:
            csv.writerow(['Through Hole Items '])
            for v in bomHoleBot:
               v.Output(csv)
        # Generate POS for Bottom layer   
        print 'Genertate POS file ', posName
        csv = OpenCSV(posName)
        OutputPosHeader(csv)        
        for v in posSMDBot:
           v.Output(csv)
        if len(posHoleBot)>0:
            csv.writerow(['Through Hole Items '])
            for v in posHoleBot:
               v.Output(csv)
        
    else:
        posName = path + '/' + bomName + '_POS.csv'
        bomName = path + '/' + bomName + '_BOM.csv'
        # Generate BOM for both layer
        print 'Genertate BOM file ', bomName
        csv = OpenCSV(bomName)
        OutputBOMHeader(csv)
        for v in bomSMDTop:
           v.Output(csv)
           
        for  v in bomSMDBot:
           v.Output(csv)
        if len(bomHoleTop)+len(bomHoleBot)>0:
            csv.writerow(['Through Hole Items '])
            for v in bomHoleTop:
               v.Output(csv)
               
            for v in bomHoleBot:
               v.Output(csv)
        
        
        # Generate POS for both layer
        print 'Genertate POS file ', posName
    
        csv = OpenCSV(posName)
        OutputPosHeader(csv)
        for v in posSMDTop:
           v.Output(csv)
           
        for v in posSMDBot:
           v.Output(csv)
        if len(posHoleTop)+len(posHoleBot)>0:
            csv.writerow(['Through Hole Items '])
            for v in posHoleTop:
               v.Output(csv)
               
            for v in posHoleBot:
               v.Output(csv)

def version():
    print "1.1"
    
    
    
    
    
    
    
    
    
    
    
    