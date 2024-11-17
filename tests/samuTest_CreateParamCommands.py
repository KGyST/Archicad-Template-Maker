from unitTest.test_runner import JSONTestSuite, JSONTestCase
import os
from TemplateMaker import ParamSection
from lxml import etree
import csv

def XMLComparer(p_Dir):      #p_working_directory
    def func(p_Obj, p_function, p_TestData, **kwargs) :
        originalXML = os.path.join(p_TestData["originalXML"])
        expectedXML = os.path.join(p_Dir, p_TestData["resultXML"])
        resultXML = os.path.join(p_Dir + "_errors", p_TestData["resultXML"])

        if "testCSV" in p_TestData:
            with open(os.path.join(p_Dir, p_TestData["testCSV"]), "r") as _testCSV:
                lArrayValS = [aR for aR in csv.reader(_testCSV)]
        else:
            lArrayValS = None

        with open(originalXML, "r") as testFile:
            ps = ParamSection(inETree=etree.XML(testFile.read()))
            ps.createParamfromCSV(p_TestData["parName"], p_TestData["value"], lArrayValS)

            resultXMLasString = etree.tostring(ps.toEtree(), pretty_print=True, xml_declaration=True, encoding='UTF-8').decode("UTF-8")
            try:
                with open(expectedXML, "r") as _expectedXML:
                    parsedXML = _expectedXML.read()
                p_Obj.assertEqual(parsedXML, resultXMLasString)
            except AssertionError:
                with open(resultXML, "w") as outputXMLFile:
                    outputXMLFile.write(resultXMLasString)
                raise
    return func


class testSuite_CreateParamCommands(JSONTestSuite):
    testOnly    = os.environ['TEST_ONLY'] if "TEST_ONLY" in os.environ else ""            # Delimiter: ; without space, filenames without ext
    targetDir   = "samuTest_CreateParamCommands"
    isActive    = False

    def __init__(self):
        #FIXME import as variable

        super(testSuite_CreateParamCommands, self).__init__(
            folder=self.targetDir,
            case_only=self.testOnly,
            comparer=XMLComparer(testSuite_CreateParamCommands.targetDir) )




# if __name__ == '__main__':
#     unittest.main()
