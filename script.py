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


def define_id_type_snapPoint(object, style_info):
    object["id"] = str(uuid.uuid4())

    if re.search(r'shape=(.*?);', style_info):
        shape = re.search(r'shape=(.*?);', style_info).group(1)
        if shape in supported_shapes:
            object['type'] = supported_shapes[shape]
        else:
            object['type'] = 'Square'
    else:
        object['type'] = 'Square'

    object['snapPointIds'] = []

# with more time, this function would be more useful with another argument
# to indicate whether it is for Text or for a Label
# That implementation would allow for cleaner outputs and
# less messy if conditions.

def define_type_text(object, style_info, shapeInfo, primitiveInfo):
    if primitiveInfo.get('value') != '' and primitiveInfo.get('value') is not None:
        object = {"id": str(uuid.uuid4()), "type": "Text", "snapPointIDs": [], "abstractAttributes": {"isPortal": True}}
        text_value = primitiveInfo.get('value')

        # Simply check if the bold, itallic, and underline tags are present and correspondingly set True or False those attributes

        if '<b>' in text_value:
            object['abstractAttributes']['isBold'] = True
        else:
            object['abstractAttributes']['isBold'] = False
        if '<i>' in text_value:
            object['abstractAttributes']['isItalic'] = True
        else:
            object['abstractAttributes']['isItalic'] = False
        if '<u>' in text_value:
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
            object['primitiveAttributes']['color'] = font_color.lower()
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

def define_abstract_attributes(object, style_info):
    object["abstractAttributes"] = {"isPortal": True}
    if re.search(r'dashed=(.*?);', style_info):
        if re.search(r'dashed=(.*?);', style_info).group(1) == "0":
            object["abstractAttributes"]["dashGapSize"] = 0
        else:
            object["abstractAttributes"]["dashGapSize"] = 10
    else:
        object["abstractAttributes"]["dashGapSize"] = 0

    if object['type'] == "Square" and re.search(r'shape=(.*?);', style_info):
        if re.search(r'shape=(.*?);', style_info).group(1) == "cube":
            object['abstractAttributes']['3d'] = True

    if re.search(r'shadow=(.*?);', style_info):
        if re.search(r'shadow=(.*?);', style_info).group(1) == "1":
            object['abstractAttributes']['dropShadow'] = True


def define_primitive_attributes(object, style_info, shapeInfo):
    if re.search(r'rounded=(.*?);', style_info) and object['type'] == "Square":
        if re.search(r'rounded=(.*?);', style_info).group(1) != "0":
            object["primitiveAttributes"]["rx"] = 10
            object["primitiveAttributes"]["ry"] = 10

    if re.search(r'fillColor=(.*?);', style_info):
        fill_color = re.search(r'fillColor=(.*?);', style_info).group(1)
        if fill_color == 'none':
            object["primitiveAttributes"]["fill"] = "transparent"
        else:
            object["primitiveAttributes"]["fill"] =fill_color.lower()
    else:
        object["primitiveAttributes"]["fill"] = "#FFFFFF"

    object["primitiveAttributes"]["width"] = int(shapeInfo.get('width'))
    object["primitiveAttributes"]["height"] = int(shapeInfo.get('height'))

    if re.search(r'strokeColor=(.*?);', style_info):
        if re.search(r'strokeColor=(.*?);', style_info).group(1) == 'none':
            object["primitiveAttributes"]["stroke"] = "transparent"
        else:
            object["primitiveAttributes"]["stroke"] =re.search(r'strokeColor=(.*?);', style_info).group(1).lower()
    else:
        object["primitiveAttributes"]["stroke"] = "#000000"

    if re.search(r'strokeWidth=(.*?);', style_info):
        object["primitiveAttributes"]["stroke-width"] =int(re.search(r'strokeWidth=(.*?);', style_info).group(1))
    else:
        object["primitiveAttributes"]["stroke-width"] = 1

    if re.search(r'opacity=(.*?);', style_info) and 'labelAttributes' in object:
        object['labelAttributes']['primitiveAttributes']['opacity'] = int(int(re.search(r'opacity=(.*?);', style_info).group(1)) / 100)
        object['primitiveAttributes']['opacity'] = int(int(re.search(r'opacity=(.*?);', style_info).group(1)) / 100)
    elif re.search(r'opacity=(.*?);', style_info):
        object['primitiveAttributes']['opacity'] = int(int(re.search(r'opacity=(.*?);', style_info).group(1)) / 100)
    elif 'labelAttributes' in object:
        object['labelAttributes']['primitiveAttributes']['opacity'] = 1
    else:
        object['primitiveAttributes']['opacity'] = 1



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
                    object['primitiveAttributes']['width'] = object['primitiveAttributes']['width'] + 10
                    object['primitiveAttributes']['height'] = object['primitiveAttributes']['height'] + 10
                    if re.search(r'textOpacity=(.*?);', style_info):
                        object['primitiveAttributes']['opacity'] =int(int(re.search(r'textOpacity=(.*?);', style_info).group(1)))/100
                    else:
                        object['primitiveAttributes']['opacity'] = 1
                    json_data['boardObjects'].append(object)
                    break
                else:
                    if len(object) != 0:
                        object = {'labelAttributes': object}

                define_id_type_snapPoint(object, style_info)

                if object['type'] == "Cylinder" and 'labelAttributes' in object:
                    object['labelAttributes']["baseTransformations"]= {"x":5,"y":53}
                    object['labelAttributes']['primitiveAttributes']['width'] = object['labelAttributes']['primitiveAttributes']['width'] + 20
                    object['labelAttributes']['primitiveAttributes']['height'] = object['labelAttributes']['primitiveAttributes']['height'] + 20
                elif 'labelAttributes' in object:
                    object['labelAttributes']["baseTransformations"] = {"x":5,"y":5}

                define_abstract_attributes(object, style_info)

                object["baseTransformations"] = {}
                object["baseTransformations"]["x"] = int(shapeInfo.get('x'))
                object["baseTransformations"]["y"] = int(shapeInfo.get('y'))

                object["primitiveAttributes"] = {}
                define_primitive_attributes(object, style_info, shapeInfo)

                json_data['boardObjects'].append(object)

    return json.dumps(json_data, indent=4)


mxGraphParent = (inflate("testFiles/diagram1arrow.xml"))
print(make_json(mxGraphParent))

# for value in make_json(mxGraphParent)['boardObjects']:
#     print(value)
#     print()Z