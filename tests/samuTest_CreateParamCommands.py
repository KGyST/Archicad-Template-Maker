from unitTest.test_runner import JSONTestSuite, JSONTestCase
import os
from TemplateMaker import ParamSection
from lxml import etree
import shutil

def XMLComparer(p_Dir):      #p_working_directory
    def func(p_Obj, p_function, p_TestData) :
        originalXML = os.path.join(p_TestData["args"][1])
        expectedXML = os.path.join(p_Dir, p_TestData["args"][2])
        resultXML = os.path.join(p_Dir + "_errors", p_TestData["args"][2])

        try:
            shutil.rmtree(p_Dir + "_errors")
        except OSError:
            pass

        try:
            os.mkdir(p_Dir + "_errors")
        except PermissionError:
            #FIXME handling
            pass

        with open(originalXML, "r") as testFile:
            ps = ParamSection(inETree=etree.XML(testFile.read()))
            ps.createParamfromCSV(p_TestData["args"][0], p_TestData["args"][3], None)

            resultXMLasString = etree.tostring(ps.toEtree(), pretty_print=True, xml_declaration=True, encoding='UTF-8').decode("UTF-8")
            try:
                parsedXML = open(expectedXML, "r").read()
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

        super(testSuite_CreateParamCommands, self).__init__(folder=self.targetDir, case_only=self.testOnly, comparer=XMLComparer(testSuite_CreateParamCommands.targetDir) )



# if __name__ == '__main__':
#     unittest.main()
