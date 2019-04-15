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
        # list_of_tests = [
        #     #parameters, value, testfilename
        #     # ('iNtegerTest -c detlevel', '1', 'integerChild.xml'),
        #     # ('iNtegerTest --child detlevel', '1', 'integerChild.xml'),
        #     # ('iNtegerTest -c detlevel -d Teszt description', '1', 'integerChild_desc.xml'),
        #     # ('iNtegerTest -c detlevel -b -d Teszt description', '1', 'integerChild_desc_b.xml'),
        #     # ('iNtegerTest -c detlevel -u -d Teszt description', '1', 'integerChild_desc_u.xml'),
        #     # ('iNtegerTest -c detlevel -b -u -d Teszt description', '1', 'integerChild_desc_bu.xml'),
        #     # ('iNtegerTest -c detlevel -b -u -h -d Teszt description', '1', 'integerChild_desc_buh.xml'),
        #     # ('iNtegerTest -c detlevel --desc Teszt description', '1', 'integerChild_desc.xml'),
        #     # ('iNtegerTest -c detlevel --description Teszt description', '1', 'integerChild_desc.xml'),
        #     # ('iNtegerTest -a iFamily', '1', 'integerAfter.xml'),
        #     # ('iNtegerTest -f iThickness', '1', 'integerInfrontof.xml'),
        #     # ('TestBoolean -c detlevel -t Boolean', '1', 'booleanChildTrue.xml'),
        #     # ('TestBoolean -c detlevel -t Boolean', '0', 'booleanChildFalse.xml'),
        #     # ('TestFillPattern -c detlevel -t FillPattern', '1', 'fillpatternChild.xml'),
        #     # ('lIneTypeTest -a iFamily -i -t LineType', '1', 'lintetypeAfter.xml'),
        #     # ('TestLength -c detlevel -t Length', '1.05', 'lengthChild.xml'),
        #     # ('TestAngle -c detlevel -t Angle', '1.5', 'angleChild.xml'),
        #     # ('iNtegerTest -a iFamily -t Integer', '1', 'integerAfter.xml'),
        #     # ('TestMaterial -c detlevel -t Material', '1', 'materialChild.xml'),
        #     # ('TestPenColor -c detlevel -t PenColor', '1', 'pencolorChild.xml'),
        #     # ('TestRealNum -c detlevel -t RealNum', '1.00', 'realnumChild.xml'),
        #     # ('TestSeparator -a iFamily -t Separator', '1', 'SeparatorAfter.xml'),
        #     # ('TestString -c detlevel -t String', '"Teszt"', 'stringChild.xml'),
        #     # ('TestTitle -a iDetLevel2D -t Title', '', 'titleAfter.xml'),
        #     # ('TestComment -a iDetLevel2D -t Comment', '', 'commentAfter.xml'),
        #     # ('iNtegerTest -c detlevel -d Teszt árvíztűrő tükörfúrógép', '1', 'integerChild_desc_unicode.xml'),
        # ]
        # with open("original.xml", "r") as testFile:
        #     testNode = testFile.read()
        #     for testCase in list_of_tests:
        #         ps = ParamSection(inETree=etree.XML(testNode))
        #         if "test_" + testCase[2][:-4] in self:
        #             i = 1
        #             while True:
        #                 if testCase[2][:-4] + "_" + str(i) not in self:
        #                     test_case = TestGUIApp(testCase, dir_baseName, ps, testCase[2][:-4] + "_" + str(i))
        #                     break
        #                 else:
        #                     i += 1
        #         else:
        #             test_case = TestGUIApp(testCase, dir_baseName, ps)
        #         self.addTest(test_case)
        for fileName in os.listdir(dir_baseName  + "_items"):
            if not fileName.startswith('_'):
                print fileName
                parsedXML = etree.parse(dir_baseName  + "_items" + "\\" + fileName, etree.XMLParser(strip_cdata=False))
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
            outFileName = inDirPrefix + "_errors" + "\\" + inParams[2]
            testFileName = inDirPrefix + "_items" + "\\" + inParams[2]
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