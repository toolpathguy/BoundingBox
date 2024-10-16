import adsk.core, adsk.fusion, adsk.cam, traceback

handlers = []

def start():
    app = adsk.core.Application.get()
    ui = app.userInterface

    cmdDef = ui.commandDefinitions.itemById('BoundingBoxCommand')
    if not cmdDef:
        cmdDef = ui.commandDefinitions.addButtonDefinition(
            'BoundingBoxCommand',
            'Create Bounding Box',
            'Create a bounding box around a selected body with customizable offsets.'
        )

    onCommandCreated = CommandCreatedHandler()
    cmdDef.commandCreated.add(onCommandCreated)
    handlers.append(onCommandCreated)

    addInPanel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
    cmdControl = addInPanel.controls.addCommand(cmdDef)
    handlers.append(cmdControl)

def stop():
    app = adsk.core.Application.get()
    ui = app.userInterface

    cmdDef = ui.commandDefinitions.itemById('BoundingBoxCommand')
    if cmdDef:
        cmdDef.deleteMe()

    addInPanel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
    cmdControl = addInPanel.controls.itemById('BoundingBoxCommand')
    if cmdControl:
        cmdControl.deleteMe()

class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            cmd = adsk.core.Command.cast(args.command)
            cmd.isExecutedWhenPreEmpted = False

            onExecute = CommandExecuteHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)

            onInputChanged = CommandInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            handlers.append(onInputChanged)

            # Define the command dialog
            inputs = cmd.commandInputs

            # Add a selection input to select a body
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

        except:
            app = adsk.core.Application.get()
            ui = app.userInterface
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

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

            # Terminate the script
            adsk.terminate()

        except:
            app = adsk.core.Application.get()
            ui = app.userInterface
            ui.messageBox('Failed:\n{}'.format(traceback.format.exc()))

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
            ui.messageBox('Failed:\n{}'.format(traceback.format.exc()))

