# python
#
# print_modified_values - v.0.3 - THIS IS A WIP
# To automatically add a child Comment with non default values in Adobe Substance 3D Designer
#
# Created by Cristobal Vila - etereaestudios.com - November 2022
#
# For more info about how to install and how to help me with the development, check this:
# https://etereaestudios.com/2022/11/13/print-modified-values-plugin-for-designer/
# Don't worry: I look for help to improve the code of this script, not financial help ;-)


# Import the required classes, tools and other sd stuff.
import os
import sd
import re
import weakref

from functools import partial
from collections import OrderedDict

from sd.tools import io
from sd.tools import graphlayout

from sd.ui.graphgrid import *
from sd.api.sbs.sdsbscompgraph import *
from sd.api.sdgraphobjectpin import *
from sd.api.sdgraphobjectframe import *
from sd.api.sdgraphobjectcomment import *
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdvalueserializer import SDValueSerializer

from PySide2 import QtCore, QtGui, QtWidgets, QtSvg


DEFAULT_ICON_SIZE = 24

def loadSvgIcon(iconName, size): # Literally copied from factory plugin 'node_align_tools'
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


class PrintModValuesToolBar(QtWidgets.QToolBar): # Adapted from factory plugin 'node_align_tools'
    __toolbarList = {}

    def __init__(self, graphViewID, uiMgr):
        super(PrintModValuesToolBar, self).__init__(parent=uiMgr.getMainWindow())

        self.setObjectName("etereaestudios.com.print_modvalues_toolbar")

        self.__graphViewID = graphViewID
        self.__uiMgr = uiMgr

        act = self.addAction(loadSvgIcon("print_modified_values_a", DEFAULT_ICON_SIZE), "PMVa")
        act.setShortcut(QtGui.QKeySequence('Q'))
        act.setToolTip(self.tr("Print Modified Values from A to B"))
        act.triggered.connect(self.__onPrintModValuesA)

        act = self.addAction(loadSvgIcon("print_modified_values_b", DEFAULT_ICON_SIZE), "PMVb")
        act.setShortcut(QtGui.QKeySequence('W'))
        act.setToolTip(self.tr("Print Modified Values from B to A"))
        act.triggered.connect(self.__onPrintModValuesB)

        self.__toolbarList[graphViewID] = weakref.ref(self)
        self.destroyed.connect(partial(PrintModValuesToolBar.__onToolbarDeleted, graphViewID=graphViewID))

    def tooltip(self):
        return self.tr("Print Modified Values")

    # Here comes the main function A
    # TO DO: This needs to be cleaned to create only 1 funtion, with arguments, and not repeat the same funtion twice
    # ---------------------------------------------------------------------------------------------------------------
    def __onPrintModValuesA(self):

        # Get the application and UI manager object.
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        uiMgr = app.getQtForPythonUIMgr()

        # Get the current graph and grid size
        sdSBSCompGraph = uiMgr.getCurrentGraph()
        cGridSize = GraphGrid.sGetFirstLevelSize()

        # Get the currently selected nodes.
        selection = uiMgr.getCurrentGraphSelectedNodes()
        size = selection.getSize()

        # I define these nodes, but order of selection does NOT exist in Designer
        nodeA = selection.getItem(0)
        nodeB = selection.getItem(1)

        roundN = 2 # Overall round value for floats. Change this to 3 or 4 for extra accuracy

        # Dictionary for Blend node (this is not valid for blend modes in Tile Generator and such)
        blend_d = {
            '0': 'Copy',
            '1': 'Add',
            '2': 'Subtract',
            '3': 'Multiply',
            '4': 'Add Sub',
            '5': 'Max',
            '6': 'Min',
            '7': 'Switch',
            '8': 'Divide',
            '9': 'Overlay',
            '10': 'Screen',
            '11': 'Soft Light',
        }

        # Crete both Ordered Dictionaries for REFERENCE/MODIFIED nodes, and for DIFFERENCES
        refmod_dict = OrderedDict()
        differ_dict = OrderedDict()

        for index, node in enumerate(selection):
            definition = node.getDefinition() # Random value at each call
            identifier = node.getIdentifier() # Fix value
            nodeFromID = sdSBSCompGraph.getNodeFromId(identifier) # Random value at each call
            nodeLabel = nodeFromID.getDefinition().getLabel() # Fix Value, name in node
            # print('NODE - definition: %s, identifier: %s, fromID: %s, label: %s' % (definition, identifier, nodeFromID, nodeLabel))

            refmod_dict[index] = OrderedDict()

            # Create a list of each property category enumeration item.
            categories = [
                SDPropertyCategory.Annotation,
                SDPropertyCategory.Input,
                SDPropertyCategory.Output
            ]

            # Get node properties for each property category.
            for category in categories:
                props = definition.getProperties(category)

                # Get the label and identifier of each property.
                for prop in props:
                    label = prop.getLabel()

                    # Get the value for the currently accessed property.
                    value = node.getPropertyValue(prop)

                    if value:
                        value = SDValueSerializer.sToString(value) # This gives a convoluted result, poor readability

                        # -----------------------------------------------------------------------------
                        # Dirty cleaner for convoluted value strings. And also for rounding floats.
                        # Example, to convert from:
                        # ('Position Random', 'SDValueFloat2(float2(0.17365,0.3249))')
                        # to a more simple and readable:
                        # ('Position Random', ('0.17', '0.32'))

                        if 'SDValueEnum' in value:
                            value = value.replace('"', '+' ) # Replace the " by +
                            value = re.sub(r'\+.*?\+', '', value) # Remove all between +
                            value = re.sub('\D', '', value) # Remove all except digits

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
                            value = str(round(float(value0), roundN)), str(round(float(value1), roundN)), str(round(float(value2), roundN)), str(round(float(value3), roundN))

                        elif 'SDValueBool(bool(' in value:
                            value = value.replace('SDValueBool(bool(','').replace('))','')

                        elif 'SDValueString(string(' in value:
                            value = value.replace('SDValueString(string(','').replace('))','')

                        elif 'SDValueTexture(SDTexture(' in value:
                            value = value.replace('SDValueTexture(SDTexture(','').replace('))','')

                        elif 'SDValueColorRGBA(ColorRGBA(' in value:
                            value = value.replace('SDValueColorRGBA(ColorRGBA(','').replace('))','')

                        else:
                            value = 'UNKNOW'

                        # Special case for Blend node only (not valid for blend modes in Tile Generator and such)
                        if nodeLabel == 'Blend':
                            if label == 'Blending Mode':
                                label = 'Blend'
                                value = blend_d[value]

                        # Special cases for Rotation/Angle, to clarify that value is Turns (not Degrees)
                        if 'Rotation' in label:
                            label = 'Rot-Turns'

                        elif 'Angle' in label:
                            label = 'Angle-Turns'

                        # -----------------------------------------------------------------------------

                        refmod_dict[index].update({label: value}) # Add our label/value combos to dictionaries


        print('Len Dict 0 = %s' % len(refmod_dict[0]))
        print('Len Dict 1 = %s' % len(refmod_dict[1]))

        # DIFFERENCE BETWEEN FUNCTION A & B <<<----------------------------------------------------------------------
        # Hack to solve order of selection problem (Designer does not recognize order of node selections)
        for key, value in refmod_dict[0].items():
            if key not in refmod_dict[1]:
                differ_dict.update({key: value})
            else:
                if value != refmod_dict[1][key]:
                    differ_dict.update({key: value})

        # For when both nodes are identical I prefer to create a Comment to clarify
        if len(differ_dict) == 0:
            differ_dict = {
                'NO': 'CHANGES'
            }

        differ_list = list(differ_dict.items()) # Convert Ordered Dictionary to list

        # Clean the resulting list for simpler and better readability, breaking lines and removing some characters
        differ_str = '\n'.join(map(str, differ_list)) # To convert to various lines
        differ_str = differ_str.replace("(","").replace(")","").replace("'","") # Extra step to remove characters (')

        print(differ_str)

        # Create New Comment attached to Node, using the order hack
        sdGraphObjectComment = SDGraphObjectComment.sNewAsChild(nodeA) # DIFFERENCE BETWEEN FUNCTION A & B <<<-------
        sdGraphObjectComment.setPosition(float2(-cGridSize*0.5, cGridSize*0.5))
        sdGraphObjectComment.setDescription('%s' % differ_str)


    # Here comes the main function B
    # TO DO: This needs to be cleaned to create only 1 funtion, with arguments, and not repeat the same funtion twice
    # ---------------------------------------------------------------------------------------------------------------
    def __onPrintModValuesB(self):

        # Get the application and UI manager object.
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        uiMgr = app.getQtForPythonUIMgr()

        # Get the current graph and grid size
        sdSBSCompGraph = uiMgr.getCurrentGraph()
        cGridSize = GraphGrid.sGetFirstLevelSize()

        # Get the currently selected nodes.
        selection = uiMgr.getCurrentGraphSelectedNodes()
        size = selection.getSize()

        # I define these nodes, but order of selection does NOT exist in Designer
        nodeA = selection.getItem(0)
        nodeB = selection.getItem(1)

        roundN = 2 # Overall round value for floats. Change this to 3 or 4 for extra accuracy

        # Dictionary for Blend node (this is not valid for blend modes in Tile Generator and such)
        blend_d = {
            '0': 'Copy',
            '1': 'Add',
            '2': 'Subtract',
            '3': 'Multiply',
            '4': 'Add Sub',
            '5': 'Max',
            '6': 'Min',
            '7': 'Switch',
            '8': 'Divide',
            '9': 'Overlay',
            '10': 'Screen',
            '11': 'Soft Light',
        }

        # Crete both Ordered Dictionaries for REFERENCE/MODIFIED nodes, and for DIFFERENCES
        refmod_dict = OrderedDict()
        differ_dict = OrderedDict()

        for index, node in enumerate(selection):
            definition = node.getDefinition() # Random value at each call
            identifier = node.getIdentifier() # Fix value
            nodeFromID = sdSBSCompGraph.getNodeFromId(identifier) # Random value at each call
            nodeLabel = nodeFromID.getDefinition().getLabel() # Fix Value, name in node
            # print('NODE - definition: %s, identifier: %s, fromID: %s, label: %s' % (definition, identifier, nodeFromID, nodeLabel))

            refmod_dict[index] = OrderedDict()

            # Create a list of each property category enumeration item.
            categories = [
                SDPropertyCategory.Annotation,
                SDPropertyCategory.Input,
                SDPropertyCategory.Output
            ]

            # Get node properties for each property category.
            for category in categories:
                props = definition.getProperties(category)

                # Get the label and identifier of each property.
                for prop in props:
                    label = prop.getLabel()                    

                    # Get the value for the currently accessed property.
                    value = node.getPropertyValue(prop)

                    if value:
                        value = SDValueSerializer.sToString(value) # This gives a convoluted result, poor readability

                        # -----------------------------------------------------------------------------
                        # Dirty cleaner for convoluted value strings. And also for rounding floats.
                        # Example, to convert from:
                        # ('Position Random', 'SDValueFloat2(float2(0.17365,0.3249))')
                        # to a more simple and readable:
                        # ('Position Random', ('0.17', '0.32'))

                        if 'SDValueEnum' in value:
                            value = value.replace('"', '+' ) # Replace the " by +
                            value = re.sub(r'\+.*?\+', '', value) # Remove all between +
                            value = re.sub('\D', '', value) # Remove all except digits

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
                            value = str(round(float(value0), roundN)), str(round(float(value1), roundN)), str(round(float(value2), roundN)), str(round(float(value3), roundN))

                        elif 'SDValueBool(bool(' in value:
                            value = value.replace('SDValueBool(bool(','').replace('))','')

                        elif 'SDValueString(string(' in value:
                            value = value.replace('SDValueString(string(','').replace('))','')

                        elif 'SDValueTexture(SDTexture(' in value:
                            value = value.replace('SDValueTexture(SDTexture(','').replace('))','')

                        elif 'SDValueColorRGBA(ColorRGBA(' in value:
                            value = value.replace('SDValueColorRGBA(ColorRGBA(','').replace('))','')

                        else:
                            value = 'UNKNOW'

                        # Special case for Blend node only (this is not valid for blend modes in Tile Generator and such)
                        if nodeLabel == 'Blend':
                            if label == 'Blending Mode':
                                label = 'Blend'
                                value = blend_d[value]

                        # Special cases for Rotation/Angle, to note that value is Turns (not Degrees)
                        if 'Rotation' in label:
                            label = 'Rot-Turns'

                        elif 'Angle' in label:
                            label = 'Angle-Turns'

                        # -----------------------------------------------------------------------------

                        refmod_dict[index].update({label: value}) # Add our label/value combos to dictionaries


        print('Len Dict 0 = %s' % len(refmod_dict[0]))
        print('Len Dict 1 = %s' % len(refmod_dict[1]))

        # DIFFERENCE BETWEEN FUNCTION A & B <<<----------------------------------------------------------------------
        # Hack to solve order of selection problem (Designer does not recognize order of node selections)
        for key, value in refmod_dict[1].items():
            if key not in refmod_dict[0]:
                differ_dict.update({key: value})
            else:
                if value != refmod_dict[0][key]:
                    differ_dict.update({key: value})

        if len(differ_dict) == 0:
            differ_dict = {
                'NO': 'CHANGES'
            }

        differ_list = list(differ_dict.items()) # Convert Ordered Dictionary to list

        # Clean the resulting list for simpler and better readability, breaking lines and removing some characters
        differ_str = '\n'.join(map(str, differ_list)) # To convert to various lines
        differ_str = differ_str.replace("(","").replace(")","").replace("'","") # Extra step to remove characters (')

        print(differ_str)

        # Create New Comment attached to Node, using the order hack
        sdGraphObjectComment = SDGraphObjectComment.sNewAsChild(nodeB) # DIFFERENCE BETWEEN FUNCTION A & B <<<-------
        sdGraphObjectComment.setPosition(float2(-cGridSize*0.5, cGridSize*0.5))
        sdGraphObjectComment.setDescription('%s' % differ_str)


    @classmethod # Literally copied from factory plugin 'node_align_tools'
    def __onToolbarDeleted(cls, graphViewID):
        del cls.__toolbarList[graphViewID]

    @classmethod # Literally copied from factory plugin 'node_align_tools'
    def removeAllToolbars(cls):
        for toolbar in cls.__toolbarList.values():
            if toolbar():
                toolbar().deleteLater()


def onNewGraphViewCreated(graphViewID, uiMgr): # Adapted from factory plugin 'node_align_tools'
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


def initializeSDPlugin(): # Literally copied from factory plugin 'node_align_tools'

    # Get the application and UI manager object.
    ctx = sd.getContext()
    app = ctx.getSDApplication()
    uiMgr = app.getQtForPythonUIMgr()

    if uiMgr:
        global graphViewCreatedCallbackID
        graphViewCreatedCallbackID = uiMgr.registerGraphViewCreatedCallback(
            partial(onNewGraphViewCreated, uiMgr=uiMgr))


def uninitializeSDPlugin(): # Adapted from factory plugin 'node_align_tools'
    ctx = sd.getContext()
    app = ctx.getSDApplication()
    uiMgr = app.getQtForPythonUIMgr()

    if uiMgr:
        global graphViewCreatedCallbackID
        uiMgr.unregisterCallback(graphViewCreatedCallbackID)
        PrintModValuesToolBar.removeAllToolbars()
