import adsk.core, adsk.fusion, adsk.cam, traceback
import os
from ...lib import fusionAddInUtils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_boundingBox'
CMD_NAME = 'Bounding Box'
CMD_Description = 'Create a bounding box around a body'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so they are not released and garbage collected.
handlers = []


def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # Add a button into the UI so the user can run the command.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED


def stop():
    # Remove the command from the UI.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    if command_control:
        command_control.deleteMe()
    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} Command Created Event')

    inputs = args.command.commandInputs

    # Add the selection input to select a body
    bodySelection = inputs.addSelectionInput('bodySelection', 'Select Body', 'Select the body to create bounding box around')
    bodySelection.addSelectionFilter(adsk.core.SelectionCommandInput.Bodies)
    bodySelection.setSelectionLimits(1, 1)

    # Get the default units for the document
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    defaultUnits = design.unitsManager.defaultLengthUnits

    # Add value inputs for positive and negative offsets for X, Y, and Z sizes
    inputs.addValueInput('xPosOffset', 'X + Offset', defaultUnits, adsk.core.ValueInput.createByString(f'0 {defaultUnits}'))
    inputs.addValueInput('xNegOffset', 'X - Offset', defaultUnits, adsk.core.ValueInput.createByString(f'0 {defaultUnits}'))
    inputs.addValueInput('yPosOffset', 'Y + Offset', defaultUnits, adsk.core.ValueInput.createByString(f'0 {defaultUnits}'))
    inputs.addValueInput('yNegOffset', 'Y - Offset', defaultUnits, adsk.core.ValueInput.createByString(f'0 {defaultUnits}'))
    inputs.addValueInput('zPosOffset', 'Z + Offset', defaultUnits, adsk.core.ValueInput.createByString(f'0 {defaultUnits}'))
    inputs.addValueInput('zNegOffset', 'Z - Offset', defaultUnits, adsk.core.ValueInput.createByString(f'0 {defaultUnits}'))

    # Attach event handlers for the command
    onExecute = CommandExecuteHandler()
    args.command.execute.add(onExecute)
    handlers.append(onExecute)

    onInputChanged = CommandInputChangedHandler()
    args.command.inputChanged.add(onInputChanged)
    handlers.append(onInputChanged)

    onDestroy = CommandDestroyHandler()
    args.command.destroy.add(onDestroy)
    handlers.append(onDestroy)


class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            design = adsk.fusion.Design.cast(app.activeProduct)
            rootComp = design.rootComponent

            inputs = args.command.commandInputs
            bodySelection = adsk.core.SelectionCommandInput.cast(inputs.itemById('bodySelection'))

            selectedBody = adsk.fusion.BRepBody.cast(bodySelection.selection(0).entity)

            # Get the bounding box
            boundingBox = selectedBody.boundingBox

            # Get the user-defined offsets
            xPosOffsetInput = adsk.core.ValueCommandInput.cast(inputs.itemById('xPosOffset'))
            xNegOffsetInput = adsk.core.ValueCommandInput.cast(inputs.itemById('xNegOffset'))
            yPosOffsetInput = adsk.core.ValueCommandInput.cast(inputs.itemById('yPosOffset'))
            yNegOffsetInput = adsk.core.ValueCommandInput.cast(inputs.itemById('yNegOffset'))
            zPosOffsetInput = adsk.core.ValueCommandInput.cast(inputs.itemById('zPosOffset'))
            zNegOffsetInput = adsk.core.ValueCommandInput.cast(inputs.itemById('zNegOffset'))

            xPosOffset = xPosOffsetInput.value
            xNegOffset = xNegOffsetInput.value
            yPosOffset = yPosOffsetInput.value
            yNegOffset = yNegOffsetInput.value
            zPosOffset = zPosOffsetInput.value
            zNegOffset = zNegOffsetInput.value

            # Define the corner points of the bounding box
            minPoint = adsk.core.Point3D.create(
                boundingBox.minPoint.x - xNegOffset,
                boundingBox.minPoint.y - yNegOffset,
                boundingBox.minPoint.z - zNegOffset
            )
            maxPoint = adsk.core.Point3D.create(
                boundingBox.maxPoint.x + xPosOffset,
                boundingBox.maxPoint.y + yPosOffset,
                boundingBox.maxPoint.z + zPosOffset
            )

            # Create a new component for the bounding box
            newOcc = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            newComp = newOcc.component
            newComp.name = 'Bounding Box'

            # Create a sketch on the XY plane
            sketches = newComp.sketches
            xyPlane = newComp.xYConstructionPlane
            sketch = sketches.add(xyPlane)

            # Draw the rectangle
            lines = sketch.sketchCurves.sketchLines
            lines.addTwoPointRectangle(
                adsk.core.Point3D.create(minPoint.x, minPoint.y, minPoint.z),
                adsk.core.Point3D.create(maxPoint.x, maxPoint.y, minPoint.z)
            )

            # Get the profile defined by the rectangle
            profile = sketch.profiles.item(0)

            # Create an extrusion input
            extrudes = newComp.features.extrudeFeatures
            extInput = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

            # Define the distance
            distance = adsk.core.ValueInput.createByReal(maxPoint.z - minPoint.z)
            extInput.setDistanceExtent(False, distance)

            # Create the extrusion
            ext = extrudes.add(extInput)

            # Rename the body to 'Bounding Box'
            boundingBoxBody = ext.bodies.item(0)
            boundingBoxBody.name = 'Bounding Box'

        except:
            app = adsk.core.Application.get()
            ui = app.userInterface
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class CommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            inputs = args.inputs
            changedInput = args.input

        except:
            app = adsk.core.Application.get()
            ui = app.userInterface
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class CommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        global handlers
        handlers = []
        futil.log(f'{CMD_NAME} Command Destroy Event')

