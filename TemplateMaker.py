#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-
#HOTFIXREQ if image dest folder is retained, remove common images from it
#HOTFIXREQ ImportError: No module named googleapiclient.discovery
#HOTFIXREQ unicode error when running ac command in path with native characters
#HOTFIXREQ SOURCE_IMAGE_DIR_NAME images are not renamed at all
#FIXME renaming errors and param csv parameter overwriting
#FIXME append param to the end when no argument for position
#FIXME library_images copy always as temporary folder; instead junction
#FIXME param editor should offer auto param inserting from Listing Parameters Google Spreadsheet
#FIXME automatic checking and warning of (collected) old project's names
#FIXME UI process messages
#FIXME MigrationTable progressing
#FIXME GDLPict progressing
# TODO When there is nothing to replace at the beginning of the source names, many unwanted things are renamed in the code
import os.path
from os import listdir
import uuid
import re
import tempfile
from subprocess import check_output
import shutil

import string

import tkinter as tk
import tkinter.filedialog
# import urllib, httplib
import copy
import argparse

from configparser import *  #FIXME not *
import csv

import http.client, urllib.request, urllib.parse, urllib.error, json, webbrowser, urllib.parse, os, hashlib, base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import pip
import multiprocessing as mp
from functools import reduce

try:
    import googleapiclient.errors
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow, Flow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

except ImportError:
    pip.main(['install', '--user', 'google-api-python-client'])
    pip.main(['install', '--user', 'google-auth-httplib2'])
    pip.main(['install', '--user', 'google-auth-oauthlib'])

    import googleapiclient.errors
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

try:
    from lxml import etree
except ImportError:
    pip.main(['install', '--user', 'lxml'])
    from lxml import etree

from GSMParamLib import *
from GSMXMLLib import *
from SamUITools import *

PERSONAL_ID = "ac4e5af2-7544-475c-907d-c7d91c810039"    #FIXME to be deleted after BO API v1 is removed

ID = ''
LISTBOX_SEPARATOR = '--------'
AC_18   = 28
SCRIPT_NAMES_LIST = ["Script_1D",
                     "Script_2D",
                     "Script_3D",
                     "Script_PR",
                     "Script_UI",
                     "Script_VL",
                     "Script_FWM",
                     "Script_BWM",]

PAR_UNKNOWN     = 0
PAR_LENGTH      = 1
PAR_ANGLE       = 2
PAR_REAL        = 3
PAR_INT         = 4
PAR_BOOL        = 5
PAR_STRING      = 6
PAR_MATERIAL    = 7
PAR_LINETYPE    = 8
PAR_FILL        = 9
PAR_PEN         = 10
PAR_SEPARATOR   = 11
PAR_TITLE       = 12
PAR_COMMENT     = 13

PARFLG_CHILD    = 1
PARFLG_BOLDNAME = 2
PARFLG_UNIQUE   = 3
PARFLG_HIDDEN   = 4

app = None

dest_sourcenames    = {}   #source name     -> DestXMLs, idx by original filename #☺FIXME could be a set
dest_guids          = {}   #dest guid       -> DestXMLs, idx by
source_guids        = {}   #Source GUID     -> Source XMLs, idx by
id_dict             = {}   #Source GUID     -> dest GUID
dest_dict           = {}   #dest name       -> DestXML
replacement_dict    = {}   #source filename -> SourceXMLs
pict_dict           = {}
source_pict_dict    = {}

all_keywords = set()

# ------------------- Google Spreadsheet API connectivity --------------------------------------------------------------

class NoGoogleCredentialsException(Exception):
    pass

class GoogleSpreadsheetConnector(object):
    GOOGLE_SPREADSHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def __init__(self, inCurrentConfig, inSpreadsheetID):
        #FIXME renaming/filling out these
        client_config = {"installed": {
            "client_id": "224241213692-7gafn34d4heprhps1rod3clt1b8j07j6.apps.googleusercontent.com",
            "project_id": "quickstart-1558854893881",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "PHWQx7k6ldF73rDkqJE2Cedl",
            "redirect_uris": {
                "urn:ietf:wg:oauth:2.0:oob",
                "http://localhost"}
        }}

        try:
            if  inCurrentConfig.has_option("GoogleSpreadsheetAPI", "access_token") and \
                inCurrentConfig.has_option("GoogleSpreadsheetAPI", "refresh_token") and \
                inCurrentConfig.has_option("GoogleSpreadsheetAPI", "token_type") and \
                inCurrentConfig.has_option("GoogleSpreadsheetAPI", "id_token") and \
                inCurrentConfig.has_option("GoogleSpreadsheetAPI", "token_uri") and \
                inCurrentConfig.has_option("GoogleSpreadsheetAPI", "client_id")and \
                inCurrentConfig.has_option("GoogleSpreadsheetAPI", "client_secret"):

                self.googleCreds = Credentials(
                    token=          inCurrentConfig.get("GoogleSpreadsheetAPI", "access_token"),
                    refresh_token=  inCurrentConfig.get("GoogleSpreadsheetAPI", "refresh_token"),
                    id_token=       inCurrentConfig.get("GoogleSpreadsheetAPI", "id_token"),
                    token_uri=      inCurrentConfig.get("GoogleSpreadsheetAPI", "token_uri"),
                    client_id=      inCurrentConfig.get("GoogleSpreadsheetAPI", "client_id"),
                    client_secret=  inCurrentConfig.get("GoogleSpreadsheetAPI", "client_secret"),
                    scopes=         GoogleSpreadsheetConnector.GOOGLE_SPREADSHEET_SCOPES
                )

                if not self.googleCreds.valid:
                    if self.googleCreds.expired and self.googleCreds.refresh_token:
                        self.googleCreds.refresh(Request())
                    else:
                        raise NoGoogleCredentialsException
            else:
                raise NoGoogleCredentialsException

        except (NoSectionError, NoOptionError, NoGoogleCredentialsException):
            flow = InstalledAppFlow.from_client_config(client_config, GoogleSpreadsheetConnector.GOOGLE_SPREADSHEET_SCOPES)
            self.googleCreds = flow.run_local_server()

        service = build('sheets', 'v4', credentials=self.googleCreds)

        sheet = service.spreadsheets()

        sheetName = sheet.get(spreadsheetId=inSpreadsheetID,
                              includeGridData=True).execute()['sheets'][0]['properties']['title']

        result = list(sheet.values()).get(spreadsheetId=inSpreadsheetID,
                                    range=sheetName).execute()

        self.values = result.get('values', [])

        if not self.values:
            print('No data found.')
        # else:
        #     for row in self.values:
        #         print('%s, %s' % (row[0], row[4]))


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
    def __init__(self, top, _dict):
        if "target" in _dict:
            self.target = _dict["target"]
            del _dict["target"]
        if "imgTarget" in _dict:
            self.imgTarget = _dict["imgTarget"]
            del _dict["imgTarget"]
        if "dict" in _dict:
            self.dict = _dict["dict"]
            del _dict["dict"]
        tk.Listbox.__init__(self, top, _dict, selectmode=tk.EXTENDED)

    def refresh(self, *_):
        if self.dict == replacement_dict:
            try:
                scanDirs(self.target.get(), SourceXMLDirName.get())
                scanDirs(self.imgTarget.get(), SourceImageDirName.get())
            except AttributeError:
                return
        self.delete(0, tk.END)
        _prevObj = None
        for f in sorted([self.dict[k] for k in list(self.dict.keys())]):
            try:
                if _prevObj and _prevObj.dirName != f.dirName:
                    self.insert(tk.END, LISTBOX_SEPARATOR + os.path.basename(os.path.normpath(f.dirName)))
                _prevObj = f
                if f.warnings:
                    self.insert(tk.END, "* " + f.name)
                self.insert(tk.END, f.name)
            except AttributeError:
                self.insert(tk.END, f.name)


class GUIApp(tk.Frame):
    def __init__(self):
        tk.Frame.__init__(self)
        self.top = self.winfo_toplevel()

        self.currentConfig = ConfigParser()
        self.appDataDir  = os.getenv('APPDATA')
        if os.path.isfile(self.appDataDir  + r"\TemplateMarker.ini"):
            self.currentConfig.read(self.appDataDir  + r"\TemplateMarker.ini")
        else:
            self.currentConfig.read("TemplateMarker.ini")    #TODO into a different class or stg

        self.SourceXMLDirName   = tk.StringVar()
        self.SourceGDLDirName   = tk.StringVar()
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

        self.bCheckParams       = tk.BooleanVar()
        self.bDebug             = tk.BooleanVar()
        self.bCleanup           = tk.BooleanVar()
        self.bOverWrite         = tk.BooleanVar()
        self.bAddStr            = tk.BooleanVar()
        self.doBOUpdate         = tk.BooleanVar()

        self.bXML               = tk.BooleanVar()
        self.bGDL               = tk.BooleanVar()
        self.isSourceGDL        = tk.BooleanVar()

        self.observer  = None

        self.warnings = []

        self.bo                 = None
        self.googleSpreadsheet  = None
        self.bWriteToSelf       = False             # Whether to write back to the file itself

        global \
            SourceXMLDirName, SourceGDLDirName, TargetXMLDirName, TargetGDLDirName, SourceImageDirName, TargetImageDirName, \
            AdditionalImageDir, bDebug, bCleanup, bCheckParams, ACLocation, bGDL, bXML, dest_dict, dest_guids, replacement_dict, id_dict, \
            pict_dict, source_pict_dict, source_guids, bAddStr, bOverWrite, all_keywords, StringTo, doBOUpdate, bWriteToSelf

        SourceXMLDirName    = self.SourceXMLDirName
        SourceGDLDirName    = self.SourceGDLDirName
        TargetXMLDirName    = self.TargetXMLDirName
        TargetGDLDirName    = self.TargetGDLDirName
        SourceImageDirName  = self.SourceImageDirName
        TargetImageDirName  = self.TargetImageDirName
        AdditionalImageDir  = self.AdditionalImageDir
        bCheckParams        = self.bCheckParams
        bDebug              = self.bDebug
        bCleanup            = self.bCleanup
        bXML                = self.bXML
        bGDL                = self.bGDL
        doBOUpdate          = self.doBOUpdate
        ACLocation          = self.ACLocation
        bAddStr             = self.bAddStr
        bOverWrite          = self.bOverWrite
        StringTo            = self.StringTo
        bWriteToSelf        = self.bWriteToSelf

        __tooltipIDPT1 = "Something like E:/_GDL_SVN/_TEMPLATE_/AC18_Opening/library"
        __tooltipIDPT2 = "Images' dir that are NOT to be renamed per project and compiled into final gdls (prev pics, for example), something like E:\_GDL_SVN\_TEMPLATE_\AC18_Opening\library_images"
        __tooltipIDPT3 = "Something like E:/_GDL_SVN/_TARGET_PROJECT_NAME_/library"
        __tooltipIDPT4 = "Final GDL output dir"
        __tooltipIDPT5 = "If set, copy project specific pictures here, too, for endcoded images. Something like E:/_GDL_SVN/_TARGET_PROJECT_NAME_/library_images"
        __tooltipIDPT6 = "Additional images' dir, for all other images, which can be used by any projects, something like E:/_GDL_SVN/_IMAGES_GENERIC_"
        __tooltipIDPT7 = "Source GDL folder name"

        try:
            for cName, cValue in self.currentConfig.items('ArchiCAD'):
                try:
                    if   cName == 'bgdl':               self.bGDL.set(cValue)
                    elif cName == 'bxml':               self.bXML.set(cValue)
                    elif cName == 'bdebug':             self.bDebug.set(cValue)
                    elif cName == 'additionalimagedir': self.AdditionalImageDir.set(cValue)
                    elif cName == 'aclocation':         self.ACLocation.set(cValue)
                    elif cName == 'stringto':           self.StringTo.set(cValue)
                    elif cName == 'stringfrom':         self.StringFrom.set(cValue)
                    elif cName == 'inputimagesource':   self.SourceImageDirName.set(cValue)
                    elif cName == 'inputimagetarget':   self.TargetImageDirName.set(cValue)
                    elif cName == 'imgstringfrom':      self.ImgStringFrom.set(cValue)
                    elif cName == 'imgstringto':        self.ImgStringTo.set(cValue)
                    elif cName == 'sourcedirname':      self.SourceXMLDirName.set(cValue)
                    elif cName == 'xmltargetdirname':   self.TargetXMLDirName.set(cValue)
                    elif cName == 'gdltargetdirname':   self.TargetGDLDirName.set(cValue)
                    elif cName == 'baddstr':            self.bAddStr.set(cValue)
                    elif cName == 'boverwrite':         self.bOverWrite.set(cValue)
                    elif cName == 'allkeywords':
                        all_keywords |= set(v.strip() for v in cValue.split(',') if v !='')
                except NoOptionError:
                    print("NoOptionError")
                    continue
                except NoSectionError:
                    print("NoSectionError")
                    continue
                except ValueError:
                    print("ValueError")
                    continue
        except NoSectionError:
            print("NoSectionError")

        self.observerXML = self.bXML.trace_variable("w", self.targetXMLModified)
        self.observerGDL = self.bGDL.trace_variable("w", self.targetGDLModified)

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

        self.listBox = ListboxWithRefresh(self.InputFrameS[iF], {"target": self.SourceXMLDirName, "imgTarget": self.SourceImageDirName, "dict": replacement_dict})
        self.listBox.grid({"row": 0, "column": 0, "sticky": tk.E + tk.W + tk.N + tk.S})
        self.observerLB1 = self.SourceXMLDirName.trace_variable("w", self.listBox.refresh)
        self.observerLB2 = self.SourceGDLDirName.trace_variable("w", self.processGDLDir)

        self.ListBoxScrollbar = tk.Scrollbar(self.InputFrameS[iF])
        self.ListBoxScrollbar.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox.config(yscrollcommand=self.ListBoxScrollbar.set)
        self.ListBoxScrollbar.config(command=self.listBox.yview)

        iF += 1

        self.listBox2 = ListboxWithRefresh(self.InputFrameS[iF], {"target": self.SourceXMLDirName, "dict": source_pict_dict})
        self.listBox2.grid({"row": 0, "column": 0, "sticky": tk.NE + tk.SW})
        self.observerLB2 = self.SourceXMLDirName.trace_variable("w", self.listBox2.refresh)

        if SourceXMLDirName:
            self.listBox.refresh()
            self.listBox2.refresh()

        self.ListBoxScrollbar2 = tk.Scrollbar(self.InputFrameS[iF])
        self.ListBoxScrollbar2.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox2.config(yscrollcommand=self.ListBoxScrollbar2.set)
        self.ListBoxScrollbar2.config(command=self.listBox2.yview)

        iF += 1

        self.sourceImageDir = InputDirPlusText(self.InputFrameS[iF], "Images' source folder", self.SourceImageDirName, __tooltipIDPT2)
        if SourceXMLDirName:
            self.listBox.refresh()
            self.listBox2.refresh()

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

        iF += 1

        self.XMLDir = InputDirPlusBool(self.outputFrameS[iF], "XML Destination folder",      self.TargetXMLDirName, self.bXML, __tooltipIDPT3)

        iF += 1

        self.GDLDir = InputDirPlusBool(self.outputFrameS[iF], "GDL Destination folder",      self.TargetGDLDirName, self.bGDL, __tooltipIDPT4)

        iF += 1

        self.listBox3 = ListboxWithRefresh(self.outputFrameS[iF], {'dict': dest_dict})
        self.listBox3.grid({"row": 0, "column": 0, "sticky": tk.SE + tk.NW})

        self.ListBoxScrollbar3 = tk.Scrollbar(self.outputFrameS[iF])
        self.ListBoxScrollbar3.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox3.config(yscrollcommand=self.ListBoxScrollbar3.set)
        self.ListBoxScrollbar3.config(command=self.listBox3.yview)

        self.listBox3.bind("<<ListboxSelect>>", self.listboxselect)

        iF += 1

        self.listBox4 = ListboxWithRefresh(self.outputFrameS[iF], {'dict': pict_dict})
        self.listBox4.grid({"row": 0, "column": 0, "sticky": tk.SE + tk.NW})

        self.ListBoxScrollbar4 = tk.Scrollbar(self.outputFrameS[iF])
        self.ListBoxScrollbar4.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox4.config(yscrollcommand=self.ListBoxScrollbar4.set)
        self.ListBoxScrollbar4.config(command=self.listBox4.yview)
        self.listBox4.bind("<<ListboxSelect>>", self.listboxImageSelect)

        iF += 1

        InputDirPlusText(self.outputFrameS[iF], "Images' destination folder",  self.TargetImageDirName, __tooltipIDPT5)

        # ------------------------------------
        # bottom row for project general settings
        # ------------------------------------

        iF = 0

        self.bottomFrame        = tk.Frame(self.top, )
        self.bottomFrame.grid({"row":1, "column": 0, "columnspan": 7, "sticky":  tk.S + tk.N, })

        self.buttonACLoc = tk.Button(self.bottomFrame, {"text": "ArchiCAD location", "command": self.setACLoc, })
        self.buttonACLoc.grid({"row": 0, "column": iF, }); iF += 1

        self.ACLocEntry                 = tk.Entry(self.bottomFrame, {"width": 40, "textvariable": self.ACLocation, })
        self.ACLocEntry.grid({"row": 0, "column": iF}); iF += 1

        self.buttonAID = tk.Button(self.bottomFrame, {"text": "Additional images' folder", "command": self.setAdditionalImageDir, })
        self.buttonAID.grid({"row": 0, "column": iF, }); iF += 1

        self.AdditionalImageDirEntry    = tk.Entry(self.bottomFrame, {"width": 40, "textvariable": self.AdditionalImageDir, })
        self.AdditionalImageDirEntry.grid({"row": 0, "column": iF}); iF += 1

        self.paramCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Check Parameters", "variable": self.bCheckParams})
        self.paramCheckButton.grid({"row": 0, "column": iF}); iF += 1

        self.debugCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Debug", "variable": self.bDebug})
        self.debugCheckButton.grid({"row": 0, "column": iF}); iF += 1

        self.cleanupCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Cleanup", "variable": self.bCleanup})
        self.cleanupCheckButton.grid({"row": 0, "column": iF}); iF += 1

        self.bAddStrCheckButton = tk.Checkbutton(self.bottomFrame, {"text": "Always add strings", "variable": self.bAddStr})
        self.bAddStrCheckButton.grid({"row": 0, "column": iF}); iF += 1

        self.OverWriteCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Overwrite", "variable": self.bOverWrite})
        self.OverWriteCheckButton.grid({"row": 0, "column": iF}); iF += 1

        self.BOUpdateCheckButton    = tk.Checkbutton(self.bottomFrame, {"text": "BO_update", "variable": self.doBOUpdate})
        self.OverWriteCheckButton.grid({"row": 0, "column": iF}); iF += 1

        self.startButton        = tk.Button(self.bottomFrame, {"text": "Start", "command": self.start})
        self.startButton.grid({"row": 0, "column": 7, "sticky": tk.E})

        # ----buttons---------------------------------------------------------------------------------------------------

        self.buttonFrame        = tk.Frame(self.top)
        self.buttonFrame.grid({"row": 0, "column": 1})

        _i = 0

        self.addAllButton       = tk.Button(self.buttonFrame, {"text": ">>", "command": self.addAllFiles})
        self.addAllButton.grid({"row":_i, "column": 0})

        _i += 1

        self.addRecursiveButton = tk.Button(self.buttonFrame, {"text": "Recursive >", "command": self.addMoreFilesRecursively})
        self.addRecursiveButton.grid({"row":_i, "column": 0, "sticky": tk.W + tk.E})
        CreateToolTip(self.addRecursiveButton, "Add macro, and all its called macro and subtypes recursively, if not added already")

        _i += 1

        self.addButton          = tk.Button(self.buttonFrame, {"text": ">", "command": self.addMoreFiles})
        self.addButton.grid({"row":_i, "column": 0, "sticky": tk.W + tk.E})

        _i += 1

        self.delButton          = tk.Button(self.buttonFrame, {"text": "X", "command": self.delFile})
        self.delButton.grid({"row":_i, "column": 0, "sticky": tk.W + tk.E})

        _i += 1

        self.resetButton         = tk.Button(self.buttonFrame, {"text": "Reset", "command": self.resetAll })
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

        #FIXME
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
        CreateToolTip(self.buttonAID, __tooltipIDPT6)

    def createDestItems(self, inList):
        firstRow = inList[0]

        for row in inList[1:]:
            if firstRow[1] == "":
                #empty header => row[1] is for destItem
                destItem = self.addFileRecursively(row[0], row[1])

            else:
                #no destitem so write to itself
                destItem = DestXML(row[0], targetFileName=row[0])
                dest_dict[destItem.name.upper()] = destItem
                dest_guids[destItem.guid] = destItem
                dest_sourcenames[destItem.sourceFile.name] = destItem
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

        try:
            self.googleSpreadsheet = GoogleSpreadsheetConnector(self.currentConfig, SpreadsheetID)
        except googleapiclient.errors.HttpError:
            print(("HttpError: Spreadsheet ID (%s) seems to be invalid" % SSIDRegex))
            return
        self.GoogleSSInfield.top.destroy()
        self.createDestItems(self.googleSpreadsheet.values)

    def paramWrite(self):
        """
        This method should write params directly into selected .GSMs/.XLSs
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
        PRODATURL   = 2
        VALUES      = 3
        csvFileName = tkinter.filedialog.askopenfilename(initialdir="/", title="Select folder", filetypes=(("CSV files", "*.csv"), ("all files","*.*")))
        if csvFileName:
            with open(csvFileName, "r") as csvFile:
                firstRow = next(csv.reader(csvFile))
                for row in csv.reader(csvFile):
                    destItem = self.addFileRecursively(row[SRC_NAME], row[TARG_NAME])
                    if row[PRODATURL]:
                        destItem.parameters.BO_update(row[PRODATURL])
                    if len(row) > 3 and next((c for c in row[PRODATURL:] if c != ""), ""):
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

    def getFromGoogleSpreadsheet(self, *args):
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

        try:
            self.googleSpreadsheet = GoogleSpreadsheetConnector(self.currentConfig, SpreadsheetID)
        except googleapiclient.errors.HttpError:
            self.GoogleSSInfield.top.destroy()
            return
        #FIXME above here paramWrite uses the same
        #FIXME from here maybe to put into a method; same as in getFromCSV
        firstRow = self.googleSpreadsheet.values[0]

        for row in self.googleSpreadsheet.values[1:]:
            destItem = self.addFileRecursively(row[0], row[1])
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

    def setACLoc(self):
        ACLoc = tkinter.filedialog.askdirectory(initialdir="/", title="Select ArchiCAD folder")
        self.ACLocation.set(ACLoc)

    def setAdditionalImageDir(self):
        AIDLoc = tkinter.filedialog.askdirectory(initialdir="/", title="Select additional images' folder")
        self.AdditionalImageDir.set(AIDLoc)

    def processGDLDir(self, *_):
        '''
        When self.SourceGDLDirName is modified, convert files to xml and set ui accordingly
        :return:
        '''
        global SourceXMLDirName, SourceImageDirName
        if not self.SourceGDLDirName.get():
            return
        self.tempXMLDir = tempfile.mkdtemp()
        self.tempImgDir = tempfile.mkdtemp()
        print("tempXMLDir: %s" % self.tempXMLDir)
        print("tempImgDir: %s" % self.tempImgDir)
        print("SourceGDLDirName %s" % self.SourceGDLDirName.get())
        l2xCommand = '"%s" l2x -img "%s" "%s" "%s"' % (os.path.join(ACLocation.get(), 'LP_XMLConverter.exe'), self.tempImgDir, self.SourceGDLDirName.get(), self.tempXMLDir)
        print("l2xCommand: %s" % l2xCommand)
        check_output(l2xCommand, shell=True)
        self.inputXMLDir.idpt.entryDirName.config(cnf={'state': tk.NORMAL})
        self.sourceImageDir.entryDirName.config(cnf={'state': tk.NORMAL})
        self.sourceImageDir.buttonDirName.config(cnf={'state': tk.NORMAL})
        self.SourceXMLDirName.set(self.tempXMLDir)
        self.SourceImageDirName.set(self.tempImgDir)
        self.inputXMLDir.idpt.entryDirName.config(cnf={'state': tk.DISABLED})
        self.sourceImageDir.entryDirName.config(cnf={'state': tk.DISABLED})
        self.sourceImageDir.buttonDirName.config(cnf={'state': tk.DISABLED})
        self.listBox.refresh()
        self.listBox2.refresh()

    def targetGDLModified(self, *_):
        if not self.bGDL.get():
            self.bXML.set(True)

    def targetXMLModified(self, *_):
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

    @staticmethod
    def start():
        main2()
        # print "Starting conversion"

    def addFile(self, sourceFileName='', targetFileName=''):
        if not sourceFileName:
            sourceFileName = self.listBox.get(tk.ACTIVE)
        if sourceFileName.startswith(LISTBOX_SEPARATOR):
            self.listBox.select_clear(tk.ACTIVE)
            return
        if sourceFileName.upper() in replacement_dict:
            if targetFileName:
                destItem = DestXML(replacement_dict[sourceFileName.upper()], targetFileName=targetFileName)
            else:
                destItem = DestXML(replacement_dict[sourceFileName.upper()], self.StringFrom.get(), self.StringTo.get())
            dest_dict[destItem.name.upper()] = destItem
            dest_guids[destItem.guid] = destItem
            dest_sourcenames[destItem.sourceFile.name] = destItem
        else:
            #File should be in library_additional, possibly worth of checking it or add a warning
            return
        self.refreshDestItem()
        return destItem

    def addMoreFiles(self):
        for sourceFileIndex in self.listBox.curselection():
            self.addFile(sourceFileName=self.listBox.get(sourceFileIndex))

    def addImageFile(self, fileName=''):
        if not fileName:
            fileName = self.listBox2.get(tk.ACTIVE)
        if not fileName.upper() in pict_dict and not fileName.startswith(LISTBOX_SEPARATOR):
            destItem = DestResource(source_pict_dict[fileName.upper()], self.StringFrom.get(), self.StringTo.get())
            pict_dict[destItem.fileNameWithExt.upper()] = destItem
        self.refreshDestItem()

    def addAllFiles(self):
        for filename in self.listBox.get(0, tk.END):
            self.addFile(filename)

        for imageFileName in self.listBox2.get(0, tk.END):
            self.addImageFile(imageFileName)

        self.addAllButton.config({"state": tk.DISABLED})

    def addFileRecursively(self, sourceFileName='', targetFileName=''):
        if not sourceFileName:
            sourceFileName = self.listBox.get(tk.ACTIVE)

        destItem = self.addFile(sourceFileName, targetFileName)

        if sourceFileName.upper() not in replacement_dict:
            #should be in library_additional
            return

        x = replacement_dict[sourceFileName.upper()]

        for k, v in x.calledMacros.items():
            if v not in dest_sourcenames:
                self.addFileRecursively(v)

        for parentGUID in x.parentSubTypes:
            if parentGUID not in id_dict:
                if parentGUID in source_guids:
                    self.addFileRecursively(source_guids[parentGUID])

        for pict in list(source_pict_dict.values()):
            for script in list(x.scripts.values()):
                if pict.fileNameWithExt.upper() in script or pict.fileNameWithOutExt.upper() in script.upper():
                    self.addImageFile(pict.fileNameWithExt)
            if pict.fileNameWithExt.upper() in x.gdlPicts:
                self.addImageFile(pict.fileNameWithExt)

        if x.prevPict:
            bN = os.path.basename(x.prevPict)
            self.addImageFile(bN)

        self.refreshDestItem()
        return destItem

    def addMoreFilesRecursively(self):
        for sourceFileIndex in self.listBox.curselection():
            self.addFileRecursively(sourceFileName=self.listBox.get(sourceFileIndex))

    def delFile(self, fileName = ''):
        if not fileName:
            fileName = self.listBox3.get(tk.ACTIVE)
        if fileName.startswith(LISTBOX_SEPARATOR):
            self.listBox3.select_clear(tk.ACTIVE)
            return

        fN = self.__unmarkFileName(fileName).upper()
        del dest_sourcenames [ dest_dict[fN].sourceFile.name ]
        del dest_guids[ dest_dict[fN].guid ]
        del dest_dict[fN]
        self.listBox3.refresh()
        if not dest_dict and not pict_dict:
            self.addAllButton.config({"state": tk.NORMAL})
        self.fileName.set('')

    def resetAll(self):
        self.XMLDir.config(state=tk.NORMAL)
        self.GDLDir.config(state=tk.NORMAL)

        dest_dict.clear()
        dest_guids.clear()
        dest_sourcenames.clear()
        replacement_dict.clear()
        id_dict.clear()
        source_guids.clear()
        pict_dict.clear()
        source_pict_dict.clear()

        self.listBox.refresh()
        self.listBox2.refresh()
        self.listBox3.refresh()
        self.listBox4.refresh()

        for w in self.warnings:
            w.destroy()

        self.addAllButton.config({"state": tk.NORMAL})
        self.sourceImageDir.entryDirName.config(cnf={'state': tk.NORMAL})
        self.sourceImageDir.buttonDirName.config(cnf={'state': tk.NORMAL})

    def listboxselect(self, event, ):
        if not event.widget.get(0):
            return
        if event.widget.get(event.widget.curselection()[0]).startswith(LISTBOX_SEPARATOR):
            return

        currentSelection = event.widget.get(int(event.widget.curselection()[0])).upper()
        if currentSelection[:2] == "* ":
            currentSelection = currentSelection[2:]
        self.destItem = dest_dict[currentSelection]
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

        self.authorEntry.delete(0, tk.END)
        self.authorEntry.insert(0, self.destItem.author)
        self.licenseEntry.delete(0, tk.END)
        self.licenseEntry.insert(0, self.destItem.license)
        self.licenseVersionEntry.delete(0, tk.END)
        self.licenseVersionEntry.insert(0, self.destItem.licneseVersion)

        for w in self.warnings:
            w.destroy()
        self.warnings = [tk.Label(self.warningFrame, {"text": w}) for w in self.destItem.warnings]
        for w, n in zip(self.warnings, list(range(len(self.warnings)))):
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
        # FIXME encrypting of sensitive data

        currentConfig = RawConfigParser()
        currentConfig.add_section("ArchiCAD")
        currentConfig.set("ArchiCAD", "aclocation",         self.ACLocEntry.get())
        currentConfig.set("ArchiCAD", "additionalimagedir", self.AdditionalImageDirEntry.get())

        currentConfig.set("ArchiCAD", "bdebug",             self.bDebug.get())
        currentConfig.set("ArchiCAD", "bxml",               self.bXML.get())
        currentConfig.set("ArchiCAD", "bgdl",               self.bGDL.get())
        if not self.isSourceGDL.get():
            currentConfig.set("ArchiCAD", "sourcedirname",      self.SourceXMLDirName.get())
            currentConfig.set("ArchiCAD", "inputimagesource",   self.SourceImageDirName.get())
        currentConfig.set("ArchiCAD", "xmltargetdirname",   self.TargetXMLDirName.get())
        currentConfig.set("ArchiCAD", "gdltargetdirname",   self.TargetGDLDirName.get())
        currentConfig.set("ArchiCAD", "inputimagetarget",   self.TargetImageDirName.get())
        currentConfig.set("ArchiCAD", "stringfrom",         self.StringFrom.get())
        currentConfig.set("ArchiCAD", "stringto",           self.StringTo.get())
        currentConfig.set("ArchiCAD", "imgstringfrom",      self.ImgStringFrom.get())
        currentConfig.set("ArchiCAD", "imgstringto",        self.ImgStringTo.get())
        currentConfig.set("ArchiCAD", "baddstr",            self.bAddStr.get())
        currentConfig.set("ArchiCAD", "boverwrite",         self.bOverWrite.get())
        currentConfig.set("ArchiCAD", "allkeywords",        ', '.join(sorted(list(all_keywords))))

        if self.bo:
            currentConfig.add_section("BOAPIv2")
            currentConfig.set("BOAPIv2", "token_type",          self.bo.token_type)
            currentConfig.set("BOAPIv2", "refresh_token",       self.bo.refresh_token)
            if self.bo.brands:
                currentConfig.set("BOAPIv2", "brands", ', '.join(list(reduce(lambda x, y: x+y, iter(self.bo.brands.items())))))

        if self.googleSpreadsheet:
            currentConfig.add_section("GoogleSpreadsheetAPI")
            currentConfig.set("GoogleSpreadsheetAPI", "access_token",   self.googleSpreadsheet.googleCreds.token)
            currentConfig.set("GoogleSpreadsheetAPI", "refresh_token",  self.googleSpreadsheet.googleCreds.refresh_token)
            currentConfig.set("GoogleSpreadsheetAPI", "id_token",       self.googleSpreadsheet.googleCreds.id_token)
            currentConfig.set("GoogleSpreadsheetAPI", "token_uri",      self.googleSpreadsheet.googleCreds.token_uri)
            currentConfig.set("GoogleSpreadsheetAPI", "client_id",      self.googleSpreadsheet.googleCreds.client_id)
            currentConfig.set("GoogleSpreadsheetAPI", "client_secret",  self.googleSpreadsheet.googleCreds.client_secret)

        with open(os.path.join(self.appDataDir, "TemplateMarker.ini"), 'w') as configFile:
            #FIXME proper config place
            try:
                currentConfig.write(configFile)
            except UnicodeEncodeError:
                #FIXME
                pass
        self.top.destroy()

    def reconnect(self):
        #FIXME
        '''Meaningful when overwriting XMLs:
        '''
        pass

    @staticmethod
    def __unmarkFileName(inFileName):
        '''removes remarks form on the GUI displayed filenames, like * at the beginning'''
        if inFileName.upper() in dest_dict:
            return inFileName
        elif inFileName[:2] == '* ':
            if inFileName[2:].upper() in dest_dict:
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

def scanDirs(inFile, inRootFolder, inAcceptedFormatS = (".XML",)):
    """
    only scanning input dir recursively to set up xml and image files' list
    :param inFile:
    :param outFile:
    :return:
    """
    # FIXME rewrite into a stateless form
    try:
        for f in listdir(inFile):
            try:
                src = os.path.join(inFile, f)
                # if it's NOT a directory
                if not os.path.isdir(src):
                    if os.path.splitext(os.path.basename(f))[1].upper() in inAcceptedFormatS:
                        sf = SourceXML(os.path.relpath(src, inRootFolder))
                        replacement_dict[sf._name.upper()] = sf
                        # id_dict[sf.guid.upper()] = ""
                    else:
                        # set up replacement dict for other files
                        if os.path.splitext(os.path.basename(f))[0].upper() not in source_pict_dict:
                            sI = SourceResource(os.path.relpath(src, inRootFolder), base_path=inRootFolder)
                            SIDN = SourceImageDirName.get()
                            if SIDN in sI.fullDirName and SIDN:
                                sI.isEncodedImage = True
                            source_pict_dict[sI.fileNameWithExt.upper()] = sI
                else:
                    scanDirs(src, inRootFolder)

            except KeyError:
                print("KeyError %s" % f)
                continue
            except etree.XMLSyntaxError:
                print("XMLSyntaxError %s" % f)
                continue
    except WindowsError:
        pass


def main2():
    """
    :return:
    """
    if bXML.get():
        tempdir = TargetXMLDirName.get()
    else:
        tempdir = tempfile.mkdtemp()

    if not bWriteToSelf:
        targGDLDir = TargetGDLDirName.get()
    else:
        targGDLDir = tempfile.mkdtemp()

    targPicDir = TargetImageDirName.get()   # For target library's encoded images
    tempPicDir = tempfile.mkdtemp()         # For every image file, collected

    print("tempdir: %s" % tempdir)
    print("tempPicDir: %s" % tempPicDir)

    pool_map = [{"dest": dest_dict[k],
                 "tempdir": tempdir,
                 "bOverWrite": bOverWrite.get(),
                 "StringTo": StringTo.get(),
                 "pict_dict": pict_dict,
                 "dest_dict": dest_dict,
                 } for k in list(dest_dict.keys()) if isinstance(dest_dict[k], DestXML)]
    cpuCount = max(mp.cpu_count() - 1, 1)

    p = mp.Pool(processes=cpuCount)
    p.map(processOneXML, pool_map)

    _picdir =  AdditionalImageDir.get() # Like IMAGES_GENERIC

    if _picdir:
        for f in listdir(_picdir):
            shutil.copytree(os.path.join(_picdir, f), os.path.join(tempPicDir, f))

    for f in list(pict_dict.keys()):
        if pict_dict[f].sourceFile.isEncodedImage:
            try:
                shutil.copyfile(os.path.join(SourceImageDirName.get(), pict_dict[f].sourceFile.relPath), os.path.join(tempPicDir, pict_dict[f].relPath))
            except IOError:
                os.makedirs(os.path.join(tempPicDir, pict_dict[f].dirName))
                shutil.copyfile(os.path.join(SourceImageDirName.get(), pict_dict[f].sourceFile.relPath), os.path.join(tempPicDir, pict_dict[f].relPath))

            if targPicDir:
                try:
                    shutil.copyfile(os.path.join(SourceImageDirName.get(), pict_dict[f].sourceFile.relPath),
                                    os.path.join(targPicDir, pict_dict[f].relPath))
                except IOError:
                    os.makedirs(os.path.join(targPicDir, pict_dict[f].dirName))
                    shutil.copyfile(os.path.join(SourceImageDirName.get(), pict_dict[f].sourceFile.relPath),
                                    os.path.join(targPicDir, pict_dict[f].relPath))
        else:
            if targGDLDir:
                try:
                    shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(targGDLDir, pict_dict[f].relPath))
                except IOError:
                    os.makedirs(os.path.join(targGDLDir, pict_dict[f].dirName))
                    shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(targGDLDir, pict_dict[f].relPath))

            if TargetXMLDirName.get():
                try:
                    shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(TargetXMLDirName.get(), pict_dict[f].relPath))
                except IOError:
                    os.makedirs(os.path.join(TargetXMLDirName.get(), pict_dict[f].dirName))
                    shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(TargetXMLDirName.get(), pict_dict[f].relPath))

    x2lCommand = '"%s" x2l -img "%s" "%s" "%s"' % (os.path.join(ACLocation.get(), 'LP_XMLConverter.exe'), tempPicDir, tempdir, targGDLDir)
    print("x2l Command being executed...")
    print(x2lCommand)

    if bWriteToSelf:
        tempGDLArchiveDir = tempfile.mkdtemp()
        print("GDL's archive dir: %s" % tempGDLArchiveDir)
        for k in list(dest_dict.keys()):
            os.rename(k.sourceFile.fullPath, os.path.join(tempGDLArchiveDir, k.sourceFile.relPath))
            os.rename(os.path.join(targGDLDir, k.sourceFile.relPath), k.sourceFile.fullPath)

    if bDebug.get():
        print("ac command:")
        print(x2lCommand)
        with open(tempdir + "\dict.txt", "w") as d:
            for k in list(dest_dict.keys()):
                d.write(k + " " + dest_dict[k].sourceFile.name + "->" + dest_dict[k].name + " " + dest_dict[k].sourceFile.guid + " -> " + dest_dict[k].guid + "\n")

        with open(tempdir + "\pict_dict.txt", "w") as d:
            for k in list(pict_dict.keys()):
                d.write(pict_dict[k].sourceFile.fullPath + "->" + pict_dict[k].relPath+ "\n")

        with open(tempdir + "\id_dict.txt", "w") as d:
            for k in list(id_dict.keys()):
                d.write(id_dict[k] + "\n")

    if bGDL.get():
        check_output(x2lCommand, shell=True)

    # cleanup ops
    if not bCleanup.get():
        shutil.rmtree(tempPicDir)
        if not bXML:
            shutil.rmtree(tempdir)
    else:
        print("tempdir: %s" % tempdir)
        print("tempPicDir: %s" % tempPicDir)

    print("*****FINISHED SUCCESFULLY******")


def processOneXML(inData):
    dest = inData['dest']
    tempdir = inData["tempdir"]
    dest_dict = inData["dest_dict"]
    pict_dict = inData["pict_dict"]
    bOverWrite = inData["bOverWrite"]
    StringTo = inData["StringTo"]

    src = dest.sourceFile
    srcPath = src.fullPath
    destPath = os.path.join(tempdir, dest.relPath)
    destDir = os.path.dirname(destPath)

    print("%s -> %s" % (srcPath, destPath,))

    # FIXME multithreading, map-reduce
    mdp = etree.parse(srcPath, etree.XMLParser(strip_cdata=False))
    mdp.getroot().attrib[dest.sourceFile.ID] = dest.guid
    # FIXME what if calledmacros are not overwritten?
    if bOverWrite and dest.retainedCalledMacros:
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
            for dI in list(dest_dict.keys()):
                d = dest_dict[dI]
                if m.find("MName").text.strip("'" + '"') == d.sourceFile.name:
                    m.find("MName").text = etree.CDATA('"' + d.name + '"')
                    m.find(dest.sourceFile.ID).text = d.guid

    for sect in ["./Script_2D", "./Script_3D", "./Script_1D", "./Script_PR", "./Script_UI", "./Script_VL",
                 "./Script_FWM", "./Script_BWM", ]:
        section = mdp.find(sect)
        if section is not None:
            t = section.text

            for dI in list(dest_dict.keys()):
                t = re.sub(r'(?<=[,"\'`\s])' + dest_dict[dI].sourceFile.name + r'(?=[,"\'`\s])', dest_dict[dI].name, t, flags=re.IGNORECASE)

            for pr in sorted(list(pict_dict.keys()), key=lambda x: -len(x)):
                # Replacing images
                t = re.sub(r'(?<=[,"\'`\s])' + pict_dict[pr].sourceFile.fileNameWithOutExt + '(?!' + StringTo + ')',
                           pict_dict[pr].fileNameWithOutExt, t, flags=re.IGNORECASE)

            section.text = etree.CDATA(t)
    # ---------------------Prevpict-------------------------------------------------------
    if dest.bPlaceable:
        section = mdp.find('Picture')
        if isinstance(section, etree._Element) and 'path' in section.attrib:
            path = os.path.basename(section.attrib['path']).upper()
            if path:
                n = next((pict_dict[p].relPath for p in list(pict_dict.keys()) if
                          os.path.basename(pict_dict[p].sourceFile.relPath).upper() == path), None)
                if n:
                    section.attrib['path'] = os.path.dirname(n) + "/" + os.path.basename(n)  # Not os.path.join!
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
        if guid.upper() in id_dict:
            print("ANCESTRY: %s" % guid)
            par = m.getparent()
            par.remove(m)

            element = etree.Element(dest.sourceFile.ID)
            element.text = id_dict[guid]
            element.tail = '\n'
            par.append(element)
    try:
        os.makedirs(destDir)
    except WindowsError:
        pass
    with open(destPath, "wb") as file_handle:
        mdp.write(file_handle, pretty_print=True, encoding="UTF-8", )


def main():
    global app

    app = GUIApp()
    app.top.protocol("WM_DELETE_WINDOW", app.writeConfigBack)
    app.top.mainloop()


if __name__ == "__main__":
    main()

