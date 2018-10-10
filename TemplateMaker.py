#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-

import os
import os.path
from os import listdir
# import sys
import uuid
import re
import tempfile
from subprocess import check_output
import shutil

from lxml import etree
import string

import Tkinter as tk
import tkFileDialog

from ConfigParser import *

GUID_REGEX = "[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}"
ID = ''
LISTBOX_SEPARATOR = '--------'
AC_18   = 28

app = None

dest_dict = {}
replacement_dict = {}
id_dict = {}
pict_dict = {}
source_pict_dict = {}

class CreateToolTip():
    def __init__(self, widget, text='widget info'):
        self.waittime = 500
        self.wraplength = 180
        self.widget = widget
        self.text = text

        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffff", relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()


class Replacement:
    def __init__(self, inR, inO):
        self.replaceString = inR

        # self.replace_with = re.sub(args[1], args[2], inR, flags=re.IGNORECASE)
        self.orig_uuid = inO
        self.new_uuid = re.sub(GUID_REGEX, str(uuid.uuid4()).upper(), inO, count=1)


class Pict_replacement:
    def __init__(self, inOriginalName, inTargetName):
        self.originalName = inOriginalName
        self.targetName = inTargetName


#------------------- GUI------------------------------
#------------------- GUI------------------------------
#------------------- GUI------------------------------

#-------------------data classes----------------------------------------------------------------------------------------

class GeneralFile:
    def __init__(self, fullPath, basePath):
        self.fullPath = fullPath
        self.path = os.path.dirname(fullPath)
        self.name = os.path.splitext(os.path.basename(fullPath))[0]
        self.ext = os.path.splitext(os.path.basename(fullPath))[1]
        try:
            self.relPath = os.path.normpath(os.path.relpath(self.path, basePath))
        except ValueError:
            pass

    def refreshFileNames(self):
        self.fullPath = self.path + "\\" + self.name + self.ext

    def __lt__(self, other):
        return self.name < other.name


class DestImage(GeneralFile):
    sourceFileName      = ""
    ext                 = ""
    fileNameWithExt     = ""
    fileNameWithOutExt  = ""
    sourceFile          = None  #reference

    #TODO TargetImageDirName is ok for images?

    def __init__(self, sourceFile, stringFrom, stringTo):
        GeneralFile.__init__(self, sourceFile.fullPath, TargetImageDirName.get())
        self.sourceFile = sourceFile
        self.path = TargetImageDirName.get() + "\\" + self.sourceFile.relPath
        self.GDLFullpath = TargetGDLDirName.get() + "\\" + self.sourceFile.relPath
        self.XMLFullpath = TargetXMLDirName.get() + "\\" + self.sourceFile.relPath
        self.sourceFileName = sourceFile.name
        self.name = re.sub(stringFrom, stringTo, sourceFile.name, flags=re.IGNORECASE)
        self.fileNameWithOutExt = os.path.splitext(os.path.basename(self.name))[0]
        self.ext = self.sourceFile.ext
        if stringTo not in self.name and bAddStr.get():
            self.fileNameWithOutExt += stringTo
            self.name = self.fileNameWithOutExt + self.ext
        self.fileNameWithExt = self.name
        self.fullPath = self.path + "\\" + self.fileNameWithExt



    def refreshFileNames(self):
        self.fullPath = self.path + "\\" + self.fileNameWithExt


class SourceImage(GeneralFile):
    def __init__(self, sourceFile):
        GeneralFile.__init__(self, sourceFile, SourceDirName.get())
        self.ext = os.path.splitext(os.path.basename(sourceFile))[1]
        self.fileNameWithExt = self.name + self.ext
        # self.fileNameWithOutExt = self.name
        self.fileNameWithOutExt = os.path.splitext(os.path.basename(sourceFile))[0]
        self.name = self.fileNameWithExt


class XMLFile(GeneralFile):
    ext         = ".xml"
    guid        = ""
    iVersion    = 0
    ID          = ""

    def __lt__(self, other):
        if self.bPlaceable and not other.bPlaceable:
            return True
        if not self.bPlaceable and other.bPlaceable:
            return False
        return self.name < other.name


class SourceXML (XMLFile, GeneralFile):
    destName    = ""    #driven by DestFile and if there are more DestFiles, not stable, sometimes overwritten

    def __init__(self, fileName):
        GeneralFile.__init__(self, fileName, SourceDirName.get())

        mroot = etree.parse(fileName)
        self.iVersion = mroot.getroot().attrib['Version']

        global ID
        if int(self.iVersion) <= AC_18:
            ID = 'UNID'
            self.ID = 'UNID'
        else:
            ID = 'MainGUID'
            self.ID = 'MainGUID'
        self.guid = mroot.getroot().attrib[ID]

        if mroot.getroot().attrib['IsPlaceable'] == 'no':
            self.bPlaceable = False
        else:
            self.bPlaceable = True


class DestXML (XMLFile, GeneralFile):
    # tags            = []      #FIXME

    def __init__(self, sourceFile, stringFrom = "", stringTo = "", ):
        self.warnings = []
        self.name           = re.sub(stringFrom, stringTo, sourceFile.name, flags=re.IGNORECASE)
        if stringTo not in self.name and bAddStr.get():
            self.name += stringTo
        if self.name.upper() in dest_dict:
            i = 1
            while self.name.upper() + "_" + str(i) in dest_dict.keys():
                i += 1
            self.name += "_" + str(i)
            self.guid = str(uuid.uuid4()).upper()

            if "XML Target file exists!" in self.warnings:
                self.warnings.remove("XML Target file exists!")
                self.refreshFileNames()

        self.sourceFile     = sourceFile
        self.sourceFileName = sourceFile.name
        self.path           = os.path.normpath(TargetXMLDirName.get() + "\\" + os.path.relpath(sourceFile.path, SourceDirName.get()))
        self.fullPath       = self.path + "\\" + self.name + self.ext
        self.guid           = str(uuid.uuid4()).upper()
        self.bPlaceable     = sourceFile.bPlaceable
        self.iVersion       = sourceFile.iVersion
        self.sourceFile.destName = os.path.splitext(self.name)[0]
        self.proDatURL = ''
        self.bOverWrite = False
        self.bRetainCalledMacros    = False
        self.retainedCalledMacros  = {}

        if os.path.isfile(self.fullPath):
            if bOverWrite.get():
                self.bOverWrite             = True
                self.bRetainCalledMacros    = True
                mdp = etree.parse(self.fullPath, etree.XMLParser(strip_cdata=False))
                self.iVersion = mdp.getroot().attrib['Version']
                if self.iVersion >= AC_18:
                    self.ID = "MainGUID"
                else:
                    self.ID = "UNID"
                self.guid = mdp.getroot().attrib[self.ID]
                print mdp.getroot().attrib[self.ID]
                #FIXME getting calledmacros' guids

                for m in mdp.findall("./CalledMacros/Macro"):
                    cM = m.find(self.ID).text
                    self.retainedCalledMacros[cM] = string.strip(m.find("MName").text, "'" + '"')
            else:
                self.warnings += ["XML Target file exists!"]
                #FIXME check for GDL, too

        if self.iVersion >= AC_18:
            # AC18 and over: adding licensing statically
            self.author         = "BIMobject"
            self.license        = "CC BY-ND"
            self.licneseVersion = "3.0"

        if self.sourceFile.guid.upper() in id_dict:
            if id_dict[self.sourceFile.guid.upper()] == "":
                id_dict[self.sourceFile.guid.upper()] = self.guid.upper()

#-----------------gui classes-------------------------------------------------------------------------------------------

class InputDirPlusText():
    listBox = None

    def __init__(self, top, text, target, tooltip=''):
        self.target = target
        self.filename = ''

        top.columnconfigure(1, weight=1)

        self.buttonDirName = tk.Button(top, {"text": text, "command": self.inputDirName, })
        self.buttonDirName.grid({"sticky": tk.W + tk.E, "row": 0, "column": 0, })

        self.entryDirName = tk.Entry(top, {"width": 30, "textvariable": target})
        self.entryDirName.grid({"row": 0, "column": 1, "sticky": tk.E + tk.W, })

        if tooltip:
            CreateToolTip(self.entryDirName, tooltip)

    def inputDirName(self):
        self.filename = tkFileDialog.askdirectory(initialdir="/", title="Select folder")
        self.target.set(self.filename)
        self.entryDirName.delete(0, tk.END)
        self.entryDirName.insert(0, self.filename)

class InputDirPlusBool(InputDirPlusText):
    def __init__(self, top, text, target, var, tooltip=''):
        top.columnconfigure(1, weight=1)

        self.checkbox = tk.Checkbutton(top, {"variable": var})
        self.checkbox.grid({"sticky": tk.W, "row": 0, "column": 0})

        self.frame = tk.Frame(top)
        self.frame.grid({"row": 0, "column": 1, "sticky": tk.E + tk.W})

        self.idpt = InputDirPlusText(self.frame, text, target, tooltip)

class InputWithListBox():
    def __init__(self, top, row, column, text, target, replaceText, callback=None):
        self.target = target

        self.frame = tk.Frame(top)
        self.frame.grid({"row": row, "column": column})
        # self.frame.grid_columnconfigure(0, weight=1)


        self.inDirFrame = tk.Frame(self.frame)
        self.inDirFrame.grid({"row": 0, "column": 0, "sticky": tk.W + tk.E, })
        self.inDirFrame.grid_columnconfigure(1, weight=1)

        InputDirPlusText(self.inDirFrame, text, target, replaceText, )

        self.listBoxFrame = tk.Frame(self.frame)
        self.listBoxFrame.grid({"row": 1, "column": 0, "sticky": tk.E + tk.W})
        self.listBoxFrame.grid_columnconfigure(0, weight=1)

        self.listBox = tk.Listbox(self.listBoxFrame)
        self.listBox.grid({"row": 0, "column": 0, "sticky": tk.E + tk.W})

        if callback:
            self.listBox.bind("<<ListboxSelect>>", callback)

        self.ListBoxScrollbar = tk.Scrollbar(self.listBoxFrame)
        self.ListBoxScrollbar.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox.config(yscrollcommand=self.ListBoxScrollbar.set)
        self.ListBoxScrollbar.config(command=self.listBox.yview)

class ListboxWithRefresh(tk.Listbox):
    def __init__(self, top, dict_):
        if "target" in dict_:
            self.target = dict_["target"]
            del dict_["target"]
        if "dict" in dict_:
            self.dict = dict_["dict"]
            del dict_["dict"]
        tk.Listbox.__init__(self, top, dict_)

    def refresh(self, *_):

            if self.dict == replacement_dict:
                FC1(self.target.get())
            self.delete(0, tk.END)
            bPlaceablesFromHere = True
            if self.dict in (pict_dict, source_pict_dict):
                bPlaceablesFromHere = False
            for f in sorted([self.dict[k] for k in self.dict.keys()]):
                try:
                    if not f.bPlaceable and bPlaceablesFromHere:
                        self.insert(tk.END, LISTBOX_SEPARATOR)
                        bPlaceablesFromHere = False
                    if f.warnings:
                        self.insert(tk.END, "* " + f.name)
                    else:
                        self.insert(tk.END, f.name)
                except AttributeError:
                    self.insert(tk.END, f.name)



class GUIApp(tk.Frame):
    def __init__(self):
        tk.Frame.__init__(self)
        self.top = self.winfo_toplevel()

        currentConfig = ConfigParser()
        currentConfig.read("TemplateMarker.ini")    #TODO into a different class or stg

        self.SourceDirName      = tk.StringVar()
        self.TargetXMLDirName   = tk.StringVar()
        self.TargetGDLDirName   = tk.StringVar()
        self.SourceImageDirName = tk.StringVar()
        self.TargetImageDirName = tk.StringVar()
        self.AdditionalImageDir = tk.StringVar()

        self.ImgStringFrom      = tk.StringVar()
        self.ImgStringTo        = tk.StringVar()

        self.StringFrom         = tk.StringVar()
        self.StringTo           = tk.StringVar()

        self.fileName           = tk.StringVar()
        self.proDatURL          = tk.StringVar()
        self.DestItem           = None

        self.ACLocation         = tk.StringVar()

        self.bDebug             = tk.BooleanVar()
        self.bOverWrite         = tk.BooleanVar()
        self.bAddStr            = tk.BooleanVar()

        self.bXML               = tk.BooleanVar()
        self.bGDL               = tk.BooleanVar()

        self.observer  = None
        self.observer2 = None

        self.warnings = []

        global \
            SourceDirName, TargetXMLDirName, TargetGDLDirName, SourceImageDirName, TargetImageDirName, \
            AdditionalImageDir, bDebug, ACLocation, bGDL, bXML, dest_dict, replacement_dict, id_dict, \
            pict_dict, source_pict_dict, bAddStr, bOverWrite

        SourceDirName       = self.SourceDirName
        TargetXMLDirName    = self.TargetXMLDirName
        TargetGDLDirName    = self.TargetGDLDirName
        SourceImageDirName  = self.SourceImageDirName
        TargetImageDirName  = self.TargetImageDirName
        AdditionalImageDir  = self.AdditionalImageDir
        bDebug              = self.bDebug
        bXML                = self.bXML
        bGDL                = self.bGDL
        ACLocation          = self.ACLocation
        bAddStr             = self.bAddStr
        bOverWrite          = self.bOverWrite

        __tooltipIDPT1 = "Something like E:/_GDL_SVN/_TEMPLATE_/AC18_Opening/library"
        __tooltipIDPT2 = "Images' dir that are NOT to be renamed per project and compiled into final gdls (prev pics, for example), something like E:\_GDL_SVN\_TEMPLATE_\AC18_Opening\library_images"
        __tooltipIDPT3 = ""
        __tooltipIDPT4 = "Final GDL output dir"
        __tooltipIDPT5 = "If set, copy project specific pictures here, too"
        __tooltipIDPT6 = "Additional images' dir, for all other images, which can be used by any projects, something like E:/_GDL_SVN/_IMAGES_GENERIC_"

        try:
            self.bGDL.set(currentConfig.get ('ArchiCAD', 'bGDL'))
            self.bXML.set(currentConfig.get ('ArchiCAD', 'bXML'))
            self.bDebug.set(currentConfig.getboolean('ArchiCAD', 'bDebug'))
            self.AdditionalImageDir.set(currentConfig.get("ArchiCAD", "AdditionalImageDir"))
            self.ACLocation.set(currentConfig.get("ArchiCAD", "ACLocation"))
            self.StringTo.set(currentConfig.get ('ArchiCAD', 'StringTo'))
            self.StringFrom.set(currentConfig.get ('ArchiCAD', 'StringFrom'))
            self.SourceImageDirName.set(currentConfig.get ('ArchiCAD', 'inputimagesource'))
            self.TargetImageDirName.set(currentConfig.get ('ArchiCAD', 'inputimagetarget'))
            self.ImgStringFrom.set(currentConfig.get ('ArchiCAD', 'ImgStringFrom'))
            self.ImgStringTo.set(currentConfig.get ('ArchiCAD', 'ImgStringTo'))
            self.SourceDirName.set(currentConfig.get("ArchiCAD", "SourceDirName"))

            self.TargetXMLDirName.set(currentConfig.get("ArchiCAD", "XMLTargetDirName"))
            self.TargetGDLDirName.set(currentConfig.get("ArchiCAD", "GDLTargetDirName"))
            # self.bDebug = currentConfig.getboolean('ArchiCAD', 'bDebug')
        except NoOptionError:
            print "NoOptionError"
        except NoSectionError:
            print "NoSectionError"
        except ValueError:
            print "ValueError"

        self.observerXML = self.bXML.trace_variable("w", self.XMLModified)
        self.observerGDL = self.bGDL.trace_variable("w", self.GDLModified)

        self.warnings = []

        #GUI itself-----------------------------------------------------------------------------------------------------

        # ----input side--------------------------------

        self.top.columnconfigure(0, weight=1)
        self.top.columnconfigure(2, weight=1)
        self.top.rowconfigure(0, weight=1)

        self.inputFrame = tk.Frame(self.top)
        self.inputFrame.grid({"row": 0, "column": 0, "sticky": tk.NW + tk.SE})
        self.inputFrame.columnconfigure(0, weight=1)
        self.inputFrame.grid_rowconfigure(2, weight=1)
        self.inputFrame.grid_rowconfigure(4, weight=1)

        self.InputFrameS = [tk.Frame(self.inputFrame) for _ in range (5)]
        for f, r, cc in zip(self.InputFrameS, range(5), [0, 1, 0, 1, 0]):
            f.grid({"row": r, "column": 0, "sticky": tk.N + tk.S + tk.E + tk.W, })
            self.InputFrameS[r].grid_columnconfigure(cc, weight=1)
            self.InputFrameS[r].rowconfigure(0, weight=1)

        iF = 0

        self.entryTextNameFrom = tk.Entry(self.InputFrameS[iF], {"width": 20, "textvariable": self.StringFrom, })
        self.entryTextNameFrom.grid({"column": 0, "sticky": tk.SE + tk.NW, })

        self.entryTextNameTo = tk.Entry(self.InputFrameS[iF], {"width": 20, "textvariable": self.StringTo, })
        self.entryTextNameTo.grid({"row":0, "column": 1, "sticky": tk.SE + tk.NW, })

        iF += 1

        InputDirPlusText(self.InputFrameS[iF], "Source folder", self.SourceDirName, __tooltipIDPT1)

        iF += 1

        self.listBox = ListboxWithRefresh(self.InputFrameS[iF], {"target": self.SourceDirName, "dict": replacement_dict})
        self.listBox.grid({"row": 0, "column": 0, "sticky": tk.E + tk.W + tk.N + tk.S})
        self.observerLB1 = self.SourceDirName.trace_variable("w", self.listBox.refresh)

        self.ListBoxScrollbar = tk.Scrollbar(self.InputFrameS[iF])
        self.ListBoxScrollbar.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox.config(yscrollcommand=self.ListBoxScrollbar.set)
        self.ListBoxScrollbar.config(command=self.listBox.yview)

        iF += 1

        InputDirPlusText(self.InputFrameS[iF], "Images' source folder",  self.SourceImageDirName, __tooltipIDPT2)

        iF += 1

        self.listBox2 = ListboxWithRefresh(self.InputFrameS[iF], {"target": self.SourceDirName, "dict": source_pict_dict})
        self.listBox2.grid({"row": 0, "column": 0, "sticky": tk.NE + tk.SW})
        self.observerLB2 = self.SourceDirName.trace_variable("w", self.listBox2.refresh)

        self.ListBoxScrollbar2 = tk.Scrollbar(self.InputFrameS[iF])
        self.ListBoxScrollbar2.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox2.config(yscrollcommand=self.ListBoxScrollbar2.set)
        self.ListBoxScrollbar2.config(command=self.listBox2.yview)

        #----output side--------------------------------

        self.outputFrame = tk.Frame(self.top)
        self.outputFrame.grid({"row": 0, "column": 2, "sticky": tk.NE + tk.SW})
        self.outputFrame.columnconfigure(0, weight=1)
        self.outputFrame.grid_rowconfigure(2, weight=1)
        self.outputFrame.grid_rowconfigure(4, weight=1)

        self.outputFrameS = [tk.Frame(self.outputFrame) for _ in range (5)]
        for f, r, cc in zip(self.outputFrameS, range(5), [1, 1, 0, 1, 0]):
            f.grid({"row": r, "column": 0, "sticky": tk.SW + tk.NE, })
            self.outputFrameS[r].grid_columnconfigure(cc, weight=1)
            self.outputFrameS[r].rowconfigure(0, weight=1)


        self.XMLDir = InputDirPlusBool(self.outputFrameS[0], "XML Destination folder",      self.TargetXMLDirName, self.bXML, __tooltipIDPT3)
        self.GDLDir = InputDirPlusBool(self.outputFrameS[1], "GDL Destination folder",      self.TargetGDLDirName, self.bGDL, __tooltipIDPT4)
        InputDirPlusText(self.outputFrameS[3], "Images' destination folder",  self.TargetImageDirName, __tooltipIDPT5)

        self.listBox3 = ListboxWithRefresh(self.outputFrameS[2], {'dict': dest_dict})
        self.listBox3.grid({"row": 0, "column": 0, "sticky": tk.SE + tk.NW})

        self.ListBoxScrollbar3 = tk.Scrollbar(self.outputFrameS[2])
        self.ListBoxScrollbar3.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox3.config(yscrollcommand=self.ListBoxScrollbar3.set)
        self.ListBoxScrollbar3.config(command=self.listBox3.yview)

        self.listBox3.bind("<<ListboxSelect>>", self.listboxselect)


        self.listBox4 = ListboxWithRefresh(self.outputFrameS[4], {'dict': pict_dict})
        self.listBox4.grid({"row": 0, "column": 0, "sticky": tk.SE + tk.NW})

        self.ListBoxScrollbar4 = tk.Scrollbar(self.outputFrameS[4])
        self.ListBoxScrollbar4.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox4.config(yscrollcommand=self.ListBoxScrollbar4.set)
        self.ListBoxScrollbar4.config(command=self.listBox4.yview)
        self.listBox4.bind("<<ListboxSelect>>", self.listboxImageSelect)

        #------------------------------------
        #bottom row for project general settings
        #------------------------------------

        self.bottomFrame        = tk.Frame(self.top, )
        self.bottomFrame.grid({"row":1, "column": 0, "columnspan": 7, "sticky":  tk.S + tk.N, })

        self.buttonACLoc = tk.Button(self.bottomFrame, {"text": "ArchiCAD location", "command": self.setACLoc, })
        self.buttonACLoc.grid({"row": 0, "column": 0, })

        self.ACLocEntry                 = tk.Entry(self.bottomFrame, {"width": 40, "textvariable": self.ACLocation, })
        self.ACLocEntry.grid({"row": 0, "column": 1})

        self.buttonAID = tk.Button(self.bottomFrame, {"text": "Additional images' folder", "command": self.setAdditionalImageDir, })
        self.buttonAID.grid({"row": 0, "column": 2, })

        self.AdditionalImageDirEntry    = tk.Entry(self.bottomFrame, {"width": 40, "textvariable": self.AdditionalImageDir, })
        self.AdditionalImageDirEntry.grid({"row": 0, "column": 3})

        self.debugCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Debug", "variable": self.bDebug})
        self.debugCheckButton.grid({"row": 0, "column": 4})

        self.bAddStrCheckButton = tk.Checkbutton(self.bottomFrame, {"text": "Always add strings", "variable": self.bAddStr})
        self.bAddStrCheckButton.grid({"row": 0, "column": 5})

        self.OverWriteCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Overwrite", "variable": self.bOverWrite})
        self.OverWriteCheckButton.grid({"row": 0, "column": 6})

        self.startButton        = tk.Button(self.bottomFrame, {"text": "Start", "command": self.start})
        self.startButton.grid({"row": 0, "column": 7, "sticky": tk.E})

        # ----buttons---------------------------------------------------------------------------------------------------

        self.buttonFrame        = tk.Frame(self.top)
        self.buttonFrame.grid({"row": 0, "column": 1})

        self.addAllButton       = tk.Button(self.buttonFrame, {"text": ">>", "command": self.addAllFiles})
        self.addAllButton.grid({"row":0, "column": 0})

        self.addButton          = tk.Button(self.buttonFrame, {"text": ">", "command": self.addFile})
        self.addButton.grid({"row":1, "column": 0, "sticky": tk.W + tk.E})

        self.delButton          = tk.Button(self.buttonFrame, {"text": "X", "command": self.delFile})
        self.delButton.grid({"row":2, "column": 0, "sticky": tk.W + tk.E})

        self.resetButton         = tk.Button(self.buttonFrame, {"text": "Reset", "command": self.resetAll })
        self.resetButton.grid({"row": 3, "sticky": tk.W + tk.E})

        # ----properties------------------------------------------------------------------------------------------------

        self.propertyFrame      = tk.Frame(self.top)
        self.propertyFrame.grid({"row": 0, "column": 3, "rowspan": 3, "sticky": tk.N})

        iNameW      = 10
        iCurRow     = 0

        tk.Label(self.propertyFrame, {"width": iNameW, "text": "Name"}).grid({"row": iCurRow, "column": 0})
        self.fileNameEntry      = tk.Entry(self.propertyFrame, {"width": 60, "textvariable": self.fileName})
        self.fileNameEntry.grid({"row": iCurRow, "column": 1})

        iCurRow += 1

        tk.Label(self.propertyFrame, {"width": iNameW, "text": "GUID"}).grid({"row": iCurRow, "column": 0})
        self.guidEntry          = tk.Entry(self.propertyFrame, {"state": tk.DISABLED, })
        self.guidEntry.grid({"row": iCurRow, "column": 1, "sticky": tk.W + tk.E, })

        iCurRow += 1

        tk.Label(self.propertyFrame, {"width": iNameW, "text": "Version"}).grid({"row": iCurRow, "column": 0})
        self.versionEntry       = tk.Entry(self.propertyFrame, {"width": 3, "state": tk.DISABLED})
        self.versionEntry.grid({"row": iCurRow, "column": 1, })

        iCurRow += 1

        tk.Label(self.propertyFrame, {"width": iNameW, "text": "prodatURL"}).grid({"row": iCurRow, "column": 0})
        self.proDatURLEntry     = tk.Entry(self.propertyFrame, {"textvariable": self.proDatURL})
        self.proDatURLEntry.grid({"row": iCurRow, "column": 1, "sticky": tk.W + tk.E, })

        iCurRow += 1

        tk.Label(self.propertyFrame, {"width": iNameW, "text": "Author"}).grid({"row": iCurRow, "column": 0})
        self.authorEntry = tk.Entry(self.propertyFrame, {})
        self.authorEntry.grid({"row": iCurRow, "column": 1, "sticky": tk.W + tk.E, })

        iCurRow += 1

        tk.Label(self.propertyFrame, {"width": iNameW, "text": "License"}).grid({"row": iCurRow, "column": 0})
        self.licenseFrame      = tk.Frame(self.propertyFrame)
        self.licenseFrame.grid({"row": iCurRow, "column": 1, })

        self.licenseEntry = tk.Entry(self.licenseFrame, {"width": 17, })
        self.licenseEntry.grid({"column": 0, "row": 0, })

        tk.Label(self.licenseFrame, {"width": 4, "text": "Ver."}).grid({"row": 0, "column": 1})
        self.licenseVersionEntry = tk.Entry(self.licenseFrame, {"width": 17, })
        self.licenseVersionEntry.grid({"column": 2, "row": 0, })

        iCurRow += 1

        tk.Label(self.propertyFrame, {"text": "Warnings:"}).grid({"row": iCurRow, "column": 0, "sticky": tk.N})
        self.warningFrame      = tk.Frame(self.propertyFrame)
        self.warningFrame.grid({"row": iCurRow, "column": 1, "sticky": tk.W})


        #FIXME to put in projectname field

        CreateToolTip(self.entryTextNameFrom, "FromSting: WARNING: this is Regex")
        CreateToolTip(self.entryTextNameTo, "If 'Always add strings' is set add to the end of every file if FromSting cannot be replaced, if not, only replace FromSting Regex pattern")
        CreateToolTip(self.AdditionalImageDirEntry, __tooltipIDPT6)
        CreateToolTip(self.AdditionalImageDirEntry, __tooltipIDPT6)


    def setACLoc(self):
        ACLoc = tkFileDialog.askdirectory(initialdir="/", title="Select ArchiCAD folder")
        self.ACLocation.set(ACLoc)

    def setAdditionalImageDir(self):
        AIDLoc = tkFileDialog.askdirectory(initialdir="/", title="Select additional images' folder")
        self.AdditionalImageDir.set(AIDLoc)

    def GDLModified(self, *_):
        if not self.bGDL.get():
            self.bXML.set(True)
            self.GDLDir.idpt.entryDirName.config(state=tk.DISABLED)
        else:   self.GDLDir.idpt.entryDirName.config(state=tk.NORMAL)

    def XMLModified(self, *_):
        if not self.bXML.get():
            self.bGDL.set(True)
            self.XMLDir.idpt.entryDirName.config(state=tk.DISABLED)
        else:   self.XMLDir.idpt.entryDirName.config(state=tk.NORMAL)

    def start(self):
        main2()
        print "Start"
        #TODO starting conversion

    def addFile(self, fileName=''):
        if not fileName:
            fileName = self.listBox.get(tk.ACTIVE)
        if fileName == LISTBOX_SEPARATOR:
            self.listBox.select_clear(tk.ACTIVE)
            return
        destItem = DestXML(replacement_dict[fileName.upper()], self.StringFrom.get(), self.StringTo.get())
        dest_dict[destItem.name.upper()] = destItem
        self.refreshDestItem()

    def addImageFile(self, fileName=''):
        if not fileName:
            fileName = self.listBox2.get(tk.ACTIVE)
        if not fileName.upper() in pict_dict and fileName != LISTBOX_SEPARATOR:
            destItem = DestImage(source_pict_dict[fileName.upper()], self.StringFrom.get(), self.StringTo.get())
            pict_dict[destItem.fileNameWithExt.upper()] = destItem
        self.refreshDestItem()

    def addAllFiles(self):
        for filename in self.listBox.get(0, tk.END):
            self.addFile(filename)

        for imageFileName in self.listBox2.get(0, tk.END):
            self.addImageFile(imageFileName)

        self.addAllButton.config({"state": tk.DISABLED})

    def delFile(self, fileName = ''):
        if not fileName:
            fileName = self.listBox3.get(tk.ACTIVE)
        if fileName == LISTBOX_SEPARATOR:
            self.listBox3.select_clear(tk.ACTIVE)
            return
        del dest_dict[fileName.upper()]
        self.listBox3.refresh()
        if not dest_dict and not pict_dict:
            self.addAllButton.config({"state": tk.NORMAL})
        self.fileName.set('')

    def resetAll(self):
        dest_dict.clear()
        replacement_dict.clear()
        id_dict.clear()
        pict_dict.clear()
        source_pict_dict.clear()

        self.listBox.refresh()
        self.listBox2.refresh()
        self.listBox3.refresh()
        self.listBox4.refresh()

        for w in self.warnings:
            w.destroy()

        self.addAllButton.config({"state": tk.NORMAL})

    def listboxselect(self, event, ):
        if not event.widget.get(0):
            return
        if event.widget.get(event.widget.curselection()[0]) == LISTBOX_SEPARATOR:
            return

        currentSelection = event.widget.get(int(event.widget.curselection()[0])).upper()
        if currentSelection[:2] == "* ":
            currentSelection = currentSelection[2:]
        self.destItem = dest_dict[currentSelection]
        self.selectedName = currentSelection

        if self.observer:
            self.fileName.trace_vdelete("w", self.observer)
        if self.observer2:
            self.proDatURL.trace_vdelete("w", self.observer2)

        self.fileName.set(self.destItem.name)
        self.observer = self.fileName.trace_variable("w", self.modifyDestItem)

        self.proDatURL.set(self.destItem.proDatURL)
        self.observer2 = self.proDatURL.trace_variable("w", self.modifyDestItemdata)

        self.guidEntry.config({"state": tk.NORMAL})
        self.guidEntry.delete(0, tk.END)
        self.guidEntry.insert(0, self.destItem.guid)
        self.guidEntry.config({"state": tk.DISABLED})

        self.versionEntry.config({"state": tk.NORMAL})
        self.versionEntry.delete(0, tk.END)
        self.versionEntry.insert(0, self.destItem.iVersion)
        self.versionEntry.config({"state": tk.DISABLED})

        self.authorEntry.delete(0, tk.END)
        self.authorEntry.insert(0, self.destItem.author)
        self.licenseEntry.delete(0, tk.END)
        self.licenseEntry.insert(0, self.destItem.license)
        self.licenseVersionEntry.delete(0, tk.END)
        self.licenseVersionEntry.insert(0, self.destItem.licneseVersion)

        for w in self.warnings:
            w.destroy()
        self.warnings = [tk.Label(self.warningFrame, {"text": w}) for w in self.destItem.warnings]
        for w, n in zip(self.warnings, range(len(self.warnings))):
            w.grid({"row": n, "sticky": tk.W})
            #FIXME wrong

    def listboxImageSelect(self, event):
        self.destItem = pict_dict[event.widget.get(int(event.widget.curselection()[0])).upper()]
        self.selectedName = event.widget.get(int(event.widget.curselection()[0])).upper()

        if self.observer:
            self.fileName.trace_vdelete("w", self.observer)
        self.fileName.set(self.destItem.fileNameWithExt)
        self.observer = self.fileName.trace_variable("w", self.modifyDestImageItem)

        self.guidEntry.config({"state": tk.NORMAL})
        self.guidEntry.delete(0, tk.END)
        self.guidEntry.config({"state": tk.DISABLED})

        self.versionEntry.config({"state": tk.NORMAL})
        self.versionEntry.delete(0, tk.END)
        self.versionEntry.config({"state": tk.DISABLED})

        self.authorEntry.delete(0, tk.END)
        self.licenseEntry.delete(0, tk.END)
        self.licenseVersionEntry.delete(0, tk.END)

    def modifyDestImageItem(self, *_):
        self.destItem.fileNameWithExt = self.fileName.get()
        self.destItem.name = self.destItem.fileNameWithExt
        pict_dict[self.destItem.fileNameWithExt.upper()] = self.destItem
        del pict_dict[self.selectedName.upper()]
        self.selectedName = self.destItem.fileNameWithExt

        self.destItem.refreshFileNames()
        self.refreshDestItem()

    def modifyDestItemdata(self, *_):
        self.destItem.proDatURL = self.proDatURL.get()

    def modifyDestItem(self, *_):
        fN = self.fileName.get().upper()
        if fN and fN not in dest_dict:
            self.destItem.name = self.fileName.get()
            dest_dict[fN] = self.destItem
            del dest_dict[self.selectedName.upper()]
            self.selectedName = self.destItem.name

            self.destItem.refreshFileNames()
            self.refreshDestItem()

    def refreshDestItem(self):
        self.listBox3.refresh()
        self.listBox4.refresh()

    def writeConfigBack(self, ):
        currentConfig = RawConfigParser()
        currentConfig.add_section("ArchiCAD")
        currentConfig.set("ArchiCAD", "path", "C:\Program Files\GRAPHISOFT\ArchiCAD SE 2016\LP_XMLConverter.exe")
        currentConfig.set("ArchiCAD", "ACLocation",         self.ACLocEntry.get())
        currentConfig.set("ArchiCAD", "AdditionalImageDir", self.AdditionalImageDirEntry.get())

        currentConfig.set("ArchiCAD", "bDebug",             self.bDebug)
        currentConfig.set("ArchiCAD", "bXML",               self.bXML.get())
        currentConfig.set("ArchiCAD", "bGDL",               self.bGDL.get())

        currentConfig.set("ArchiCAD", "SourceDirName",      self.SourceDirName.get())
        currentConfig.set("ArchiCAD", "XMLTargetDirName",   self.TargetXMLDirName.get())
        currentConfig.set("ArchiCAD", "GDLTargetDirName",   self.TargetGDLDirName.get())
        currentConfig.set("ArchiCAD", "inputImageSource",   self.SourceImageDirName.get())
        currentConfig.set("ArchiCAD", "inputImageTarget",   self.TargetImageDirName.get())
        currentConfig.set("ArchiCAD", "StringFrom",         self.StringFrom.get())
        currentConfig.set("ArchiCAD", "StringTo",           self.StringTo.get())
        currentConfig.set("ArchiCAD", "ImgStringFrom",      self.ImgStringFrom.get())
        currentConfig.set("ArchiCAD", "ImgStringTo",        self.ImgStringTo.get())

        with open("TemplateMarker.ini", 'wb') as configFile:
            #TODO proper config place
            currentConfig.write(configFile)
        self.top.destroy()

#-------------------/GUI------------------------------
#-------------------/GUI------------------------------
#-------------------/GUI------------------------------

def FC1(inFile):
    """
    only scanning input dir recursively to set up xml and image files' list
    :param inFile:
    :param outFile:
    :return:
    """
    try:
        for f in listdir(inFile):
            try:
                src = inFile + "\\" + f
                # if it's NOT a directory
                if not os.path.isdir(src):
                    if os.path.splitext(os.path.basename(f))[1].upper() in [".XML", ]:
                        sf = SourceXML(src)
                        replacement_dict[sf.name.upper()] = sf
                        id_dict[sf.guid.upper()] = ""

                    elif os.path.splitext(os.path.basename(f))[1].upper() in (".JPG", ".PNG", ".SVG", ):
                        if os.path.splitext(os.path.basename(f))[0].upper() not in source_pict_dict:
                            # set up replacement dict for image names
                            sI = SourceImage(src)
                            source_pict_dict[sI.fileNameWithExt.upper()] = sI
                else:
                    FC1(src)

            except KeyError:
                print "KeyError %s" % f
                continue
    except WindowsError:
        pass

def main2():
    if bXML:
        tempdir = TargetXMLDirName.get()
    else:
        tempdir = tempfile.mkdtemp()

    tempPicDir = tempfile.mkdtemp()
    print "tempdir: %s" % tempdir
    print "tempPicDir: %s" % tempPicDir

    for k in dest_dict.keys():
        dest = dest_dict[k]
        src = dest.sourceFile
        srcPath = src.fullPath
        destPath = dest.fullPath

        print "%s -> %s" % (srcPath, destPath,)

        # try:
        mdp = etree.parse(srcPath, etree.XMLParser(strip_cdata=False))
        mdp.getroot().attrib[ID] = dest.guid

        #FIXME what if calledmacros are not overwritten?
        if bOverWrite.get() and dest_dict[k].retainedCalledMacros:
            cmRoot = mdp.find("./CalledMacros")
            for m in mdp.findall("./CalledMacros/Macro"):
                cmRoot.remove(m)

            for key in dest.retainedCalledMacros.keys():
                cM = dest.retainedCalledMacros[key]
                macro = etree.Element("Macro")

                mName = etree.Element("MName")
                mName.text = etree.CDATA('"' + cM + '"')
                macro.append(mName)

                guid = etree.Element(dest.ID)
                guid.text = key
                macro.append(guid)

                cmRoot.append(macro)
        else:
            for m in mdp.findall("./CalledMacros/Macro"):
                for dI in dest_dict.keys():
                    d = dest_dict[dI]
                    if  string.strip(m.find("MName").text, "'" + '"')  == d.sourceFile.name:
                        m.find("MName").text = etree.CDATA('"' + d.name + '"')
                        m.find(ID).text = d.guid

        for sect in ["./Script_2D", "./Script_3D", "./Script_1D", "./Script_PR", "./Script_UI", "./Script_VL", "./Script_FWM", "./Script_BWM", ]:
            t = mdp.find(sect).text

            for dI in dest_dict.keys():
                # if re.search(dest_dict[dI].sourceFile.fileName, t):
                #     print "*****************", dest_dict[dI].sourceFile.fileName, dest_dict[dI].fileName
                t = re.sub(dest_dict[dI].sourceFile.name, dest_dict[dI].name, t, flags=re.IGNORECASE)

            for pr in pict_dict.keys():
                #Replacing images
                # print pict_dict[pr].originalName
                t = re.sub(pict_dict[pr].sourceFile.fileNameWithOutExt, pict_dict[pr].fileNameWithOutExt, t, flags=re.IGNORECASE)

            mdp.find(sect).text = etree.CDATA(t)

        # ---------------------AC18 and over: adding licensing statically---------------------
        if dest.iVersion >= AC_18:
            for cr in mdp.getroot().findall("Copyright"):
                mdp.getroot().remove(cr)

            eCopyright = etree.Element("Copyright", SectVersion="1", SectionFlags="0", SubIdent="0")
            eAuthor = etree.Element("Author")
            eCopyright.append(eAuthor)
            eAuthor.text = dest.author

            eLicense = etree.Element("License")
            eCopyright.append(eLicense)

            eLType = etree.Element("Type")
            eLicense.append(eLType)
            eLType.text = dest.license

            eLVersion = etree.Element("Version")
            eLicense.append(eLVersion)

            eLVersion.text = dest.licneseVersion

            mdp.getroot().append(eCopyright)

        stRoot = mdp.find("./ParamSection/Parameters")
        for stPar in stRoot.findall("String"):
            if stPar.attrib["Name"] == "BO_prodaturl":
                stRoot.remove(stPar)
            if stPar.attrib["Name"] == "BO_productguid":
                stRoot.remove(stPar)
            if stPar.attrib["Name"] == "BO_edinum":
                stRoot.remove(stPar)
        #FIXME BO_edinum to -1, removing BO_productguid

        eProdatUrl= etree.Element("String", Name="BO_prodaturl", )
        paramPos = mdp.find("./ParamSection/Parameters")
        paramPos.append(eProdatUrl)

        eProdatDesc = etree.Element("Description")
        eProdatDesc.text = etree.CDATA('"Product data url:"')
        eProdatUrl.append(eProdatDesc)

        eParFlags = etree.Element("Flags")
        eParFlags.append(etree.Element("ParFlg_Child", ))
        eProdatUrl.append(eParFlags)

        eProdatVal = etree.Element("Value", )
        eProdatVal.text = etree.CDATA('"' + dest.proDatURL + '"')
        eProdatUrl.append(eProdatVal)

        #FIXME not clear, check, writes an extra empty mainunid field
        for m in mdp.findall("./Ancestry/" + ID):
            name = m.text
            if name.upper() in id_dict:
                print "ANCESTRY: %s" % name
                m.text = id_dict[name]
                par = m.getparent()
                par.remove(m)
            # else:
            #     pass
        try:
            os.makedirs(dest.path)
        except WindowsError:
            pass
        # print destPath, "w"
        with open(destPath, "w") as file_handle:
            mdp.write(file_handle, pretty_print=True, encoding="UTF-8", )

    #try:
    #FIXME
    _picdir =  AdditionalImageDir.get()
    _picdir2 = SourceImageDirName.get()

    # shutil.copytree(_picdir, tempPicDir + "\\IMAGES_GENERIC")
    if _picdir:
        for f in listdir(_picdir):
            shutil.copytree(_picdir + "\\" + f, tempPicDir + "\\" + f)

    if _picdir2:
        for f in listdir(_picdir2):
            shutil.copytree(_picdir2 + "\\" + f, tempPicDir + "\\" + f)

    for f in pict_dict.keys():
        try:
            shutil.copyfile(pict_dict[f].sourceFile.fullPath, pict_dict[f].fullPath, )
        except IOError:
            os.makedirs(pict_dict[f].path)
            shutil.copyfile(pict_dict[f].sourceFile.fullPath, pict_dict[f].fullPath, )

        try:
            shutil.copyfile(pict_dict[f].sourceFile.fullPath, pict_dict[f].GDLFullpath + "\\" + pict_dict[f].fileNameWithExt, )
        except IOError:
            os.makedirs(pict_dict[f].GDLFullpath)
            shutil.copyfile(pict_dict[f].sourceFile.fullPath, pict_dict[f].GDLFullpath + "\\" + pict_dict[f].fileNameWithExt, )

        try:
            shutil.copyfile(pict_dict[f].sourceFile.fullPath, pict_dict[f].XMLFullpath + "\\" + pict_dict[f].fileNameWithExt, )
        except IOError:
            os.makedirs(pict_dict[f].XMLFullpath)
            shutil.copyfile(pict_dict[f].sourceFile.fullPath, pict_dict[f].XMLFullpath + "\\" + pict_dict[f].fileNameWithExt, )

    x2lCommand = '"%s\LP_XMLConverter.exe" x2l -img "%s" "%s" "%s"' % (ACLocation.get(), tempPicDir, tempdir, TargetGDLDirName.get())

    if bDebug.get():
        print "ac command:"
        print x2lCommand
        with open(tempdir + "\dict.txt", "w") as d:
            for k in replacement_dict.keys():
                d.write(k + " " + replacement_dict[k].replaceString + "->" + replacement_dict[k].replace_with + " " + replacement_dict[k].orig_uuid + " -> " + replacement_dict[k].new_uuid + "\n")

        with open(tempdir + "\pict_dict.txt", "w") as d:
            for k in pict_dict.keys():
                d.write(pict_dict[k].originalName + "->" + pict_dict[k].targetName + "\n")

        with open(tempdir + "\id_dict.txt", "w") as d:
            for k in id_dict.keys():
                d.write(id_dict[k] + "\n")
    else:
        pass

    if bGDL.get():
        check_output(x2lCommand, shell=True)

    # cleanup ops
    if not bDebug.get():
        shutil.rmtree(tempPicDir)
        if not bXML:
            shutil.rmtree(tempdir)
    else:
        print "tempdir: %s" % tempdir
        print "tempPicDir: %s" % tempPicDir

    print "*****FINISHED SUCCESFULLY******"

def main():
    global app

    app = GUIApp()
    app.top.protocol("WM_DELETE_WINDOW", app.writeConfigBack)
    app.top.mainloop()

    # main2()

if __name__ == "__main__":
    main()