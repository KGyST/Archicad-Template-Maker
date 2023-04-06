from unitTest.test_runner import JSONTestSuite, JSONTestCase
import os
from TemplateMaker import Param
from lxml import etree
import shutil
import csv

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

def XMLComparer(p_Dir):      #p_working_directory
    def func(p_Obj, p_function, p_TestData, *args, **kwargs):
        sFile = kwargs["file_name"][:-5]
        originalXML = os.path.join(p_Dir, sFile + ".xml")
        expectedXML = os.path.join(p_Dir, sFile + ".xml")
        resultXML = os.path.join(p_Dir + "_errors", sFile + ".xml")

        with open(originalXML, "r") as testFile:
            par = Param(inETree=etree.XML(testFile.read()))

            resultXMLasString = etree.tostring(par.eTree, pretty_print=True, ).decode("UTF-8")
            try:
                with open(expectedXML, "r") as _expectedXML:
                    parsedXML = _expectedXML.read()
                p_Obj.assertEqual(parsedXML, resultXMLasString)

                fChild = False
                fUnique = False
                fHidden = False
                fBold = False

                if par.iType not in (PAR_COMMENT,):
                    if PARFLG_CHILD     in par.flags: fChild  = True
                    if PARFLG_UNIQUE    in par.flags: fUnique = True
                    if PARFLG_HIDDEN    in par.flags: fHidden = True
                    if PARFLG_BOLDNAME  in par.flags: fBold   = True

                par2 = Param(
                    inType = par.iType,
                    inName = par.name,
                    inDesc = par.desc,
                    inValue = par.value,
                    inAVals = par.aVals,
                    inChild=fChild,
                    inUnique=fUnique,
                    inHidden=fHidden,
                    inBold=fBold)

                p_Obj.assertEqual(parsedXML, etree.tostring(par2.eTree, pretty_print=True, ).decode("UTF-8"))

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
