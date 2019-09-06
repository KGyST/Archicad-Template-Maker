#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-
#HOTFIXREQ if image dest folder is retained, remove common images from it
#HOTFIXREQ ImportError: No module named googleapiclient.discovery
#FIXME renaming errors and param csv parameter overwriting
#FIXME append param to the end when no argument for position
#FIXME substring issues
#FIXME library_images copy always as temporary folder
#FIXME param editor should offer auto param inserting from Listing Parameters Google Spreadsheet
#FIXME automatic checking and warning of old project's names

# import os
import os.path
from os import listdir
import uuid
import re
import tempfile
from subprocess import check_output
import shutil

import string

import Tkinter as tk
import tkFileDialog
# import urllib, httplib
import copy
import argparse

from ConfigParser import *  #FIXME not *
import csv

import httplib, urllib, json, webbrowser, urlparse, os, hashlib, base64
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import pip

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
except ImportError:
    pip.main(['install', '--user', 'google-api-python-client'])
    pip.main(['install', '--user', 'google-auth-httplib2'])
    pip.main(['install', '--user', 'google-auth-oauthlib'])

    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

try:
    from lxml import etree
except ImportError:
    pip.main(['install', '--user', 'lxml'])
    from lxml import etree


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

dest_sourcenames    = {}   #source name     -> DestXMLs, idx by original filename #FIXME could be a set
dest_guids          = {}   #dest guid       -> DestXMLs, idx by
source_guids        = {}   #Source GUID     -> Source XMLs, idx by
id_dict             = {}   #Source GUID     -> dest GUID
dest_dict           = {}   #dest name       -> DestXML
replacement_dict    = {}   #source filename -> SourceXMLs
pict_dict           = {}
source_pict_dict    = {}

all_keywords = set()

# ------------------- parameter classes --------------------------------------------------------------------------------

class ArgParse(argparse.ArgumentParser):
    # Overriding exit method that stops whole program in case of bad parametrization
    def exit(self, *_):
        try:
            pass
        except TypeError:
            pass


class ParamSection:
    """
    iterable class of all params
    """
    def __init__(self, inETree):
        self.eTree          = inETree
        self.__header       = inETree.find("ParamSectHeader")
        self.__paramList    = []
        self.__paramDict    = {}
        self.__index        = 0
        self.usedParamSet   = {}

        for attr in ["SectVersion", "SectionFlags", "SubIdent", ]:
            if attr in self.eTree.attrib:
                setattr(self, attr, self.eTree.attrib[attr])
            else:
                setattr(self, attr, None)

        for p in inETree.find("Parameters"):
            param = Param(p)
            self.append(param, param.name)

    def __iter__(self):
        return self

    def next(self):
        if self.__index >= len(self.__paramList) - 1:
            raise StopIteration
        else:
            self.__index += 1
            return self.__paramList[self.__index]

    def __contains__(self, item):
        return item in self.__paramDict

    def __setitem__(self, key, value):
        #FIXME currently only existing ones
        if key in self.__paramDict:
            self.__paramDict[key].setValue(value)

    def append(self, inEtree, inName):
        self.__paramList.append(inEtree)
        if not isinstance(inEtree, etree._Comment):
            self.__paramDict[inName] = inEtree

    def insertAfter(self, inParName, inEtree):
        self.__paramList.insert(self.__getIndex(inParName) + 1, inEtree)

    def insertBefore(self, inParName, inEtree):
        self.__paramList.insert(self.__getIndex(inParName), inEtree)

    def insertAsChild(self, inParentParName, inEtree):
        """
        inserting under a title
        :param inParentParName:
        :param inEtree:
        :param inPos:      position, 0 is first, -1 is last #FIXME
        :return:
        """
        base = self.__getIndex(inParentParName)
        i = 1
        if self.__paramList[base].iType == PAR_TITLE:
            nP = self.__paramList[base + i]
            try:
                while nP.iType != PAR_TITLE and \
                        PARFLG_CHILD in nP.flags:
                    i += 1
                    nP = self.__paramList[base + i]
            except IndexError:
                pass
            self.__paramList.insert(base + i, inEtree)
            self.__paramDict[inEtree.name] = inEtree

    def remove_param(self, inParName):
        if inParName in self.__paramDict:
            obj = self.__paramDict[inParName]
            while obj in self.__paramList:
                self.__paramList.remove(obj)
            del self.__paramDict[inParName]

    def upsert_param(self, inParName):
        #FIXME
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
        """
        Return children of a Parameter
        :param inETree:
        :return:        List of children, as lxml Elements
        """
        result = []
        idx = self.__getIndex(inETree.name)
        if inETree.iType != PAR_TITLE:    return None
        for p in self.__paramList[idx:]:
            if PARFLG_CHILD in p.flags:
                result.append(p)
            else:
                return result

    def toEtree(self):
        eTree = etree.Element("ParamSection", SectVersion=self.SectVersion, SectionFlags=self.SectionFlags, SubIdent=self.SubIdent, )
        eTree.text = '\n\t'
        eTree.append(self.__header)
        eTree.tail = '\n'

        parTree = etree.Element("Parameters")
        parTree.text = '\n\t\t'
        parTree.tail = '\n'
        eTree.append(parTree)
        for par in self.__paramList:
            elem = par.eTree
            ix = self.__paramList.index(par)
            if ix == len(self.__paramList) - 1:
                elem.tail = '\n\t'
            else:
                if self.__paramList[ix + 1].iType == PAR_COMMENT:
                    elem.tail = '\n\n\t\t'
            parTree.append(elem)
        return eTree

    def BO_update(self, prodatURL):
        #FIXME code for unsuccessful updates, BO_edinum to -1, removing BO_productguid
        #FIXME new authentication
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
        resp = response.read()
        resTree = etree.fromstring(resp)

        BO_PARAM_TUPLE = ('BO_Title',
                          'BO_Separator',
                          'BO_prodinfo',
                          'BO_prodsku', 'BO_Manufac', 'BO_brandurl', 'BO_prodfam', 'BO_prodgroup',
                          'BO_mancont', 'BO_designcont', 'BO_publisdat', 'BO_edinum', 'BO_width',
                          'BO_height', 'BO_depth', 'BO_weight', 'BO_productguid',
                          'BO_links',
                          'BO_boqrurl', 'BO_producturl', 'BO_montins', 'BO_prodcert', 'BO_techcert',
                          'BO_youtube', 'BO_ean',
                          'BO_real',
                          'BO_mainmat', 'BO_secmat',
                          'BO_classific',
                          'BO_bocat', 'BO_ifcclas', 'BO_unspc', 'BO_uniclass_1_4_code', 'BO_uniclass_1_4_desc',
                          'BO_uniclass_2_0_code', 'BO_uniclass_2_0_desc', 'BO_uniclass2015_code', 'BO_uniclass2015_desc', 'BO_nbs_ref',
                          'BO_nbs_desc', 'BO_omniclass_code', 'BO_omniclass_name', 'BO_masterformat2014_code', 'BO_masterformat2014_name',
                          'BO_uniformat2_code', 'BO_uniformat2_name', 'BO_cobie_type_cat',
                          'BO_regions',
                          'BO_europe', 'BO_northamerica', 'BO_southamerica', 'BO_middleeast', 'BO_asia',
                          'BO_oceania', 'BO_africa', 'BO_antarctica', 'BO_Separator2',)
        for p in BO_PARAM_TUPLE:
            self.remove_param(p)

        for p in BO_PARAM_TUPLE:
            e = next((par for par in resTree.findall("Object/Parameters/Parameter") if par.get('VariableName') == p), '')
            if isinstance(e, etree._Element):
                varName = e.get('VariableName')
                if varName in ('BO_Title', 'BO_prodinfo', 'BO_links', 'BO_real', 'BO_classific', 'BO_regions',):
                    comment = Param(inName=varName,
                                    inDesc=e.get('VariableDescription'),
                                    inType=PAR_COMMENT,)
                    self.append(comment, 'BO_Title')
                param = Param(inName=varName,
                              inDesc=e.get('VariableDescription'),
                              inValue=e.text,
                              inTypeStr=e.get('VariableType'),
                              inAVals=None,
                              inChild=(e.get('VariableModifier')=='Child'),
                              inBold=(e.get('VariableStyle')=='Bold'), )
                self.append(param, varName)
            self.__paramList[-1].tail = '\n\t'

    def BO_update2(self, prodatURL, currentConfig, bo):
        '''
        FIXME
        BO_update with API v2
        :param prodatURL:
        :return:
        '''
        _brandName = prodatURL.split('/')[3].encode()
        _productGUID = prodatURL.split('/')[5].encode()
        try:
            brandGUID = bo.brands[_brandName]
        except KeyError:
            bo.refreshBrandDict()
            brandGUID = bo.brands[_brandName]

        _data = bo.getProductData(brandGUID, _productGUID)

        BO_PARAM_TUPLE = (('BO_Title', ''),
                          ('BO_Separator', ''),
                          ('BO_prodinfo', ''),
                          ('BO_prodsku', 'data//'), ('BO_Manufac'), ('BO_brandurl'), ('BO_prodfam'), ('BO_prodgroup'),
                          # ('BO_mancont'), ('BO_designcont'), ('BO_publisdat'), ('BO_edinum'), ('BO_width'),
                          # ('BO_height'), ('BO_depth'), ('BO_weight'), ('BO_productguid'),
                          # ('BO_links'),
                          # ('BO_boqrurl'), ('BO_producturl'), ('BO_montins'), ('BO_prodcert'), ('BO_techcert'),
                          # ('BO_youtube'), ('BO_ean'),
                          # ('BO_real'),
                          # ('BO_mainmat', 'BO_secmat'),
                          # ('BO_classific'),
                          # ('BO_bocat'), ('BO_ifcclas'), ('BO_unspc'), ('BO_uniclass_1_4_code'), ('BO_uniclass_1_4_desc'),
                          # ('BO_uniclass_2_0_code'), ('BO_uniclass_2_0_desc'), ('BO_uniclass2015_code'), ('BO_uniclass2015_desc'), ('BO_nbs_ref'),
                          # ('BO_nbs_desc'), ('BO_omniclass_code'), ('BO_omniclass_name'), ('BO_masterformat2014_code'), ('BO_masterformat2014_name'),
                          # ('BO_uniformat2_code'), ('BO_uniformat2_name'), ('BO_cobie_type_cat'),
                          # ('BO_regions'),
                          # ('BO_europe'), ('BO_northamerica'), ('BO_southamerica'), ('BO_middleeast'), ('BO_asia'),
                          # ('BO_oceania'), ('BO_africa'), ('BO_antarctica'), ('BO_Separator2',)
                          )
        for p in BO_PARAM_TUPLE:
            self.remove_param(p[0])

    def createParamfromCSV(self, inParName, inCol):
        splitPars = inParName.split(" ")
        parName = splitPars[0]
        ap = ArgParse(add_help=False)
        ap.add_argument("-d", "--desc" , "--description", nargs="+")        # action=ConcatStringAction,
        ap.add_argument("-t", "--type")
        ap.add_argument("-f", "--frontof" )
        ap.add_argument("-a", "--after" )
        ap.add_argument("-c", "--child")
        ap.add_argument("-h", "--hidden", action='store_true')
        ap.add_argument("-b", "--bold", action='store_true')
        ap.add_argument("-u", "--unique", action='store_true')
        ap.add_argument("-o", "--overwrite", action='store_true')
        ap.add_argument("-i", "--inherit", action='store_true', help='Inherit properties form the other parameter')

        parsedArgs = ap.parse_known_args(splitPars)[0]

        if parsedArgs.desc is not None:
            desc = " ".join(parsedArgs.desc)
        else:
            desc = ''

        if parName not in self:
            # if inCol:
            #     if inCol[0] != '"':
            #         inCol = '"' + inCol
            #     if inCol[-1] != '"':
            #         inCol = inCol + '"'
            # else:
            #     inCol = '""'

            parType = PAR_UNKNOWN
            if parsedArgs.type:
                if parsedArgs.type in ("Length", ):
                    parType = PAR_LENGTH
                    inCol = float(inCol)
                elif parsedArgs.type in ("Angle", ):
                    parType = PAR_ANGLE
                    inCol = float(inCol)
                elif parsedArgs.type in ("RealNum", ):
                    parType = PAR_REAL
                    inCol = float(inCol)
                elif parsedArgs.type in ("Integer", ):
                    parType = PAR_INT
                    inCol = int(inCol)
                elif parsedArgs.type in ("Boolean", ):
                    parType = PAR_BOOL
                    inCol = bool(int(inCol))
                elif parsedArgs.type in ("String", ):
                    parType = PAR_STRING
                elif parsedArgs.type in ("Material", ):
                    parType = PAR_MATERIAL
                    inCol = int(inCol)
                elif parsedArgs.type in ("LineType", ):
                    parType = PAR_LINETYPE
                    inCol = int(inCol)
                elif parsedArgs.type in ("FillPattern", ):
                    parType = PAR_FILL
                    inCol = int(inCol)
                elif parsedArgs.type in ("PenColor", ):
                    parType = PAR_PEN
                    inCol = int(inCol)
                elif parsedArgs.type in ("Separator", ):
                    parType = PAR_SEPARATOR
                elif parsedArgs.type in ("Title", ):
                    parType = PAR_TITLE
                    inCol = None
                elif parsedArgs.type in ("Comment", ):
                    parType = PAR_COMMENT
                    parName = " " + parName + ": PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK "
            else:
                if re.match(r'\bis[A-Z]', splitPars[0]) or re.match(r'\bb[A-Z]', splitPars[0]):
                    parType = PAR_BOOL
                elif re.match(r'\bi[A-Z]', splitPars[0]) or re.match(r'\bn[A-Z]', splitPars[0]):
                    parType = PAR_INT
                elif re.match(r'\bs[A-Z]', splitPars[0]) or re.match(r'\bst[A-Z]', splitPars[0]) or re.match(r'\bmp_', splitPars[0]):
                    parType = PAR_STRING
                elif re.match(r'\bx[A-Z]', splitPars[0]) or re.match(r'\by[A-Z]', splitPars[0]) or re.match(r'\bz[A-Z]', splitPars[0]):
                    parType = PAR_LENGTH
                elif re.match(r'\bx[A-Z]', splitPars[0]):
                    parType = PAR_ANGLE
                else:
                    parType = PAR_STRING

            if parsedArgs.inherit:
                if parsedArgs.child:
                    paramToInherit = self.__paramDict[parsedArgs.child]
                elif parsedArgs.after:
                    paramToInherit = self.__paramDict[parsedArgs.after]
                elif parsedArgs.frontof:
                    paramToInherit = self.__paramDict[parsedArgs.frontof]

                isChild  =  PARFLG_CHILD in paramToInherit.flags
                isBold = PARFLG_BOLDNAME in paramToInherit.flags
                isUnique = PARFLG_UNIQUE in paramToInherit.flags
                isHidden = PARFLG_HIDDEN in paramToInherit.flags
            else:
                isChild = "child" in dir(parsedArgs)
                isBold = parsedArgs.bold
                isUnique = parsedArgs.unique
                isHidden = parsedArgs.hidden

            param = Param(inType=parType,
                          inName=parName,
                          inDesc=desc,
                          inValue=inCol,
                          inChild=isChild,
                          inBold=isBold,
                          inHidden=isHidden,
                          inUnique=isUnique,)

            if parsedArgs.child:
                self.insertAsChild(parsedArgs.child, param)
            elif parsedArgs.after:
                self.insertAfter(parsedArgs.after, param)
            elif parsedArgs.frontof:
                self.insertBefore(parsedArgs.frontof, param)

            if parType == PAR_TITLE:
                paramComment = Param(inType=PAR_COMMENT,
                                     inName=" " + parName + ": PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ===== PARAMETER BLOCK ", )
                self.insertBefore(param.name, paramComment)
        else:
            #FIXME Pickin around an existing param, to be thought through
            self[parName] = inCol
            if desc:
                self.__paramDict[parName].desc = " ".join(parsedArgs.desc)


class Param(object):
    tagBackList = ["", "Length", "Angle", "RealNum", "Integer", "Boolean", "String", "Material",
                   "LineType", "FillPattern", "PenColor", "Separator", "Title", "Comment"]

    def __init__(self, inETree = None,
                 inType = PAR_UNKNOWN,
                 inName = '',
                 inDesc = '',
                 inValue = None,
                 inAVals = None,
                 inTypeStr='',
                 inChild=False,
                 inUnique=False,
                 inHidden=False,
                 inBold=False):
        self.value      = None

        if inETree is not None:
            self.eTree = inETree
        else:            # Start from a scratch
            self.iType  = inType
            if inTypeStr:
                self.iType  = self.getTypeFromString(inTypeStr)

            self.name   = inName
            if len(self.name) > 32 and self.iType != PAR_COMMENT: self.name = self.name[:32]
            if inValue is not None:
                self.value = inValue

            if self.iType != PAR_COMMENT:
                self.flags = set()
                if inChild:
                    self.flags |= {PARFLG_CHILD}
                if inUnique:
                    self.flags |= {PARFLG_UNIQUE}
                if inHidden:
                    self.flags |= {PARFLG_HIDDEN}
                if inBold:
                    self.flags |= {PARFLG_BOLDNAME}

            if self.iType not in (PAR_COMMENT, PAR_SEPARATOR, ):
                self.desc   = inDesc
                self.aVals  = inAVals
            elif self.iType == PAR_SEPARATOR:
                self.desc   = inDesc
                self._aVals = None
                self.value  = None
            elif self.iType == PAR_COMMENT:
                pass
        self.isInherited    = False
        self.isUsed         = True

    def setValue(self, inVal):
        #FIXME to be removed?
        self.value = self.__toFormat(inVal)

    def __toFormat(self, inData):

        """
        Returns data converted from string according to self.iType
        :param inData:
        :return:
        """
        if self.iType in (PAR_LENGTH, PAR_REAL, PAR_ANGLE):
            # self.digits = 2
            return float(inData)
        elif self.iType in (PAR_INT, PAR_MATERIAL, PAR_PEN, PAR_LINETYPE, PAR_MATERIAL):
            return int(inData)
        elif self.iType in (PAR_BOOL, ):
            return bool(int(inData))
        elif self.iType in (PAR_SEPARATOR, PAR_TITLE, ):
            return None
        else:
            return inData

    def _valueToString(self, inVal):
        if self.iType in (PAR_STRING, ):
            if inVal is not None:
                if not inVal.startswith('"'):
                    inVal = '"' + inVal
                if not inVal.endswith('"') or len(inVal) == 1:
                    inVal += '"'
                return etree.CDATA(inVal)
            else:
                return etree.CDATA('""')
        elif self.iType in (PAR_REAL, PAR_LENGTH, PAR_ANGLE):
            nDigits = 0
            eps = 1E-7
            maxN = 1E12
            # if maxN < abs(inVal) or eps > abs(inVal) > 0:
            #     return "%E" % inVal
            #FIXME 1E-012 and co
            # if -eps < inVal < eps:
            #     return 0
            s = '%.' + str(nDigits) + 'f'
            while nDigits < 8:
                if (inVal - eps < float(s % inVal) < inVal + eps):
                    break
                nDigits += 1
                s = '%.' + str(nDigits) + 'f'
            return s % inVal
        elif self.iType in (PAR_BOOL, ):
            return "0" if not inVal else "1"
        elif self.iType in (PAR_SEPARATOR, ):
            return None
        else:
            return str(inVal)

    @property
    def eTree(self):
        if self.iType < PAR_COMMENT:
            tagString = self.tagBackList[self.iType]
            elem = etree.Element(tagString, Name=self.name)
            nTabs = 3 if self.desc or self.flags is not None or self.value is not None or self.aVals is not None else 2
            elem.text = '\n' + nTabs * '\t'

            desc = etree.Element("Description")
            if not self.desc.startswith('"'):
                self.desc = '"' + self.desc
            if not self.desc.endswith('"') or self.desc == '"':
                self.desc += '"'
            desc.text = etree.CDATA(self.desc)
            nTabs = 3 if len(self.flags) or self.value is not None or self.aVals is not None else 2
            desc.tail = '\n' + nTabs * '\t'
            elem.append(desc)

            if self.flags:
                flags = etree.Element("Flags")
                nTabs = 3 if self.value is not None or self.aVals is not None else 2
                flags.tail = '\n' + nTabs * '\t'
                flags.text = '\n' + 4 * '\t'
                elem.append(flags)
                flagList = list(self.flags)
                for f in flagList:
                    if   f == PARFLG_CHILD:    element = etree.Element("ParFlg_Child")
                    elif f == PARFLG_UNIQUE:   element = etree.Element("ParFlg_Unique")
                    elif f == PARFLG_HIDDEN:   element = etree.Element("ParFlg_Hidden")
                    elif f == PARFLG_BOLDNAME: element = etree.Element("ParFlg_BoldName")
                    nTabs = 4 if flagList.index(f) < len(flagList) - 1 else 3
                    element.tail = '\n' + nTabs * '\t'
                    flags.append(element)

            if self.value is not None or (self.iType == PAR_STRING and self.aVals is None):
                #FIXME above line why string?
                value = etree.Element("Value")
                value.text = self._valueToString(self.value)
                value.tail = '\n' + 2 * '\t'
                elem.append(value)
            elif self.aVals is not None:
                elem.append(self.aVals)
            elem.tail = '\n' + 2 * '\t'
        else:
            elem = etree.Comment(self.name)
            elem.tail = 2 * '\n' + 2 * '\t'
        return elem

    @eTree.setter
    def eTree(self, inETree):
        self.text = inETree.text
        self.tail = inETree.tail
        if not isinstance(inETree, etree._Comment):
            self.__eTree = inETree
            self.flags = set()
            self.iType = self.getTypeFromString(self.__eTree.tag)

            self.name       = self.__eTree.attrib["Name"]
            self.desc       = self.__eTree.find("Description").text
            self.descTail   = self.__eTree.find("Description").tail

            val = self.__eTree.find("Value")
            if val is not None:
                self.value = self.__toFormat(val.text)
                self.valTail = val.tail
            else:
                self.value = None
                self.valTail = None

            self.aVals = self.__eTree.find("ArrayValues")

            if self.__eTree.find("Flags") is not None:
                self.flagsTail = self.__eTree.find("Flags").tail
                for f in self.__eTree.find("Flags"):
                    if f.tag == "ParFlg_Child":     self.flags |= {PARFLG_CHILD}
                    if f.tag == "ParFlg_Unique":    self.flags |= {PARFLG_UNIQUE}
                    if f.tag == "ParFlg_Hidden":    self.flags |= {PARFLG_HIDDEN}
                    if f.tag == "ParFlg_BoldName":  self.flags |= {PARFLG_BOLDNAME}

        else:  # _Comment
            self.iType = PAR_COMMENT
            self.name = inETree.text
            self.desc = ''
            self.value = None
            self.aVals = None

    @property
    def aVals(self):
        if self._aVals is not None:
            aValue = etree.Element("ArrayValues", FirstDimension=str(self.__fd), SecondDimension=str(self.__sd))
        else:
            return None
        aValue.text = '\n' + 4 * '\t'
        aValue.tail = '\n' + 2 * '\t'

        for rowIdx, row in enumerate(self._aVals):
            for colIdx, cell in enumerate(row):
                if self.__sd:
                    arrayValue = etree.Element("AVal", Column=str(colIdx + 1), Row=str(rowIdx + 1))
                    nTabs = 3 if colIdx == len(row) - 1 and rowIdx == len(self._aVals) - 1 else 4
                else:
                    arrayValue = etree.Element("AVal", Row=str(rowIdx + 1))
                    nTabs = 3 if rowIdx == len(self._aVals) - 1 else 4
                arrayValue.tail = '\n' + nTabs * '\t'
                aValue.append(arrayValue)
                arrayValue.text = self._valueToString(cell)
        return aValue

    @aVals.setter
    def aVals(self, inETree):
        if inETree is not None:
            self.__fd = int(inETree.attrib["FirstDimension"])
            self.__sd = int(inETree.attrib["SecondDimension"])
            if self.__sd > 0:
                self._aVals = [["" for _ in range(self.__sd)] for _ in range(self.__fd)]
                for v in inETree.iter("AVal"):
                    x = int(v.attrib["Column"]) - 1
                    y = int(v.attrib["Row"]) - 1
                    self._aVals[y][x] = self.__toFormat(v.text)
            else:
                self._aVals = [[""] for _ in range(self.__fd)]
                for v in inETree.iter("AVal"):
                    y = int(v.attrib["Row"]) - 1
                    self._aVals[y][0] = self.__toFormat(v.text)
            self.aValsTail = inETree.tail
        else:
            self._aVals = None

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

# -------------------/parameter classes --------------------------------------------------------------------------------

# ------------------- API2 connectivity --------------------------------------------------------------------------------

class BOAPIv2(object):
    BROWSER_CLOSE_WINDOW = '''<!DOCTYPE html> 
                            <html> 
                                    <script type="text/javascript"> 
                                        function close_window() { close(); }
                                    </script>
                                <body onload="close_window()"/>
                            </html>'''
    CLIENT_ID = "NL8IZo82T84ZCOruAZom4LlmrzkQFXPW"
    CLIENT_SECRET = "5RNNKjqAAA1szIImP0CO2IFNC6Z8OoBMQeiMKwwoxST7ntSFJhIQKVG1s1DEbLOV"
    REDIRECT_URI = "http://localhost"
    PORT_NUMBER = 80
    MAX_PAGE_NUMBER = 10
    PAGE_MAX_SIZE = 1000
    code = None
    server = None
    brands = {}  # brand permalink-guid

    class myHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            global data
            self.wfile.write(BOAPIv2.BROWSER_CLOSE_WINDOW)
            data = urlparse.parse_qs(urlparse.urlparse(self.path).query)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            BOAPIv2.code = data['code']

            BOAPIv2.server.server_close()


    def __init__(self, inCurrentConfig):
        self.token_type = ""
        self.refresh_token = ""
        self.access_token = ""

        try:
            if  inCurrentConfig.has_option("BOAPIv2", "token_type") and \
                inCurrentConfig.has_option("BOAPIv2", "refresh_token"):
                self.token_type = inCurrentConfig.get("BOAPIv2", "token_type")
                self.refresh_token = inCurrentConfig.get("BOAPIv2", "refresh_token")
                self.get_access_token_from_refresh_token()

            if inCurrentConfig.has_option("BOAPIv2", "brands"):
                b = inCurrentConfig.get("BOAPIv2", "brands").split(', ')
                self.brands = {k: v for k, v in zip(b[::2], b[1::2])}
        except (NoSectionError, NoOptionError):
            pass

    def refreshBrandDict(self):
        page = 1
        while page < BOAPIv2.MAX_PAGE_NUMBER:
            res = self.get_data_with_access_token("/admin/v1/brands",
                                            {"fields": "permalink, id",
                                             "page": page,
                                             "pageSize": BOAPIv2.PAGE_MAX_SIZE})
            rjson = json.load(res)
            if res.status == httplib.OK:
                for brand in rjson['data'] :
                    self.brands[brand['permalink']] = brand['id']
                if rjson['meta']['hasNextPage']:
                    page += 1
                else:
                    break
            else:
                break

    def getProductData(self, inBrandGUID, inProductPermalink):
        products = self.get_data_with_access_token("/admin/v1/brands/%s/products" % (inBrandGUID, ), {"pageSize": BOAPIv2.PAGE_MAX_SIZE})
        jProd = json.load(products)
        foundData = next((prod for prod in jProd['data'] if prod['permalink'].lower() == inProductPermalink.lower()), None)
        iPage = 1

        while jProd['meta']['hasNextPage'] and not foundData:
            iPage += 1
            products = self.get_data_with_access_token("/admin/v1/brands/%s/products" % (inBrandGUID, ), {'page': iPage,
                                                                                                          "pageSize": BOAPIv2.PAGE_MAX_SIZE})
            jProd = json.load(products)
            foundData = next((prod for prod in jProd['data'] if prod['permalink'].lower() == inProductPermalink.lower()), None)

        productGUID = foundData['id'] if foundData else None

        res = json.load(self.get_data_with_access_token("/admin/v1/brands/%s/products/%s" % (inBrandGUID, productGUID, ), {}))
        return res

        # 1. Logging in with access token

    def get_data_with_access_token(self, inPath, inUrlDict):
        response = self._get_data_with_access_token(inPath, inUrlDict)

        if response.status != httplib.OK:
            self.log_in()
            response = self._get_data_with_access_token(inPath, inUrlDict)
        return response

    def _get_data_with_access_token(self, inPath, inUrlDict):
        conn = httplib.HTTPSConnection("api.bimobject.com")
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Authorization": self.token_type + " " + self.access_token}
        urlDict = urllib.urlencode(inUrlDict)
        conn.request("GET", inPath + "?" +  urlDict, '', headers)
        return conn.getresponse()

    # 2. If access token doesn't work, try refresh_token
    def get_access_token_from_refresh_token(self):
        conn = httplib.HTTPSConnection("api.bimobject.com")
        urlDict = urllib.urlencode({"client_id": BOAPIv2.CLIENT_ID,
                                    "client_secret": BOAPIv2.CLIENT_SECRET,
                                    "grant_type": "refresh_token",
                                    "refresh_token": self.refresh_token, })
        headers = {"Content-type": "application/x-www-form-urlencoded", }
        conn.request("POST", "/oauth2/token", urlDict, headers)
        response = conn.getresponse()
        if response.status != httplib.OK:
            self.log_in()
        else:
            rjson = json.load(response)
            self.access_token = rjson['access_token']

    # 3. Logging in explicitely
    def log_in(self):
        code_verifier = base64.urlsafe_b64encode(os.urandom(64))
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier).digest()).rstrip(b'=')
        # code_challenge = base64.b64encode(hashlib.sha256(code_verifier).digest())

        authorizePath = '/identity/connect/authorize'
        urlDict = urllib.urlencode({"client_id": BOAPIv2.CLIENT_ID,
                                    "response_type": "code",
                                    "redirect_uri": BOAPIv2.REDIRECT_URI,
                                    "scope": "admin admin.brand admin.product offline_access",
                                    # "scope"                 : "search_api search_api_downloadbinary",
                                    "code_challenge": code_challenge,
                                    "code_challenge_method": "S256",
                                    "state": "1",
                                    })

        ue = urlparse.urlunparse(('https',
                                  'accounts.bimobject.com',
                                  authorizePath,
                                  '',
                                  urlDict,
                                  '',))
        webbrowser.open(ue)
        BOAPIv2.server = HTTPServer(('', BOAPIv2.PORT_NUMBER), BOAPIv2.myHandler)

        try:
            BOAPIv2.server.serve_forever()
        except IOError:
            pass

        urlDict2 = urllib.urlencode({"client_id": BOAPIv2.CLIENT_ID,
                                     "client_secret": BOAPIv2.CLIENT_SECRET,
                                     "grant_type": "authorization_code",
                                     # "grant_type"       : "client_credentials_for_admin",
                                     "code": BOAPIv2.code,
                                     "code_verifier": code_verifier,
                                     "redirect_uri": BOAPIv2.REDIRECT_URI, })

        # print urlDict2

        headers = {"Content-type": "application/x-www-form-urlencoded", }
        conn = httplib.HTTPSConnection("accounts.bimobject.com")
        conn.request("POST", "/identity/connect/token", urlDict2, headers)
        # conn.request("GET", "/identity/connect/authorize", urlDict2, headers)
        response = conn.getresponse().read()
        print "response: " + response

        try:
            self.access_token  = json.loads(response)['access_token']
            self.refresh_token = json.loads(response)['refresh_token']
            self.token_type    = json.loads(response)['token_type']
        except KeyError:
            pass


# ------------------- Google Drive API connectivity --------------------------------------------------------------------


# ------------------- GUI ------------------------------
# ------------------- GUI ------------------------------
# ------------------- GUI ------------------------------

# ------------------- data classes -------------------------------------------------------------------------------------

class GeneralFile(object) :
    """
    ###basePath:   C:\...\
    fullPath:   C:\...\relPath\fileName.ext  -only for sources; dest stuff can always be modified
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
    """
    def __init__(self, relPath, **kwargs):
        self.relPath            = relPath           #.replace("\\", "/")
        self.fileNameWithExt    = os.path.basename(relPath)
        self.fileNameWithOutExt = os.path.splitext(self.fileNameWithExt)[0]
        self.ext                = os.path.splitext(self.fileNameWithExt)[1]
        self.dirName            = os.path.dirname(relPath)
        if 'root' in kwargs:
            self.fullPath = os.path.join(kwargs['root'], self.relPath)
            self.fullDirName         = os.path.dirname(self.fullPath)


    def refreshFileNames(self):
        self.fileNameWithExt    = self.name + self.ext
        self.fileNameWithOutExt = self.name
        self.relPath            = self.dirName + self.fileNameWithExt

    def __lt__(self, other):
        return self.fileNameWithOutExt < other.name


class SourceFile(GeneralFile):
    def __init__(self, relPath, **kwargs):
        super(SourceFile, self).__init__(relPath, **kwargs)
        # self.fullPath = SourceXMLDirName.get() + "/" + relPath.replace("\\", "/")
        self.fullPath = os.path.join(SourceXMLDirName.get(), relPath)


class DestFile(GeneralFile):
    def __init__(self, fileName, **kwargs):
        super(DestFile, self).__init__(fileName)
        self.sourceFile         = kwargs['sourceFile']
        #FIXME sourcefile multiple times defined in Dest* classes
        self.ext                = self.sourceFile.ext


class SourceImage(SourceFile):
    def __init__(self, sourceFile, **kwargs):
        super(SourceImage, self).__init__(sourceFile, **kwargs)
        self.name = self.fileNameWithExt
        self.isEncodedImage = False


class DestImage(DestFile):
    def __init__(self, sourceFile, stringFrom, stringTo):
        self._name               = re.sub(stringFrom, stringTo, sourceFile.name, flags=re.IGNORECASE)
        self.sourceFile         = sourceFile
        self.relPath            = sourceFile.dirName + "//" + self._name
        super(DestImage, self).__init__(self.relPath, sourceFile=self.sourceFile)
        # self.path               = TargetImageDirName.get() + "/" + self.relPath
        self.ext                = self.sourceFile.ext

        if stringTo not in self._name and bAddStr.get():
            self.fileNameWithOutExt = os.path.splitext(self._name)[0] + stringTo
            self._name           = self.fileNameWithOutExt + self.ext
        self.fileNameWithExt = self._name

        self.relPath            = sourceFile.dirName + "//" + self._name
        super(DestImage, self).__init__(self.relPath, sourceFile=self.sourceFile)
        # self.path               = TargetImageDirName.get() + "/" + self.relPath

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, inName):
        self._name      = inName
        # self.relPath    = self.dirName + "/" + self._name
        self.relPath    = os.path.join(self.dirName, self._name)

    def refreshFileNames(self):
        pass

    #FIXME self.name as @property


class XMLFile(GeneralFile):
    def __init__(self, relPath, **kwargs):
        super(XMLFile, self).__init__(relPath, **kwargs)
        self._name       = self.fileNameWithOutExt
        self.bPlaceable  = False
        self.prevPict    = ''

    def __lt__(self, other):
        if self.bPlaceable and not other.bPlaceable:
            return True
        if not self.bPlaceable and other.bPlaceable:
            return False
        return self._name < other.name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, inName):
        self._name   = inName
        # self.relPath = self.dirName + "/" + self._name
        # self.fileNameWithExt = self._name + self.ext


class SourceXML (XMLFile, SourceFile):

    def __init__(self, relPath):
        global all_keywords
        super(SourceXML, self).__init__(relPath)
        self.calledMacros   = {}
        self.parentSubTypes = []
        self.scripts        = {}

        mroot = etree.parse(self.fullPath, etree.XMLParser(strip_cdata=False))
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

        for a in mroot.findall("./Ancestry"):
            for ancestryID in a.findall(ID):
                self.parentSubTypes += [ancestryID.text]

        for m in mroot.findall("./CalledMacros/Macro"):
            calledMacroID = m.find(ID).text
            self.calledMacros[calledMacroID] = string.strip(m.find("MName").text, "'" + '"')

        #Parameter manipulation: checking usage and later add custom pars
        self.parameters = ParamSection(mroot.find("./ParamSection"))

        for scriptName in SCRIPT_NAMES_LIST:
            script = mroot.find("./%s" % scriptName)
            if script is not None:
                self.scripts[scriptName] = script.text

        # for par in self.parameters:
        #     par.isUsed = self.checkParameterUsage(par, set())
        k = mroot.find("./Keywords")
        if k is not None:
            t = re.sub("\n", ", ", k.text)
            self.keywords = [kw.strip() for kw in t.split(",") if kw != ''][1:-1]
            all_keywords |= set(self.keywords)
        else:
            self.keywords = None

        if self.guid.upper() not in source_guids:
            source_guids[self.guid.upper()] = self.name

        pic = mroot.find("./Picture")
        if pic is not None:
            if "path" in pic.attrib:
                self.prevPict = pic.attrib["path"]

    def checkParameterUsage(self, inPar, inMacroSet):
        """
        Checking whether a certain Parameter is used in the macro or any of its called macros
        :param inPar:       Parameter
        :param inMacroSet:  set of macros that the parameter was searched in before
        :return:        boolean
        """
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

    def __init__(self, sourceFile, stringFrom = "", stringTo = "", **kwargs):
        # Renaming
        if 'targetFileName' in kwargs:
            self.name     = kwargs['targetFileName']
        else:
            self.name     = re.sub(stringFrom, stringTo, sourceFile.name, flags=re.IGNORECASE)
            if stringTo not in self.name and bAddStr.get():
                self.name += stringTo
        if self.name.upper() in dest_dict:
            i = 1
            while self.name.upper() + "_" + str(i) in dest_dict.keys():
                i += 1
            self.name += "_" + str(i)

            # if "XML Target file exists!" in self.warnings:
            #     self.warnings.remove("XML Target file exists!")
            #     self.refreshFileNames()
        self.relPath                = os.path.join(sourceFile.dirName, self.name + sourceFile.ext)

        super(DestXML, self).__init__(self.relPath, sourceFile=sourceFile)
        self.warnings               = []

        self.sourceFile             = sourceFile
        self.guid                   = str(uuid.uuid4()).upper()
        self.bPlaceable             = sourceFile.bPlaceable
        self.iVersion               = sourceFile.iVersion
        self.proDatURL              = ''
        self.bOverWrite             = False
        self.bRetainCalledMacros    = False

        self.parameters             = copy.deepcopy(sourceFile.parameters)

        fullPath                    = os.path.join(TargetXMLDirName.get(), self.relPath)
        if os.path.isfile(fullPath):
            #for overwriting existing xmls while retaining GUIDs etx
            if bOverWrite.get():
                #FIXME to finish it
                self.bOverWrite             = True
                self.bRetainCalledMacros    = True
                mdp = etree.parse(fullPath, etree.XMLParser(strip_cdata=False))
                # self.iVersion = mdp.getroot().attrib['Version']
                # if self.iVersion >= AC_18:
                #     self.ID = "MainGUID"
                # else:
                #     self.ID = "UNID"
                self.guid = mdp.getroot().attrib[ID]
                print mdp.getroot().attrib[ID]
            else:
                self.warnings += ["XML Target file exists!"]

        fullGDLPath                 = os.path.join(TargetGDLDirName.get(), self.fileNameWithOutExt + ".gsm")
        if os.path.isfile(fullGDLPath):
            self.warnings += ["GDL Target file exists!"]

        if self.iVersion >= AC_18:
            # AC18 and over: adding licensing statically, can be manually owerwritten on GUI
            self.author         = "BIMobject"
            self.license        = "CC BY-ND"
            self.licneseVersion = "3.0"

        if self.sourceFile.guid.upper() not in id_dict:
            # if id_dict[self.sourceFile.guid.upper()] == "":
            id_dict[self.sourceFile.guid.upper()] = self.guid.upper()

    def getCalledMacro(self):
        """
        getting called marco scripts
        FIXME to be removed
        :return:
        """

#----------------- gui classes -----------------------------------------------------------------------------------------

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
        idx = self.id
        self.id = None
        if idx:
            self.widget.after_cancel(idx)

    def showtip(self, event=None):
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


class InputDirPlusText():
    def __init__(self, top, text, target, tooltip=''):
        self.target = target
        self.filename = ''
        self._frame = tk.Frame(top)
        self._frame.grid()

        self._frame.columnconfigure(1, weight=1)

        self.buttonDirName = tk.Button(self._frame, {"text": text, "command": self.inputDirName, })
        self.buttonDirName.grid({"sticky": tk.W + tk.E, "row": 0, "column": 0, })

        self.entryDirName = tk.Entry(self._frame, {"width": 30, "textvariable": target})
        self.entryDirName.grid({"row": 0, "column": 1, "sticky": tk.E + tk.W, })

        if tooltip:
            CreateToolTip(self._frame, tooltip)

    def inputDirName(self):
        self.filename = tkFileDialog.askdirectory(initialdir="/", title="Select folder")
        self.target.set(self.filename)
        self.entryDirName.delete(0, tk.END)
        self.entryDirName.insert(0, self.filename)


class InputDirPlusBool():
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
        tk.Listbox.__init__(self, top, _dict)

    def refresh(self, *_):
        if self.dict == replacement_dict:
            try:
                FC1(self.target.get(), SourceXMLDirName.get())
                FC1(self.imgTarget.get(), SourceImageDirName.get())
            except AttributeError:
                return
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
        self.bOverWrite         = tk.BooleanVar()
        self.bAddStr            = tk.BooleanVar()

        self.bXML               = tk.BooleanVar()
        self.bGDL               = tk.BooleanVar()

        self.observer  = None
        self.observer2 = None

        self.warnings = []

        self.bo = None

        global \
            SourceXMLDirName, SourceGDLDirName, TargetXMLDirName, TargetGDLDirName, SourceImageDirName, TargetImageDirName, \
            AdditionalImageDir, bDebug, bCheckParams, ACLocation, bGDL, bXML, dest_dict, dest_guids, replacement_dict, id_dict, \
            pict_dict, source_pict_dict, source_guids, bAddStr, bOverWrite, all_keywords, StringTo

        SourceXMLDirName    = self.SourceXMLDirName
        SourceGDLDirName    = self.SourceXMLDirName
        TargetXMLDirName    = self.TargetXMLDirName
        TargetGDLDirName    = self.TargetGDLDirName
        SourceImageDirName  = self.SourceImageDirName
        TargetImageDirName  = self.TargetImageDirName
        AdditionalImageDir  = self.AdditionalImageDir
        bCheckParams        = self.bCheckParams
        bDebug              = self.bDebug
        bXML                = self.bXML
        bGDL                = self.bGDL
        ACLocation          = self.ACLocation
        bAddStr             = self.bAddStr
        bOverWrite          = self.bOverWrite
        StringTo            = self.StringTo

        __tooltipIDPT1 = "Something like E:/_GDL_SVN/_TEMPLATE_/AC18_Opening/library"
        __tooltipIDPT2 = "Images' dir that are NOT to be renamed per project and compiled into final gdls (prev pics, for example), something like E:\_GDL_SVN\_TEMPLATE_\AC18_Opening\library_images"
        __tooltipIDPT3 = "Something like E:/_GDL_SVN/_TARGET_PROJECT_NAME_/library"
        __tooltipIDPT4 = "Final GDL output dir"
        __tooltipIDPT5 = "If set, copy project specific pictures here, too"
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
                    print "NoOptionError"
                    continue
                except NoSectionError:
                    print "NoSectionError"
                    continue
                except ValueError:
                    print "ValueError"
                    continue
        except NoSectionError:
            print "NoSectionError"

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

        self.InputFrameS = [tk.Frame(self.inputFrame) for _ in range (6)]
        for f, r, cc in zip(self.InputFrameS, range(6), [0, 1, 1, 0, 0, 1, ]):
            f.grid({"row": r, "column": 0, "sticky": tk.N + tk.S + tk.E + tk.W, })
            self.InputFrameS[r].grid_columnconfigure(cc, weight=1)
            self.InputFrameS[r].rowconfigure(0, weight=1)

        iF = 0

        self.entryTextNameFrom = tk.Entry(self.InputFrameS[iF], {"width": 20, "textvariable": self.StringFrom, })
        self.entryTextNameFrom.grid({"column": 0, "sticky": tk.SE + tk.NW, })

        iF += 1

        InputDirPlusText(self.InputFrameS[iF], "XML Source folder", self.SourceXMLDirName, __tooltipIDPT1)

        iF += 1

        InputDirPlusText(self.InputFrameS[iF], "GDL Source folder", self.SourceGDLDirName, __tooltipIDPT7)

        iF += 1

        self.listBox = ListboxWithRefresh(self.InputFrameS[iF], {"target": self.SourceXMLDirName, "imgTarget": self.SourceImageDirName, "dict": replacement_dict})
        self.listBox.grid({"row": 0, "column": 0, "sticky": tk.E + tk.W + tk.N + tk.S})
        self.observerLB1 = self.SourceXMLDirName.trace_variable("w", self.listBox.refresh)

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

        InputDirPlusText(self.InputFrameS[iF], "Images' source folder",  self.SourceImageDirName, __tooltipIDPT2)
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
        for f, r, cc in zip(self.outputFrameS, range(6), [0, 1, 1, 0, 0, 1]):
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

        self.bAddStrCheckButton = tk.Checkbutton(self.bottomFrame, {"text": "Always add strings", "variable": self.bAddStr})
        self.bAddStrCheckButton.grid({"row": 0, "column": iF}); iF += 1

        self.OverWriteCheckButton   = tk.Checkbutton(self.bottomFrame, {"text": "Overwrite", "variable": self.bOverWrite})
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

        self.addRecursiveButton = tk.Button(self.buttonFrame, {"text": "Recursive >", "command": self.addFileRecursively})
        self.addRecursiveButton.grid({"row":_i, "column": 0, "sticky": tk.W + tk.E})
        CreateToolTip(self.addRecursiveButton, "Add macro, and all its called macro and subtypes recursively, if not added already")

        _i += 1

        self.addButton          = tk.Button(self.buttonFrame, {"text": ">", "command": self.addFile})
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

        #FIXME
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
        CreateToolTip(self.AdditionalImageDirEntry, __tooltipIDPT6)

    def getFromCSV(self):
        csvFileName = tkFileDialog.askopenfilename(initialdir="/", title="Select folder", filetypes=(("CSV files", "*.csv"), ("all files","*.*")))
        if csvFileName:
            with open(csvFileName, "r") as csvFile:
                firstRow = next(csv.reader(csvFile))
                for row in csv.reader(csvFile):
                    destItem = self.addFileRecursively(row[0], row[1])
                    if row[2]:
                        destItem.parameters.BO_update(row[2])
                    if len(row) > 3 and next((c for c in row[2:] if c != ""), ""):
                        for parName, col in zip(firstRow[3:], row[3:]):
                            destItem.parameters.createParamfromCSV(parName, col)

    def showGoogleSpreadsheetEntry(self):
        self.GoogleSSInfield = GoogleSSInfield(self)
        self.GoogleSSInfield.top.protocol("WM_DELETE_WINDOW", self.getFromGoogleSpreadsheet)

        self.GoogleSSBbutton.config(cnf={'state': tk.DISABLED})

    def getFromGoogleSpreadsheet(self):
        self.GoogleSSBbutton.config(cnf={'state': tk.NORMAL})
        print self.GoogleSSInfield.GoogleSSURL.get()
        self.GoogleSSInfield.top.destroy()

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

    @staticmethod
    def start():
        main2()
        # print "Starting conversion"

    def addFile(self, sourceFileName='', targetFileName=''):
        if not sourceFileName:
            sourceFileName = self.listBox.get(tk.ACTIVE)
        if sourceFileName == LISTBOX_SEPARATOR:
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

    def addFileRecursively(self, sourceFileName='', targetFileName=''):
        if not sourceFileName:
            sourceFileName = self.listBox.get(tk.ACTIVE)

        destItem = self.addFile(sourceFileName, targetFileName)

        if sourceFileName.upper() not in replacement_dict:
            #should be in library_additional
            return

        x = replacement_dict[sourceFileName.upper()]

        for k, v in x.calledMacros.iteritems():
            if v not in dest_sourcenames:
                self.addFileRecursively(v)

        for parentGUID in x.parentSubTypes:
            if parentGUID not in id_dict:
                if parentGUID in source_guids:
                    self.addFileRecursively(source_guids[parentGUID])

        for pict in source_pict_dict.values():
            for script in x.scripts.values():
                if pict.fileNameWithExt.upper() in script or pict.fileNameWithOutExt.upper() in script.upper():
                    self.addImageFile(pict.fileNameWithExt)

        if x.prevPict:
            bN = os.path.basename(x.prevPict)
            self.addImageFile(bN)

        self.refreshDestItem()
        return destItem

    def delFile(self, fileName = ''):
        if not fileName:
            fileName = self.listBox3.get(tk.ACTIVE)
        if fileName == LISTBOX_SEPARATOR:
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
        # self.destItem.parameters.BO_update(self.destItem.proDatURL)
        # print "BOupdate ready"

        if not self.bo:
            self.bo = BOAPIv2(self.currentConfig)

        self.destItem.parameters.BO_update2(self.destItem.proDatURL, self.currentConfig, self.bo)
        _brandName = self.destItem.proDatURL.split('/')[3].encode()
        _productGUID = self.destItem.proDatURL.split('/')[5].encode()
        try:
            self.brandGUID = self.bo.brands[_brandName]
        except KeyError:
            self.bo.refreshBrandDict()
            self.brandGUID = self.bo.brands[_brandName]

        print self.bo.getProductData(self.brandGUID, _productGUID)

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
        currentConfig.set("ArchiCAD", "aclocation",         self.ACLocEntry.get())
        currentConfig.set("ArchiCAD", "additionalimagedir", self.AdditionalImageDirEntry.get())

        currentConfig.set("ArchiCAD", "bdebug",             self.bDebug.get())
        currentConfig.set("ArchiCAD", "bxml",               self.bXML.get())
        currentConfig.set("ArchiCAD", "bgdl",               self.bGDL.get())

        currentConfig.set("ArchiCAD", "sourcedirname", self.SourceXMLDirName.get())
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
        currentConfig.set("ArchiCAD", "allkeywords",        ', '.join(sorted(list(all_keywords))))

        if self.bo:
            currentConfig.add_section("BOAPIv2")
            currentConfig.set("BOAPIv2", "token_type",          self.bo.token_type)
            currentConfig.set("BOAPIv2", "refresh_token",       self.bo.refresh_token)
            if self.bo.brands:
                currentConfig.set("BOAPIv2", "brands", ', '.join(list(reduce(lambda x, y: x+y, self.bo.brands.iteritems()))))

        with open(self.appDataDir + "/TemplateMarker.ini", 'wb') as configFile:
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


# ------------------- Parameter editing window ------

# -------------------/GUI------------------------------
# -------------------/GUI------------------------------
# -------------------/GUI------------------------------

def FC1(inFile, inRootFolder):
    """
    only scanning input dir recursively to set up xml and image files' list
    :param inFile:
    :param outFile:
    :return:
    """
    try:
        for f in listdir(inFile):
            try:
                src = os.path.join(inFile, f)           #.replace("\\", "/")
                # if it's NOT a directory
                if not os.path.isdir(src):
                    if os.path.splitext(os.path.basename(f))[1].upper() in (".XML", ):
                        sf = SourceXML(os.path.relpath(src, inRootFolder))
                        replacement_dict[sf._name.upper()] = sf
                        # id_dict[sf.guid.upper()] = ""
                    else:
                        # set up replacement dict for other files
                        if os.path.splitext(os.path.basename(f))[0].upper() not in source_pict_dict:
                            sI = SourceImage(os.path.relpath(src, inRootFolder), root=inRootFolder)
                            SIDN = SourceImageDirName.get()
                            if SIDN in sI.fullDirName:
                                sI.isEncodedImage = True
                            source_pict_dict[sI.fileNameWithExt.upper()] = sI
                else:
                    FC1(src, inRootFolder)

            except KeyError:
                print "KeyError %s" % f
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
        tempdir = os.path.join(tempfile.mkdtemp(), "library")

    # tempPicDir = TargetImageDirName.get()
    targPicDir = TargetImageDirName.get()

    if not targPicDir:
        _head, _libDir = os.path.split(tempdir)
        if _libDir == "library":
            targPicDir = os.path.join(_head, "library_images")
        else:
            targPicDir = os.path.join(tempdir)

    if not targPicDir:
        tempPicDir = tempfile.mkdtemp()
    else:
        tempPicDir = targPicDir

    print "tempdir: %s" % tempdir
    print "tempPicDir: %s" % tempPicDir

    for k in dest_dict.keys():
        dest        = dest_dict[k]
        src         = dest.sourceFile
        srcPath     = src.fullPath
        destPath    = os.path.join(tempdir, dest.relPath)
        destDir     = os.path.dirname(destPath)

        print "%s -> %s" % (srcPath, destPath,)

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
            if section is not None:
                t = section.text

                for dI in dest_dict.keys():
                    t = re.sub(dest_dict[dI].sourceFile.name, dest_dict[dI].name, t, flags=re.IGNORECASE)

                for pr in pict_dict.keys():
                    #Replacing images
                    t = re.sub(pict_dict[pr].sourceFile.fileNameWithOutExt + '(?!' + StringTo.get() + ')', pict_dict[pr].fileNameWithOutExt, t, flags=re.IGNORECASE)

                section.text = etree.CDATA(t)

        # ---------------------Prevpict-------------------------------------------------------

        if dest.bPlaceable:
            section = mdp.find('Picture')
            if isinstance(section, etree._Element) and 'path' in section.attrib:
                path = os.path.basename(section.attrib['path']).upper()
                if path:
                    n = next((pict_dict[p].relPath for p in pict_dict.keys() if
                              os.path.basename(pict_dict[p].sourceFile.relPath).upper() == path), None)
                    if n:
                        section.attrib['path'] = os.path.dirname(n) +"/" + os.path.basename(n)

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

        #FIXME not clear, check, writes an extra empty mainunid field
        #FIXME ancestries to be used in param checking
        #FIXME this is unclear what id does
        for m in mdp.findall("./Ancestry/" + ID):
            guid = m.text
            if guid.upper() in id_dict:
                print "ANCESTRY: %s" % guid
                par = m.getparent()
                par.remove(m)

                element = etree.Element(ID)
                element.text = id_dict[guid]
                element.tail = '\n'
                par.append(element)
        try:
            os.makedirs(destDir)
        except WindowsError:
            pass
        with open(destPath, "w") as file_handle:
            mdp.write(file_handle, pretty_print=True, encoding="UTF-8", )

    _picdir =  AdditionalImageDir.get()
    # _picdir2 = SourceImageDirName.get()

    # shutil.copytree(_picdir, tempPicDir + "/IMAGES_GENERIC")
    if _picdir:
        for f in listdir(_picdir):
            shutil.copytree(os.path.join(_picdir, f), os.path.join(tempPicDir, f))

    # if _picdir2:
    #     for f in listdir(_picdir2):
    #         shutil.copytree(_picdir2 + "/" + f, tempPicDir + "/" + f)

    for f in pict_dict.keys():
        if pict_dict[f].sourceFile.isEncodedImage:
            try:
                shutil.copyfile(os.path.join(SourceImageDirName.get(), pict_dict[f].sourceFile.relPath), os.path.join(targPicDir, pict_dict[f].relPath))
            except IOError:
                os.makedirs(os.path.join(targPicDir, pict_dict[f].dirName))
                shutil.copyfile(os.path.join(SourceImageDirName.get(), pict_dict[f].sourceFile.relPath), os.path.join(targPicDir, pict_dict[f].relPath))

            try:
                shutil.copyfile(os.path.join(SourceImageDirName.get(), pict_dict[f].sourceFile.relPath), os.path.join(tempPicDir, pict_dict[f].relPath))
            except IOError:
                os.makedirs(os.path.join(tempPicDir, pict_dict[f].dirName))
                shutil.copyfile(os.path.join(SourceImageDirName.get(), pict_dict[f].sourceFile.relPath), os.path.join(tempPicDir, pict_dict[f].relPath))
        else:
            if TargetGDLDirName.get():
                try:
                    shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(TargetGDLDirName.get(), pict_dict[f].relPath))
                except IOError:
                    os.makedirs(os.path.join(TargetGDLDirName.get(), pict_dict[f].dirName))
                    shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(TargetGDLDirName.get(), pict_dict[f].relPath))

            if TargetXMLDirName.get():
                try:
                    shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(TargetXMLDirName.get(), pict_dict[f].relPath))
                except IOError:
                    os.makedirs(os.path.join(TargetXMLDirName.get(), pict_dict[f].dirName))
                    shutil.copyfile(pict_dict[f].sourceFile.fullPath, os.path.join(TargetXMLDirName.get(), pict_dict[f].relPath))

    print "x2l Command being executed..."
    x2lCommand = '"%s" x2l -img "%s" "%s" "%s"' % (os.path.join(ACLocation.get(), 'LP_XMLConverter.exe'), tempPicDir, tempdir, TargetGDLDirName.get())

    if bDebug.get():
        print "ac command:"
        print x2lCommand
        with open(tempdir + "\dict.txt", "w") as d:
            for k in dest_dict.keys():
                d.write(k + " " + dest_dict[k].sourceFile.name + "->" + dest_dict[k].name + " " + dest_dict[k].sourceFile.guid + " -> " + dest_dict[k].guid + "\n")

        with open(tempdir + "\pict_dict.txt", "w") as d:
            for k in pict_dict.keys():
                d.write(pict_dict[k].sourceFile.fullPath + "->" + pict_dict[k].relPath+ "\n")

        with open(tempdir + "\id_dict.txt", "w") as d:
            for k in id_dict.keys():
                d.write(id_dict[k] + "\n")

    if bGDL.get():
        check_output(x2lCommand, shell=True)

    # cleanup ops
    if not bDebug.get():
        shutil.rmtree(tempPicDir) #FIXME
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

