import math
import vtk
import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingOpenGL2

from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import vtkQuadric
from vtkmodules.vtkFiltersCore import vtkContourFilter, vtkAppendFilter
from vtkmodules.vtkFiltersModeling import vtkOutlineFilter
from vtkmodules.vtkImagingCore import vtkExtractVOI
from vtkmodules.vtkImagingHybrid import vtkSampleFunction
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkCamera,
    vtkPolyDataMapper,
    vtkDataSetMapper,
    vtkProperty,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkPropPicker,
)
from vtkmodules.vtkFiltersSources import vtkCubeSource, vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera

# 전역 변수 설정 (회전 상태와 변환 객체 저장)
colors = vtkNamedColors()
finger_transforms = {}  # 각 손가락 마디의 변환 객체 저장
finger_actors = {}  # 각 손가락 마디의 액터 저장
old_rotations = {}  # 회전 상태 추적
render_window = None  # 렌더윈도우 전역 참조


# 마우스 상호작용 핸들러 클래스 정의
class MouseInteractorHighLightActor(vtkInteractorStyleTrackballCamera):
    def __init__(self, parent=None):
        self.AddObserver("LeftButtonPressEvent", self.leftButtonPressEvent)
        self.LastPickedActor = None
        self.LastPickedProperty = vtkProperty()

    def leftButtonPressEvent(self, obj, event):
        clickPos = self.GetInteractor().GetEventPosition()

        picker = vtkPropPicker()
        picker.Pick(clickPos[0], clickPos[1], 0, self.GetDefaultRenderer())

        # 선택된 액터 확인
        self.NewPickedActor = picker.GetActor()

        # 무언가 선택된 경우
        if self.NewPickedActor:
            # 이전에 선택된 액터가 있으면 속성 초기화
            if self.LastPickedActor:
                self.LastPickedActor.GetProperty().DeepCopy(self.LastPickedProperty)

            # 선택된 액터의 속성 저장
            self.LastPickedProperty.DeepCopy(self.NewPickedActor.GetProperty())

            # 선택된 액터 강조 표시
            self.NewPickedActor.GetProperty().SetColor(colors.GetColor3d("Red"))
            self.NewPickedActor.GetProperty().SetDiffuse(1.0)
            self.NewPickedActor.GetProperty().SetSpecular(0.0)
            self.NewPickedActor.GetProperty().EdgeVisibilityOn()

            # 액터 ID 찾기
            actor_id = None
            for key, actor in finger_actors.items():
                if actor == self.NewPickedActor:
                    actor_id = key
                    break

            # 해당 액터 ID가 있으면 회전 적용
            if actor_id and actor_id in finger_transforms:
                transform = finger_transforms[actor_id]

                # 회전 상태가 없으면 초기화
                if actor_id not in old_rotations:
                    old_rotations[actor_id] = 1

                # 회전 애니메이션 적용
                i = 0
                while i < 45:
                    transform.Identity()
                    # 엄지는 Z축 회전, 나머지 손가락은 X축 회전
                    if "thumb" in actor_id:
                        transform.RotateZ(-i * old_rotations[actor_id])
                    else:
                        transform.RotateX(-i * old_rotations[actor_id])
                    render_window.Render()
                    i += 1

                # 다음 회전 방향 반전
                old_rotations[actor_id] *= -1

            # 마지막 선택된 액터 저장
            self.LastPickedActor = self.NewPickedActor

        # 기본 왼쪽 버튼 다운 이벤트 처리
        self.OnLeftButtonDown()
        return


def create_quadric_visualization(colors):
    # Collection of all actors to return
    actors = []

    # Sample quadric function
    quadric = vtkQuadric()
    quadric.SetCoefficients(1, 2, 3, 0, 1, 0, 0, 0, 0, 0)

    sample = vtkSampleFunction()
    sample.SetSampleDimensions(25, 25, 25)
    sample.SetImplicitFunction(quadric)

    # Create isosurface
    isoActor = vtkActor()
    create_isosurface(sample, isoActor)
    actors.append(isoActor)

    outlineIsoActor = vtkActor()
    create_outline(sample, outlineIsoActor)
    actors.append(outlineIsoActor)

    # Create planes
    planesActor = vtkActor()
    create_planes(sample, planesActor, 3)
    planesActor.AddPosition(isoActor.GetBounds()[0] * 2.0, 0, 0)
    actors.append(planesActor)

    outlinePlanesActor = vtkActor()
    create_outline(sample, outlinePlanesActor)
    outlinePlanesActor.AddPosition(isoActor.GetBounds()[0] * 2.0, 0, 0)
    actors.append(outlinePlanesActor)

    # Create contours
    contourActor = vtkActor()
    create_contours(sample, contourActor, 3, 15)
    contourActor.AddPosition(isoActor.GetBounds()[0] * 4.0, 0, 0.8)
    actors.append(contourActor)

    outlineContourActor = vtkActor()
    create_outline(sample, outlineContourActor)
    outlineContourActor.AddPosition(isoActor.GetBounds()[0] * 4.0, 0, 0)
    actors.append(outlineContourActor)

    return actors


def create_isosurface(func, actor, numberOfContours=5):
    # Generate implicit surface
    contour = vtkContourFilter()
    contour.SetInputConnection(func.GetOutputPort())
    ranges = [1.0, 3.0]
    contour.GenerateValues(numberOfContours, ranges)

    # Map contour
    contourMapper = vtkPolyDataMapper()
    contourMapper.SetInputConnection(contour.GetOutputPort())
    contourMapper.SetScalarRange(0, 9)

    actor.SetMapper(contourMapper)
    return


def create_planes(func, actor, numberOfPlanes):
    # Extract planes from implicit function
    append = vtkAppendFilter()

    dims = func.GetSampleDimensions()
    sliceIncr = (dims[2] - 1) // (numberOfPlanes + 1)
    sliceNum = -4
    for i in range(0, numberOfPlanes):
        extract = vtkExtractVOI()
        extract.SetInputConnection(func.GetOutputPort())
        extract.SetVOI(
            0, dims[0] - 1, 0, dims[1] - 1, sliceNum + sliceIncr, sliceNum + sliceIncr
        )
        append.AddInputConnection(extract.GetOutputPort())
        sliceNum += sliceIncr
    append.Update()

    # Map planes
    planesMapper = vtkDataSetMapper()
    planesMapper.SetInputConnection(append.GetOutputPort())
    planesMapper.SetScalarRange(0, 4)

    actor.SetMapper(planesMapper)
    actor.GetProperty().SetAmbient(1.0)
    return


def create_contours(func, actor, numberOfPlanes, numberOfContours):
    # Extract planes from implicit function
    append = vtkAppendFilter()

    dims = func.GetSampleDimensions()
    sliceIncr = (dims[2] - 1) // (numberOfPlanes + 1)

    sliceNum = -4
    for i in range(0, numberOfPlanes):
        extract = vtkExtractVOI()
        extract.SetInputConnection(func.GetOutputPort())
        extract.SetVOI(
            0, dims[0] - 1, 0, dims[1] - 1, sliceNum + sliceIncr, sliceNum + sliceIncr
        )
        ranges = [1.0, 6.0]
        contour = vtkContourFilter()
        contour.SetInputConnection(extract.GetOutputPort())
        contour.GenerateValues(numberOfContours, ranges)
        append.AddInputConnection(contour.GetOutputPort())
        sliceNum += sliceIncr
    append.Update()

    # Map planes
    planesMapper = vtkDataSetMapper()
    planesMapper.SetInputConnection(append.GetOutputPort())
    planesMapper.SetScalarRange(0, 7)

    actor.SetMapper(planesMapper)
    actor.GetProperty().SetAmbient(1.0)
    return


def create_outline(source, actor):
    outline = vtkOutlineFilter()
    outline.SetInputConnection(source.GetOutputPort())
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(outline.GetOutputPort())
    actor.SetMapper(mapper)
    return


def create_hand_actors(colors):
    all_actors = []

    def create_palm():
        palm_source = vtkCubeSource()
        palm_source.SetXLength(6.0)
        palm_source.SetYLength(5.0)
        palm_source.SetZLength(1.0)
        palm_source.SetCenter(0.0, 0.0, 0.0)

        palm_mapper = vtkPolyDataMapper()
        palm_mapper.SetInputConnection(palm_source.GetOutputPort())

        palm_actor = vtkActor()
        palm_actor.SetMapper(palm_mapper)
        palm_actor.GetProperty().SetColor(colors.GetColor3d("Wheat"))
        palm_actor.RotateX(-10)

        return palm_actor

    def create_phalanx(x, y, z, length, width, height, angle_z=0, actor_id=None):
        phalanx_source = vtkCubeSource()
        phalanx_source.SetXLength(width)
        phalanx_source.SetYLength(length)
        phalanx_source.SetZLength(height)
        phalanx_source.SetCenter(0, length / 2 - 0.05, 0)

        phalanx_mapper = vtkPolyDataMapper()
        phalanx_mapper.SetInputConnection(phalanx_source.GetOutputPort())

        # 변환 객체 생성 (회전과 위치 지정을 위해)
        transform = vtk.vtkTransform()
        transform.PostMultiply()

        # 위치 설정
        transform.Translate(x, y, z)

        # Z축 회전 (엄지용)
        if angle_z != 0:
            transform.RotateZ(angle_z)

        # 변환 객체 저장
        if actor_id:
            finger_transforms[actor_id] = transform

        phalanx_actor = vtkActor()
        phalanx_actor.SetMapper(phalanx_mapper)
        phalanx_actor.SetUserTransform(transform)
        phalanx_actor.GetProperty().SetColor(colors.GetColor3d("Wheat"))
        phalanx_actor.GetProperty().SetSpecular(0.3)
        phalanx_actor.GetProperty().SetSpecularPower(20)

        # 액터 저장
        if actor_id:
            finger_actors[actor_id] = phalanx_actor

        return phalanx_actor

    palm_actor = create_palm()
    all_actors.append(palm_actor)

    # 엄지
    def create_thumb():
        thumb_actors = []
        start_x = -2.8
        start_y = 1.0
        start_z = 0.0
        angle_z = 120

        current_x, current_y, current_z = start_x, start_y, start_z
        length = 1.4
        width = 1.2
        height = 0.8
        angle_rad = math.radians(angle_z)
        dx = length * math.cos(angle_rad)
        dy = length * math.sin(angle_rad)

        phalanx1 = create_phalanx(
            current_x,
            current_y,
            current_z,
            length,
            width,
            height,
            angle_z,
            "thumb_phalanx1",
        )
        thumb_actors.append(phalanx1)

        current_x += dx
        current_y += dy

        length = 1.2
        width = 1.1
        height = 0.7
        phalanx2 = create_phalanx(
            current_x,
            current_y,
            current_z,
            length,
            width,
            height,
            angle_z,
            "thumb_phalanx2",
        )
        thumb_actors.append(phalanx2)

        current_x += dx * (length / 1.4)
        current_y += dy * (length / 1.4)

        length = 1.0
        width = 1.0
        height = 0.6
        phalanx3 = create_phalanx(
            current_x,
            current_y,
            current_z,
            length,
            width,
            height,
            angle_z,
            "thumb_phalanx3",
        )
        thumb_actors.append(phalanx3)

        return thumb_actors

    # 검지
    def create_index_finger():
        finger_actors = []
        start_x, start_y, start_z = -1.8, 2.5, 0.0

        length = 1.6
        width = 1.0
        height = 0.7
        phalanx1 = create_phalanx(
            start_x, start_y, start_z, length, width, height, 0, "index_phalanx1"
        )
        finger_actors.append(phalanx1)

        current_y = start_y + length

        length = 1.4
        width = 0.9
        height = 0.7
        phalanx2 = create_phalanx(
            start_x, current_y, start_z, length, width, height, 0, "index_phalanx2"
        )
        finger_actors.append(phalanx2)

        current_y += length

        length = 1.2
        width = 0.8
        height = 0.6
        phalanx3 = create_phalanx(
            start_x, current_y, start_z, length, width, height, 0, "index_phalanx3"
        )
        finger_actors.append(phalanx3)

        return finger_actors

    # 중지
    def create_middle_finger():
        finger_actors = []
        start_x, start_y, start_z = -0.3, 2.5, 0.0

        length = 1.8
        width = 1.0
        height = 0.7
        phalanx1 = create_phalanx(
            start_x, start_y, start_z, length, width, height, 0, "middle_phalanx1"
        )
        finger_actors.append(phalanx1)

        current_y = start_y + length

        length = 1.6
        width = 0.9
        height = 0.7
        phalanx2 = create_phalanx(
            start_x, current_y, start_z, length, width, height, 0, "middle_phalanx2"
        )
        finger_actors.append(phalanx2)

        current_y += length

        length = 1.3
        width = 0.8
        height = 0.6
        phalanx3 = create_phalanx(
            start_x, current_y, start_z, length, width, height, 0, "middle_phalanx3"
        )
        finger_actors.append(phalanx3)

        return finger_actors

    # 약지
    def create_ring_finger():
        finger_actors = []
        start_x, start_y, start_z = 1.2, 2.5, 0.0

        length = 1.7
        width = 1.0
        height = 0.7
        phalanx1 = create_phalanx(
            start_x, start_y, start_z, length, width, height, 0, "ring_phalanx1"
        )
        finger_actors.append(phalanx1)

        current_y = start_y + length

        length = 1.5
        width = 0.9
        height = 0.7
        phalanx2 = create_phalanx(
            start_x, current_y, start_z, length, width, height, 0, "ring_phalanx2"
        )
        finger_actors.append(phalanx2)

        current_y += length

        length = 1.3
        width = 0.8
        height = 0.6
        phalanx3 = create_phalanx(
            start_x, current_y, start_z, length, width, height, 0, "ring_phalanx3"
        )
        finger_actors.append(phalanx3)

        return finger_actors

    # 소지
    def create_pinky_finger():
        finger_actors = []
        start_x, start_y, start_z = 2.5, 2.2, 0.0

        length = 1.4
        width = 0.8
        height = 0.6
        phalanx1 = create_phalanx(
            start_x, start_y, start_z, length, width, height, 0, "pinky_phalanx1"
        )
        finger_actors.append(phalanx1)

        current_y = start_y + length

        length = 1.2
        width = 0.7
        height = 0.6
        phalanx2 = create_phalanx(
            start_x, current_y, start_z, length, width, height, 0, "pinky_phalanx2"
        )
        finger_actors.append(phalanx2)

        current_y += length

        length = 1.0
        width = 0.6
        height = 0.5
        phalanx3 = create_phalanx(
            start_x, current_y, start_z, length, width, height, 0, "pinky_phalanx3"
        )
        finger_actors.append(phalanx3)

        return finger_actors

    all_actors.extend(create_thumb())
    all_actors.extend(create_index_finger())
    all_actors.extend(create_middle_finger())
    all_actors.extend(create_ring_finger())
    all_actors.extend(create_pinky_finger())

    return all_actors


def main():
    global render_window
    colors = vtkNamedColors()

    # Create render window and interactor
    render_window = vtkRenderWindow()
    render_window.SetSize(1200, 600)
    render_window.SetWindowName("Interactive Hand with Quadric Visualization")

    interactor = vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)

    # Left renderer: Quadric Visualization
    ren_left = vtkRenderer()
    ren_left.SetViewport(0.0, 0.0, 0.5, 1.0)
    ren_left.SetBackground(colors.GetColor3d("SlateGray"))

    # Get all actors from quadric visualization
    quadric_actors = create_quadric_visualization(colors)
    for actor in quadric_actors:
        ren_left.AddActor(actor)

    # Right renderer: Hand
    ren_right = vtkRenderer()
    ren_right.SetViewport(0.5, 0.0, 1.0, 1.0)
    ren_right.SetBackground(colors.GetColor3d("DarkSlateGray"))
    hand_actors = create_hand_actors(colors)
    for actor in hand_actors:
        ren_right.AddActor(actor)

    # Camera setup for left viewport (quadric visualization)
    cam_left = ren_left.GetActiveCamera()
    cam_left.SetPosition(0, -40, 30)
    cam_left.SetFocalPoint(0, 0, 0)
    cam_left.Azimuth(30)
    cam_left.Elevation(20)
    ren_left.ResetCamera()

    # Camera setup for right viewport (hand)
    cam_right = ren_right.GetActiveCamera()
    cam_right.SetPosition(0, -5, 20)
    cam_right.SetFocalPoint(0, 0, 0)
    cam_right.SetViewUp(0, 1, 0)
    cam_right.Elevation(20)
    ren_right.ResetCamera()

    # Add renderers to window
    render_window.AddRenderer(ren_left)
    render_window.AddRenderer(ren_right)

    # 상호작용 스타일 설정
    style = MouseInteractorHighLightActor()
    style.SetDefaultRenderer(ren_right)  # 오른쪽 뷰포트에서만 마우스 상호작용 활성화
    interactor.SetInteractorStyle(style)

    # Enable two-sided lighting for better visualization
    ren_left.TwoSidedLightingOn()

    render_window.Render()
    interactor.Initialize()
    interactor.Start()


if __name__ == "__main__":
    main()
