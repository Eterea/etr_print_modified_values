# python
#
# etr_print_modified_values - v.1.0
# To automatically add a child Comment with non default values in Adobe Substance 3D Designer
#
# Created by Cristobal Vila - etereaestudios.com - November 2022
# Special thanks to Luca Giarrizo, 'est', Nicolas Wirrmann, Divyansh from the Substance Discord
#
# For more info about how to install and curiosities about development:
# https://etereaestudios.com/2022/11/13/print-modified-values-plugin-for-designer/


# Import the required classes, tools and other sd stuff.
import os
import sd
import re
import weakref

from functools import partial
from collections import OrderedDict

from sd.tools import io
from sd.tools import graphlayout
from sd.api import sdmodule
from sd.api import sdproperty
from sd.api import sdtypeenum


from sd.ui.graphgrid import *
from sd.api.sbs.sdsbscompgraph import *
from sd.api.sdgraphobjectpin import *
from sd.api.sdgraphobjectframe import *
from sd.api.sdgraphobjectcomment import *
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdvalueserializer import SDValueSerializer
from sd.api.sdapplication import SDApplicationPath

from PySide2 import QtCore, QtGui, QtWidgets, QtSvg


DEFAULT_ICON_SIZE = 24

# Literally copied from factory plugin 'node_align_tools'
def loadSvgIcon(iconName, size):
    currentDir = os.path.dirname(__file__)
    iconFile = os.path.abspath(os.path.join(currentDir, iconName + '.svg'))

    svgRenderer = QtSvg.QSvgRenderer(iconFile)
    if svgRenderer.isValid():
        pixmap = QtGui.QPixmap(QtCore.QSize(size, size))

        if not pixmap.isNull():
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            svgRenderer.render(painter)
            painter.end()

        return QtGui.QIcon(pixmap)

    return None

# Adapted from factory plugin 'node_align_tools'
class PrintModValuesToolBar(QtWidgets.QToolBar):
    __toolbarList = {}

    def __init__(self, graphViewID, uiMgr):
        super(PrintModValuesToolBar, self).__init__(parent=uiMgr.getMainWindow())

        self.setObjectName("etereaestudios.com.print_modvalues_toolbar")

        self.__graphViewID = graphViewID
        self.__uiMgr = uiMgr

        act = self.addAction(loadSvgIcon("print_modified_values_a", DEFAULT_ICON_SIZE), "PMVa")
        act.setShortcut(QtGui.QKeySequence('Q'))
        act.setToolTip(self.tr("Print Modified Values"))
        act.triggered.connect(self.__onPrintModValues)

        self.__toolbarList[graphViewID] = weakref.ref(self)
        self.destroyed.connect(partial(PrintModValuesToolBar.__onToolbarDeleted, graphViewID=graphViewID))

    def tooltip(self):
        return self.tr("Print Modified Values")

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    #
    #
    #
    # ------------ START MAIN FUNCTION ------------------------------------------------------------------------------
    #
    #
    #

    def __onPrintModValues(self):

        # ////////////////////////////////////////////////////////////////////////////////////////////////////////////
        #
        # ----------- DEFINE SOME VARIABLES, DICTIONARIES AND LISTS -------------------------------------------------
        # 

        roundN = 2 # Overall round value for floats. Change this to 3 or 4 for extra accuracy

        # Define Ordered Dictionaries for MODIFIED & REFERENCE nodes and also for DIFFERENCES
        modifNode_dict = OrderedDict()
        referNode_dict = OrderedDict()
        different_dict = OrderedDict()


        # Create a list of each property category enumeration item
        categories = [
            SDPropertyCategory.Annotation,
            SDPropertyCategory.Input
        ]


        # ////////////////////////////////////////////////////////////////////////////////////////////////////////////
        #
        # ------------ START SUB FUNCTION - GET NODE PROPERTES ( LABELS & VALUES ) ----------------------------------
        #

        # Function to get all Properties and Values from a Node as an Ordered Dictionary
        def getNodePropValues(node, nodeLabel):

            # Define an internal Ordered Dictionary for function
            node_dict = OrderedDict()

            # Get node properties for each property category
            for category in categories:
                properties = node.getProperties(category)

                # Get the label and identifier of each property
                for prop in properties:
                    propLabel = prop.getLabel()

                    # Get the value for the currently accessed property
                    value = node.getPropertyValue(prop)

                    if value:
                        valueType = value.getType()
                        valueClass = value.getClassName()
                        value = SDValueSerializer.sToString(value) # This gives a convoluted result, poor readability

                        # ///////////////////////////////////////////////////////////////////////////////////////////
                        #
                        # -------- START DIRTY CLEANER for convoluted value strings. And also for rounding floats
                        #    
                        # Example, to convert from:
                        #       ('Position Random', 'SDValueFloat2(float2(0.17365,0.3249))')
                        # to a more simple and readable:
                        #       ('Position Random', ('0.17', '0.32'))

                        if valueClass == 'SDValueEnum':

                            # To get the final integer (I'm sure this can be done easier)
                            value = value.replace('"', '+' ) # Replace the " by +
                            value = re.sub(r'\+.*?\+', '', value) # Remove all between +
                            value = re.sub('\D', '', value) # Remove all except digits
                            value = int(value)

                            enums = valueType.getEnumerators()
                            enum_dict = {}

                            for enum in enums:
                                enum_dict[enum.getDefaultValue().get()] = enum.getId()

                            value = enum_dict[value].title() # Some results are lower case. Best feedback in Uppercase

                        elif 'SDValueArray(SDValueStruct(' in value:
                            value = 'GRAPH'

                        elif 'SDValueInt(int(' in value:
                            value = value.replace('SDValueInt(int(','').replace('))','')

                        elif 'SDValueInt2(int2(' in value:
                            value = value.replace('SDValueInt2(int2(','').replace('))','')

                        elif 'SDValueFloat(float(' in value:
                            value = value.replace('SDValueFloat(float(','').replace('))','')
                            value = str(round(float(value), roundN))

                        elif 'SDValueFloat2(float2(' in value:
                            value = value.replace('SDValueFloat2(float2(','').replace('))','')
                            value0 = value.split(',')[0]
                            value1 = value.split(',')[1]
                            value = str(round(float(value0), roundN)), str(round(float(value1), roundN))

                        elif 'SDValueFloat3(float3(' in value:
                            value = value.replace('SDValueFloat3(float3(','').replace('))','')
                            value0 = value.split(',')[0]
                            value1 = value.split(',')[1]
                            value2 = value.split(',')[2]
                            value = str(round(float(value0), roundN)), str(round(float(value1), roundN)), str(round(float(value2), roundN))

                        elif 'SDValueFloat4(float4(' in value:
                            value = value.replace('SDValueFloat4(float4(','').replace('))','')
                            value0 = value.split(',')[0]
                            value1 = value.split(',')[1]
                            value2 = value.split(',')[2]
                            value3 = value.split(',')[3]

                            # Special case for 'Dual Nodes' (ie LEVELS) to choose only the first float if it's acting as Grayscale
                            if modifNodeLabel in dualNodes and modifNodeDepth == 'gray':
                                value = str(round(float(value0), roundN))
                            else:
                                value = str(round(float(value0), roundN)), str(round(float(value1), roundN)), str(round(float(value2), roundN)), str(round(float(value3), roundN))

                        elif 'SDValueColorRGBA(ColorRGBA(' in value:
                            value = value.replace('SDValueColorRGBA(ColorRGBA(','').replace('))','')
                            value0 = value.split(',')[0]
                            value1 = value.split(',')[1]
                            value2 = value.split(',')[2]
                            value3 = value.split(',')[3]
                            value = str(round(float(value0), roundN)), str(round(float(value1), roundN)), str(round(float(value2), roundN)), str(round(float(value3), roundN))

                        elif 'SDValueBool(bool(' in value:
                            value = value.replace('SDValueBool(bool(','').replace('))','')

                        elif 'SDValueString(string(' in value:
                            value = value.replace('SDValueString(string(','').replace('))','')

                        elif 'SDValueTexture(SDTexture(' in value:
                            value = value.replace('SDValueTexture(SDTexture(','').replace('))','')

                        else:
                            value = 'UNKNOW'

                        # Special cases to give a better/short readability
                        if propLabel in betterLabelDict:
                            propLabel = betterLabelDict[propLabel]

                        if value in betterValueDict:
                            value = betterValueDict[value]
                        
                        # -------- END DIRTY CLEANER ----------------------------------------------------------------
                        #
                        # ///////////////////////////////////////////////////////////////////////////////////////////

                        # Add our label/value combos to dictionary
                        node_dict.update({propLabel: value}) # Add our label/value combos to dictionaries

            return node_dict

        #
        # ------------ END SUB FUNCTION - GET NODE PROPERTES ( LABELS & VALUES ) ------------------------------------
        #
        # ////////////////////////////////////////////////////////////////////////////////////////////////////////////


        # ////////////////////////////////////////////////////////////////////////////////////////////////////////////
        #
        # ------------------------------------------------------------------------------------------------------------
        # Get the application and UI manager object
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        uiMgr = app.getQtForPythonUIMgr()
        pkMgr = app.getPackageMgr()
        modMgr = app.getModuleMgr()

        # Get the current graph and grid size
        graph = uiMgr.getCurrentGraph()
        gridSize = GraphGrid.sGetFirstLevelSize()

        # Get the currently selected nodes
        selection = uiMgr.getCurrentGraphSelectedNodes()
        size = selection.getSize()

        # If more than 1 node selected gives alert
        if size != 1:
            print('Select 1 and only 1 node')

        # ------------------------------------------------------------------------------------------------------------
        # Dictionary for special cases to give a better/short readability in Labels
        betterLabelDict = {
            'Rotation' : 'Rot-Turns',
            'Angle' : 'Rot-Turns',
            'Output Color' : 'RGBA',
            'Blending Mode' : 'Blend',
            'Tiling Mode' : 'Tiling',
            'Edge Roundness' : 'Edge Round',
            'Vector Map Displacement' : 'Vector Map Displ',
            'Vector Map Multiplier' : 'Vector Map Multip',
            'Mask Map Threshold' : 'Mask Map Thres',
            'Luminance By Number' : 'Lumi by Number',
            'Luminance By Scale' : 'Lumi by Scale',
            'Luminance Random' : 'Lumi Random',
            'Luminance by Ring Number' : 'Lumi by Ring Number',
            'Luminance by Pattern Number' : 'Lumi by Patt Number',
            'Color Parametrization Multiplier' : 'Color Param Multip',
            'Color Parametrization Mode' : 'Color Param Mode',
            'Alpha Channel Content' : 'Alpha Chan Cont',
            'Cropping Area' : 'Crop',
            'Gradient Orientation' : 'Grad Orient',
            'Gradient RGBA' : 'Grad RGBA',
            'Spline Rotation Random' : 'Spline Rot Rand',
            'Warp Angle Input Multiplier' : 'Warp Ang Inp Multi',
            'Spline Distortion Random' : 'Spline Distr Rand',
            'Spline Distortion Frequency' : 'Spline Distr Freq',
            'Spline Width Random' : 'Spline Width Rand',
            'Rotation Random' : 'Rot Rand',
            'Scale Random' : 'Scale Rand',
            'Transform matrix' : 'Matrix',
            'Interstice X/Y' : 'Inters X/Y',
            'Pattern Input Number' : 'Patt Input Numb'
        }

        # Dictionary for special cases to give a better/short readability in Values
        betterValueDict = {
            'true' : 'TRUE',
            'false' : 'FALSE',
            'No_Tiling' : 'NO',
            'Horizontal_Tiling' : 'HORIZ',
            'Vertical_Tiling' : 'VERT',
            'Image Input' : 'Img Input'
        }

        # Supported Atomic Nodes (better to list Supported than Unsupported bacause user can create custom Labels for some nodes)
        supportAtomic = ['Blend', 'Blur', 'Channels Shuffle', 'Curve', 'Directional Blur', 'Directional Warp', 
        'Distance', 'Emboss', 'Gradient (Dynamic)', 'Gradient Map', 'Grayscale Conversion', 'HSL', 'Levels', 
        'Normal', 'Sharpen', 'Text', 'Transformation 2D', 'Uniform Color', 'Warp']

        # Unsupported Instances. For the moment, Atomic Nodes that really appear as Instances when using 'modifNode.getReferencedResource()'
        unsupportInstances = ['SVG', 'Bitmap', 'FX-Map']


        # ------------------------------------------------------------------------------------------------------------
        # Get first (and supposedly unique) node and also the nice label (the top title in the node)

        try:
            modifNode = selection.getItem(0) 
            modifNodeLabel = modifNode.getDefinition().getLabel()

        except:
            modifNode_dict = {'Non': 'Supported'}


        # ------------------------------------------------------------------------------------------------------------
        # Discern if node is acting as Grayscale or Color. At least necessary for LEVELS, maybe also with others
        output_node = None
        output_prop = None
        modifNodeDepth = None
        dualNodes = ['Levels']

        if modifNodeLabel in dualNodes:
            for prop in modifNode.getProperties(sdproperty.SDPropertyCategory.Input):
                if prop.isConnectable():
                    for conn in modifNode.getPropertyConnections(prop):
                        output_prop = conn.getInputProperty()
                        output_node = conn.getInputPropertyNode()

            try:
                output_node_bpp = output_node.getPropertyValue(output_prop).get().getBytesPerPixel()
            except:
                modifNodeDepth = 'gray'

            if output_node_bpp > 2:
                modifNodeDepth = 'color'
            else:
                modifNodeDepth = 'gray'

        # ------------------------------------------------------------------------------------------------------------
        # Get Ordered Dictionary for Modified Node using our function
        try:
            modifNode_dict = getNodePropValues(modifNode, modifNodeLabel)

        except:
            modifNode_dict = {'Non': 'Supported'}

        # Identify if node is Atomic or Instance, and also 'Referenced Graph' & 'From Package' if Instance
        modifNode_refRsc = modifNode.getReferencedResource()

        # ------------------------------------------------------------------------------------------------------------
        # Load and Identify procedure for INSTANCE NODES
        if modifNode_refRsc:

            if modifNodeLabel not in unsupportInstances:

                # Get the Pack File Path and Graph Instance info (the one you see at top of Attributes)
                pack_file_path = modifNode_refRsc.getPackage().getFilePath()
                graph_instance = modifNode_refRsc.getIdentifier()

                # Convoluted procedure to load an Instance Node, same as selected, to be used as Reference
                package = pkMgr.loadUserPackage(pack_file_path)
                resource = package.findResourceFromUrl('%s' % graph_instance)

                if resource:
                    referNode = graph.newInstanceNode(resource)
                    pkMgr.unloadUserPackage(package) # This is necessary, to Unload, because Package also loads in Explorer

                    # Get Ordered Dictionary for Reference Instance Node
                    referNode_dict = getNodePropValues(referNode, modifNodeLabel)

                    graph.deleteNode(referNode) # Delete that Reference Node, once we got the needed info (already in our dict)

                else:
                    pkMgr.unloadUserPackage(package) # This is necessary, to Unload, because Package also loads in Explorer
                    modifNode_dict = {'Non': 'Supported'}
            else:
                modifNode_dict = {'Non': 'Supported'}

        # ------------------------------------------------------------------------------------------------------------
        # Load and Identify procedure for ATOMIC NODES
        else:
            if modifNodeLabel in supportAtomic:

                atomic_nodes_module = modMgr.getModuleFromId("sbs::compositing")
                label_identifier_dict = {} # Create a dictionary on the fly to identify 'nice' labels with internal names

                for item in atomic_nodes_module.getDefinitions():
                    label_identifier_dict[item.getLabel()] = item.getId()

                referNode = graph.newNode(label_identifier_dict["%s" % modifNodeLabel])
                referNodeLabel = referNode.getDefinition().getLabel() # Get nice label (the top title in the node)
                referNode_dict = getNodePropValues(referNode, referNodeLabel) # Get Ordered Dictionary for Reference Atomic Node
                graph.deleteNode(referNode) # Delete that Reference Node, once we got the needed info (already in our dict)

            # For those non supported Atomic Nodes
            else:
                modifNode_dict = {'Non': 'Supported'}

        # ------------------------------------------------------------------------------------------------------------
        # Differences between dictionaries
        for key, value in modifNode_dict.items():
            if key not in referNode_dict:
                different_dict.update({key: value})
            else:
                if value != referNode_dict[key]:
                    different_dict.update({key: value})

        # ------------------------------------------------------------------------------------------------------------
        # For when both nodes are identical I prefer to create a Comment to clarify
        if len(different_dict) == 0:
            different_dict = {'All by': 'default'}

        # ------------------------------------------------------------------------------------------------------------
        # Super-special case for a 'Normal-OUTPUT-Node' to differenciate from a 'Normal-Node' (both share same Nice Label)
        if 'Mipmaps' in different_dict:
            different_dict = {'Non': 'Supported'}

        # ------------------------------------------------------------------------------------------------------------
        # Clean the resulting list for simpler and better readability, breaking lines and removing some characters
        differ_list = list(different_dict.items()) # Convert Ordered Dictionary to list
        differ_str = '\n'.join(map(str, differ_list)) # To convert to various lines
        differ_str = differ_str.replace("(","").replace(")","").replace("'","").replace(", "," ") # Cleaning characters

        print(f'Different Values : {differ_str}')

        # ------------------------------------------------------------------------------------------------------------
        # Create New Comment attached to Node with our info
        sdGraphObjectComment = SDGraphObjectComment.sNewAsChild(modifNode)
        sdGraphObjectComment.setPosition(float2(-gridSize*0.5, gridSize*0.5))
        sdGraphObjectComment.setDescription('%s' % differ_str)

    #
    # ------------ END MAIN FUNCTION -----------------------------------------------------------------------------
    #
    #
    #
    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////
    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////


    # Literally copied from factory plugin 'node_align_tools'
    @classmethod
    def __onToolbarDeleted(cls, graphViewID):
        del cls.__toolbarList[graphViewID]

    # Literally copied from factory plugin 'node_align_tools'
    @classmethod 
    def removeAllToolbars(cls):
        for toolbar in cls.__toolbarList.values():
            if toolbar():
                toolbar().deleteLater()

# Adapted from factory plugin 'node_align_tools'
def onNewGraphViewCreated(graphViewID, uiMgr):
    # Ignore graph types not supported by the Python API.
    if not uiMgr.getCurrentGraph():
        return

    toolbar = PrintModValuesToolBar(graphViewID, uiMgr)
    uiMgr.addToolbarToGraphView(
        graphViewID,
        toolbar,
        icon = loadSvgIcon("print_modified_values", DEFAULT_ICON_SIZE),
        tooltip = toolbar.tooltip())


graphViewCreatedCallbackID = 0

# Literally copied from factory plugin 'node_align_tools'
def initializeSDPlugin():

    # Get the application and UI manager object.
    ctx = sd.getContext()
    app = ctx.getSDApplication()
    uiMgr = app.getQtForPythonUIMgr()

    if uiMgr:
        global graphViewCreatedCallbackID
        graphViewCreatedCallbackID = uiMgr.registerGraphViewCreatedCallback(
            partial(onNewGraphViewCreated, uiMgr=uiMgr))


# Adapted from factory plugin 'node_align_tools'
def uninitializeSDPlugin():
    ctx = sd.getContext()
    app = ctx.getSDApplication()
    uiMgr = app.getQtForPythonUIMgr()

    if uiMgr:
        global graphViewCreatedCallbackID
        uiMgr.unregisterCallback(graphViewCreatedCallbackID)
        PrintModValuesToolBar.removeAllToolbars()
