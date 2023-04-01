import os
from lxml import etree
import json
import shutil


dir_baseName = 'test_getFromCSV'
sTargetDir = 'samuTest_CreateParamCommands_errors'
for fileName in os.listdir(dir_baseName  + "_items"):
    if os.path.splitext(fileName)[1] == '.xml':
        sFile = os.path.splitext(fileName)[0]
        parsedXML = etree.parse(os.path.join(dir_baseName  + "_items", fileName), etree.XMLParser(strip_cdata=False))
        value = parsedXML.find("./Value").text
        embeddedXML = etree.tostring(parsedXML.find("./ParamSection"), encoding="UTF-8", pretty_print=True, xml_declaration=True, )

        dData = {
                 "parName": parsedXML.getroot().attrib["Command"],
                 "originalXML": parsedXML.getroot().attrib["OriginalXML"],
                 "resultXML": fileName,
                 "value": parsedXML.find("./Value").text,
                 "result": 1.0,
                 # "description": parsedXML.find("./Note").text if parsedXML.find("./Note") else "",
                 }

        if 'TestCSV' in parsedXML.getroot().attrib:
            dData["testCSV"] = parsedXML.getroot().attrib["TestCSV"]
            shutil.copyfile(os.path.join(dir_baseName  + "_items", dData["testCSV"]), os.path.join(sTargetDir, dData["testCSV"]))

        if sNote := parsedXML.find("./Note"):
            dData["description"] = sNote.text

        sFile = os.path.join(sTargetDir, sFile)
        with open(sFile + ".json", "w") as fJSON:
            json.dump(dData, fJSON, indent=2)

        with open(sFile + ".xml", "w") as fXML:
            fXML.write(embeddedXML.decode("UTF-8"))


