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
import urllib, httplib
import copy

from ConfigParser import *

PERSONAL_ID = "ac4e5af2-7544-475c-907d-c7d91c810039"
GUID_REGEX = "[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}"
#FIXME to check this:
# GUID_REGEX = r"([0-9A-Fa-f]){8}-\1{4}-\1{4}-\1{4}-\1{12}"
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

PARFLG_HIDDEN   = 1
PARFLG_CHILD    = 2
PARFLG_BOLDNAME = 3

app = None

dest_dict = {}
replacement_dict = {}   #SourceXMLs' list, idx by name
id_dict = {}            #Source GUID -> dest GUID
pict_dict = {}
source_pict_dict = {}


class ParamSection:
    '''
    iterable class of all params
    '''
    def __init__(self, inETree):
        self.eTree = inETree
        self.__header = inETree.find("ParamSectHeader")
        self.__paramList    = []
        self.__paramDict    = {}
        self.__index        = 0
        self.usedParamSet   = {}
        for p in inETree.find("Parameters"):
            param = Param(p)
            self.__paramList += [param]
            self.__paramDict[param.name] = param

    def __iter__(self):
        return self

    def next(self):
        if self.__index >= len(self.__paramList) - 1:
            raise StopIteration
        else:
            self.__index += 1
            return self.__paramList[self.__index]

    def append(self, inEtree):
        self.__paramList.append(inEtree)

    def insertAfter(self, inParName, inEtree):
        self.__paramList.insert(self.__getIndex(inParName) + 1, inEtree)

    def insertBefore(self, inParName, inEtree):
        self.__paramList.insert(self.__getIndex(inParName), inEtree)

    def insertUnder(self, inParName, inEtree, inPos):
        """
        inserting under a title
        :param inParName:
        :param inEtree:
        :param inPos:      position, 0 is first, -1 is last #FIXME
        :return:
        """
        base = self.__getIndex(inParName)
        i = 1
        if self.__paramList[base].iType == PAR_TITLE:
            nP = self.__paramList[base + i]
            try:
                while nP.iType != PAR_TITLE and \
                    PARFLG_CHILD in nP.flags:
                    i += 1
                    nP = self.__paramList[i]
                self.__paramList.insert(i, inEtree)
            except IndexError:
                self.__paramList.append(inEtree)

    def remove_param(self, inParName):
        #TODO
        pass

    def upsert_param(self, inParName):
        #TODO
        pass

    def __getIndex(self, inName):
        return [p.name for p in self.__paramList].index(inName)

    def get(self, inName):
        '''
        Get parameter by its name as lxml Element
        :param inName:
        :return:
        '''
        return self.__paramList[self.__getIndex(inName)]

    def getChildren(self, inETree):
        '''
        Return children of a Parameter
        :param inETree:
        :return:        List of children, as lxml Elements
        '''
        result = []
        idx = self.__getIndex(inETree.name)
        if inETree.iType != PAR_TITLE:    return None
        for p in self.__paramList[idx:]:
            if PARFLG_CHILD in p.flags:
                result.append(p)
            else:
                return result

    # def refreshDependencies(self, inSourceXML):
    #     '''
    #     refreshing parameter dependencies
    #     :return:
    #     '''
    #     calledMarcoList = []
    #
    #     for _, calledMacro in inSourceXML.calledMacros.iteritems():
    #         calledMarcoList += [replacement_dict[calledMacro]]
    #
    #     for p in self.__paramList:
    #         isUsed = False
    #         p.
    #         if p.isUsed:

    def toEtree(self):
        eTree = etree.Element("ParamSection", SectVersion="25", SectionFlags="0", SubIdent="0", )
        eTree.append(self.__header)

        parTree = etree.Element("Parameters")
        eTree.append(parTree)
        for par in self.__paramList:
            elem = par.toEtree()

            parTree.append(elem)
        return eTree

    def BO_update(self, prodatURL):
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        _xml = urllib.urlencode({"value": "<?xml version='1.0' encoding='UTF-8'?>"
                                            "<Bim API='%s'>"
                                                "<Objects>"
                                                    "<Object ProductId='%s'/>"
                                                "</Objects>"
                                            "</Bim>" % (PERSONAL_ID, prodatURL, )})

        conn = httplib.HTTPSConnection("api.bimobject.com")
        conn.request("POST", "/GetBimObjectInfoXml2", _xml, headers)
        response = conn.getresponse()
        r = response.read()

        tree = etree.fromstring(r)
        # print tree
#'BO_Title', 'BO_Separator',
        BO_PARAM_TUPLE = ('BO_prodinfo',)
        for p in BO_PARAM_TUPLE:
            self.remove_param(p)

        for p in BO_PARAM_TUPLE:
            print p
            e = next((par for par in tree.findall("Object/Parameters/Parameter") if par.get('VariableName') == p), '')
            print e
            param = Param(  inName=e.get('VariableName'),
                            inDesc=e.get('VariableDescription'),
                           inValue=e.get('BIMParameterName'),
                            inType=e.get('VariableType'),
                           inAVals=None,
                           inChild=(e.get('VariableModifier')=='Child'),
                            inBold=(e.get('VariableStyle')=='Bold'),)
            if p in ('BO_Title',):
                pass
                # comment = Param()
            self.append(param)


class Param:
    tagBackList = ["", "Length", "Angle", "RealNum", "Integer", "Boolean", "String", "Material",
                   "LineType", "FillPattern", "PenColor", "Separator", "Title", "Comment"]

    def __init__(self, inETree = None,
                 inType = PAR_UNKNOWN,
                 inName = '',
                 inDesc = '',
                 inValue = None,
                 inAVals = None,
                 inChild=False,
                 inBold=False):
        if inETree != None:
            self.text = inETree.text
            self.tail = inETree.tail
            if not isinstance(inETree, etree._Comment):
                self.__eTree = inETree
                self.flags = set()
                self.iType = self.getTypeFromString(self.__eTree.tag)

                self.name = self.__eTree.attrib["Name"]
                self.desc = self.__eTree.find("Description").text
                self.descTail = self.__eTree.find("Description").tail

                val = self.__eTree.find("Value")
                if val != None:
                    self.value = self.__toFormat(val.text)
                    self.valTail = val.tail
                else:
                    self.value = None
                    self.valTail = None

                __aVals = self.__eTree.find("ArrayValues")
                if __aVals != None:
                    fd = int(__aVals.attrib["FirstDimension"])
                    sd = int(__aVals.attrib["SecondDimension"])
                    if sd > 0:
                        self.aVals = [["" for _ in range(fd)] for _ in range(sd)]
                        for v in __aVals.iter("AVal"):
                            x = int(v.attrib["Column"]) - 1
                            y = int(v.attrib["Row"]) - 1
                            self.aVals[x][y] = self.__toFormat(v.text)
                    else:
                        self.aVals = [["" for _ in range(fd)]]
                        for v in __aVals.iter("AVal"):
                            y = int(v.attrib["Row"]) - 1
                            self.aVals[0][y] = self.__toFormat(v.text)
                    self.aValsTail = __aVals.tail
                else:
                    self.aVals = None

                if self.__eTree.find("Flags") != None:
                    self.flagsTail = self.__eTree.find("Flags").tail
                    for f in self.__eTree.find("Flags"):
                        if f.tag == "ParFlg_Hidden":    self.flags |= {PARFLG_HIDDEN}
                        if f.tag == "ParFlg_Child":     self.flags |= {PARFLG_CHILD}
                        if f.tag == "ParFlg_BoldName":  self.flags |= {PARFLG_BOLDNAME}
                        #FIXME unique etc
            else:
                self.iType = PAR_COMMENT
                self.name = inETree.text
                self.desc = ''
                self.value = None
                self.aVals = None
        else:
            self.iType  = self.getTypeFromString(inType)
            self.name   = inName
            self.desc   = inDesc
            self.value  = inValue
            self.aVals  = inAVals
            self.flags = set()
            if inChild:
                self.flags |= {PARFLG_CHILD}
            if inBold:
                self.flags |= {PARFLG_BOLDNAME}

        self.isInherited    = False
        self.isUsed         = True

    def __toFormat(self, inData):
        '''
        Returns data converted from string according to self.iType
        :param inData:
        :return:
        '''
        if self.iType in (PAR_LENGTH, PAR_REAL, PAR_ANGLE):
            return float(inData)
        elif self.iType in (PAR_INT, PAR_MATERIAL, PAR_PEN, PAR_LINETYPE, PAR_MATERIAL):
            return int(inData)
        elif self.iType in (PAR_BOOL, ):
            return bool(inData)
        elif self.iType in (PAR_SEPARATOR, ):
            return None
        else:
            return inData

    def __valueFormat(self, inVal):
        if self.iType in (PAR_STRING, ):
            return etree.CDATA(inVal)
        elif self.iType in (PAR_BOOL, ):
            return "0" if not inVal else "1"
        elif self.iType in (PAR_SEPARATOR, ):
            return None
        else:
            return str(inVal)

    def toEtree(self):
        if self.iType < PAR_COMMENT:
            tagString = self.tagBackList[self.iType]
            elem = etree.Element(tagString, Name=self.name)

            desc = etree.Element("Description")
            desc.tail = self.descTail
            elem.append(desc)
            desc.text = etree.CDATA(self.desc)

            if self.flags:
                flags = etree.Element("Flags")
                elem.append(flags)
                flags.tail = self.flagsTail

            for f in self.flags:
                if f == PARFLG_HIDDEN:   flags.append(etree.Element("ParFlg_Hidden"))
                if f == PARFLG_CHILD:    flags.append(etree.Element("ParFlg_Child"))
                if f == PARFLG_BOLDNAME: flags.append(etree.Element("ParFlg_BoldName"))

            if self.value != None:
                value = etree.Element("Value")
                elem.append(value)
                # if isinstance(self.value, basestring):
                value.text = self.__valueFormat(self.value)
                # elif isinstance(self.value, bool):
                #     value.text = "0" if not self.value else "1"
                # else:
                #     value.text = str(self.value)
                value.tail = self.valTail

            elif self.aVals != None:
                fd = len(self.aVals[0])
                sd = len(self.aVals)
                aValue = etree.Element("ArrayValues", FirstDimension=str(fd), SecondDimension=str(sd))
                aValue.tail = self.aValsTail
                elem.append(aValue)
                for colIdx, col in enumerate(self.aVals):
                    for rowIdx, cell in enumerate(col):
                        arrayValue = etree.Element("AVal", Column=str(colIdx + 1), Row=str(rowIdx + 1))
                        aValue.append(arrayValue)
                        arrayValue.text = self.__valueFormat(cell)
        else:
            elem = etree.Comment(self.name)
        elem.text = self.text
        elem.tail = self.tail
        return elem

    @staticmethod
    def getTypeFromString(inString):
        if inString in ("Length"):
            return PAR_LENGTH
        elif inString in ("Angle"):
            return PAR_ANGLE
        elif inString in ("RealNum", "Real"):
            return PAR_REAL
        elif inString in ("Integer"):
            return PAR_INT
        elif inString in ("Boolean"):
            return PAR_BOOL
        elif inString in ("String"):
            return PAR_STRING
        elif inString in ("Material"):
            return PAR_MATERIAL
        elif inString in ("LineType"):
            return PAR_LINETYPE
        elif inString in ("FillPattern"):
            return PAR_FILL
        elif inString in ("PenColor"):
            return PAR_PEN
        elif inString in ("Separator"):
            return PAR_SEPARATOR
        elif inString in ("Title"):
            return PAR_TITLE

class CreateToolTip:
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


# ------------------- GUI ------------------------------
# ------------------- GUI ------------------------------
# ------------------- GUI ------------------------------

# -------------------data classes---------------------------------------------------------------------------------------


class GeneralFile(object) :
    '''
    fullpath:   C:\...\relPath\fileName.ext  -only for sources; dest stuff can always be modified
    relPath:           relPath\fileName.ext
    dirName            relPath
    fileNameWithExt:           fileName.ext
    name:                      fileName     - for XMLs
    name:                      fileName.ext - for images
    fileNameWithOutExt:        fileName     - for images
    ext:                               .ext

    Inheritances:

                    GeneralFile
                        |
        +---------------+--------------+
        |               |              |
    SourceFile      DestFile        XMLFile
        |               |              |
        |               |              +---------------+
        |               |              |               |
        +-------------- | -------------+               |
        |               |              |               |
        |               +------------- | --------------+
        |               |              |               |
    SourceImage     DestImage       SourceXML       DestXML
    '''
    def __init__(self, relPath):
        self.relPath            = relPath
        self.fileNameWithExt    = os.path.basename(relPath)
        self.fileNameWithOutExt = os.path.splitext(self.fileNameWithExt)[0]
        self.ext                = os.path.splitext(self.fileNameWithExt)[1]
        self.dirName            = os.path.dirname(relPath)

    def refreshFileNames(self):
        # self.fullPath = self.relPath + "\\" + self.fileNameWithExt
        pass

    def __lt__(self, other):
        return self.fileNameWithOutExt < other.name


class SourceFile(GeneralFile):
    def __init__(self, relPath):
        super(SourceFile, self).__init__(relPath)
        self.fullPath = SourceDirName.get() + "\\" + relPath


class DestFile(GeneralFile):
    def __init__(self, sourceFile):
        super(DestFile, self).__init__(sourceFile)
        # self.sourceFile = replacement_dict[string.upper(self.sourceFile.name)]
        self.ext        = self.sourceFile.ext


class SourceImage(SourceFile):
    def __init__(self, sourceFile):
        super(SourceImage, self).__init__(sourceFile)
        # GeneralFile.__init__(self, sourceFile, SourceDirName.get())
        # self.ext = os.path.splitext(os.path.basename(sourceFile))[1]
        # self.fileNameWithExt = self.name + self.ext
        # self.fileNameWithOutExt = self.name
        # self.fileNameWithOutExt = os.path.splitext(os.path.basename(sourceFile))[0]
        self.name = self.fileNameWithExt


class DestImage(DestFile):
    # fileNameWithOutExt  = ""
    # sourceFile          = None  #reference

    #TODO TargetImageDirName is ok for images?

    def __init__(self, sourceFile, stringFrom, stringTo):
        GeneralFile.__init__(self, sourceFile.relPath)
        self.sourceFile         = sourceFile
        self.relPath            = sourceFile.relPath
        self.path               = TargetImageDirName.get() + "\\" + self.relPath
        self.GDLFullpath        = TargetGDLDirName.get()   + "\\" + self.relPath
        self.XMLFullpath        = TargetXMLDirName.get()   + "\\" + self.relPath
        self.sourceFileName     = sourceFile.name
        self.name               = re.sub(stringFrom, stringTo, sourceFile.name, flags=re.IGNORECASE)
        # self.fileNameWithOutExt = os.path.splitext(os.path.basename(self.name))[0]
        self.ext                = self.sourceFile.ext

        if stringTo not in self.name and bAddStr.get():
            self.fileNameWithOutExt += stringTo
            self.name           = self.fileNameWithOutExt + self.ext
        self.fileNameWithExt = self.name
        self.fullPath = self.path + "\\" + self.fileNameWithExt

    def refreshFileNames(self):
        self.fullPath = self.path + "\\" + self.fileNameWithExt


class XMLFile(GeneralFile):

    def __init__(self, relPath):
        super(XMLFile, self).__init__(relPath)
        # self.ext        = ".xml"
        # self.guid       = ""
        # self.iVersion   = 0
        # self.ID         = ""
        self.name       = self.fileNameWithOutExt
        self.bPlaceable = False


    def __lt__(self, other):
        if self.bPlaceable and not other.bPlaceable:
            return True
        if not self.bPlaceable and other.bPlaceable:
            return False
        return self.name < other.name


class SourceXML (XMLFile, SourceFile):

    def __init__(self, relPath):
        super(SourceXML, self).__init__(relPath)
        self.calledMacros   = {}
        self.parentSubTypes = {}
        self.scripts        = {}

        mroot = etree.parse(self.fullPath, etree.XMLParser(strip_cdata=False))
        # mroot = etree.parse(self.fullPath)
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

        #Filtering params in source in place of dest cos it's feasible and in dest later added params are unused
        # FIXME getting calledmacros' guids.

        if self.iVersion >= AC_18:
            ID = "MainGUID"
        else:
            ID = "UNID"

        for m in mroot.findall("./CalledMacros/Macro"):
            calledMacroID = m.find(ID).text
            self.calledMacros[calledMacroID] = string.strip(m.find("MName").text, "'" + '"')

        #Parameter manipulation: checking usage and later add custom pars
        self.parameters = ParamSection(mroot.find("./ParamSection"))

        for scriptName in SCRIPT_NAMES_LIST:
            script = mroot.find("./%s" % scriptName)
            if script:
                self.scripts[scriptName] = script.text

        for par in self.parameters:
            par.isUsed = self.checkParameterUsage(par, set())

    def checkParameterUsage(self, inPar, inMacroSet):
        '''
        Checking whether a certain Parameter is used in the macro or any of its called macros
        :param inPar:       Parameter
        :param inMacroSet:  set of macros that the parameter was searched in before
        :return:        boolean
        '''
        #FIXME check parameter passings: a called macro without PARAMETERS ALL
        for script in self.scripts:
            if inPar.name in script:
                return True

        for _, macroName in self.calledMacros.iteritems():
            if macroName in replacement_dict:
                if macroName not in inMacroSet:
                    if replacement_dict[macroName].checkParameterUsage(inPar, inMacroSet):
                        return True

        return False


class DestXML (XMLFile, DestFile):
    # tags            = []      #FIXME later; from BO site

    def __init__(self, sourceFile, stringFrom = "", stringTo = "", ):
        # Renaming
        self.name     = re.sub(stringFrom, stringTo, sourceFile.name, flags=re.IGNORECASE)
        if stringTo not in self.name and bAddStr.get():
            self.name += stringTo
        if self.name.upper() in dest_dict:
            i = 1
            while self.name.upper() + "_" + str(i) in dest_dict.keys():
                i += 1
            self.name += "_" + str(i)
            self.guid = str(uuid.uuid4()).upper()

            # if "XML Target file exists!" in self.warnings:
            #     self.warnings.remove("XML Target file exists!")
            #     self.refreshFileNames()
        self.sourceFile     = sourceFile

        super(DestXML, self).__init__(self.name)
        self.warnings = []

        # self.sourceFileName = sourceFile.name
        # self.path           = os.path.normpath(TargetXMLDirName.get() + "\\" + sourceFile.relPath)
        #FIXME refresh paths if XML folder is changed OR do it on the fly
        self.fullPath       = TargetXMLDirName.get() + "\\" + self.relPath
        self.fullGDLPath    = TargetGDLDirName.get() + "\\" + self.fileNameWithOutExt + ".gsm"
        # self.dirName        = os.path.dirname(self.fullPath)
        self.guid           = str(uuid.uuid4()).upper()
        self.bPlaceable     = sourceFile.bPlaceable
        self.iVersion       = sourceFile.iVersion
        # self.sourceFile.destName    = os.path.splitext(self.name)[0]
        self.proDatURL              = ''
        self.bOverWrite             = False
        self.bRetainCalledMacros    = False
        self.parameters             = copy.deepcopy(sourceFile.parameters)

        if os.path.isfile(self.fullPath):
            #for overwriting existing xmls while retaining GUIDs etx
            if bOverWrite.get():
                #FIXME to finish it
                self.bOverWrite             = True
                self.bRetainCalledMacros    = True
                mdp = etree.parse(self.fullPath, etree.XMLParser(strip_cdata=False))
                # self.iVersion = mdp.getroot().attrib['Version']
                # if self.iVersion >= AC_18:
                #     self.ID = "MainGUID"
                # else:
                #     self.ID = "UNID"
                self.guid = mdp.getroot().attrib[ID]
                print mdp.getroot().attrib[ID]

            else:
                self.warnings += ["XML Target file exists!"]

        if os.path.isfile(self.fullGDLPath):
            self.warnings += ["GDL Target file exists!"]

        if self.iVersion >= AC_18:
            # AC18 and over: adding licensing statically, can be manually owerwritten on GUI
            self.author         = "BIMobject"
            self.license        = "CC BY-ND"
            self.licneseVersion = "3.0"

        if self.sourceFile.guid.upper() in id_dict:
            if id_dict[self.sourceFile.guid.upper()] == "":
                id_dict[self.sourceFile.guid.upper()] = self.guid.upper()

    def getCalledMacro(self):
        '''
        getting called marco scripts
        FIXME to be removed
        :return:
        '''

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
        self.appDataDir  = os.getenv('APPDATA')
        if os.path.isfile(self.appDataDir  + r"\TemplateMarker.ini"):
            currentConfig.read(self.appDataDir  + r"\TemplateMarker.ini")
        else:
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


        for cName, cValue in currentConfig.items('ArchiCAD'):
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
                elif cName == 'sourcedirname':      self.SourceDirName.set(cValue)
                elif cName == 'xmltargetdirname':   self.TargetXMLDirName.set(cValue)
                elif cName == 'gdltargetdirname':   self.TargetGDLDirName.set(cValue)
                elif cName == 'baddstr':            self.bAddStr.set(cValue)
                elif cName == 'boverwrite':         self.bOverWrite.set(cValue)
            except NoOptionError:
                print "NoOptionError"
                continue
            except NoSectionError:
                print "NoSectionError"
                continue
            except ValueError:
                print "ValueError"
                continue

        self.observerXML = self.bXML.trace_variable("w", self.XMLModified)
        self.observerGDL = self.bGDL.trace_variable("w", self.GDLModified)

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

        if SourceDirName:
            self.listBox.refresh()
            self.listBox2.refresh()

        self.ListBoxScrollbar2 = tk.Scrollbar(self.InputFrameS[iF])
        self.ListBoxScrollbar2.grid(row=0, column=1, sticky=tk.E + tk.N + tk.S)

        self.listBox2.config(yscrollcommand=self.ListBoxScrollbar2.set)
        self.ListBoxScrollbar2.config(command=self.listBox2.yview)

        # ----output side--------------------------------

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

        # ------------------------------------
        # bottom row for project general settings
        # ------------------------------------

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

        # self.reconnectButton      = tk.Button(self.buttonFrame, {"text": "Reconnect", "command": self.reconnect })
        # self.reconnectButton.grid({"row": 4, "sticky": tk.W + tk.E})

        #FIXME
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
        self.destItem.parameters.BO_update(self.destItem.proDatURL)

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
        # currentConfig.set("ArchiCAD", "path", "C:\Program Files\GRAPHISOFT\ArchiCAD SE 2016\LP_XMLConverter.exe")
        currentConfig.set("ArchiCAD", "aclocation",         self.ACLocEntry.get())
        currentConfig.set("ArchiCAD", "additionalimagedir", self.AdditionalImageDirEntry.get())

        currentConfig.set("ArchiCAD", "bdebug",             self.bDebug.get())
        currentConfig.set("ArchiCAD", "bxml",               self.bXML.get())
        currentConfig.set("ArchiCAD", "bgdl",               self.bGDL.get())

        currentConfig.set("ArchiCAD", "sourcedirname",      self.SourceDirName.get())
        currentConfig.set("ArchiCAD", "xmltargetdirname",   self.TargetXMLDirName.get())
        currentConfig.set("ArchiCAD", "gdltargetdirname",   self.TargetGDLDirName.get())
        currentConfig.set("ArchiCAD", "inputimagesource",   self.SourceImageDirName.get())
        currentConfig.set("ArchiCAD", "inputimagetarget",   self.TargetImageDirName.get())
        currentConfig.set("ArchiCAD", "stringfrom",         self.StringFrom.get())
        currentConfig.set("ArchiCAD", "stringto",           self.StringTo.get())
        currentConfig.set("ArchiCAD", "imgstringfrom",      self.ImgStringFrom.get())
        currentConfig.set("ArchiCAD", "imgstringto",        self.ImgStringTo.get())
        currentConfig.set("ArchiCAD", "baddstr",            self.bAddStr.get())
        currentConfig.set("ArchiCAD", "boverwrite",         self.bOverWrite.get())

        with open(self.appDataDir + r"\TemplateMarker.ini", 'wb') as configFile:
            #FIXME proper config place
            currentConfig.write(configFile)
        self.top.destroy()

    def reconnect(self):
        #FIXME
        '''Meaningful when overwriting XMLs:
        '''
        pass
# -------------------/GUI------------------------------
# -------------------/GUI------------------------------
# -------------------/GUI------------------------------

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
                    if os.path.splitext(os.path.basename(f))[1].upper() in (".XML", ):
                        sf = SourceXML(os.path.relpath(src, SourceDirName.get()))
                        replacement_dict[sf.name.upper()] = sf
                        id_dict[sf.guid.upper()] = ""

                    elif os.path.splitext(os.path.basename(f))[1].upper() in (".JPG", ".PNG", ".SVG", ):
                        if os.path.splitext(os.path.basename(f))[0].upper() not in source_pict_dict:
                            # set up replacement dict for image names
                            sI = SourceImage(os.path.relpath(src, SourceDirName.get()))
                            source_pict_dict[sI.fileNameWithExt.upper()] = sI
                else:
                    FC1(src)

            except KeyError:
                print "KeyError %s" % f
                continue
    except WindowsError:
        pass

def main2():
    '''

    :return:
    '''
    if bXML.get():
        tempdir = TargetXMLDirName.get()
    else:
        tempdir = tempfile.mkdtemp()

    tempPicDir = tempfile.mkdtemp()
    print "tempdir: %s" % tempdir
    print "tempPicDir: %s" % tempPicDir

    for k in dest_dict.keys():
        dest        = dest_dict[k]
        src         = dest.sourceFile
        srcPath     = src.fullPath
        # destPath = dest.fullPath
        destPath    = tempdir + "\\" + dest.relPath + dest.ext
        destDir     = os.path.dirname(destPath)

        print "%s -> %s" % (srcPath, destPath,)

        # try:
        #FIXME multithreading, map-reduce
        mdp = etree.parse(srcPath, etree.XMLParser(strip_cdata=False))
        mdp.getroot().attrib[ID] = dest.guid

        #FIXME what if calledmacros are not overwritten?
        if bOverWrite.get() and dest_dict[k].retainedCalledMacros:
            cmRoot = mdp.find("./CalledMacros")
            for m in mdp.findall("./CalledMacros/Macro"):
                cmRoot.remove(m)

            for key, cM in dest.retainedCalledMacros.iteritems():
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
            section = mdp.find(sect)
            if section:
                t = section.text

                for dI in dest_dict.keys():
                    # if re.search(dest_dict[dI].sourceFile.fileName, t):
                    #     print "*****************", dest_dict[dI].sourceFile.fileName, dest_dict[dI].fileName
                    t = re.sub(dest_dict[dI].sourceFile.name, dest_dict[dI].name, t, flags=re.IGNORECASE)

                for pr in pict_dict.keys():
                    #Replacing images
                    # print pict_dict[pr].originalName
                    t = re.sub(pict_dict[pr].sourceFile.fileNameWithOutExt, pict_dict[pr].fileNameWithOutExt, t, flags=re.IGNORECASE)

                section.text = etree.CDATA(t)

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

        # ---------------------BO_update preparations---------------------
        # parRoot = mdp.find("./ParamSection/Parameters")
        parRoot = mdp.find("./ParamSection")
        parPar = parRoot.getparent()
        parPar.remove(parRoot)

        destPar = dest.parameters.toEtree()
        parPar.append(destPar)

        #FIXME rewriting this as Parameter instead of xml
        # for stPar in stRoot.findall("String"):
        #     if stPar.attrib["Name"] == "BO_prodaturl":
        #         stRoot.remove(stPar)
        #     if stPar.attrib["Name"] == "BO_productguid":
        #         stRoot.remove(stPar)
        #     if stPar.attrib["Name"] == "BO_edinum":
        #         stRoot.remove(stPar)
        #FIXME BO_edinum to -1, removing BO_productguid

        # eProdatUrl= etree.Element("String", Name="BO_prodaturl", )
        # # destPar = mdp.find("./ParamSection/Parameters")
        # destPar.append(eProdatUrl)
        #
        # eProdatDesc = etree.Element("Description")
        # eProdatDesc.text = etree.CDATA('"Product data url:"')
        # eProdatUrl.append(eProdatDesc)
        #
        # eParFlags = etree.Element("Flags")
        # eParFlags.append(etree.Element("ParFlg_Child", ))
        # eProdatUrl.append(eParFlags)
        #
        # eProdatVal = etree.Element("Value", )
        # eProdatVal.text = etree.CDATA('"' + dest.proDatURL + '"')
        # eProdatUrl.append(eProdatVal)

        #FIXME not clear, check, writes an extra empty mainunid field
        for m in mdp.findall("./Ancestry/" + ID):
            name = m.text
            if name.upper() in id_dict:
                print "ANCESTRY: %s" % name
                m.text = id_dict[name]
                par = m.getparent()
                par.remove(m)
        try:
            os.makedirs(destDir)
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
        if TargetImageDirName.get():
            try:
                shutil.copyfile(pict_dict[f].sourceFile.fullPath, TargetImageDirName.get() + "\\" + pict_dict[f].relPath)
            except IOError:
                os.makedirs(TargetImageDirName.get() + "\\" + pict_dict[f].dirName)
                shutil.copyfile(pict_dict[f].sourceFile.fullPath, TargetImageDirName.get() + "\\" + pict_dict[f].relPath)

        if TargetGDLDirName.get():
            try:
                shutil.copyfile(pict_dict[f].sourceFile.fullPath, TargetGDLDirName.get() + "\\" + pict_dict[f].relPath)
            except IOError:
                os.makedirs(TargetGDLDirName.get() + "\\" + pict_dict[f].dirName)
                shutil.copyfile(pict_dict[f].sourceFile.fullPath, TargetGDLDirName.get() + "\\" + pict_dict[f].relPath)

        if TargetXMLDirName.get():
            try:
                shutil.copyfile(pict_dict[f].sourceFile.fullPath, TargetXMLDirName.get() + "\\" + pict_dict[f].relPath)
            except IOError:
                os.makedirs(TargetXMLDirName.get() + "\\" + pict_dict[f].dirName)
                shutil.copyfile(pict_dict[f].sourceFile.fullPath, TargetXMLDirName.get() + "\\" + pict_dict[f].relPath)

    print "x2l Command being executed..."
    x2lCommand = '"%s\LP_XMLConverter.exe" x2l -img "%s" "%s" "%s"' % (ACLocation.get(), tempPicDir, tempdir, TargetGDLDirName.get())

    if bDebug.get():
        print "ac command:"
        print x2lCommand
        with open(tempdir + "\dict.txt", "w") as d:
            for k in dest_dict.keys():
                d.write(k + " " + dest_dict[k].sourceFile.name + "->" + dest_dict[k].name + " " + dest_dict[k].sourceFile.guid + " -> " + dest_dict[k].guid + "\n")

        with open(tempdir + "\pict_dict.txt", "w") as d:
            for k in pict_dict.keys():
                d.write(pict_dict[k].sourceFile.fullPath + "->" + pict_dict[k].fullPath+ "\n")

        with open(tempdir + "\id_dict.txt", "w") as d:
            for k in id_dict.keys():
                d.write(id_dict[k] + "\n")

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

if __name__ == "__main__":
    main()