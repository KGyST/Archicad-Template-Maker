#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-

import unittest
import os
from TemplateMaker import ParamSection
from lxml import etree
import csv

from xml import dom
from xml.dom import minidom


class XMLTree(minidom.Element):
    PATH_SEPARATOR = "/"

    def __init__(self, inDoc):
        self.__dict__ = inDoc.__dict__

    def getroot(self):
        return self.childNodes[0]

    def find(self, sPath):
        lPath = sPath.split(XMLTree.PATH_SEPARATOR)[1:]
        return self._getNode(self.getroot(), lPath)

    def _getNode(self, inNode, inListPath):
        if inListPath:
            for cN in inNode.childNodes:
                if cN.nodeType == XMLTree.ELEMENT_NODE:
                    if cN.nodeName == inListPath[0]:
                        return inNode._getNode(cN, inListPath[1:])
        else:
            return inNode


class TestSuite_CreateParamCommands(unittest.TestSuite):
    def __init__(self):
        self._tests = []
        dir_baseName = 'test_getFromCSV'
        for fileName in os.listdir(dir_baseName  + "_items"):
            if not fileName.startswith('_') and os.path.splitext(fileName)[1] == '.xml':
                parsedXML = etree.parse(os.path.join(dir_baseName  + "_items", fileName), etree.XMLParser(strip_cdata=False))
                # parsedXML = minidom.parse (os.path.join(dir_baseName  + "_items", fileName))
                meta = parsedXML.getroot()
                value = parsedXML.find("./Value").text
                embeddedXML = etree.tostring(parsedXML.find("./ParamSection"), encoding="UTF-8")
                if parsedXML.find("./Note") is not None:
                    print(parsedXML.find("./Note").text)
                else:
                    print(fileName)
                with open(meta.attrib['OriginalXML'], "r") as testFile:
                    if 'TestCSV' in meta.attrib:
                        aVals = [aR for aR in csv.reader(open(os.path.join(dir_baseName  + "_items", meta.attrib['TestCSV']), "r"))]
                    else:
                        aVals = None
                    testNode = testFile.read()
                    ps = ParamSection(inETree=etree.XML(testNode))
                    testCase = (meta.attrib['Command'], value, fileName)
                    test_case = TestCase_CreateParamCommands(testCase, dir_baseName, ps, embeddedXML=embeddedXML, AVals=aVals)
                    self.addTest(test_case)
        super(TestSuite_CreateParamCommands, self).__init__(self._tests)

    def __contains__(self, inName):
        for test in self._tests:
            if test._testMethodName == inName:
                return True
        return False


class TestCase_CreateParamCommands(unittest.TestCase):
    def __init__(self, inParams, inDirPrefix, inParamSection, inCustomName=None, embeddedXML=None, AVals=None):
        func = self.GUIAppTestCaseFactory(inParams, inDirPrefix, inParamSection, inCustomName, embeddedXML, AVals)
        setattr(TestCase_CreateParamCommands, func.__name__, func)
        super(TestCase_CreateParamCommands, self).__init__(func.__name__)

    @staticmethod
    def GUIAppTestCaseFactory(inParams, inDirPrefix, inParamSection, inCustomName=None, embeddedXML=None, AVals=None):
        def func(inObj):
            inParamSection.createParamfromCSV(inParams[0], inParams[1], AVals)
            outFileName = os.path.join(inDirPrefix + "_errors", inParams[2])
            testFileName = os.path.join(inDirPrefix + "_items", inParams[2])
            if os.path.isfile(outFileName):
                os.remove(outFileName)
            resultXMLasString = etree.tostring(inParamSection.toEtree(), encoding="UTF-8")
            try:
                if embeddedXML:
                    inObj.assertEqual(embeddedXML, resultXMLasString)
                else:
                    inObj.assertEqual(open(testFileName, "r").read(), resultXMLasString)
            except AssertionError:
                print(inParams[2])
                with open(outFileName, "w") as outputXMLFile:
                    outputXMLFile.write(resultXMLasString)
                raise
            except UnicodeDecodeError:
                inObj.assertEqual(embeddedXML.decode("UTF-8"), resultXMLasString.decode("UTF-8"))
        if not inCustomName:
            func.__name__ = "test_" + inParams[2][:-4]
        else:
            func.__name__ = inCustomName
        return func


#---------------------pytest---------------------
import pytest

def getTests():
    tests = []
    dir_baseName = 'test_getFromCSV'
    for fileName in os.listdir(dir_baseName + "_items"):
        if not fileName.startswith('_') and os.path.splitext(fileName)[1] == '.xml':
            parsedXML = etree.parse(os.path.join(dir_baseName + "_items", fileName), etree.XMLParser(strip_cdata=False))
            meta = parsedXML.getroot()
            value = parsedXML.find("./Value").text
            embeddedXML = etree.tostring(parsedXML.find("./ParamSection"), encoding="UTF-8")
            sNote = None

            if parsedXML.find("./Note") is not None:
                print(parsedXML.find("./Note").text)
                sNote = parsedXML.find("./Note").text
            else:
                print(fileName)

            with open(meta.attrib['OriginalXML'], "r") as testFile:
                    if 'TestCSV' in meta.attrib:
                        aVals = [aR for aR in
                                 csv.reader(open(os.path.join(dir_baseName + "_items", meta.attrib['TestCSV']), "r"))]
                    else:
                        aVals = None
                    testNode = testFile.read()
                    ps = ParamSection(inETree=etree.XML(testNode))
                    testCase = (meta.attrib['Command'], value, fileName)
                    test_case = {   'params':       testCase,
                                    'dirPrefix':    dir_baseName,
                                    'paramSection': ps,
                                    # 'customName':   None,
                                    'embeddedXML':  embeddedXML,
                                    'fileName':     fileName,
                                    'AVals':        aVals,
                                    'Note':         sNote, }
                    tests.append(test_case)
    return tests


class Test_File:
    dirPrefix = 'test_param'

    @pytest.mark.parametrize(
        'inTestCase', getTests()
    )
    def test_file(self, inTestCase):
        inParams        = inTestCase['params']
        inDirPrefix     = inTestCase['dirPrefix']
        inParamSection  = inTestCase['paramSection']
        embeddedXML     = inTestCase['embeddedXML']
        AVals           = inTestCase['AVals']

        inParamSection.createParamfromCSV(inParams[0], inParams[1], AVals)
        outFileName = os.path.join(inDirPrefix + "_errors", inParams[2])
        testFileName = os.path.join(inDirPrefix + "_items", inParams[2])
        if os.path.isfile(outFileName):
            os.remove(outFileName)
        resultXMLasString = etree.tostring(inParamSection.toEtree(), encoding="UTF-8")
        try:
            if embeddedXML:
                assert embeddedXML == resultXMLasString
            else:
                assert open(testFileName, "r").read() == resultXMLasString
        except AssertionError:
            print(inParams[2])
            with open(outFileName, "w") as outputXMLFile:
                outputXMLFile.write(resultXMLasString)
            raise
        except UnicodeDecodeError:
            assert embeddedXML.decode("UTF-8") == resultXMLasString.decode("UTF-8")