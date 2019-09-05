#!C:\Program Files\Python27amd64\python.exe
# -*- coding: utf-8 -*-

import unittest
import os
from TemplateMaker import ParamSection
from lxml import etree
import json

class TestGUIAppSuite(unittest.TestSuite):
    def __init__(self):
        self._tests = []
        dir_baseName = 'test_getFromCSV'
        for fileName in os.listdir(dir_baseName  + "_items"):
            if not fileName.startswith('_'):
                print fileName
                parsedXML = etree.parse(os.path.join(dir_baseName  + "_items", fileName), etree.XMLParser(strip_cdata=False))
                meta = parsedXML.getroot()
                value = parsedXML.find("./Value").text
                embeddedXML = etree.tostring(parsedXML.find("./ParamSection"))
                with open(meta.attrib['OriginalXML'], "r") as testFile:
                    testNode = testFile.read()
                    ps = ParamSection(inETree=etree.XML(testNode))
                    testCase = (meta.attrib['Command'], value, fileName)
                    test_case = TestGUIApp(testCase, dir_baseName, ps, embeddedXML=embeddedXML)
                    self.addTest(test_case)
        super(TestGUIAppSuite, self).__init__(self._tests)

    def __contains__(self, inName):
        for test in self._tests:
            if test._testMethodName == inName:
                return True
        return False

class TestGUIApp(unittest.TestCase):
    def __init__(self, inParams, inDirPrefix, inParamSection, inCustomName=None, embeddedXML=None):
        func = self.GUIAppTestCaseFactory(inParams, inDirPrefix, inParamSection, inCustomName, embeddedXML)
        setattr(TestGUIApp, func.__name__, func)
        super(TestGUIApp, self).__init__(func.__name__)

    @staticmethod
    def GUIAppTestCaseFactory(inParams, inDirPrefix, inParamSection, inCustomName=None, embeddedXML=None):
        def func(inObj):
            inParamSection.createParamfromCSV(inParams[0], inParams[1])
            outFileName = os.path.join(inDirPrefix + "_errors", inParams[2])
            testFileName = os.path.join(inDirPrefix + "_items", inParams[2])
            if os.path.isfile(outFileName):
                os.remove(outFileName)
            resultXMLasString = etree.tostring(inParamSection.toEtree())
            try:
                if embeddedXML:
                    inObj.assertEqual(embeddedXML, resultXMLasString)
                else:
                    inObj.assertEqual(open(testFileName, "r").read(), resultXMLasString)
            except AssertionError:
                print inParams[2]
                with open(outFileName, "w") as outputXMLFile:
                    outputXMLFile.write(resultXMLasString)
                raise
        if not inCustomName:
            func.__name__ = "test_" + inParams[2][:-4]
        else:
            func.__name__ = inCustomName
        return func