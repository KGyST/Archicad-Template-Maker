from unitTest.test_runner import JSONTestSuite, JSONTestCase
import os
from TemplateMaker import Param
from lxml import etree
import shutil
import csv

def XMLComparer(p_Dir):      #p_working_directory
    def func(p_Obj, p_function, p_TestData, *args, **kwargs):
        sFile = kwargs["file_name"][:-5]
        originalXML = os.path.join(p_Dir, sFile + ".xml")
        expectedXML = os.path.join(p_Dir, sFile + ".xml")
        resultXML = os.path.join(p_Dir + "_errors", sFile + ".xml")

        # if "aVals" in p_TestData:
        #     with open(os.path.join(p_Dir, p_TestData["aVals"]), "r") as _testCSV:
        #         lArrayValS = [aR for aR in csv.reader(_testCSV)]
        # else:
        #     lArrayValS = None

        with open(originalXML, "r") as testFile:
            param = Param(inETree=etree.XML(testFile.read()))

            resultXMLasString = etree.tostring(param.eTree, pretty_print=True, ).decode("UTF-8")
            try:
                with open(expectedXML, "r") as _expectedXML:
                    parsedXML = _expectedXML.read()
                p_Obj.assertEqual(parsedXML, resultXMLasString)
            except AssertionError:
                with open(resultXML, "w") as outputXMLFile:
                    outputXMLFile.write(resultXMLasString)
                raise
    return func


class testSuite_param(JSONTestSuite):
    testOnly    = os.environ['TEST_ONLY'] if "TEST_ONLY" in os.environ else ""            # Delimiter: ; without space, filenames without ext
    targetDir   = "samuTest_param"
    isActive    = False

    def __init__(self):
        #FIXME import as variable

        super(testSuite_param, self).__init__(
            folder=self.targetDir,
            case_only=self.testOnly,
            comparer=XMLComparer(testSuite_param.targetDir))





# if __name__ == '__main__':
#     unittest.main()
