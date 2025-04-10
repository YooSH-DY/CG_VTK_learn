#!/usr/bin/env python

import vtk

# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkMinimalStandardRandomSequence
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkPropPicker,
    vtkProperty,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkRenderer,
)


colors = vtkNamedColors()
NUMBER_OF_SPHERES = 10
armActor = vtk.vtkActor()
armTransform = vtk.vtkTransform()
renwin = vtkRenderWindow()
forearmActor = vtk.vtkActor()
forearmTransform = vtk.vtkTransform()
handTransform = vtk.vtkTransform()
handActor = vtk.vtkActor()
hand = vtk.vtkCylinderSource()
oldRotate = [1, 1, 1]


class MouseInteractorHighLightActor(vtkInteractorStyleTrackballCamera):
    def __init__(self, parent=None):
        self.AddObserver("LeftButtonPressEvent", self.leftButtonPressEvent)

        self.LastPickedActor = None
        self.LastPickedProperty = vtkProperty()

    def leftButtonPressEvent(self, obj, event):
        clickPos = self.GetInteractor().GetEventPosition()

        picker = vtkPropPicker()
        picker.Pick(clickPos[0], clickPos[1], 0, self.GetDefaultRenderer())

        # get the new
        self.NewPickedActor = picker.GetActor()

        # If something was selected
        if self.NewPickedActor:
            # If we picked something before, reset its property
            if self.LastPickedActor:
                self.LastPickedActor.GetProperty().DeepCopy(self.LastPickedProperty)

            # Save the property of the picked actor so that we can
            # restore it next time
            self.LastPickedProperty.DeepCopy(self.NewPickedActor.GetProperty())
            # Highlight the picked actor by changing its properties
            self.NewPickedActor.GetProperty().SetColor(colors.GetColor3d("Red"))
            self.NewPickedActor.GetProperty().SetDiffuse(1.0)
            self.NewPickedActor.GetProperty().SetSpecular(0.0)
            self.NewPickedActor.GetProperty().EdgeVisibilityOn()

            if picker.GetActor() == armActor:
                i = 0
                while i < 45:
                    armTransform.Identity()
                    armTransform.RotateZ(-i * oldRotate[0])
                    # renwin.Render()
                    i += 1
                oldRotate[0] *= -1

            if picker.GetActor() == forearmActor:
                i = 0
                while i < 45:
                    forearmTransform.Identity()
                    forearmTransform.RotateZ(i * oldRotate[1])
                    # renwin.Render()
                    i += 1
                oldRotate[1] *= -1

            if picker.GetActor() == handActor:
                handCenter = hand.GetCenter()
                i = 0
                while i < 45:
                    handTransform.Identity()
                    handTransform.Translate(handCenter[0], handCenter[1], handCenter[2])
                    handTransform.RotateZ(-i * oldRotate[2])
                    handTransform.Translate(
                        -handCenter[0], -handCenter[1], -handCenter[2]
                    )
                    # renwin.Render()
                    i += 1
                oldRotate[2] *= -1

            # save the last picked actor
            self.LastPickedActor = self.NewPickedActor

        self.OnLeftButtonDown()
        return


def main():
    # A renderer and render window
    renderer = vtkRenderer()
    renderer.SetBackground(colors.GetColor3d("SteelBlue"))

    # renwin = vtkRenderWindow()
    renwin.AddRenderer(renderer)
    renwin.SetSize(640, 480)
    renwin.SetWindowName("HighlightPickedActor")

    # An interactor
    interactor = vtkRenderWindowInteractor()
    interactor.SetRenderWindow(renwin)

    # add the custom style
    style = MouseInteractorHighLightActor()
    style.SetDefaultRenderer(renderer)
    interactor.SetInteractorStyle(style)

    arm = vtk.vtkCylinderSource()
    arm.SetRadius(8)
    arm.SetHeight(20)
    arm.SetResolution(20)

    armMapper = vtk.vtkPolyDataMapper()
    armMapper.SetInputConnection(arm.GetOutputPort())

    # armTransform = vtk.vtkTransform()

    # armActor = vtk.vtkActor()
    armActor.SetUserTransform(armTransform)
    armActor.SetMapper(armMapper)
    armActor.GetProperty().SetColor(colors.GetColor3d("SandyBrown"))

    forearm = vtk.vtkCylinderSource()
    forearm.SetRadius(6)
    forearm.SetHeight(15)
    forearm.SetResolution(20)
    # forearm.SetCenter(arm.GetCenter(), arm.GetCenter()+ 1 + forearm.GetHeight(), arm.GetCenter() + 2)
    armCenter = arm.GetCenter()
    forearm.SetCenter(armCenter[0], armCenter[1] + forearm.GetHeight(), armCenter[2])

    forearmMapper = vtk.vtkPolyDataMapper()
    forearmMapper.SetInputConnection(forearm.GetOutputPort())
    # forearmTransform = vtk.vtkTransform()
    forearmTransform.SetInput(armTransform)

    # forearmActor = vtk.vtkActor()
    forearmActor.SetUserTransform(forearmTransform)
    forearmActor.SetMapper(forearmMapper)
    forearmActor.GetProperty().SetColor(colors.GetColor3d("RoyalBLue"))

    # hand = vtk.vtkCylinderSource()
    hand.SetRadius(4)
    hand.SetHeight(10)
    hand.SetResolution(20)
    # hand.SetCenter(*(forearm.GetCenter()),*(forearm.GetCenter() + 1) + hand.GetHeight(),*(forearm.GetCenter() + 2))
    forearmCenter = forearm.GetCenter()
    hand.SetCenter(
        forearmCenter[0], forearmCenter[1] + hand.GetHeight(), forearmCenter[2]
    )

    handMapper = vtk.vtkPolyDataMapper()
    handMapper.SetInputConnection(hand.GetOutputPort())

    # handTransform = vtk.vtkTransform()
    handTransform.SetInput(forearmTransform)

    # handActor = vtk.vtkActor()
    handActor.SetUserTransform(handTransform)
    handActor.SetMapper(handMapper)
    handActor.GetProperty().SetColor(colors.GetColor3d("GreenYellow"))

    renderer.AddActor(armActor)
    renderer.AddActor(forearmActor)
    renderer.AddActor(handActor)

    renwin.Render()

    # i = 0
    # while i < 45:
    #    armTransform.Identity()
    #    armTransform.RotateZ(-i)
    #    renwin.Render()
    #    i += 1

    # i = 0
    # while i < 45:
    #     forearmTransform.Identity()
    #     forearmTransform.RotateZ(-i)
    #     renwin.Render()
    #     i += 1

    # add the custom style
    # style = MouseInteractorHighLightActor()
    # style.SetDefaultRenderer(renderer)
    # interactor.SetInteractorStyle(style)

    # randomSequence = vtkMinimalStandardRandomSequence()
    # randomSequence.SetSeed(1043618065)
    # randomSequence.SetSeed(5170)
    # randomSequence.SetSeed(8775070)
    # Add spheres to play with
    # for i in range(NUMBER_OF_SPHERES):
    # source = vtkSphereSource()

    # random position and radius
    # x = randomSequence.GetRangeValue(-5.0, 5.0)
    # randomSequence.Next()
    # y = randomSequence.GetRangeValue(-5.0, 5.0)
    # randomSequence.Next()
    # z = randomSequence.GetRangeValue(-5.0, 5.0)
    # randomSequence.Next()
    # radius = randomSequence.GetRangeValue(0.5, 1.0)
    # randomSequence.Next()

    # source.SetRadius(radius)
    # source.SetCenter(x, y, z)
    # source.SetPhiResolution(11)
    # source.SetThetaResolution(21)

    # mapper = vtkPolyDataMapper()
    # mapper.SetInputConnection(source.GetOutputPort())
    # actor = vtkActor()
    # actor.SetMapper(mapper)

    # r = randomSequence.GetRangeValue(0.4, 1.0)
    # randomSequence.Next()
    # g = randomSequence.GetRangeValue(0.4, 1.0)
    # randomSequence.Next()
    # b = randomSequence.GetRangeValue(0.4, 1.0)
    # randomSequence.Next()

    # actor.GetProperty().SetDiffuseColor(r, g, b)
    # actor.GetProperty().SetDiffuse(.8)
    # actor.GetProperty().SetSpecular(.5)
    # actor.GetProperty().SetSpecularColor(colors.GetColor3d('White'))
    # actor.GetProperty().SetSpecularPower(30.0)

    # renderer.AddActor(actor)

    # Start
    interactor.Initialize()
    # renwin.Render()
    interactor.Start()


if __name__ == "__main__":
    main()
