import math
import vtk
import time
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
)
from vtkmodules.vtkFiltersSources import vtkCubeSource, vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera

# 전역 변수 설정
colors = vtkNamedColors()
finger_transforms = {}  # 각 손가락 마디의 변환 객체 저장
finger_actors = {}  # 각 손가락 마디의 액터 저장
render_window = None  # 렌더윈도우 전역 참조
interactor = None  # 인터랙터 전역 참조
joint_actors = []  # 손가락 관절 액터 저장 리스트


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


# 관절 생성 함수
def create_joint(radius=0.025, color=(0.1, 0.9, 0.2), transform=None):
    source = vtk.vtkSphereSource()
    source.SetRadius(radius)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    if transform:
        actor.SetUserTransform(transform)
    actor.GetProperty().SetColor(color)
    return actor, source, transform


# 마디 생성 함수
def create_phalanx(
    width=0.15, height=0.2, depth=0.1, color=(0.8, 0.7, 0.6), transform=None
):
    source = vtk.vtkCubeSource()
    source.SetXLength(width)
    source.SetYLength(height)
    source.SetZLength(depth)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    if transform:
        actor.SetUserTransform(transform)
    actor.GetProperty().SetColor(color)
    return actor, source, transform


# 손바닥 생성 함수
def create_palm(
    width=0.8, height=0.6, depth=0.15, color=(0.8, 0.7, 0.6), transform=None
):
    source = vtk.vtkCubeSource()
    source.SetXLength(width)
    source.SetYLength(height)
    source.SetZLength(depth)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    if transform:
        actor.SetUserTransform(transform)
    actor.GetProperty().SetColor(color)
    return actor, source, transform


# transform 함수
def transform(
    transformation,
    translate=(0.0, 0.0, 0.0),
    rotate=(0.0, 0.0, 0.0),
    scale=(1.0, 1.0, 1.0),
):
    transformation.Translate(translate)
    transformation.RotateZ(rotate[2])
    transformation.RotateY(rotate[1])
    transformation.RotateX(rotate[0])
    transformation.Scale(scale)
    return transformation


# 인터랙터 스타일 클래스 - 액터 선택 및 회전 기능 (hand.py에서 가져옴)
class MouseInteractorHighLightActor(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(
        self, parent=None, renderer=None, render_window=None, joint_transforms=None
    ):
        self.AddObserver("LeftButtonPressEvent", self.leftButtonPressEvent)
        self.LastPickedActor = None
        self.LastPickedProperty = vtk.vtkProperty()
        self.renderer = renderer
        self.render_window = render_window
        self.joint_transforms = joint_transforms  # 관절 transform 저장
        self.original_colors = {}  # 원래 색상 저장

        # 각 관절의 상태를 저장하는 딕셔너리 추가
        self.joint_state = {}  # (finger_idx, joint_idx): bent(True) or straight(False)

    def leftButtonPressEvent(self, obj, event):
        clickPos = self.GetInteractor().GetEventPosition()
        picker = vtk.vtkPropPicker()
        picker.Pick(clickPos[0], clickPos[1], 0, self.renderer)

        # 선택된 액터 가져오기
        self.NewPickedActor = picker.GetActor()

        # 이전에 선택된 액터가 있다면 원래 색상으로 복원
        if self.LastPickedActor:
            if self.LastPickedActor in self.original_colors:
                self.LastPickedActor.GetProperty().SetColor(
                    self.original_colors[self.LastPickedActor]
                )
            else:
                self.LastPickedActor.GetProperty().DeepCopy(self.LastPickedProperty)

        # 새로 선택된 액터가 있다면
        if self.NewPickedActor:
            # 현재 색상 저장
            current_color = [0, 0, 0]
            self.NewPickedActor.GetProperty().GetColor(current_color)
            self.original_colors[self.NewPickedActor] = current_color

            # 액터 강조 표시 (빨간색)
            self.NewPickedProperty = vtk.vtkProperty()
            self.NewPickedProperty.DeepCopy(self.NewPickedActor.GetProperty())
            self.NewPickedActor.GetProperty().SetColor(1.0, 0.0, 0.0)  # 빨간색

            # 선택된 액터에 해당하는 관절 찾기
            found_joint = False
            for finger_idx, finger_joints in enumerate(self.joint_transforms):
                for joint_idx, joint_transform in enumerate(finger_joints):
                    # 관절의 액터 리스트와 비교
                    for j, (actor, transform) in enumerate(
                        joint_actors[finger_idx][joint_idx]
                    ):
                        if self.NewPickedActor == actor:
                            # 관절 회전 애니메이션
                            self.rotateJoint(finger_idx, joint_idx)
                            found_joint = True
                            break
                    if found_joint:
                        break
                if found_joint:
                    break

            # 마지막으로 선택된 액터 업데이트
            self.LastPickedActor = self.NewPickedActor

        self.OnLeftButtonDown()
        return

    def rotateJoint(self, finger_idx, joint_idx):
        """선택된 관절을 클릭에 따라 굽히거나 펴는 함수"""
        # 관절 상태 키
        joint_key = (finger_idx, joint_idx)

        # 현재 관절이 굽혀져 있는지 펴져 있는지 확인 (기본값은 펴져 있음)
        is_bent = self.joint_state.get(joint_key, False)

        # 회전 각도 설정
        max_angle = 45

        # 엄지와 다른 손가락에 대한 처리를 구분
        if not is_bent:  # 관절이 펴져 있으면 굽힌다
            # 관절 굽히기
            if finger_idx == 0:  # 엄지 손가락
                # 엄지는 다른 손가락 방향으로 구부리기 위해 Z축 회전
                for angle in range(0, max_angle, 5):
                    if joint_idx == 0:  # 엄지의 첫 번째 관절
                        transform(
                            self.joint_transforms[finger_idx][joint_idx],
                            rotate=(0, 0, 5),
                        )
                    else:  # 엄지의 다른 관절
                        transform(
                            self.joint_transforms[finger_idx][joint_idx],
                            rotate=(5, 0, 0),
                        )
                    self.render_window.Render()
                    time.sleep(0.03)
            else:  # 다른 손가락들
                # 일반적인 X축 회전
                for angle in range(0, max_angle, 5):
                    transform(
                        self.joint_transforms[finger_idx][joint_idx], rotate=(5, 0, 0)
                    )
                    self.render_window.Render()
                    time.sleep(0.03)

            # 상태 업데이트 - 굽혀짐
            self.joint_state[joint_key] = True
        else:  # 관절이 굽혀져 있으면 편다
            # 관절 펴기
            if finger_idx == 0:  # 엄지 손가락
                # 엄지 펴기
                for angle in range(0, max_angle, 5):
                    if joint_idx == 0:  # 엄지의 첫 번째 관절
                        transform(
                            self.joint_transforms[finger_idx][joint_idx],
                            rotate=(0, 0, -5),
                        )
                    else:  # 엄지의 다른 관절
                        transform(
                            self.joint_transforms[finger_idx][joint_idx],
                            rotate=(-5, 0, 0),
                        )
                    self.render_window.Render()
                    time.sleep(0.03)
            else:  # 다른 손가락들
                # 일반적인 X축 회전
                for angle in range(0, max_angle, 5):
                    transform(
                        self.joint_transforms[finger_idx][joint_idx], rotate=(-5, 0, 0)
                    )
                    self.render_window.Render()
                    time.sleep(0.03)

            # 상태 업데이트 - 펴짐
            self.joint_state[joint_key] = False


def create_hand_actors():
    global joint_actors

    all_actors = []

    # 손바닥 생성
    palm_transform = vtk.vtkTransform()
    palm_actor, palm_source, _ = create_palm(transform=palm_transform)
    all_actors.append(palm_actor)

    # 손가락 위치 및 각도 - 엄지가 바깥을 향하도록 수정
    finger_positions = [
        # 엄지 위치
        {"pos": (-0.4, 0.05, -0.0), "angle": (0, -20, 30)},
        # 검지 위치
        {"pos": (-0.25, 0.31, 0.0), "angle": (0, 0, 0)},
        # 중지 위치
        {"pos": (-0.06, 0.31, 0.0), "angle": (0, 0, 0)},
        # 약지 위치
        {"pos": (0.12, 0.31, 0.0), "angle": (0, 0, 0)},
        # 소지 위치
        {"pos": (0.3, 0.31, 0.0), "angle": (0, 0, 0)},
    ]

    # 관절 반지름
    joint_radius = 0.02

    # 변환 객체 및 액터 저장 리스트
    joint_transforms = []
    joint_actors = []

    # 각 손가락 생성
    for finger_idx, finger_pos in enumerate(finger_positions):
        finger_joints = []  # 각 손가락의 관절 변환 저장
        finger_actors = []  # 각 손가락의 액터 저장

        # 첫 번째 관절 생성
        joint0_transform = vtk.vtkTransform()
        joint0_transform.SetInput(palm_transform)
        transform(
            joint0_transform, translate=finger_pos["pos"], rotate=finger_pos["angle"]
        )
        joint0_actor, joint0_source, _ = create_joint(
            radius=joint_radius, transform=joint0_transform
        )
        all_actors.append(joint0_actor)
        finger_joints.append(joint0_transform)
        finger_actors.append([(joint0_actor, joint0_transform)])

        # 첫 번째 마디 생성
        height1 = 0.15 if finger_idx == 0 else 0.18
        width1 = 0.12
        phalanx1_transform = vtk.vtkTransform()
        phalanx1_transform.SetInput(joint0_transform)
        offset = joint_radius + height1 / 2 - 0.002
        transform(phalanx1_transform, translate=(0.0, offset, 0.0))
        phalanx1_actor, phalanx1_source, _ = create_phalanx(
            width=width1, height=height1, transform=phalanx1_transform
        )
        all_actors.append(phalanx1_actor)
        finger_actors[0].append((phalanx1_actor, phalanx1_transform))

        # 두 번째 관절 생성
        joint1_transform = vtk.vtkTransform()
        joint1_transform.SetInput(phalanx1_transform)
        offset = height1 / 2 + joint_radius - 0.002
        transform(joint1_transform, translate=(0.0, offset, 0.0))
        joint1_actor, joint1_source, _ = create_joint(
            radius=joint_radius, transform=joint1_transform
        )
        all_actors.append(joint1_actor)
        finger_joints.append(joint1_transform)
        finger_actors.append([(joint1_actor, joint1_transform)])

        # 두 번째 마디 생성
        height2 = 0.12 if finger_idx == 0 else 0.15
        width2 = 0.11
        phalanx2_transform = vtk.vtkTransform()
        phalanx2_transform.SetInput(joint1_transform)
        offset = joint_radius + height2 / 2 - 0.002
        transform(phalanx2_transform, translate=(0.0, offset, 0.0))
        phalanx2_actor, phalanx2_source, _ = create_phalanx(
            width=width2, height=height2, transform=phalanx2_transform
        )
        all_actors.append(phalanx2_actor)
        finger_actors[1].append((phalanx2_actor, phalanx2_transform))

        # 세 번째 관절 생성
        joint2_transform = vtk.vtkTransform()
        joint2_transform.SetInput(phalanx2_transform)
        offset = height2 / 2 + joint_radius - 0.002
        transform(joint2_transform, translate=(0.0, offset, 0.0))
        joint2_actor, joint2_source, _ = create_joint(
            radius=joint_radius, transform=joint2_transform
        )
        all_actors.append(joint2_actor)
        finger_joints.append(joint2_transform)
        finger_actors.append([(joint2_actor, joint2_transform)])

        # 세 번째 마디 생성
        height3 = 0.1 if finger_idx == 0 else 0.12
        width3 = 0.1
        phalanx3_transform = vtk.vtkTransform()
        phalanx3_transform.SetInput(joint2_transform)
        offset = joint_radius + height3 / 2 - 0.002
        transform(phalanx3_transform, translate=(0.0, offset, 0.0))
        phalanx3_actor, phalanx3_source, _ = create_phalanx(
            height=height3, width=width3, transform=phalanx3_transform
        )
        all_actors.append(phalanx3_actor)
        finger_actors[2].append((phalanx3_actor, phalanx3_transform))

        # 변환 객체와 액터 리스트에 저장
        joint_transforms.append(finger_joints)
        joint_actors.append(finger_actors)

    return all_actors, joint_transforms


# 손가락 애니메이션 함수 - 필요시 사용 가능
def animate_fingers(joint_transforms, render_window):
    # 모든 손가락을 동시에 구부리기
    max_angles = [20, 30, 40]  # 각 관절마다 다른 최대 각도

    # 구부리기
    for angle in range(0, 40, 5):
        for finger_idx, finger_joints in enumerate(joint_transforms):
            for joint_idx, joint_transform in enumerate(finger_joints):
                # 현재 관절의 최대 각도까지만 회전
                current_max = max_angles[joint_idx]
                if angle <= current_max:
                    transform(joint_transform, rotate=(5, 0, 0))

        render_window.Render()
        time.sleep(0.03)  # 약간 더 빠른 애니메이션

    # 잠시 구부린 상태 유지
    time.sleep(0.5)

    # 모든 손가락을 동시에 펴기
    for angle in range(0, 40, 5):
        for finger_idx, finger_joints in enumerate(joint_transforms):
            for joint_idx, joint_transform in enumerate(finger_joints):
                # 현재 관절의 최대 각도까지만 회전
                current_max = max_angles[joint_idx]
                if angle <= current_max:
                    transform(joint_transform, rotate=(-5, 0, 0))

        render_window.Render()
        time.sleep(0.03)


# 타이머 콜백 함수 - 자동 애니메이션 비활성화
def timer_callback(obj, event):
    # 자동 애니메이션 비활성화
    pass


def main():
    global render_window, interactor, hand_joint_transforms
    colors = vtkNamedColors()

    # Create render window and interactor
    render_window = vtkRenderWindow()
    render_window.SetSize(1200, 600)
    render_window.SetWindowName("Hand with All Five Fingers Animation")

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

    # 손 액터와 관절 변환 객체 생성
    hand_actors, hand_joint_transforms = create_hand_actors()
    for actor in hand_actors:
        ren_right.AddActor(actor)

    # 커스텀 인터랙터 스타일 설정 (액터 선택 및 회전 기능)
    style = MouseInteractorHighLightActor(
        renderer=ren_right,
        render_window=render_window,
        joint_transforms=hand_joint_transforms,
    )
    style.SetDefaultRenderer(ren_right)
    interactor.SetInteractorStyle(style)

    # Camera setup for left viewport (quadric visualization)
    cam_left = ren_left.GetActiveCamera()
    cam_left.SetPosition(0, -40, 30)
    cam_left.SetFocalPoint(0, 0, 0)
    cam_left.Azimuth(30)
    cam_left.Elevation(20)
    ren_left.ResetCamera()

    # Camera setup for right viewport (hand)
    cam_right = ren_right.GetActiveCamera()
    cam_right.SetPosition(0, 0, 3)
    cam_right.SetFocalPoint(0, 0.5, 0)
    cam_right.SetViewUp(0, 1, 0)
    ren_right.ResetCamera()

    # Add renderers to window
    render_window.AddRenderer(ren_left)
    render_window.AddRenderer(ren_right)

    # Enable two-sided lighting for better visualization
    ren_left.TwoSidedLightingOn()
    ren_right.TwoSidedLightingOn()

    # 타이머 콜백 추가 (자동 애니메이션 비활성화를 위해 주석 처리)
    # interactor.AddObserver("TimerEvent", timer_callback)

    render_window.Render()
    interactor.Initialize()

    # 애니메이션 자동 시작 비활성화
    # interactor.CreateOneShotTimer(1000)  # 1초 후 애니메이션 시작

    interactor.Start()


if __name__ == "__main__":
    main()
