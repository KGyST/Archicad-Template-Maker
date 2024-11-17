import csv
import os
from lxml import etree
from TemplateMaker import Param
import json

PARFLG_CHILD    = 1
PARFLG_BOLDNAME = 2
PARFLG_UNIQUE   = 3
PARFLG_HIDDEN   = 4

dir_baseName = 'test_param'
sTargetDir = 'samuTest_param_errors'
sTargetDir = 'samuTest_param2_errors'
for fileName in os.listdir(dir_baseName  + "_items"):
    if os.path.splitext(fileName)[1] == '.txt' and fileName[0] != '_':
        sFile = os.path.splitext(fileName)[0]
        parsedXML = etree.parse(os.path.join(dir_baseName  + "_items", fileName), etree.XMLParser(strip_cdata=False))
        embeddedXML = etree.tostring(parsedXML.getroot(), encoding="UTF-8", pretty_print=True, xml_declaration=True, )

        sFile = os.path.join(sTargetDir, sFile)

        with open(sFile + ".xml", "w") as fXML:
            fXML.write(embeddedXML.decode("UTF-8"))

            par = Param(inETree=etree.XML(embeddedXML))



            dData = {
                "type": par.iType,
                "name": par.name,
                "desc": par.value,
                # "value": parsedXML.find("./Value").text,
                # "aVals": par.aVals,
                "child": PARFLG_CHILD in par.flags,
                "unique": PARFLG_UNIQUE in par.flags,
                "hidden": PARFLG_HIDDEN in par.flags,
                "bold": PARFLG_BOLDNAME in par.flags,
            }

            if par.aVals:
                dData["aVals"] = sFile + ".csv"
                _iFirstD= int(par.aVals.attrib["FirstDimension"])
                _iSecondD= int(par.aVals.attrib["SecondDimension"])

                with open(sFile + ".csv", "w", newline='') as fCSV:
                    csvWriter = csv.writer(fCSV)
                    if not _iSecondD:
                        _d = {}
                        _iMax = 0
                        for cell in par.aVals:
                            _idx = int(cell.attrib["Row"])
                            _d[_idx] = cell.text
                            _iMax = max([_iMax, _idx])
                        _row = [_d[i] for i in range (1, _iMax + 1)]
                        csvWriter.writerow(_row)
                    else:
                        _d = {}
                        _iMaxC = 0
                        _iMaxR = 0
                        for cell in par.aVals:
                            _idxC = int(cell.attrib["Column"])
                            _idxR = int(cell.attrib["Row"])
                            if _idxC not in _d:
                                _d[_idxC] = {"_idxR":0}
                            _d[_idxC][_idxR] = cell.text

                            _iMaxC = max([_iMaxC, _idxC])
                            _d[_idxC]["_idxR"] = max([_d[_idxC]["_idxR"], _idxR])
                        for iRow in sorted(_d.keys()):
                            _row = [_d[iRow][i] for i in range (1, _d[iRow]["_idxR"] + 1)]
                            csvWriter.writerow(_row)

        with open(sFile + ".json", "w") as fJSON:
            json.dump(dData, fJSON, indent=2)




