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

""" In 2016 draw.io started compressing 'using standard deflate'
        https://about.draw.io/extracting-the-xml-from-mxfiles/
        Testing has shown this is deflate WITH NO HEADER
        https://docs.python.org/3/library/zlib.html shows
        how what value (-15) works for such a case
    """

def inflate(mxfileName: str):
    file = open(mxfileName, "r")
    # find the diagram tag and only decode that
    mxfile = re.search("<diagram.*>([^<]+)</diagram>",file.read()).group(1)
    mxfile = base64.b64decode(mxfile)
    # make it into proper xml so it can be used (it is made into an xml tree so I can use it like a dictionary)
    return ET.fromstring(unquote(zlib.decompress(mxfile,-15).decode('utf8')))


def define_id_type_snapPoint(object, style_info):
    # make the id using UUID
    object["id"] = str(uuid.uuid4())
    # check the text between 'shape=' and ';' and compare it with the supported shapes dictionary
    # if it is supported then use it, else, default it to a square
    if re.search(r'shape=(.*?);', style_info):
        shape = re.search(r'shape=(.*?);', style_info).group(1)
        if shape in supported_shapes:
            object['type'] = supported_shapes[shape]
        else:
            object['type'] = 'Square'
    else:
        object['type'] = 'Square'
    # empty snapPointIDs list
    object['snapPointIds'] = []

# with more time, this function would be more useful with another argument
# to indicate whether it is for Text or for a Label
# That implementation would allow for cleaner outputs and
# less messy if conditions.

def define_type_text(object, style_info, shapeInfo, primitiveInfo):
    # if the xml content has defined a value for text which is not empty or none, then make a text object
    # take in our current [empty] object (represents an object in a diagram) and make Ids, define type, and make abstractAttributes
    if primitiveInfo.get('value') != '' and primitiveInfo.get('value') is not None:
        object = {"id": str(uuid.uuid4()), "type": "Text", "snapPointIDs": [], "abstractAttributes": {"isPortal": True}}
        text_value = primitiveInfo.get('value')

        # Simply check if the bold, itallic, and underline tags are present and correspondingly set True or False those attributes
        # in the abstractAttributes dictionary within object

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

        # Because the xml content creates a pattern of where the tags for text styling are located,
        # such as <b><i><u> text </u></i></b>, check the tags from inside to outside to make sure
        # we only get the text
        if re.search(r'<u>', text_value):
            object['abstractAttributes']['text'] = re.search(r'<u>(.*?)</u>', text_value).group(1)
        elif re.search(r'<i>', text_value):
            object['abstractAttributes']['text'] = re.search(r'<i>(.*?)</i>', text_value).group(1)
        elif re.search(r'<b>', text_value):
            object['abstractAttributes']['text'] = re.search(r'<b>(.*?)</b>', text_value).group(1)
        else:
            object['abstractAttributes']['text'] = text_value

        # if the object type is text (from xml) then make the base transformation the x and y location
        # else keep 'baseTransformations' empty to be used later
        object["baseTransformations"] = {}
        if "text" in style_info:
            object["baseTransformations"]["x"] = int(shapeInfo.get('x'))
            object["baseTransformations"]["y"] = int(shapeInfo.get('y'))

        # define primitiveAttributes such as font color, font size, width, and height using the same technique
        # of checking the text in between text I know exists.
        object['primitiveAttributes'] = {}
        # make sure something is inside 'fontColor= ;' (from the xml style info string) and then grab that value
        # else, default to black
        if re.search(r'fontColor=(.*?);', style_info):
            font_color = re.search(r'fontColor=(.*?);', style_info).group(1)
            object['primitiveAttributes']['color'] = font_color.lower()
        else:
            object['primitiveAttributes']['color'] = "#000000"
        # make sure something is inside 'fontSize= ;' (from the xml style info string) and then grab that value
        # else, default to 14 (just looked the best)
        if re.search(r'fontSize=(.*?);', style_info):
            font_size =int(re.search(r'fontSize=(.*?);', style_info).group(1))
            object['primitiveAttributes']['font-size'] = font_size
        else:
            object['primitiveAttributes']['font-size'] = 14

        # use the dictionary function to get the height and width and subtract by 10 according to Terrastruct's pattern
        object['primitiveAttributes']['width'] = int(shapeInfo.get('width')) - 10
        object['primitiveAttributes']['height'] = int(shapeInfo.get('height')) - 10
    return object

def define_abstract_attributes(object, style_info):
    # make abstractAttributes dicitonary as an attribute of the object
    object["abstractAttributes"] = {"isPortal": True}
    # make sure something is inside 'dashed= ;' (from the xml style info string) and then grab that value
    # If the value is 0, make dashGapSize 0, else default to 10
    # if dashed doesn't exist, define no dash gap size
    if re.search(r'dashed=(.*?);', style_info):
        if re.search(r'dashed=(.*?);', style_info).group(1) == "0":
            object["abstractAttributes"]["dashGapSize"] = 0
        else:
            object["abstractAttributes"]["dashGapSize"] = 10
    else:
        object["abstractAttributes"]["dashGapSize"] = 0
    # if the object type is square and shape exists in the xml style info string, check if shape is defined as cube in xml
    # if it is, then 3d is true, else do nothing
    if object['type'] == "Square" and re.search(r'shape=(.*?);', style_info):
        if re.search(r'shape=(.*?);', style_info).group(1) == "cube":
            object['abstractAttributes']['3d'] = True
    # check if 'shadow=;' exists and if the value inside is 1, dropShadow is true
    if re.search(r'shadow=(.*?);', style_info):
        if re.search(r'shadow=(.*?);', style_info).group(1) == "1":
            object['abstractAttributes']['dropShadow'] = True


def define_primitive_attributes(object, style_info, shapeInfo):
    # check if 'rounded= ;' exists and if the shape is Square
    # if both are true and the rounded value is not 0, default radius of object to 10
    if re.search(r'rounded=(.*?);', style_info) and object['type'] == "Square":
        if re.search(r'rounded=(.*?);', style_info).group(1) != "0":
            object["primitiveAttributes"]["rx"] = 10
            object["primitiveAttributes"]["ry"] = 10
    # check if 'fillColor= ;' exists in the xml style info string and if it does, get the value
    # check if the value is 'none', and if it is, fillColor will be transparent
    # else set the fill color to the recieved value and make all characters lowercase
    # if fill color doesn't exist, then default to fill color of white
    if re.search(r'fillColor=(.*?);', style_info):
        fill_color = re.search(r'fillColor=(.*?);', style_info).group(1)
        if fill_color == 'none':
            object["primitiveAttributes"]["fill"] = "transparent"
        else:
            object["primitiveAttributes"]["fill"] =fill_color.lower()
    else:
        object["primitiveAttributes"]["fill"] = "#FFFFFF"

    # get the width and height from xml dictionary and turn it into int from a string
    object["primitiveAttributes"]["width"] = int(shapeInfo.get('width'))
    object["primitiveAttributes"]["height"] = int(shapeInfo.get('height'))
    # check if strokeColor= ; exists in the xml style info string and if it does, get the value
    # if the value is 'none' set strokeColor to transparent
    # else, set the strokeColor to the value from xml string and lower case it
    # if strokeColor=; does not exist default to black stroke color
    if re.search(r'strokeColor=(.*?);', style_info):
        if re.search(r'strokeColor=(.*?);', style_info).group(1) == 'none':
            object["primitiveAttributes"]["stroke"] = "transparent"
        else:
            object["primitiveAttributes"]["stroke"] =re.search(r'strokeColor=(.*?);', style_info).group(1).lower()
    else:
        object["primitiveAttributes"]["stroke"] = "#000000"
    # check if stroke width exists in the xml style info string and if it does get that value and turn it into an int
    # set stroke-width equal to that valuee
    # if it doesn't exist default to stroke-width of 1
    if re.search(r'strokeWidth=(.*?);', style_info):
        object["primitiveAttributes"]["stroke-width"] =int(re.search(r'strokeWidth=(.*?);', style_info).group(1))
    else:
        object["primitiveAttributes"]["stroke-width"] = 1
    # opacity is a tricky one because draw.io allows setting different opacity for text and shape, even if the shape has a label
    # Terrastruct lets us adjust opacity of both the text and shape (when it is as a label) as one value, but if the object
    # is just a text box, opacity affects the text only
    # thus, if the opacity value exists and labelAttributes is in object (if the text is a label) set both opacities
    # to the same value
    # if that fails, check if opacity exists and if it does (that means that 'labelAttributes' does not) set shape opacity to
    # the value given.
    # if that fails, check if label attributes are in the object which means that the opacity value is not in xml string
    # set both label attributes and primitive attributes opacity to 1
    # if everything fails, that means that it is a text object so set primitive opacity to 1
    if re.search(r'opacity=(.*?);', style_info) and 'labelAttributes' in object:
        object['labelAttributes']['primitiveAttributes']['opacity'] = int(int(re.search(r'opacity=(.*?);', style_info).group(1)) / 100)
        object['primitiveAttributes']['opacity'] = int(int(re.search(r'opacity=(.*?);', style_info).group(1)) / 100)
    elif re.search(r'opacity=(.*?);', style_info):
        object['primitiveAttributes']['opacity'] = int(int(re.search(r'opacity=(.*?);', style_info).group(1)) / 100)
    elif 'labelAttributes' in object:
        object['labelAttributes']['primitiveAttributes']['opacity'] = 1
        object['primitiveAttributes']['opacity'] = 1
    else:
        object['primitiveAttributes']['opacity'] = 1



def make_json(mxGraphParent):
    # this gets all the xml cells labeled <mxCell> and puts it in a list.
    # Do this because primitive shape info is in this and
    # another tag, <mxGeometry> has more shape info
    # In order to get <mxGeometry> and primitive Shape info, we need mxCells
    mxCells = mxGraphParent.iter("mxCell")
    # Initiate the boardObjects dictionary to turn into json
    json_data = {'boardObjects': []}
    # mxCells is a list, so we operate on each cell in this loop
    for mxCell in mxCells:
        # mxCells have mxGeometry cells in them which contain extra shape info
        # this gets the mxGeometry cells in each mxCell and puts them in a list
        mxGeometryCells = mxCell.iter("mxGeometry")
        # for each mxGeometry cell do this:
        for mxGeometryCell in mxGeometryCells:
            # the '.attrib' attribute gives me the data as a dictionary within the cell
            # things like 'value', 'strokeColor', and 'shape' can be found using .attrib
            primitiveInfo = mxCell.attrib
            shapeInfo = mxGeometryCell.attrib
            # an initial filter to remove excess mxCells that are not useful for this project (empty mxCells or arrows)
            if primitiveInfo.get('value') is not None:
                # initialize the object dictionary which represents the object of a diagram
                object = {}
                # this has style info for text, shape color, opacity, and width/height
                style_info = primitiveInfo.get('style')
                # we define each object as only text initially to prevent having to compute labels later on
                # this will take in our empty object and either return an object with text information
                # or an empty object
                object = define_type_text(object, style_info, shapeInfo, primitiveInfo)
                # if the xml data says that the type is 'text' then do some extra computation that can't be done
                # without making sure it is text (things like primitive height and weight vary for shape labels and only texts)
                # also define opacity here if it is only text
                # if it is not a text box, then put the current data in a labelAttributes key, just like a shape label
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
                # only runs code from here on out if the type is not a text box
                # this gets the true type of the object and defines the id and snapPointIDs
                define_id_type_snapPoint(object, style_info)
                # label attribute base transformations and height and width vary based on the shape we are dealing with,
                # if it is a cylinder, initialize base transormations of x and y to 5 and 53,
                # and add 20 to height and width based on a pattern observed with terrastruct
                # else, x and y are 5
                if object['type'] == "Cylinder" and 'labelAttributes' in object:
                    object['labelAttributes']["baseTransformations"]= {"x":5,"y":53}
                    object['labelAttributes']['primitiveAttributes']['width'] = object['labelAttributes']['primitiveAttributes']['width'] + 20
                    object['labelAttributes']['primitiveAttributes']['height'] = object['labelAttributes']['primitiveAttributes']['height'] + 20
                elif 'labelAttributes' in object:
                    object['labelAttributes']["baseTransformations"] = {"x":5,"y":5}
                # calls define_abstract_attributes to input abstract attributes
                define_abstract_attributes(object, style_info)
                # didn't require its own function, just getting x and y from a dictionary and turning them into int
                object["baseTransformations"] = {}
                object["baseTransformations"]["x"] = int(shapeInfo.get('x'))
                object["baseTransformations"]["y"] = int(shapeInfo.get('y'))
                # defining primitive attributes
                object["primitiveAttributes"] = {}
                define_primitive_attributes(object, style_info, shapeInfo)
                # append this object to json_data[boardObjects], which is a list to store all objects
                # its position inside the if statement prevents lines from being appended
                # putting it outside and adding line support would work - also keeping it outside would work for current use
                json_data['boardObjects'].append(object)
    # make the dictionary json_data a json object
    return json.dumps(json_data, indent=4)

# inflate function takes in your file path/name
mxGraphParent = (inflate("testFiles/textonly.xml"))
print(make_json(mxGraphParent))

