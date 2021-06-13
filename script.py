from urllib.parse import unquote
import zlib
import base64
import re
import json
import xml.etree.ElementTree as ET
import uuid
import json

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
    return ET.fromstring(unquote(zlib.decompress(mxfile,-15).decode('utf8')))


def define_type_snapPoint(object, style_info):
    if re.search(r'shape=(.*?);', style_info):
        shape = re.search(r'shape=(.*?);', style_info).group(1)
        if shape in supported_shapes:
            object['type'] = supported_shapes[shape]
        else:
            object['type'] = 'Square'
    else:
        object['type'] = 'Square'

    object['snapPointIds'] = []

# have another argument for whether to put it into a label attribute *if 'text' in style_info: say that attribute is true, then return the correct baseTransformations
def define_type_text(object, style_info, shapeInfo, primitiveInfo):
    if primitiveInfo.get('value') != '':
        object = {"id": str(uuid.uuid4()), "type": "Text", "snapPointIDs": [], "abstractAttributes": {"isPortal": True}}
        text_value = primitiveInfo.get('value')

        # Simply check if the bold, itallic, and underline tags are present and correspondingly set True or False those attributes

        if re.search(r'<b>', text_value):
            object['abstractAttributes']['isBold'] = True
        else:
            object['abstractAttributes']['isBold'] = False
        if re.search(r'<i>', text_value):
            object['abstractAttributes']['isItalic'] = True
        else:
            object['abstractAttributes']['isItalic'] = False
        if re.search(r'<u>', text_value):
            object['abstractAttributes']['isUnderline'] = True
        else:
            object['abstractAttributes']['isUnderline'] = False

        # Default each position of text to Middle Center
        object['abstractAttributes']['labelPosition'] = "INSIDE_MIDDLE_CENTER"

        # When getting the text
        if re.search(r'<u>', text_value):
            object['abstractAttributes']['text'] = re.search(r'<u>(.*?)</u>', text_value).group(1)
        elif re.search(r'<i>', text_value):
            object['abstractAttributes']['text'] = re.search(r'<i>(.*?)</i>', text_value).group(1)
        elif re.search(r'<b>', text_value):
            object['abstractAttributes']['text'] = re.search(r'<b>(.*?)</b>', text_value).group(1)
        else:
            object['abstractAttributes']['text'] = text_value

        object["baseTransformations"] = {}
        if "text" in style_info:
            object["baseTransformations"]["x"] = int(shapeInfo.get('x'))
            object["baseTransformations"]["y"] = int(shapeInfo.get('y'))

        object['primitiveAttributes'] = {}

        if re.search(r'fontColor=(.*?);', style_info):
            font_color = re.search(r'fontColor=(.*?);', style_info).group(1)
            object['primitiveAttributes']['color'] = font_color
        else:
            object['primitiveAttributes']['color'] = "#000000"

        if re.search(r'fontSize=(.*?);', style_info):
            font_size =int(re.search(r'fontSize=(.*?);', style_info).group(1))
            object['primitiveAttributes']['font-size'] = font_size
        else:
            object['primitiveAttributes']['font-size'] = 14


        object['primitiveAttributes']['width'] = int(shapeInfo.get('width')) - 10
        object['primitiveAttributes']['height'] = int(shapeInfo.get('height')) - 10
    return object



def make_json(mxGraphParent):

    mxCells = mxGraphParent.iter("mxCell")

    json_data = {'boardObjects': []}

    for mxCell in mxCells:

        mxGeometryCells = mxCell.iter("mxGeometry")

        for mxGeometryCell in mxGeometryCells:

            primitiveInfo = mxCell.attrib
            shapeInfo = mxGeometryCell.attrib

            # print(primitiveInfo)
            # print()
            # print(shapeInfo)

            if primitiveInfo.get('value') is not None:

                object = {}

                style_info = primitiveInfo.get('style')

                object = define_type_text(object, style_info, shapeInfo, primitiveInfo)

                if "text" in style_info:
                    if re.search(r'textOpacity=(.*?);', style_info):
                        object['primitiveAttributes']['opacity'] =int(int(re.search(r'textOpacity=(.*?);', style_info).group(1)))/100
                        json_data['boardObjects'].append(object)
                        break
                    else:
                        object['primitiveAttributes']['opacity'] = 1
                        json_data['boardObjects'].append(object)
                        break
                else:
                    object = {'labelAttributes': object}

                object["id"] = str(uuid.uuid4())
                define_type_snapPoint(object, style_info)

                if object['type'] == "Cylinder":
                    object['labelAttributes']['baseTransformations']= {"x": 5, "y": 53}
                else:
                    object['labelAttributes']['baseTransformations']= {"x": 5, "y":5}

                object["abstractAttributes"] = {"isPortal": True}
                if re.search(r'dashed=(.*?);', style_info):
                    if re.search(r'dashed=(.*?);', style_info).group(1) == "0":
                        object["abstractAttributes"]["dashGapSize"] = 0
                    else:
                        object["abstractAttributes"]["dashGapSize"] = 5
                else:
                    object["abstractAttributes"]["dashGapSize"] = 0

                if object['type'] == "Square":
                    if re.search(r'shape=(.*?);', style_info):
                        if re.search(r'shape=(.*?);', style_info).group(1) == "cube":
                            object['abstractAttributes']['3d'] = True
                        else:
                            object['abstractAttributes']['3d'] = False
                    else:
                        object['abstractAttributes']['3d'] = False

                object["baseTransformations"] = {}
                object["baseTransformations"]["x"] = int(shapeInfo.get('x'))
                object["baseTransformations"]["y"] = int(shapeInfo.get('y'))

                object["primitiveAttributes"] = {}
                if re.search(r'rounded=(.*?);', style_info):
                    if re.search(r'rounded=(.*?);', style_info).group(1) != "0":
                        object["primitiveAttributes"]["rx"] = 10
                        object["primitiveAttributes"]["ry"] = 10
                    else:
                        object["primitiveAttributes"]["rx"] = 0
                        object["primitiveAttributes"]["ry"] = 0

                if re.search(r'fillColor=(.*?);', style_info):
                    fill_color = re.search(r'fillColor=(.*?);', style_info).group(1)
                    if fill_color == 'none':
                        object["primitiveAttributes"]["fill"] = "#FFFFFF"
                    else:
                        object["primitiveAttributes"]["fill"] =re.search(r'fillColor=(.*?);', style_info).group(1)
                else:
                    object["primitiveAttributes"]["fill"] = "#FFFFFF"

                object["primitiveAttributes"]["width"] = int(shapeInfo.get('width'))
                object["primitiveAttributes"]["height"] = int(shapeInfo.get('height'))

                if re.search(r'strokeColor=(.*?);', style_info):
                    if re.search(r'strokeColor=(.*?);', style_info).group(1) == 'none':
                        object["primitiveAttributes"]["stroke"] = "#000000"
                    else:
                        object["primitiveAttributes"]["stroke"] =re.search(r'strokeColor=(.*?);', style_info).group(1)
                else:
                    object["primitiveAttributes"]["stroke"] = "#000000"

                if re.search(r'strokeWidth=(.*?);', style_info):
                    object["primitiveAttributes"]["stroke-width"] =int(re.search(r'strokeWidth=(.*?);', style_info).group(1))
                else:
                    object["primitiveAttributes"]["stroke-width"] = 1

                    #label attributes were here

                if re.search(r'opacity=(.*?);', style_info):
                    object['labelAttributes']['primitiveAttributes']['opacity'] = 1
                    object['primitiveAttributes']['opacity'] = int(re.search(r'opacity=(.*?);', style_info).group(1)) / 100

                if re.search(r'shadow=(.*?);', style_info):
                    if re.search(r'shadow=(.*?);', style_info).group(1) == "1":
                        object['abstractAttributes']['dropShadow'] = True

            json_data['boardObjects'].append(object)

    return json.dumps(json_data, indent=4)


mxGraphParent = (inflate("testFiles/diagram1.xml"))
print(make_json(mxGraphParent))

# for value in make_json(mxGraphParent)['boardObjects']:
#     print(value)
#     print()