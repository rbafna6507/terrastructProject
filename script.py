from urllib.parse import unquote
import zlib
import base64
import re
import json
import xml.etree.ElementTree as ET
import uuid

supported_shapes = {
    "callout" : "Callout",
    "parallelogram" : "Parallelogram",
    "cylinder3" : "Cylinder",
    "cloud" : "Cloud",
    "document" : "Document"}

# Draw.io uses standard deflate compression

""" In 2016 draw.io started compressing 'using standard deflate'
        https://about.draw.io/extracting-the-xml-from-mxfiles/
        Testing has shown this is deflate WITH NO HEADER
        https://docs.python.org/3/library/zlib.html shows
        how what value (-15) works for such a case
    """

def inflate(mxfileName: str):
    file = open(mxfileName, "r")
    mxfile = re.search("<diagram.*>([^<]+)</diagram>",file.read()).group(1)
    mxfile = base64.b64decode(mxfile)
    return unquote(zlib.decompress(mxfile,-15).decode('utf8'))

mxGraphParent = (inflate("actualnew5.xml"))
mxGraphParent = ET.fromstring(mxGraphParent)

def make_json(mxGraphParent):

    mxCells = mxGraphParent.iter("mxCell")

    json_data = {'boardObjects': []}

    for mxCell in mxCells:

        mxGeometryCells = mxCell.iter("mxGeometry")
        primitiveInfo = mxCell.attrib

        if primitiveInfo.get('value') is not None:

            object = {}
            object["id"] = str(uuid.uuid4())

            style_info = primitiveInfo.get('style')

            if re.search(r'shape=(.*?);', style_info):
                shape = re.search(r'shape=(.*?);', style_info).group(1)
                if shape in supported_shapes:
                    object['type'] = supported_shapes[shape]
                else:
                    object['type'] = 'Square'
            else:
                object['type'] = 'Square'

            object['snapPointIds'] = []

            print(primitiveInfo)

            if primitiveInfo.get('value') != '':
                object['labelAttributes'] = {"id": str(uuid.uuid4()), "type": "Text", "snapPointIDs": [], "abstractAttributes": {"isPortal": True}}
                text_value = primitiveInfo.get('value')

                if re.search(r'<b>', text_value):
                    object['labelAttributes']['abstractAttributes']['isBold'] = True
                else:
                    object['labelAttributes']['abstractAttributes']['isBold'] = False
                if re.search(r'<i>', text_value):
                    object['labelAttributes']['abstractAttributes']['isItalic'] = True
                else:
                    object['labelAttributes']['abstractAttributes']['isItalic'] = False
                if re.search(r'<u>', text_value):
                    object['labelAttributes']['abstractAttributes']['isUnderline'] = True
                else:
                    object['labelAttributes']['abstractAttributes']['isUnderline'] = False

                object['labelAttributes']['abstractAttributes']['labelPosition'] = "INSIDE_MIDDLE_CENTER"

                if re.search(r'<u>', text_value):
                    object['labelAttributes']['abstractAttributes']['text'] = re.search(r'<u>(.*?)</u>', text_value).group(1)
                elif re.search(r'<i>', text_value):
                    object['labelAttributes']['abstractAttributes']['text'] = re.search(r'<i>(.*?)</i>', text_value).group(1)
                elif re.search(r'<b>', text_value):
                    object['labelAttributes']['abstractAttributes']['text'] = re.search(r'<b>(.*?)</b>', text_value).group(1)

                if object['type'] == "Cylinder":
                    object['labelAttributes']['baseTransformation'] = {"x": 5, "y":53}
                else:
                    object['labelAttributes']['baseTransformation'] = {"x": 5, "y":5}

                object['labelAttributes']['primitiveAttributes'] = {}

                if re.search(r'fontColor=(.*?);', style_info):
                    font_color = re.search(r'shape=(.*?);', style_info).group(1)
                    object['labelAttributes']['primitiveAttributes']['color'] = font_color
                else:
                    object['labelAttributes']['primitiveAttributes']['color'] = "#000000"

                if re.search(r'fontSize=(.*?);', style_info):
                    font_size =re.search(r'fontSize=(.*?);', style_info).group(1)
                    object['labelAttributes']['primitiveAttributes']['font-size'] = font_size
                else:
                    object['labelAttributes']['primitiveAttributes']['font-size'] = "14"
            json_data['boardObjects'].append(object)

            for mxGeometryCell in mxGeometryCells:
                print(mxGeometryCell.attrib)
    #return json_data
make_json(mxGraphParent)

