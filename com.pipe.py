# 웹소켓 클라이언트 모듈 import
import websocket_client

websocket_client.start_websocket_client_thread()

import math
import vtk
import time
import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingOpenGL2


# 쿼터니언 관련 유틸리티 함수 추가
def quaternion_to_euler(w, x, y, z):
    """쿼터니언(w, x, y, z)을 오일러 각도(도)로 변환"""
    # Roll (x축 회전)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (y축 회전)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)  # 범위를 벗어나면 90도 사용
    else:
        pitch = math.asin(sinp)

    # Yaw (z축 회전)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    # 라디안에서 도(degree)로 변환
    roll = math.degrees(roll)
    pitch = math.degrees(pitch)
    yaw = math.degrees(yaw)

    return roll, pitch, yaw


def quaternion_to_matrix(w, x, y, z):
    """쿼터니언을 VTK 행렬로 변환"""
    matrix = vtk.vtkMatrix4x4()

    # 쿼터니언에서 행렬 요소 계산
    xx = x * x
    xy = x * y
    xz = x * z
    xw = x * w

    yy = y * y
    yz = y * z
    yw = y * w

    zz = z * z
    zw = z * w

    # 회전 행렬 설정 (3x3 부분)
    matrix.SetElement(0, 0, 1 - 2 * (yy + zz))
    matrix.SetElement(0, 1, 2 * (xy - zw))
    matrix.SetElement(0, 2, 2 * (xz + yw))

    matrix.SetElement(1, 0, 2 * (xy + zw))
    matrix.SetElement(1, 1, 1 - 2 * (xx + zz))
    matrix.SetElement(1, 2, 2 * (yz - xw))

    matrix.SetElement(2, 0, 2 * (xz - yw))
    matrix.SetElement(2, 1, 2 * (yz + xw))
    matrix.SetElement(2, 2, 1 - 2 * (xx + yy))

    # 이동 요소는 0으로 설정
    matrix.SetElement(0, 3, 0)
    matrix.SetElement(1, 3, 0)
    matrix.SetElement(2, 3, 0)
    matrix.SetElement(3, 0, 0)
    matrix.SetElement(3, 1, 0)
    matrix.SetElement(3, 2, 0)
    matrix.SetElement(3, 3, 1)

    return matrix


def apply_quaternion_to_transform(transform, w, x, y, z):
    """쿼터니언 회전을 VTK 변환 객체에 적용"""
    # 쿼터니언을 행렬로 변환
    matrix = quaternion_to_matrix(w, x, y, z)

    # 변환 객체에 행렬 적용
    transform.SetMatrix(matrix)

    return transform


# 쿼터니언 관련 추가 유틸리티 함수
def quaternion_multiply(q1, q2):
    """두 쿼터니언 q1, q2의 곱을 계산"""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2

    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2

    return w, x, y, z


def quaternion_inverse(q):
    """쿼터니언의 역(inverse)을 계산"""
    w, x, y, z = q
    norm_sq = w * w + x * x + y * y + z * z

    if norm_sq < 1e-10:  # 0에 가까운 경우 처리
        return 1, 0, 0, 0

    inv_norm_sq = 1.0 / norm_sq
    return w * inv_norm_sq, -x * inv_norm_sq, -y * inv_norm_sq, -z * inv_norm_sq


def get_relative_quaternion(initial_q, current_q):
    """초기 쿼터니언 기준 현재 쿼터니언의 상대적 회전 계산"""
    inv_initial = quaternion_inverse(
        (initial_q["w"], initial_q["x"], initial_q["y"], initial_q["z"])
    )
    current = (current_q["w"], current_q["x"], current_q["y"], current_q["z"])

    # 초기 쿼터니언의 역(inverse)과 현재 쿼터니언을 곱해 상대 회전 계산
    relative_q = quaternion_multiply(current, inv_initial)

    return {
        "w": relative_q[0],
        "x": relative_q[1],
        "y": relative_q[2],
        "z": relative_q[3],
    }


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
from vtkmodules.vtkFiltersSources import (
    vtkCubeSource,
    vtkSphereSource,
    vtkSuperquadricSource,
)
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter
from vtkmodules.vtkFiltersCore import vtkAppendPolyData

# 전역 변수 설정
colors = vtkNamedColors()
finger_transforms = {}  # 각 손가락 마디의 변환 객체 저장
finger_actors = {}  # 각 손가락 마디의 액터 저장
render_window = None  # 렌더윈도우 전역 참조
interactor = None  # 인터랙터 전역 참조
joint_actors = []  # 손가락 관절 액터 저장 리스트
hand_joint_transforms = []  # 손가락 관절 트랜스폼 글로벌 참조
initial_quaternion_dot1 = {"w": 1, "x": 0, "y": 0, "z": 0}  # DOT1 초기 쿼터니언
initial_quaternion_dot2 = {"w": 1, "x": 0, "y": 0, "z": 0}  # DOT2 초기 쿼터니언
is_calibrated = False  # 캘리브레이션 상태 플래그


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


def create_capsule(height=0.2, radius=0.05, color=(0.8, 0.7, 0.6), transform=None):
    """캡슐(원통 + 양 끝 구) 형태 생성"""
    # 1) Cylinder body
    cylinder = vtk.vtkCylinderSource()
    cylinder.SetRadius(radius)
    cylinder.SetHeight(height)
    cylinder.SetResolution(36)

    # 2) Sphere ends
    sphere_top = vtk.vtkSphereSource()
    sphere_top.SetRadius(radius)
    sphere_top.SetThetaResolution(36)
    sphere_top.SetPhiResolution(36)
    tf_top = vtk.vtkTransform()
    tf_top.Translate(0, height / 2, 0)
    tpf_top = vtkTransformPolyDataFilter()
    tpf_top.SetTransform(tf_top)
    tpf_top.SetInputConnection(sphere_top.GetOutputPort())

    sphere_bot = vtk.vtkSphereSource()
    sphere_bot.SetRadius(radius)
    sphere_bot.SetThetaResolution(36)
    sphere_bot.SetPhiResolution(36)
    tf_bot = vtk.vtkTransform()
    tf_bot.Translate(0, -height / 2, 0)
    tpf_bot = vtkTransformPolyDataFilter()
    tpf_bot.SetTransform(tf_bot)
    tpf_bot.SetInputConnection(sphere_bot.GetOutputPort())

    # 3) Append all
    appender = vtkAppendPolyData()
    appender.AddInputConnection(cylinder.GetOutputPort())
    appender.AddInputConnection(tpf_top.GetOutputPort())
    appender.AddInputConnection(tpf_bot.GetOutputPort())
    appender.Update()

    # 4) Mapper + Actor
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(appender.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    if transform:
        actor.SetUserTransform(transform)
    actor.GetProperty().SetColor(color)
    return actor, appender, transform


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
    # 캡슐 반지름은 너비의 절반 정도로 설정
    radius = width / 2
    return create_capsule(
        height=height, radius=radius, color=color, transform=transform
    )
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


def create_palm(
    width=1.7, height=0.4, depth=1.3, color=(0.8, 0.7, 0.6), transform=None
):
    """둥근 모서리(rounded box) 형태의 손바닥 생성"""
    source = vtkSuperquadricSource()
    source.SetToroidal(0)  # 토러스가 아닌 일반 슈퍼쿼드릭
    source.SetPhiRoundness(0.8)  # φ 방향 라운딩 정도 (0.1~2.0)
    source.SetThetaRoundness(0.8)  # θ 방향 라운딩 정도
    source.SetThickness(0.8)  # 필렛(모서리 둥글기) 정도
    # 슈퍼쿼드릭 기본 크기는 [-1,1] 범위이므로 절반 값으로 스케일
    source.SetScale(width / 2, height / 2, depth / 2)
    source.SetPhiResolution(32)  # 더 부드러운 표면을 위한 해상도
    source.SetThetaResolution(32)

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
    global joint_actors, palm_transform

    all_actors = []

    # 손바닥 생성 - 초기 상태를 수평으로 설정
    palm_transform = vtk.vtkTransform()
    # 기울어짐 보정
    transform(
        palm_transform, rotate=(0, 0, -45)
    )  # Z축 -45도로 수정하여 대각선 기울기 제거

    # 손바닥이 수평이 되도록 X축으로 -90도 회전
    transform(palm_transform, rotate=(-90, 0, 0))
    palm_actor, palm_source, _ = create_palm(transform=palm_transform)
    all_actors.append(palm_actor)

    # 왼손
    # finger_positions = [
    #     # 엄지 위치
    #     {"pos": (0.4, 0.05, -0.0), "angle": (0, 20, -30)},  # 각도도 반전
    #     # 검지 위치
    #     {"pos": (0.25, 0.31, 0.0), "angle": (0, 0, 0)},
    #     # 중지 위치
    #     {"pos": (0.06, 0.31, 0.0), "angle": (0, 0, 0)},
    #     # 약지 위치
    #     {"pos": (-0.12, 0.31, 0.0), "angle": (0, 0, 0)},
    #     # 소지 위치
    #     {"pos": (-0.3, 0.31, 0.0), "angle": (0, 0, 0)},
    # ]
    finger_positions = [
        # 엄지 위치
        {"pos": (-0.38, 0.05, -0.0), "angle": (0, 20, 30)},  # 각도 방향 변경
        # 검지 위치
        {"pos": (-0.25, 0.28, 0.0), "angle": (0, 0, 0)},
        # 중지 위치
        {"pos": (-0.06, 0.31, 0.0), "angle": (0, 0, 0)},
        # 약지 위치
        {"pos": (0.12, 0.28, 0.0), "angle": (0, 0, 0)},
        # 소지 위치
        {"pos": (0.3, 0.24, 0.0), "angle": (0, 0, 0)},
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
        height1 = (
            0.15
            if finger_idx == 0
            else (0.2 if finger_idx == 2 else (0.15 if finger_idx == 4 else 0.18))
        )
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
        height2 = (
            0.12
            if finger_idx == 0
            else (0.17 if finger_idx == 2 else (0.13 if finger_idx == 4 else 0.15))
        )
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
        height3 = (
            0.1
            if finger_idx == 0
            else (0.14 if finger_idx == 2 else (0.09 if finger_idx == 4 else 0.12))
        )
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
    global initial_quaternion_dot1, initial_quaternion_dot2, is_calibrated
    initial_relative_dot2_to_dot1 = {
        "w": 1,
        "x": 0,
        "y": 0,
        "z": 0,
    }  # 두 센서 간 초기 상대 관계
    # 연결 상태 확인
    current_time = time.time()
    last_data_time = getattr(websocket_client, "last_data_time", 0)

    # DOT1 센서에서 쿼터니언 데이터 가져오기 (손등 센서)
    dot1_data = websocket_client.dot_data["DOT1"]
    w_dot1 = dot1_data["w"]
    x_dot1 = dot1_data["x"]
    y_dot1 = dot1_data["y"]
    z_dot1 = dot1_data["z"]

    # DOT2 센서에서 쿼터니언 데이터 가져오기 (손가락 센서)
    dot2_data = websocket_client.dot_data["DOT2"]
    w_dot2 = dot2_data["w"]
    x_dot2 = dot2_data["x"]
    y_dot2 = dot2_data["y"]
    z_dot2 = dot2_data["z"]

    # 데이터가 유효한지 확인
    valid_dot1_data = w_dot1 != 0 or x_dot1 != 0 or y_dot1 != 0 or z_dot1 != 0
    valid_dot2_data = w_dot2 != 0 or x_dot2 != 0 or y_dot2 != 0 or z_dot2 != 0

    # 초기 캘리브레이션 수행 부분 수정 (739번 줄 근처)
    if not is_calibrated and valid_dot1_data and valid_dot2_data:
        # 초기값 저장
        initial_quaternion_dot1 = dot1_data.copy()
        initial_quaternion_dot2 = dot2_data.copy()

        # 두 센서 사이의 초기 상대적 회전 계산
        # 손등 센서의 역회전 계산
        dot1_initial_inv = quaternion_inverse(
            (
                initial_quaternion_dot1["w"],
                initial_quaternion_dot1["x"],
                initial_quaternion_dot1["y"],
                initial_quaternion_dot1["z"],
            )
        )

        # 손가락 센서의 초기 회전
        dot2_initial = (
            initial_quaternion_dot2["w"],
            initial_quaternion_dot2["x"],
            initial_quaternion_dot2["y"],
            initial_quaternion_dot2["z"],
        )

        # 초기 상대 회전 (손등 기준 손가락의 초기 상태)
        initial_relative = quaternion_multiply(dot2_initial, dot1_initial_inv)
        initial_relative_dot2_to_dot1 = {
            "w": initial_relative[0],
            "x": initial_relative[1],
            "y": initial_relative[2],
            "z": initial_relative[3],
        }

        is_calibrated = True
        print("센서 초기 위치 캘리브레이션 완료!")
        print(
            f"DOT1 초기값: w={w_dot1:.4f}, x={x_dot1:.4f}, y={y_dot1:.4f}, z={z_dot1:.4f}"
        )
        print(
            f"DOT2 초기값: w={w_dot2:.4f}, x={x_dot2:.4f}, y={y_dot2:.4f}, z={z_dot2:.4f}"
        )
        print(
            f"상대 회전: w={initial_relative[0]:.4f}, x={initial_relative[1]:.4f}, y={initial_relative[2]:.4f}, z={initial_relative[3]:.4f}"
        )
        return  # 첫 번째 프레임에서는 모델 업데이트 없이 종료

    # 캘리브레이션된 경우 상대 회전으로 보정
    if is_calibrated and valid_dot1_data:
        # 보정된 값을 사용하므로 상대적 쿼터니언 재계산 불필요

        # 안정화 영역 설정 - 미세 움직임을 무시하는 데드존 추가
        dead_zone = 0.01  # 데드존 크기 조정
        if (
            abs(dot1_data["x"]) < dead_zone
            and abs(dot1_data["y"]) < dead_zone
            and abs(dot1_data["z"]) < dead_zone
        ):
            # 작은 값은 무시하고 초기 자세로 유지
            adjusted_q = {"w": 1, "x": 0, "y": 0, "z": 0}
        else:
            # 좌표계 변환을 위한 축 매핑 조정
            adjusted_q = {
                "w": dot1_data["w"],
                "x": -dot1_data["y"],  # 센서 Y축 → 모델 X축
                "y": dot1_data["x"],  # 센서 X축 → 모델 Y축
                "z": dot1_data["z"],  # Z축은 부호 반전
            }

    if is_calibrated and valid_dot2_data:
        # 상대 회전 계산하여 원본 데이터 업데이트
        dot2_data = get_relative_quaternion(initial_quaternion_dot2, dot2_data)

    # 캘리브레이션이 완료되고 유효한 데이터가 있을 때만 처리
    if is_calibrated and valid_dot1_data:
        # 손바닥 초기화 및 기본 위치/회전 설정
        palm_transform.Identity()
        transform(palm_transform, rotate=(0, 0, 0))  # Z축 -45도로 수정
        # 손바닥 중심점 계산 - 엄지와 소지 사이의 중간점 추정
        # 오른손 기준으로 손바닥 중심을 계산 (오른손의 경우 x=0 정도가 중심)
        hand_center_x = 0.0  # 손바닥 중심의 x 좌표
        hand_center_y = 0.15  # 손바닥 중심의 y 좌표
        hand_center_z = 0.0  # 손바닥 중심의 z 좌표

        # 1. 먼저 손바닥 중심으로 이동
        palm_transform.Translate(hand_center_x, hand_center_y, hand_center_z)

        # 2. 쿼터니언 회전 적용
        # 좌표계 변환을 위한 축 매핑 조정
        adjusted_q = {
            "w": dot1_data["w"],
            "x": -dot1_data["y"],  # 센서 Y축 → 모델 X축
            "y": dot1_data["x"],  # 센서 X축 → 모델 Y축
            "z": dot1_data["z"],  # Z축은 부호 반전
        }

        # 기본 X축 -90도 회전을 쿼터니언으로 표현
        base_q = {"w": 0.7071, "x": -0.7071, "y": 0, "z": 0}

        # 두 쿼터니언을 곱하여 하나의 회전으로 통합
        combined_q = quaternion_multiply(
            (base_q["w"], base_q["x"], base_q["y"], base_q["z"]),
            (adjusted_q["w"], adjusted_q["x"], adjusted_q["y"], adjusted_q["z"]),
        )

        # 회전 적용
        apply_quaternion_to_transform(
            palm_transform, combined_q[0], combined_q[1], combined_q[2], combined_q[3]
        )

        # 3. 다시 원래 위치로 이동
        palm_transform.Translate(-hand_center_x, -hand_center_y, -hand_center_z)

    # 손가락 제어에 대한 처리
    target_angle = 0
    if is_calibrated and valid_dot2_data:
        # 상대적인 쿼터니언 계산
        relative_q_dot2 = get_relative_quaternion(initial_quaternion_dot2, dot2_data)

        # 쿼터니언을 오일러 각도로 변환
        roll, pitch, yaw = quaternion_to_euler(
            relative_q_dot2["w"],
            relative_q_dot2["x"],
            relative_q_dot2["y"],
            relative_q_dot2["z"],
        )

        # 손가락 굽힘에는 주로 roll 값 사용
        target_angle = roll  # 음수 값이 굽힘을 의미

        # 범위 제한
        max_bend = 10
        min_bend = -90
        target_angle = max(min_bend, min(max_bend, target_angle))

    # 왼손
    # finger_positions = [
    #     # 엄지 위치
    #     {"pos": (0.4, 0.05, -0.0), "angle": (0, 20, -30)},  # 각도도 반전
    #     # 검지 위치
    #     {"pos": (0.25, 0.31, 0.0), "angle": (0, 0, 0)},
    #     # 중지 위치
    #     {"pos": (0.06, 0.31, 0.0), "angle": (0, 0, 0)},
    #     # 약지 위치
    #     {"pos": (-0.12, 0.31, 0.0), "angle": (0, 0, 0)},
    #     # 소지 위치
    #     {"pos": (-0.3, 0.31, 0.0), "angle": (0, 0, 0)},
    # ]
    # 오른손
    finger_positions = [
        # 엄지 위치
        {"pos": (-0.38, 0.05, -0.0), "angle": (0, 20, 30)},  # 각도 방향 변경
        # 검지 위치
        {"pos": (-0.25, 0.28, 0.0), "angle": (0, 0, 0)},
        # 중지 위치
        {"pos": (-0.06, 0.31, 0.0), "angle": (0, 0, 0)},
        # 약지 위치
        {"pos": (0.12, 0.28, 0.0), "angle": (0, 0, 0)},
        # 소지 위치
        {"pos": (0.3, 0.24, 0.0), "angle": (0, 0, 0)},
    ]

    # 선택된 손가락만 제어
    for finger_idx in websocket_client.selected_fingers:
        if finger_idx < len(hand_joint_transforms):
            # 첫 번째 관절 제어
            joint0_transform = hand_joint_transforms[finger_idx][0]
            joint0_transform.Identity()
            transform(
                joint0_transform,
                translate=finger_positions[finger_idx]["pos"],
                rotate=finger_positions[finger_idx]["angle"],
            )
            # 회전 적용
            transform(joint0_transform, rotate=(target_angle, 0, 0))

            # 관절 반지름
            joint_radius = 0.02

            # 첫 번째 마디 연결
            if len(joint_actors[finger_idx][0]) > 1:
                phalanx1_actor, phalanx1_transform = joint_actors[finger_idx][0][1]
                height1 = 0.15 if finger_idx == 0 else 0.18
                offset1 = joint_radius + height1 / 2 - 0.002

                phalanx1_transform.Identity()
                phalanx1_transform.SetInput(joint0_transform)
                transform(phalanx1_transform, translate=(0.0, offset1, 0.0))

            # 두 번째 관절 제어
            if len(hand_joint_transforms[finger_idx]) > 1:
                joint1_transform = hand_joint_transforms[finger_idx][1]
                joint1_transform.Identity()
                joint1_transform.SetInput(phalanx1_transform)
                height1 = 0.15 if finger_idx == 0 else 0.18
                offset = height1 / 2 + joint_radius - 0.002
                transform(joint1_transform, translate=(0.0, offset, 0.0))
                # 회전 적용
                transform(joint1_transform, rotate=(target_angle, 0, 0))

                # 두 번째 마디 연결
                if len(joint_actors[finger_idx][1]) > 1:
                    phalanx2_actor, phalanx2_transform = joint_actors[finger_idx][1][1]
                    height2 = 0.12 if finger_idx == 0 else 0.15
                    offset2 = joint_radius + height2 / 2 - 0.002

                    phalanx2_transform.Identity()
                    phalanx2_transform.SetInput(joint1_transform)
                    transform(phalanx2_transform, translate=(0.0, offset2, 0.0))

                # 세 번째 관절 제어
                if len(hand_joint_transforms[finger_idx]) > 2:
                    joint2_transform = hand_joint_transforms[finger_idx][2]
                    joint2_transform.Identity()
                    joint2_transform.SetInput(phalanx2_transform)
                    height2 = 0.12 if finger_idx == 0 else 0.15
                    offset = height2 / 2 + joint_radius - 0.002
                    transform(joint2_transform, translate=(0.0, offset, 0.0))
                    # 회전 적용
                    transform(joint2_transform, rotate=(target_angle, 0, 0))

                    # 세 번째 마디 연결
                    if len(joint_actors[finger_idx][2]) > 1:
                        phalanx3_actor, phalanx3_transform = joint_actors[finger_idx][
                            2
                        ][1]
                        height3 = 0.1 if finger_idx == 0 else 0.12
                        offset3 = joint_radius + height3 / 2 - 0.002

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
    cam_right.SetPosition(-6, 0, 0)
    cam_right.SetFocalPoint(0, 0, 0)
    cam_right.SetViewUp(0, 1, 0)
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
