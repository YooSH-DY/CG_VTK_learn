# 웹소켓 클라이언트 모듈 import
import websocket_client

websocket_client.start_websocket_client_thread()

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
hand_joint_transforms = []  # 손가락 관절 트랜스폼 글로벌 참조


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
        super().__init__()
        # 클릭 이벤트
        self.AddObserver("LeftButtonPressEvent", self.leftButtonPressEvent)
        # 키 이벤트 (숫자키 처리)
        self.AddObserver("KeyPressEvent", self.on_key_press)

        self.LastPickedActor = None
        self.LastPickedProperty = vtk.vtkProperty()
        self.renderer = renderer
        self.render_window = render_window
        self.joint_transforms = joint_transforms  # 관절 transform 저장
        self.original_colors = {}  # 원래 액터 색상 저장

        # (finger_idx, joint_idx) → bent 여부 저장
        self.joint_state = {}

    def leftButtonPressEvent(self, obj, event):
        clickPos = self.GetInteractor().GetEventPosition()
        picker = vtk.vtkPropPicker()
        picker.Pick(clickPos[0], clickPos[1], 0, self.renderer)

        self.NewPickedActor = picker.GetActor()

        # 이전 선택 복원
        if self.LastPickedActor:
            if self.LastPickedActor in self.original_colors:
                self.LastPickedActor.GetProperty().SetColor(
                    self.original_colors[self.LastPickedActor]
                )
            else:
                self.LastPickedActor.GetProperty().DeepCopy(self.LastPickedProperty)

        # 새 선택된 액터 강조 및 회전 처리
        if self.NewPickedActor:
            # 원래 색상 저장
            curr = [0, 0, 0]
            self.NewPickedActor.GetProperty().GetColor(curr)
            self.original_colors[self.NewPickedActor] = curr

            self.NewPickedProperty = vtk.vtkProperty()
            self.NewPickedProperty.DeepCopy(self.NewPickedActor.GetProperty())
            self.NewPickedActor.GetProperty().SetColor(1.0, 0.0, 0.0)

            # 관절 찾고 회전
            found = False
            for f_idx, finger_j in enumerate(self.joint_transforms):
                for j_idx, joint_tf in enumerate(finger_j):
                    for actor, tf in joint_actors[f_idx][j_idx]:
                        if self.NewPickedActor == actor:
                            self.rotateJoint(f_idx, j_idx)
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

            self.LastPickedActor = self.NewPickedActor

        # 원래 LeftButtonDown 흐름 유지
        self.OnLeftButtonDown()
        return

    def rotateJoint(self, finger_idx, joint_idx):
        """클릭 시 관절을 굽혔다 폈다 토글"""
        key = (finger_idx, joint_idx)
        is_bent = self.joint_state.get(key, False)
        max_angle = 80

        # 굽힘 또는 폄 방향 선택
        delta = 5 if not is_bent else -5

        # 엄지와 기타 손가락 분리
        axis = (delta, 0, 0)
        if finger_idx == 0 and joint_idx == 0:
            axis = (delta, 0, 0)  # 필요시 Z축 등 조정

        # 애니메이션
        for _ in range(0, max_angle, abs(delta)):
            transform(
                self.joint_transforms[finger_idx][joint_idx],
                rotate=axis,
            )
            self.render_window.Render()
            time.sleep(0.03)

        self.joint_state[key] = not is_bent

    def on_key_press(self, obj, event):
        """숫자키 4~7로 제어 손가락 변경"""
        key = self.GetInteractor().GetKeySym()
        mapping = {
            "4": [1],  # 검지
            "5": [2],  # 중지
            "6": [1, 2],  # 검지+중지
            "7": [0, 1, 2, 3, 4],  # 모두
        }
        if key in mapping:
            websocket_client.select_fingers(*mapping[key])
            print(f"키 {key} 입력됨 → 제어 손가락: {websocket_client.selected_fingers}")
            return  # VTK 기본 '3' 모드 전환 핸들러를 막기 위해 이벤트 소모

        # 기본 키 이벤트 처리
        super().OnKeyPress()


def create_hand_actors():
    global joint_actors, palm_transform  # palm_transform을 전역으로 추가

    all_actors = []

    # 손바닥 생성
    palm_transform = vtk.vtkTransform()
    palm_actor, palm_source, _ = create_palm(transform=palm_transform)
    all_actors.append(palm_actor)

    # 손가락 위치 및 각도 - 엄지가 바깥을 향하도록 수정
    finger_positions = [
        # 엄지 위치
        {"pos": (0.4, 0.05, -0.0), "angle": (0, 20, -30)},  # 각도도 반전
        # 검지 위치
        {"pos": (0.25, 0.31, 0.0), "angle": (0, 0, 0)},
        # 중지 위치
        {"pos": (0.06, 0.31, 0.0), "angle": (0, 0, 0)},
        # 약지 위치
        {"pos": (-0.12, 0.31, 0.0), "angle": (0, 0, 0)},
        # 소지 위치
        {"pos": (-0.3, 0.31, 0.0), "angle": (0, 0, 0)},
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


# 타이머 콜백 함수 - DOT2 센서의 Roll 값에 따라 손가락 관절 제어
def timer_callback(obj, event):
    global hand_joint_transforms, render_window, joint_actors, palm_transform

    # 연결 상태 확인 (last_data_time 사용)
    current_time = time.time()
    last_data_time = getattr(websocket_client, "last_data_time", 0)

    # DOT1 센서 Roll 값으로 손바닥 제어
    roll_value_dot1 = websocket_client.dot_data["DOT1"]["roll"]

    # 기본 자세는 수직(90도)
    palm_angle = 90

    # Roll 값의 부호에 따라 처리 - 방향 반전
    if roll_value_dot1 < 0:  # 음수일 때 - 뒤로 꺾임 (90도에서 최대 40도까지)
        # roll 값이 -80에 가까울수록 더 많이 꺾임
        max_backward_bend = 40  # 최대 뒤로 40도
        backward_bend = min(max_backward_bend, abs(roll_value_dot1) * (40 / 80))
        palm_angle = 90 - backward_bend  # 90도(수직)에서 최소 50도까지
    else:  # 양수일 때 - 앞으로 꺾임 (최대 90도)
        max_forward_bend = 90  # 최대 앞으로 90도
        forward_bend = min(max_forward_bend, roll_value_dot1 * (90 / 80))
        palm_angle = 90 + forward_bend  # 90도(수직)에서 최대 180도까지

    # 손바닥 변환 초기화 및 회전 적용
    palm_transform.Identity()
    # X축 회전으로 손바닥을 앞뒤로 꺾음
    transform(palm_transform, rotate=(palm_angle, 0, 0))

    # DOT2 센서 Roll 값으로 손가락 제어 (기존 코드)
    roll_value_dot2 = websocket_client.dot_data["DOT2"]["roll"]
    normalized_roll_dot2 = websocket_client.get_normalized_roll(roll_value_dot2)
    target_angle = -normalized_roll_dot2

    # 손가락 위치 정보 (create_hand_actors 함수의 값과 동일하게 설정)
    finger_positions = [
        # 엄지 위치
        {"pos": (0.4, 0.05, -0.0), "angle": (0, 20, -30)},  # 각도도 반전
        # 검지 위치
        {"pos": (0.25, 0.31, 0.0), "angle": (0, 0, 0)},
        # 중지 위치
        {"pos": (0.06, 0.31, 0.0), "angle": (0, 0, 0)},
        # 약지 위치
        {"pos": (-0.12, 0.31, 0.0), "angle": (0, 0, 0)},
        # 소지 위치
        {"pos": (-0.3, 0.31, 0.0), "angle": (0, 0, 0)},
    ]

    # 선택된 손가락만 제어 (웹소켓 모듈에서 지정된 손가락들)
    for finger_idx in websocket_client.selected_fingers:
        if finger_idx < len(hand_joint_transforms):
            # 첫 번째 관절(뿌리 관절) 위치 복원 및 회전 적용
            joint0_transform = hand_joint_transforms[finger_idx][0]
            joint0_transform.Identity()
            transform(
                joint0_transform,
                translate=finger_positions[finger_idx]["pos"],
                rotate=finger_positions[finger_idx]["angle"],
            )
            # 첫 번째 관절에 회전 적용 - 모든 관절에 동일한 각도 적용
            transform(joint0_transform, rotate=(target_angle, 0, 0))

            # 관절 반지름 (원래 크기에 맞춤)
            joint_radius = 0.02

            # 첫 번째 마디는 첫 번째 관절에 연결
            if len(joint_actors[finger_idx][0]) > 1:
                phalanx1_actor, phalanx1_transform = joint_actors[finger_idx][0][1]
                height1 = 0.15 if finger_idx == 0 else 0.18  # 엄지는 다른 길이
                offset1 = joint_radius + height1 / 2 - 0.002

                # 마디1의 변환 초기화 및 위치 설정
                phalanx1_transform.Identity()
                phalanx1_transform.SetInput(joint0_transform)
                transform(phalanx1_transform, translate=(0.0, offset1, 0.0))

            # 두 번째 관절 (첫 번째 마디에 연결)
            if len(hand_joint_transforms[finger_idx]) > 1:
                joint1_transform = hand_joint_transforms[finger_idx][1]
                joint1_transform.Identity()
                joint1_transform.SetInput(phalanx1_transform)
                height1 = 0.15 if finger_idx == 0 else 0.18
                offset = height1 / 2 + joint_radius - 0.002
                transform(joint1_transform, translate=(0.0, offset, 0.0))
                # 두 번째 관절에도 동일한 각도 적용
                transform(joint1_transform, rotate=(target_angle, 0, 0))

                # 두 번째 마디는 두 번째 관절에 연결
                if len(joint_actors[finger_idx][1]) > 1:
                    phalanx2_actor, phalanx2_transform = joint_actors[finger_idx][1][1]
                    height2 = 0.12 if finger_idx == 0 else 0.15
                    offset2 = joint_radius + height2 / 2 - 0.002

                    # 마디2의 변환 초기화 및 위치 설정
                    phalanx2_transform.Identity()
                    phalanx2_transform.SetInput(joint1_transform)
                    transform(phalanx2_transform, translate=(0.0, offset2, 0.0))

                # 세 번째 관절 (두 번째 마디에 연결)
                if len(hand_joint_transforms[finger_idx]) > 2:
                    joint2_transform = hand_joint_transforms[finger_idx][2]
                    joint2_transform.Identity()
                    joint2_transform.SetInput(phalanx2_transform)
                    height2 = 0.12 if finger_idx == 0 else 0.15
                    offset = height2 / 2 + joint_radius - 0.002
                    transform(joint2_transform, translate=(0.0, offset, 0.0))
                    # 세 번째 관절에도 동일한 각도 적용
                    transform(joint2_transform, rotate=(target_angle, 0, 0))

                    # 세 번째 마디는 세 번째 관절에 연결
                    if len(joint_actors[finger_idx][2]) > 1:
                        phalanx3_actor, phalanx3_transform = joint_actors[finger_idx][
                            2
                        ][1]
                        height3 = 0.1 if finger_idx == 0 else 0.12
                        offset3 = joint_radius + height3 / 2 - 0.002

                        # 마디3의 변환 초기화 및 위치 설정
                        phalanx3_transform.Identity()
                        phalanx3_transform.SetInput(joint2_transform)
                        transform(phalanx3_transform, translate=(0.0, offset3, 0.0))

    # 화면 갱신
    render_window.Render()


def main():
    global render_window, interactor, hand_joint_transforms
    colors = vtkNamedColors()

    # Create render window and interactor
    render_window = vtkRenderWindow()
    render_window.SetSize(1200, 600)
    render_window.SetWindowName("Hand Animation with DOT Sensor")

    interactor = vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)

    # 웹소켓 클라이언트 시작 (DOT 센서 데이터 수신 시작)

    # 제어할 손가락 선택 (선택적으로 수정 가능)
    websocket_client.select_fingers(1)  # 기본: 검지, 중지, 약지 제어

    # Right renderer: Hand (전체 창 사용)
    ren_right = vtkRenderer()
    ren_right.SetViewport(0.0, 0.0, 1.0, 1.0)
    ren_right.SetBackground(colors.GetColor3d("DarkSlateGray"))

    # 손 액터와 관절 변환 객체 생성
    hand_actors, hand_joint_transforms = create_hand_actors()
    for actor in hand_actors:
        ren_right.AddActor(actor)

    # 커스텀 인터랙터 스타일 설정
    style = MouseInteractorHighLightActor(
        renderer=ren_right,
        render_window=render_window,
        joint_transforms=hand_joint_transforms,
    )
    style.SetDefaultRenderer(ren_right)
    interactor.SetInteractorStyle(style)

    # Camera setup for hand viewport
    cam_right = ren_right.GetActiveCamera()
    cam_right.SetPosition(0, 4, 0)
    cam_right.SetFocalPoint(0, -2, 0)
    cam_right.SetViewUp(0, 0, 1)
    ren_right.ResetCameraClippingRange()
    # cam_right.Zoom(0.8)  # 추가 축소를 위한 줌 아웃 (1보다 작은 값)

    # Add only hand renderer
    render_window.AddRenderer(ren_right)

    ren_right.TwoSidedLightingOn()

    # 타이머 콜백 설정 (30ms마다 실행 - 약 33fps)
    interactor.AddObserver("TimerEvent", timer_callback)
    interactor.CreateRepeatingTimer(20)

    print("프로그램 시작: DOT2 센서의 Roll 값에 따라 손가락 움직임이 제어됩니다.")
    print(
        f"제어 중인 손가락: {websocket_client.selected_fingers} (0:엄지, 1:검지, 2:중지, 3:약지, 4:소지)"
    )

    render_window.Render()
    interactor.Initialize()
    interactor.Start()


if __name__ == "__main__":
    main()
