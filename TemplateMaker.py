#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-
# HOTFIXREQ if image dest folder is retained, remove common images from it
# HOTFIXREQ ImportError: No module named googleapiclient.discovery
# HOTFIXREQ unicode error when running ac command in path with native characters
# HOTFIXREQ SOURCE_IMAGE_DIR_NAME images are not renamed at all
# FIXME renaming errors and param csv parameter overwriting
# FIXME append param to the end when no argument for position
# FIXME library_images copy always as temporary folder; instead junction
# FIXME param editor should offer auto param inserting from Listing Parameters Google Spreadsheet
# FIXME automatic checking and warning of (collected) old project's names
# FIXME UI process messages
# FIXME MigrationTable progressing
# FIXME GDLPict progressing
# FIXME when adding files, the renaming shouldtn't be done at the moment of adding but when being processed
# TODO When there is nothing to replace at the beginning of the source names, many unwanted things are renamed in the code
# FIXME async + output screen + logging

import os.path
from os import listdir
import tempfile
import shutil

import tkinter.filedialog
from tkinter import scrolledtext

import csv

import pip
import multiprocessing as mp

try:
  from lxml import etree
except ImportError:
  pip.main(['install', '--user', 'lxml'])
  from lxml import etree

from GSMParamLib.GSMXMLLib import *
from SamUITools import *
from samuTeszt import Recorder
from GSMParamLib.GUIAppSingletonBase import XMLProcessorBase
from GSMParamLib.Async import Loop
from GSMParamLib.GoogleSpreadsheetConnector import GoogleSpreadsheetConnector

LISTBOX_SEPARATOR = '--------'
LP_XML_CONVERTER = 'LP_XMLConverter.exe'

# ------------------- GUI ------------------------------
# ------------------- GUI ------------------------------
# ------------------- GUI ------------------------------

#----------------- gui classes -----------------------------------------------------------------------------------------


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
  def __init__(self, top, data: dict):
    self.data = data
    tk.Listbox.__init__(self, top, data, selectmode=tk.EXTENDED)

  def refresh(self, *_):
    self.delete(0, tk.END)
    _prevObj = None
    for f in sorted([self.data[k] for k in list(self.data.keys())]):
      try:
        if _prevObj and _prevObj.dirName != f.dirName:
          self.insert(tk.END, LISTBOX_SEPARATOR + os.path.basename(os.path.normpath(f.dirName)))
        _prevObj = f
        if f.warnings:
          self.insert(tk.END, "* " + f.name)
        self.insert(tk.END, f.name)
      except AttributeError:
        self.insert(tk.END, f.name)


class GUIApp(XMLProcessorBase):
  def __init__(self):
    super().__init__("TemplateMarker")

    # Example usage of an encrypted param:
    # from cryptography.fernet import Fernet
    # self.SourceXMLDirName   = self.currentConfig.register(tk.StringVar(self.top), "SourceXMLDirName", encrypt=Fernet)
    # self.SourceXMLDirName   = self.currentConfig.register(tk.StringVar(self.top), "SourceXMLDirName")

    self.SourceGDLDirName   = self.currentConfig.register(tk.StringVar(self.top), "SourceGDLDirName")
    self.TargetXMLDirName   = self.currentConfig.register(tk.StringVar(self.top), "TargetXMLDirName")
    self.TargetGDLDirName   = self.currentConfig.register(tk.StringVar(self.top), "TargetGDLDirName")
    self.TargetImageDirName = self.currentConfig.register(tk.StringVar(self.top), "TargetImageDirName")
    self.AdditionalImageDir = self.currentConfig.register(tk.StringVar(self.top), "AdditionalImageDir")

    self.StringFrom         = self.currentConfig.register(tk.StringVar(self.top), "StringFrom")
    self.StringTo           = self.currentConfig.register(tk.StringVar(self.top), "StringTo")

    self.ImgStringFrom      = self.currentConfig.register(tk.StringVar(self.top), "ImgStringFrom")
    self.ImgStringTo        = self.currentConfig.register(tk.StringVar(self.top), "ImgStringTo")

    self.fileName           = self.currentConfig.register(tk.StringVar(self.top), "fileName")

    self.ACLocation         = self.currentConfig.register(tk.StringVar(self.top), "ACLocation")

    self.bCheckParams       = self.currentConfig.register(tk.BooleanVar(self.top), "bCheckParams")
    self.bDebug             = self.currentConfig.register(tk.BooleanVar(self.top), "bDebug")
    self.bCleanup           = self.currentConfig.register(tk.BooleanVar(self.top), "bCleanup")
    self.bOverWrite         = self.currentConfig.register(tk.BooleanVar(self.top), "bOverWrite")
    self.bAddStr            = self.currentConfig.register(tk.BooleanVar(self.top), "bAddStr")

    self.bXML               = self.currentConfig.register(tk.BooleanVar(self.top), "bXML")
    self.bGDL               = self.currentConfig.register(tk.BooleanVar(self.top), "bGDL")
    self.isSourceGDL        = self.currentConfig.register(tk.BooleanVar(self.top), "isSourceGDL")

    self.observer  = None

    self.warnings = []

    self.googleSpreadsheet  = None
    self.bWriteToSelf       = False             # Whether to write back to the file itself

    __tooltipIDPT1 = "Something like E:/_GDL_SVN/_TEMPLATE_/AC18_Opening/library"
    __tooltipIDPT2 = "Images' dir that are NOT to be renamed per project and compiled into final gdls (prev pics, for example), something like E:\_GDL_SVN\_TEMPLATE_\AC18_Opening\library_images"
    __tooltipIDPT3 = "Something like E:/_GDL_SVN/_TARGET_PROJECT_NAME_/library"
    __tooltipIDPT4 = "Final GDL output dir"
    __tooltipIDPT5 = "If set, copy project specific pictures here, too, for endcoded images. Something like E:/_GDL_SVN/_TARGET_PROJECT_NAME_/library_images"
    __tooltipIDPT6 = "Additional images' dir, for all other images, which can be used by any projects, something like E:/_GDL_SVN/_IMAGES_GENERIC_"
    __tooltipIDPT7 = "Source GDL folder name"

    self.observerXML = self.bXML.trace_variable("w", self._targetXMLModified)
    self.observerGDL = self.bGDL.trace_variable("w", self._targetGDLModified)

    self.warnings = []

    # GUI itself----------------------------------------------------------------------------------------------------

    # ----input side--------------------------------

    self.top.columnconfigure(0, weight=1)
    self.top.columnconfigure(2, weight=1)
    self.top.rowconfigure(0, weight=1)

    self.inputFrame = tk.Frame(self.top)
    self.inputFrame.grid({"row": 0, "column": 0, "sticky": tk.NW + tk.SE})
    self.inputFrame.columnconfigure(0, weight=1)
    self.inputFrame.grid_rowconfigure(2, weight=1)
    self.inputFrame.grid_rowconfigure(4, weight=1)

    self.InputFrameS = [tk.Frame(self.inputFrame) for _ in range (6)]
    for f, r, cc in zip(self.InputFrameS, list(range(6)), [0, 1, 1, 0, 0, 1, ]):
      f.grid({"row": r, "column": 0, "sticky": tk.N + tk.S + tk.E + tk.W, })
      self.InputFrameS[r].grid_columnconfigure(cc, weight=1)
      self.InputFrameS[r].rowconfigure(0, weight=1)

    iF = 0

    self.entryTextNameFrom = tk.Entry(self.InputFrameS[iF], {"width": 20, "textvariable": self.StringFrom, })
    self.entryTextNameFrom.grid({"column": 0, "sticky": tk.SE + tk.NW, })

    iF += 1

    self.inputXMLDir = InputDirPlusRadio(self.InputFrameS[iF], "XML Source folder", self.SourceXMLDirName, self.isSourceGDL, False, __tooltipIDPT1)

    iF += 1

    InputDirPlusRadio(self.InputFrameS[iF], "GDL Source folder", self.SourceGDLDirName, self.isSourceGDL, True, __tooltipIDPT7)

    iF += 1

    self.lbSourceXML = ListboxWithRefresh(self.InputFrameS[iF], SourceXML.replacement_dict)
    self.lbSourceXML.grid({"row": 0, "column": 0, "sticky": tk.E + tk.W + tk.N + tk.S})

    self.ListBoxScrollbar = tk.Scrollbar(self.InputFrameS[iF])
    self.ListBoxScrollbar.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

    self.lbSourceXML.config(yscrollcommand=self.ListBoxScrollbar.set)
    self.ListBoxScrollbar.config(command=self.lbSourceXML.yview)

    iF += 1

    self.lbSourceResource = ListboxWithRefresh(self.InputFrameS[iF], SourceResource.source_pict_dict)
    self.lbSourceResource.grid({"row": 0, "column": 0, "sticky": tk.NE + tk.SW})

    if self.isSourceGDL.get():
      self.observerLB1 = self.SourceGDLDirName.trace_variable("w", self.processGDLDir)
    else:
      self.observerLB1 = self.SourceXMLDirName.trace_variable("w", self._lbXMLRefresh)

    self.observerLB2 = self.SourceXMLDirName.trace_variable("w", self._listBoxResourceRefresh)

    if self.SourceXMLDirName:
      self.lbSourceXML.refresh()
      self.lbSourceResource.refresh()

    self.ListBoxScrollbar2 = tk.Scrollbar(self.InputFrameS[iF])
    self.ListBoxScrollbar2.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

    self.lbSourceResource.config(yscrollcommand=self.ListBoxScrollbar2.set)
    self.ListBoxScrollbar2.config(command=self.lbSourceResource.yview)

    iF += 1

    self.sourceImageDir = InputDirPlusText(self.InputFrameS[iF], "Images' source folder", self.SourceImageDirName, __tooltipIDPT2)
    if self.SourceImageDirName:
      self.lbSourceXML.refresh()
      self.lbSourceResource.refresh()

    # ----output side--------------------------------

    self.outputFrame = tk.Frame(self.top)
    self.outputFrame.grid({"row": 0, "column": 2, "sticky": tk.NE + tk.SW})
    self.outputFrame.columnconfigure(0, weight=1)
    self.outputFrame.grid_rowconfigure(2, weight=1)
    self.outputFrame.grid_rowconfigure(4, weight=1)

    self.outputFrameS = [tk.Frame(self.outputFrame) for _ in range (6)]
    for f, r, cc in zip(self.outputFrameS, list(range(6)), [0, 1, 1, 0, 0, 1]):
      f.grid({"row": r, "column": 0, "sticky": tk.SW + tk.NE, })
      self.outputFrameS[r].grid_columnconfigure(cc, weight=1)
      self.outputFrameS[r].rowconfigure(0, weight=1)

    iF = 0

    self.entryTextNameTo = tk.Entry(self.outputFrameS[iF], {"width": 20, "textvariable": self.StringTo, })
    self.entryTextNameTo.grid({"row":0, "column": 0, "sticky": tk.SE + tk.NW, })

    self.bAddStrCheckButton = tk.Checkbutton(self.outputFrameS[iF], {"text": "Always add strings", "variable": self.bAddStr})
    self.bAddStrCheckButton.grid({"row": 0, "column": 1})

    iF += 1

    self.XMLDir = InputDirPlusBool(self.outputFrameS[iF], "XML Destination folder",      self.TargetXMLDirName, self.bXML, __tooltipIDPT3)

    iF += 1

    self.GDLDir = InputDirPlusBool(self.outputFrameS[iF], "GDL Destination folder",      self.TargetGDLDirName, self.bGDL, __tooltipIDPT4)

    iF += 1

    self.lbDestXML = ListboxWithRefresh(self.outputFrameS[iF], DestXML.dest_dict)
    self.lbDestXML.grid({"row": 0, "column": 0, "sticky": tk.SE + tk.NW})

    self.ListBoxScrollbar3 = tk.Scrollbar(self.outputFrameS[iF])
    self.ListBoxScrollbar3.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

    self.lbDestXML.config(yscrollcommand=self.ListBoxScrollbar3.set)
    self.ListBoxScrollbar3.config(command=self.lbDestXML.yview)

    self.lbDestXML.bind("<<ListboxSelect>>", self.listboxselect)

    iF += 1

    self.lbDestResource = ListboxWithRefresh(self.outputFrameS[iF], DestResource.pict_dict)
    self.lbDestResource.grid({"row": 0, "column": 0, "sticky": tk.SE + tk.NW})

    self.ListBoxScrollbar4 = tk.Scrollbar(self.outputFrameS[iF])
    self.ListBoxScrollbar4.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

    self.lbDestResource.config(yscrollcommand=self.ListBoxScrollbar4.set)
    self.ListBoxScrollbar4.config(command=self.lbDestResource.yview)
    self.lbDestResource.bind("<<ListboxSelect>>", self.listboxImageSelect)

    iF += 1

    InputDirPlusText(self.outputFrameS[iF], "Images' destination folder",  self.TargetImageDirName, __tooltipIDPT5)

    # ------------------------------------
    # bottom row for project general settings
    # ------------------------------------

    self.bottomFrame        = tk.Frame(self.top, )
    self.bottomFrame.grid({"row":1, "column": 0, "columnspan": 7, "sticky":  tk.S + tk.N, })

    iF = 0

    self.progressInfo = tk.Label(self.bottomFrame, text=f"{self.iCurrent} / {self.iTotal}")
    self.progressInfo.grid({"column": iF, "sticky": tk.W});

    iF += 1

    # self.scrolledText = scrolledtext.ScrolledText()
    # self.scrolledText.grid(column=iF, sticky=tk.SE + tk.NW)

    InputDirPlusText(self.bottomFrame, "ArchiCAD location",  self.ACLocation, column=iF)

    iF += 1

    InputDirPlusText(self.bottomFrame, "Additional images' folder",  self.AdditionalImageDir, column=iF, tooltip=__tooltipIDPT6)

    iF += 1

    self.paramCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Check Parameters", "variable": self.bCheckParams})
    self.paramCheckButton.grid({"row": 0, "column": iF}); iF += 1

    self.debugCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Debug", "variable": self.bDebug})
    self.debugCheckButton.grid({"row": 0, "column": iF}); iF += 1

    self.cleanupCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Cleanup", "variable": self.bCleanup})
    self.cleanupCheckButton.grid({"row": 0, "column": iF}); iF += 1

    self.OverWriteCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Overwrite", "variable": self.bOverWrite})
    self.OverWriteCheckButton.grid({"row": 0, "column": iF}); iF += 1

    self.OverWriteCheckButton.grid({"row": 0, "column": iF}); iF += 1

    self.startButton = tk.Button(self.bottomFrame, {"text": "Start", "command": self.start})
    self.startButton.grid({"row": 0, "column": 7, "sticky": tk.E})

    # ----buttons---------------------------------------------------------------------------------------------------

    self.buttonFrame        = tk.Frame(self.top)
    self.buttonFrame.grid({"row": 0, "column": 1})

    _i = 0

    self.addAllButton       = tk.Button(self.buttonFrame, {"text": ">>", "command": self.addAllFiles})
    self.addAllButton.grid({"row":_i, "column": 0})

    _i += 1

    self.addRecursiveButton = tk.Button(self.buttonFrame, {"text": "Recursive >", "command": self.addMoreXMLsRecursively})
    self.addRecursiveButton.grid({"row":_i, "column": 0, "sticky": tk.W + tk.E})
    CreateToolTip(self.addRecursiveButton, "Add macro, and all its called macro and subtypes recursively, if not added already")

    _i += 1

    self.addButton          = tk.Button(self.buttonFrame, {"text": ">", "command": self.addMoreFiles})
    self.addButton.grid({"row":_i, "column": 0, "sticky": tk.W + tk.E})

    _i += 1

    self.delButton          = tk.Button(self.buttonFrame, {"text": "X", "command": self.delXML})
    self.delButton.grid({"row":_i, "column": 0, "sticky": tk.W + tk.E})

    _i += 1

    self.resetButton         = tk.Button(self.buttonFrame, {"text": "Reset", "command": self._resetAll})
    self.resetButton.grid({"row": _i, "sticky": tk.W + tk.E})

    _i += 1

    self.CSVbutton          = tk.Button(self.buttonFrame, {"text": "CSV", "command": self.getFromCSV, })
    self.CSVbutton.grid({"row": _i, "sticky": tk.W + tk.E})

    _i += 1

    self.GoogleSSBbutton     = tk.Button(self.buttonFrame, {"text": "Google Spreadsheet", "command": self.showGoogleSpreadsheetEntry, })
    self.GoogleSSBbutton.grid({"row": _i, "sticky": tk.W + tk.E})

    _i += 1

    self.ParamWriteButton    = tk.Button(self.buttonFrame, {"text": "Write params", "command": self.paramWrite, })
    self.ParamWriteButton.grid({"row": _i, "sticky": tk.W + tk.E})

    # FIXME
    #
    #_i += 1
    #
    # self.reconnectButton      = tk.Button(self.buttonFrame, {"text": "Reconnect", "command": self.reconnect })
    # self.reconnectButton.grid({"row": _i, "sticky": tk.W + tk.E})

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

    # FIXME to put in projectname field

    CreateToolTip(self.entryTextNameFrom, "FromSting: WARNING: this is Regex")
    CreateToolTip(self.entryTextNameTo, "If 'Always add strings' is set add to the end of every file if FromSting cannot be replaced, if not, only replace FromSting Regex pattern")

    self.loop = Loop(self.top)
    self._iCurrent = 0
    self._iTotal = 0
    self._lbXMLRefresh()
    DestXML.sDestXMLDir = self.TargetXMLDirName.get()

  def _lbXMLRefresh(self, *_):
    def _lbXMLRefreshCallback(task):
      self.startButton.config(state=tk.NORMAL, text="Start")
      self.inputXMLDir.config(state=tk.NORMAL)
      self.progressInfo.config(text=f"{self.iCurrent} / {self.iTotal} Scanning dirs took {self.tick:.2f} seconds")
      self.lbSourceXML.refresh()
      self.lbSourceResource.refresh()

    if _sSXD := self.SourceXMLDirName.get():
      _ = self.tick
      self.inputXMLDir.config(width=len(_sSXD))
      self.startButton.config(state=tk.DISABLED, text="Processing...")
      self.inputXMLDir.config(state=tk.DISABLED)
      self.start_source_xml_processing(_lbXMLRefreshCallback)

  def _listBoxResourceRefresh(self, *_):
    self.lbSourceResource.refresh()

  def createDestItems(self, inList):
    firstRow = inList[0]

    for row in inList[1:]:
      if firstRow[1] == "":
        # empty header => row[1] is for destItem
        destItem = self._addXMLRecursively(row[0], row[1])

      else:
        # no destitem so write to itself
        destItem = DestXML(row[0], dest_file_name=row[0])
        DestXML.dest_dict[destItem.name] = destItem
        [destItem.sourceFile.name] = destItem
      if len(row) > 2 and next((c for c in row[2:] if c != ""), ""):
        for parName, col in zip(firstRow[2:], row[2:]):
          destItem.parameters.createParamfromCSV(parName, col)

  def getListFromGoogleSpreadsheet(self):
    self.GoogleSSBbutton.config(cnf={'state': tk.NORMAL})
    SSIDRegex = "/spreadsheets/d/([a-zA-Z0-9-_]+)"
    findall = re.findall(SSIDRegex, self.GoogleSSInfield.GoogleSSURL.get())
    if findall:
      SpreadsheetID = findall[0]
    else:
      SpreadsheetID = findall
    print(SpreadsheetID)

    self.googleSpreadsheet = GoogleSpreadsheetConnector(self.currentConfig, SpreadsheetID)

    self.GoogleSSInfield.top.destroy()
    self.createDestItems(self.googleSpreadsheet.values)

  def paramWrite(self):
    """
    This method should write params from a Google SpreadSheet directly into selected .GSMs/.XLSs
    (source and destination is the same)
    :return:
    """
    self.bWriteToSelf = True
    self.XMLDir.config(state=tk.DISABLED)
    self.GDLDir.config(state=tk.DISABLED)
    self.showGoogleSpreadsheetEntry(inFunc=self.getListFromGoogleSpreadsheet)

  def getFromCSV(self):
    """
    Source-dest file conversation based on csv
    :return:
    """
    SRC_NAME    = 0
    TARG_NAME   = 1
    # PRODATURL   = 2
    VALUES      = 2
    csvFileName = tkinter.filedialog.askopenfilename(initialdir="/", title="Select folder", filetypes=(("CSV files", "*.csv"), ("all files","*.*")))
    if csvFileName:
      with open(csvFileName, "r") as csvFile:
        firstRow = next(csv.reader(csvFile))
        for row in csv.reader(csvFile):
          destItem = self._addXMLRecursively(row[SRC_NAME], row[TARG_NAME])
          # if row[PRODATURL]:
          #     destItem.parameters.BO_update(row[PRODATURL])
          if len(row) > 3 and next((c for c in row[VALUES-1:] if c != ""), ""):
            for parName, col in zip(firstRow[VALUES:], row[VALUES:]):
              if "-y" in parName or "-array" in parName:
                arrayValues = []
                with open(col, "r") as arrayCSV:
                  for arrayRow in csv.reader(arrayCSV):
                    if arrayRow[TARG_NAME].strip() == row[TARG_NAME].strip:
                      arrayValues = [[arrayRow[2:]]]
                    if arrayValues \
                        and len(arrayRow) > 2 \
                        and not arrayRow[TARG_NAME] \
                        and arrayRow[2] != "":
                      arrayValues += [arrayRow[2:]]
                    else:
                      break
                destItem.parameters.createParamfromCSV(parName, col, arrayValues)
              else:
                destItem.parameters.createParamfromCSV(parName, col)

  def convertFilesGoogleSpreadsheet(self):
    """
    Source-dest file conversation based on Google Spreadsheet
    :return:
    """
    self.showGoogleSpreadsheetEntry()

  def getFromGoogleSpreadsheet(self):
    self.GoogleSSBbutton.config(cnf={'state': tk.NORMAL})
    SSIDRegex = "/spreadsheets/d/([a-zA-Z0-9-_]+)"
    findall = re.findall(SSIDRegex, self.GoogleSSInfield.GoogleSSURL.get())
    if not findall:
      self.GoogleSSInfield.top.destroy()
      return
    if findall:
      SpreadsheetID = findall[0]
    else:
      SpreadsheetID = findall
    print(SpreadsheetID)

    self.googleSpreadsheet = GoogleSpreadsheetConnector(self.currentConfig, SpreadsheetID)
    #FIXME above here paramWrite uses the same
    #FIXME from here maybe to put into a method; same as in getFromCSV
    firstRow = self.googleSpreadsheet.values[0]

    for row in self.googleSpreadsheet.values[1:]:
      destItem = self._addXMLRecursively(row[0], row[1])
      if row[2]:
        destItem.parameters.BO_update(row[2])
      if len(row) > 3 and next((c for c in row[2:] if c != ""), ""):
        for parName, col in zip(firstRow[3:], row[3:]):
          destItem.parameters.createParamfromCSV(parName, col)

    self.GoogleSSInfield.top.destroy()

  def showGoogleSpreadsheetEntry(self, inFunc=None):
    if not inFunc:
      inFunc = self.getFromGoogleSpreadsheet
    self.GoogleSSInfield = GoogleSSInfield(self)
    self.GoogleSSInfield.top.protocol("WM_DELETE_WINDOW", inFunc)
    self.GoogleSSBbutton.config(cnf={'state': tk.DISABLED})

  def processGDLDir(self, *_):
    '''
    When self.SourceGDLDirName is modified, convert files to xml and set ui accordingly
    :return:
    '''
    # FIXME check all this
    if not self.SourceGDLDirName.get():
      return
    _tempXMLDir = tempfile.mkdtemp()
    _tempImgDir = tempfile.mkdtemp()

    self.run_converter("l2x", self.SourceGDLDirName.get(), _tempXMLDir, _tempImgDir)

    self.inputXMLDir.idpt.entryName.config(cnf={'state': tk.NORMAL})
    self.sourceImageDir.reset()
    self.SourceXMLDirName.set(_tempXMLDir)
    self.SourceImageDirName.set(_tempImgDir)

    self.inputXMLDir.idpt.entryName.config(cnf={'state': tk.DISABLED})
    self.sourceImageDir.reset()
    self.lbSourceXML.refresh()
    self.lbSourceResource.refresh()

  def _targetGDLModified(self, *_):
    if not self.bGDL.get():
      self.bXML.set(True)

  def _targetXMLModified(self, *_):
    DestXML.sDestXMLDir = self.TargetXMLDirName.get()
    if not self.bXML.get():
      self.bGDL.set(True)

  def sourceGDLModified(self, *_):
    if not self.bGDL.get():
      self.bXML.set(True)
      self.GDLDir.idpt.entryDirName.config(state=tk.DISABLED)
    else:   self.GDLDir.idpt.entryDirName.config(state=tk.NORMAL)

  def sourceXMLModified(self, *_):
    if not self.bXML.get():
      self.bGDL.set(True)
      self.XMLDir.idpt.entryDirName.config(state=tk.DISABLED)
    else:   self.XMLDir.idpt.entryDirName.config(state=tk.NORMAL)

  def start(self):
    self._start()
    # print "Starting conversion"

# ---- Adding/removing files------------------------------------------------------------------------------------------

  def _addXML(self, source_file: str, target_file: str = "") -> DestXML | None:
    """
    :param source_file:
    :param target_file:
    :return:
    """
    assert source_file
    assert source_file in SourceXML.replacement_dict

    destItem = DestXML(SourceXML.replacement_dict[source_file], target_file,  self.StringFrom.get(), self.StringTo.get(), self.bAddStr.get())
    self.refreshDestItem()
    return destItem

  def _addXMLRecursively(self, source_file: str, target_file: str = "") -> DestXML | None:
    """
    Not to be called from UI as doesn't check for validity of source file name
    :param source_file:
    :param target_file:
    :return:
    """
    assert source_file
    assert source_file in SourceXML.replacement_dict

    destItem = self._addXML(source_file, target_file)

    if source_file not in SourceXML.replacement_dict:
      # should be in library_additional
      # FIXME build a filelist of that dict and check against it
      return

    _dSR = SourceXML.replacement_dict[source_file]

    for k, v in _dSR.calledMacros.items():
      if v not in DestXML.dest_sourcenames:
        self._addXMLRecursively(v)

    for parentGUID in _dSR.parentSubTypes:
      if parentGUID not in DestXML.id_dict:
        if parentGUID in SourceXML.source_guids:
          self._addXMLRecursively(SourceXML.source_guids[parentGUID])

    for pict in list(SourceResource.source_pict_dict.values()):
      for script in list(_dSR.scripts.values()):
        if pict.fileNameWithOutExt.upper() in script.upper():
          sTarget = DestXML.getValidName(pict.fileNameWithExt, self.StringFrom.get(), self.StringTo.get(), self.bAddStr.get())
          self._addResourceFile(pict.fileNameWithExt, sTarget)
      if pict.fileNameWithExt.upper() in _dSR.gdlPicts:
        self._addResourceFile(pict.fileNameWithExt)

    if _dSR.prevPict:
      _sBase = os.path.basename(_dSR.prevPict)
      self._addResourceFile(_sBase)

    self.refreshDestItem()
    return destItem

  def _addResourceFile(self, source_file: str, target_file: str = ""):
    """
    Not to be called from UI as doesn't check for validity of source file name
    :param source_file:
    :param target_file:
    :return:
    """
    assert source_file
    assert source_file in SourceResource.source_pict_dict

    _sr = SourceResource.source_pict_dict[source_file]
    if _sr.isEncodedImage:
      DestResource(_sr, self.SourceImageDirName.get(), _sr.name)
    else:
      DestResource(_sr, DestXML.sDestXMLDir, target_file)
    self.refreshDestItem()

  def addMoreFiles(self):
    for sourceFileIndex in self.lbSourceXML.curselection():
      sTargetXML = DestXML.getValidName(sSourceXML := self.lbSourceXML.get(sourceFileIndex), self.StringFrom.get(), self.StringTo.get(), self.bAddStr.get())
      self._addXML(sSourceXML, sTargetXML)

    for sourceResourceIndex in self.lbSourceResource.curselection():
      sTargetRes = DestResource.getValidName(sSourceRes := self.lbSourceResource.get(sourceResourceIndex), self.StringFrom.get(), self.StringTo.get(), self.bAddStr.get())
      self._addResourceFile(sSourceRes, sTargetRes)

  def addAllFiles(self):
    for sSourceXML in self.lbSourceXML.get(0, tk.END):
      sTargetXML = DestXML.getValidName(sSourceXML, self.StringFrom.get(), self.StringTo.get(), self.bAddStr.get())
      self._addXML(sSourceXML, sTargetXML)

    for sSourceRes in self.lbSourceResource.get(0, tk.END):
      sTargetRes = DestResource.getValidName(sSourceRes, self.StringFrom.get(), self.StringTo.get(), self.bAddStr.get())
      self._addResourceFile(sSourceRes, sTargetRes)

    self.addAllButton.config({"state": tk.DISABLED})

  def addMoreXMLsRecursively(self):
    for sourceFileIndex in self.lbSourceXML.curselection():
      sTargetXML = DestXML.getValidName(sSourceXML := self.lbSourceXML.get(sourceFileIndex), self.StringFrom.get(), self.StringTo.get(), self.bAddStr.get())
      self._addXMLRecursively(sSourceXML, sTargetXML)

  # ---- Adding/removing files------------------------------------------------------------------------------------------

  def delXML(self):
    fileName = self.lbDestXML.get(tk.ACTIVE)
    if fileName.startswith(LISTBOX_SEPARATOR):
      self.lbDestXML.select_clear(tk.ACTIVE)
      return

    fN = self.__unmarkFileName(fileName)
    assert fN in DestXML.dest_dict
    assert DestXML.dest_dict[fN].sourceFile.name in DestXML.dest_sourcenames

    del DestXML.dest_sourcenames[ DestXML.dest_dict[fN].sourceFile.name ]
    del DestXML.dest_dict[fN]
    self.lbDestXML.refresh()

    if not DestXML.dest_dict and not DestResource.pict_dict:
      self.addAllButton.config({"state": tk.NORMAL})
    self.fileName.set('')

  # ---- Adding/removing files------------------------------------------------------------------------------------------

  def _refreshAll(self):
    self.lbSourceXML.refresh()
    self.lbSourceResource.refresh()
    self.lbDestXML.refresh()
    self.lbDestResource.refresh()

  def _resetAll(self):
    self.XMLDir.config(state=tk.NORMAL)
    self.GDLDir.config(state=tk.NORMAL)

    SourceXML.replacement_dict.clear()
    SourceXML.source_guids.clear()
    DestXML.dest_dict.clear()
    DestXML.dest_sourcenames.clear()
    DestXML.id_dict.clear()

    SourceResource.source_pict_dict.clear()
    DestResource.pict_dict.clear()

    self._refreshAll()

    for w in self.warnings:
      w.destroy()

    self.addAllButton.config({"state": tk.NORMAL})
    self.sourceImageDir.reset()

  def listboxselect(self, event, ):
    if not event.widget.get(0):
      return
    if event.widget.get(event.widget.curselection()[0]).startswith(LISTBOX_SEPARATOR):
      return

    currentSelection = event.widget.get(int(event.widget.curselection()[0])).upper()
    if currentSelection[:2] == "* ":
      currentSelection = currentSelection[2:]
    self.destItem = DestXML.dest_dict[currentSelection]
    self.selectedName = currentSelection

    if self.observer:
      self.fileName.trace_vdelete("w", self.observer)

    self.fileName.set(self.destItem.name)
    self.observer = self.fileName.trace_variable("w", self.modifyDestItem)

    self.guidEntry.config({"state": tk.NORMAL})
    self.guidEntry.delete(0, tk.END)
    self.guidEntry.insert(0, self.destItem.guid)
    self.guidEntry.config({"state": tk.DISABLED})

    self.versionEntry.config({"state": tk.NORMAL})
    self.versionEntry.delete(0, tk.END)
    self.versionEntry.insert(0, self.destItem.iVersion)
    self.versionEntry.config({"state": tk.DISABLED})

    # self.authorEntry.delete(0, tk.END)
    # self.authorEntry.insert(0, self.destItem.author)
    # self.licenseEntry.delete(0, tk.END)
    # self.licenseEntry.insert(0, self.destItem.license)
    # self.licenseVersionEntry.delete(0, tk.END)
    # self.licenseVersionEntry.insert(0, self.destItem.licneseVersion)

    for w in self.warnings:
      w.destroy()
    self.warnings = [tk.Label(self.warningFrame, {"text": w}) for w in self.destItem.warnings]
    for w, n in zip(self.warnings, list(range(len(self.warnings)))):
      w.grid({"row": n, "sticky": tk.W})
      #FIXME wrong

  def listboxImageSelect(self, event):
    self.destItem = DestResource.pict_dict[event.widget.get(int(event.widget.curselection()[0]))]
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
    DestResource.pict_dict[self.destItem.fileNameWithExt] = self.destItem

    del DestResource.pict_dict[self.selectedName]
    self.selectedName = self.destItem.fileNameWithExt

    self.destItem.refreshFileNames()
    self.refreshDestItem()

  def modifyDestItem(self, *_):
    fN = self.fileName.get().upper()
    if fN and fN not in DestXML.dest_dict:
      self.destItem.name = self.fileName.get()
      DestXML.dest_dict[fN] = self.destItem
      del DestXML.dest_dict[self.selectedName]
      self.selectedName = self.destItem.name

      self.destItem.refreshFileNames()
      self.refreshDestItem()

  def refreshDestItem(self):
    self.lbDestXML.refresh()
    self.lbDestResource.refresh()

  def _start(self):
    """
    :return:
    """
    if self.bXML.get():
      DestXML.sDestXMLDir = self.TargetXMLDirName.get()
      assert not len(os.listdir(DestXML.sDestXMLDir)) or self.bOverWrite.get()
    else:
      DestXML.sDestXMLDir = tempfile.mkdtemp()

    if self.bWriteToSelf:
      targGDLDir = tempfile.mkdtemp()
    else:
      targGDLDir = self.TargetGDLDirName.get()
      assert not len(os.listdir(targGDLDir)) or self.bOverWrite.get()

    tempPicDir = tempfile.mkdtemp()  # For every image file, collected
    targPicDir = self.TargetImageDirName.get()  # For target library's encoded images
    assert not len(os.listdir(targPicDir)) or self.bOverWrite.get()

    print("targXMLDir: %s" % DestXML.sDestXMLDir)
    print("tempPicDir: %s" % tempPicDir)

    pool_map = [ProcessData (
      dest_xml=DestXML.dest_dict[k],
      dest_dir=DestXML.sDestXMLDir,
      overwrite=self.bOverWrite.get(),
      string_to=self.StringTo.get(),) for k in list(DestXML.dest_dict.keys()) if isinstance(DestXML.dest_dict[k], DestXML)]

    cpuCount = max(mp.cpu_count() - 1, 1)

    p = mp.Pool(processes=cpuCount)
    p.map(processOneXML, pool_map)

    _picdir = self.AdditionalImageDir.get()  # Like IMAGES_GENERIC

    if _picdir:
      for f in listdir(_picdir):
        shutil.copytree(os.path.join(_picdir, f), os.path.join(tempPicDir, f))

    def _copyFile(dest: DestResource, dir_to: str):
      assert os.path.exists(dir_to)
      if not os.path.exists(os.path.join(dir_to, dest.dirName)):
        os.makedirs(os.path.join(dir_to, dest.dirName))
      shutil.copyfile(os.path.join(dest.sourceFile.fullPath), os.path.join(dir_to, dest.relPath))

    for f in list(DestResource.pict_dict.keys()):
      if DestResource.pict_dict[f].sourceFile.isEncodedImage:
        _copyFile(DestResource.pict_dict[f], tempPicDir)

        if targPicDir:
          _copyFile(DestResource.pict_dict[f], targPicDir)
      else:
        _copyFile(DestResource.pict_dict[f], targGDLDir)

        if self.TargetXMLDirName.get():
          _copyFile(DestResource.pict_dict[f], self.TargetXMLDirName.get())

    if self.bWriteToSelf:
      tempGDLArchiveDir = tempfile.mkdtemp()
      print("GDL's archive dir: %s" % tempGDLArchiveDir)
      for k in list(DestXML.dest_dict.keys()):
        os.rename(k.sourceFile.fullPath, os.path.join(tempGDLArchiveDir, k.sourceFile.relPath))
        os.rename(os.path.join(targGDLDir, k.sourceFile.relPath), k.sourceFile.fullPath)

    if self.bGDL.get():
      self.run_converter("x2l", DestXML.sDestXMLDir, targGDLDir, tempPicDir)

    # cleanup ops
    if not self.bCleanup.get():
      shutil.rmtree(tempPicDir)
      if not self.bXML:
        shutil.rmtree(DestXML.sDestXMLDir)
    else:
      print("targXMLDir: %s" % DestXML.sDestXMLDir)
      print("tempPicDir: %s" % tempPicDir)

    print("*****FINISHED SUCCESFULLY******")

  def run_converter(self, command: str, source_dir: str, target_dir: str, img_dir: str = ''):
    assert command
    assert os.path.exists(target_dir)
    assert os.path.exists(source_dir)
    assert os.path.exists(_sConverterPath := (os.path.join(self.ACLocation.get(), LP_XML_CONVERTER)))
    assert os.path.exists(img_dir) or not img_dir

    lImgCommand = ['-img', img_dir] if img_dir else []
    # sImgCommand = f' -img "{img_dir}" ' if img_dir else ''


    print("Command:")
    print(" ".join([_sConverterPath, command, *lImgCommand, source_dir, target_dir]))

    import subprocess
    result = subprocess.run(
      [_sConverterPath, command, *lImgCommand, source_dir, target_dir],
      capture_output=True, text=True, encoding="utf-8")
    output = result.stdout
    print(output)

  def destroyApp(self, ):
    if self.bDebug.get():
      self.currentConfig.writeConfigBack(default=True, exclude_list=['bDebug'])
    else:
      self.currentConfig.update_current_vars()
      self.currentConfig.writeConfigBack(default=False)
    self.loop.stop()
    self.top.destroy()

  def reconnect(self):
    # FIXME
    """Meaningful when overwriting XMLs:
    """
    pass

  @staticmethod
  def __unmarkFileName(inFileName):
    """removes remarks form on the GUI displayed filenames, like * at the beginning"""
    if inFileName in DestXML.dest_dict:
      return inFileName
    elif inFileName[:2] == '* ':
      if inFileName[2:] in DestXML.dest_dict:
        return inFileName [2:]

# ------------------- Google SpreadSheet infield window ------

class GoogleSSInfield(tk.Frame):
  def __init__(self, sender):
    tk.Frame.__init__(self)
    self.top = tk.Toplevel()

    self.GoogleSSURL = tk.Entry(self.top, {"width": 40,})
    self.GoogleSSURL.grid({"row": 0, "column": 0})

    self.OKButton = tk.Button(self.top, {"text": "OK", "command": sender.getFromGoogleSpreadsheet, })
    self.OKButton.grid({"row": 0, "column": 1})

    self.top.bind('<Return>', sender.getFromGoogleSpreadsheet)

# ------------------- Parameter editing window ------

# -------------------/GUI------------------------------
# -------------------/GUI------------------------------
# -------------------/GUI------------------------------

from dataclasses import dataclass
@dataclass
class ProcessData:
  dest_xml: DestXML
  dest_dir: str
  overwrite: bool
  string_to: str

def processOneXML(data: ProcessData):
  dest = data.dest_xml

  src = dest.sourceFile
  srcPath = src.fullPath
  destPath = os.path.join(data.dest_dir, dest.relPath)
  destDir = os.path.dirname(destPath)

  assert os.path.exists(data.dest_dir)
  assert os.path.exists(srcPath)
  assert not os.path.exists(destPath) or os.access(destPath, os.W_OK)

  print("%s -> %s" % (srcPath, destPath,))

  # FIXME multithreading, map-reduce
  mdp = etree.parse(srcPath, etree.XMLParser(strip_cdata=False))
  mdp.getroot().attrib[dest.sourceFile.ID] = dest.guid
  # FIXME what if calledmacros are not overwritten?
  if data.overwrite and dest.retainedCalledMacros:
    cmRoot = mdp.find("./CalledMacros")
    for m in mdp.findall("./CalledMacros/Macro"):
      cmRoot.remove(m)

    for key, cM in dest.retainedCalledMacros.items():
      macro = etree.Element("Macro")

      mName = etree.Element("MName")
      mName.text = etree.CDATA('"' + cM + '"')
      macro.append(mName)

      guid = etree.Element(dest.sourceFile.ID)
      guid.text = key
      macro.append(guid)

      cmRoot.append(macro)
  else:
    for m in mdp.findall("./CalledMacros/Macro"):
      for dI in list(DestXML.dest_dict.keys()):
        d = DestXML.dest_dict[dI]
        if m.find("MName").text.strip("'" + '"') == d.sourceFile.name:
          m.find("MName").text = etree.CDATA('"' + d.name + '"')
          m.find(dest.sourceFile.ID).text = d.guid

  for sect in ["./Script_2D", "./Script_3D", "./Script_1D", "./Script_PR", "./Script_UI", "./Script_VL",
               "./Script_FWM", "./Script_BWM", ]:
    section = mdp.find(sect)
    if section is not None:
      section.text = etree.CDATA(replace_filenames(data.string_to, DestXML.dest_dict, DestResource.pict_dict, section.text))

  # ---------------------Prevpict-------------------------------------------------------
  if dest.bPlaceable:
    section = mdp.find('Picture')
    if isinstance(section, etree._Element) and 'path' in section.attrib:
      path = os.path.basename(section.attrib['path']).upper()
      if path:
        n = next((DestResource.pict_dict[p].relPath for p in list(DestResource.pict_dict.keys()) if
                  os.path.basename(DestResource.pict_dict[p].sourceFile.relPath).upper() == path), None)
        if n:
          section.attrib['path'] = os.path.dirname(n) + "/" + os.path.basename(n)  # Not os.path.join!
  # ---------------------AC18 and over: adding licensing statically---------------------
  # if dest.iVersion >= AC_18:
  #   for cr in mdp.getroot().findall("Copyright"):
  #     mdp.getroot().remove(cr)
  #
  #   eCopyright = etree.Element("Copyright", SectVersion="1", SectionFlags="0", SubIdent="0")
  #   eAuthor = etree.Element("Author")
  #   eCopyright.append(eAuthor)
  #   eAuthor.text = dest.author
  #
  #   eLicense = etree.Element("License")
  #   eCopyright.append(eLicense)
  #
  #   eLType = etree.Element("Type")
  #   eLicense.append(eLType)
  #   eLType.text = dest.license
  #
  #   eLVersion = etree.Element("Version")
  #   eLicense.append(eLVersion)
  #
  #   eLVersion.text = dest.licneseVersion
  #
  #   mdp.getroot().append(eCopyright)
  # ---------------------BO_update---------------------
  parRoot = mdp.find("./ParamSection")
  parPar = parRoot.getparent()
  parPar.remove(parRoot)
  destPar = dest.parameters.toEtree()
  parPar.append(destPar)
  # ---------------------Ancestries--------------------
  # FIXME not clear, check, writes an extra empty mainunid field
  # FIXME ancestries to be used in param checking
  # FIXME this is unclear what id does
  for m in mdp.findall("./Ancestry/" + dest.sourceFile.ID):
    guid = m.text
    if guid in DestXML.id_dict:
      print("ANCESTRY: %s" % guid)
      par = m.getparent()
      par.remove(m)

      element = etree.Element(dest.sourceFile.ID)
      element.text = DestXML.id_dict[guid]
      element.tail = '\n'
      par.append(element)
  try:
    os.makedirs(destDir)
  except WindowsError:
    pass
  with open(destPath, "wb") as file_handle:
    mdp.write(file_handle, pretty_print=True, encoding="UTF-8", )


# @Recorder()
def replace_filenames(StringTo:str, dest_dict:dict, pict_dict:dict, text: str | etree.CDATA) -> str:
  for dI in list(dest_dict.keys()):
    text = re.sub(r'(?<=[,"\'`\s])' + dest_dict[dI].sourceFile.name + r'(?=[,"\'`\s])', dest_dict[dI].name, text,
                  flags=re.IGNORECASE)
  # Replacing images:
  for pr in sorted(list(pict_dict.keys()), key=lambda x: -len(x)):
    text = re.sub(r'(?<=[,"\'`\s])' + pict_dict[pr].sourceFile.fileNameWithOutExt + '(?!' + StringTo + ')',
                  pict_dict[pr].fileNameWithOutExt, text, flags=re.IGNORECASE)
  return text


if __name__ == "__main__":
  app = GUIApp()
  app.mainloop()

