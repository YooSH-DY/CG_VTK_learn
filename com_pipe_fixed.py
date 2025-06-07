# vtk 모듈 및 필요 라이브러리 import
import math
import vtk
import time
import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import vtkQuadric
from vtkmodules.vtkFiltersCore import vtkContourFilter, vtkAppendFilter, vtkAppendPolyData
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
    vtkCylinderSource,
)
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter
from vtkmodules.vtkCommonTransforms import vtkTransform


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


# 전역 변수 설정
colors = vtkNamedColors()
finger_transforms = {}  # 각 손가락 마디의 변환 객체 저장
finger_actors = {}  # 각 손가락 마디의 액터 저장
render_window = None  # 렌더윈도우 전역 참조
interactor = None  # 인터랙터 전역 참조
joint_actors = []  # 손가락 관절 액터 저장 리스트
hand_joint_transforms = []  # 손가락 관절 트랜스폼 글로벌 참조

# 전역 변수 설정
colors = vtkNamedColors()
finger_transforms = {}  # 각 손가락 마디의 변환 객체 저장
finger_actors = {}  # 각 손가락 마디의 액터 저장
render_window = None  # 렌더윈도우 전역 참조
interactor = None  # 인터랙터 전역 참조
joint_actors = []  # 손가락 관절 액터 저장 리스트
hand_joint_transforms = []  # 손가락 관절 트랜스폼 글로벌 참조
# 웹소켓 연결 관련 변수 제거


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


def create_capsule(height=0.2, radius=0.001, color=(0.8, 0.7, 0.6), transform=None):
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
    width=1.2, height=0.4, depth=1.35, color=(0.8, 0.7, 0.6), transform=None
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


def create_wrist(
    width=0.5, height=1.0, depth=0.5, color=(0.8, 0.7, 0.6), transform=None
):
    """원통형 팔목 생성"""
    source = vtkCylinderSource()
    source.SetRadius(width / 3)
    source.SetHeight(height)
    source.SetResolution(32)  # 부드러운 원통을 위한 해상도

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
        # 이벤트 옵저버 등록
        self.AddObserver("LeftButtonPressEvent", self.leftButtonPressEvent)
        self.AddObserver("KeyPressEvent", self.on_key_press)
        # 주요 속성 초기화
        self.renderer = renderer
        self.render_window = render_window
        self.joint_transforms = joint_transforms
        self.LastPickedActor = None
        self.LastPickedProperty = vtk.vtkProperty()
        self.original_colors = {}
        self.chopstick_mode_active = False
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
        delta = -5 if not is_bent else 5

        # 엄지와 기타 손가락 분리 - 엄지는 Y축 방향으로 굽히기
        if finger_idx == 0:  # 엄지손가락
            if joint_idx == 0:
                axis = (delta, 0, 0)  # 첫 번째 관절은 X축
            else:
                axis = (0, delta, 0)  # 두 번째, 세 번째 관절은 Y축 방향으로 굽히기
        else:  # 다른 손가락들
            axis = (delta, 0, 0)  # X축 방향으로 굽히기

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
        """숫자키로 다양한 손동작 제어"""
        key = self.GetInteractor().GetKeySym()
        
        if not self.joint_transforms:
            super().OnKeyPress()
            return
        if key == "1":
            self.point_gesture()
        elif key == "2":
            self.peace_gesture()
        elif key == "4":
            self.curl_finger(1)
        elif key == "5":
            self.pinch_gesture()
        elif key == "6":
            self.chopstick_gesture()
        elif key.lower() == '8':
            # 8번: 팔뚝(wrist_transform) 위아래로 움직이기
            self.animate_wrist_swing(45)
            time.sleep(0.5)
            self.animate_wrist_swing(0)
            time.sleep(1)
            self.animate_wrist_swing(-45)
            time.sleep(0.5)
            self.animate_wrist_swing(0)
        elif key.lower() == '9':
            # 9 키: Z축 기준으로 왼쪽→중앙→오른쪽으로 손바닥 트위스트
            self.animate_hand_twist(45)
            time.sleep(0.5)
            self.animate_hand_twist(0)
            time.sleep(1)
            self.animate_hand_twist(-45)
            time.sleep(0.5)
            self.animate_hand_twist(0)
        elif key == "7":
            for finger_idx in [0,1,2,3,4]:
                if finger_idx < len(self.joint_transforms):
                    for joint_idx in range(len(self.joint_transforms[finger_idx])):
                        self.rotateJoint(finger_idx, joint_idx)
        elif key == '0':
            # 0 키: 손바닥(palm)과 손등(back) 뒤집기 애니메이션
            self.animate_hand_flip(180)
            time.sleep(0.5)
            self.animate_hand_flip(0)
        else:
            super().OnKeyPress()
            return
        if self.render_window:
            self.render_window.Render()

    def reset_all_fingers(self):
        """모든 손가락을 초기 상태로 리셋"""
        if not self.joint_transforms:
            return
            
        for finger_idx in range(len(self.joint_transforms)):
            if finger_idx < len(self.joint_transforms):
                for joint_idx in range(len(self.joint_transforms[finger_idx])):
                    key = (finger_idx, joint_idx)
                    if key in self.joint_state and self.joint_state[key]:
                        # 굽혀진 상태면 펴기
                        self.rotateJoint(finger_idx, joint_idx)

    def point_gesture(self):
        """엄지와 검지만 펼치고 나머지는 주먹 (포인팅 제스처)"""
        if not self.joint_transforms:
            return
            
        print("포인팅 제스처 실행")
        
        # 먼저 모든 손가락을 펼친 상태로 리셋
        self.reset_all_fingers()
        time.sleep(0.5)
        
        # 중지, 약지, 소지만 굽히기 (인덱스 2, 3, 4)
        for finger_idx in [2, 3, 4]:
            if finger_idx < len(self.joint_transforms):
                for joint_idx in range(len(self.joint_transforms[finger_idx])):
                    key = (finger_idx, joint_idx)
                    if not self.joint_state.get(key, False):
                        self.rotateJoint(finger_idx, joint_idx)
                        time.sleep(0.1)

    def peace_gesture(self):
        """검지와 중지로 V자 동작"""
        if not self.joint_transforms:
            return
            
        print("피스 제스처 실행")
        
        # 먼저 모든 손가락을 리셋
        self.reset_all_fingers()
        time.sleep(0.5)
        
        # 검지와 중지 사이 각도 벌리기 (Z축 회전) - V자 만들기
        if len(self.joint_transforms) > 2:
            # 검지(finger_idx=1)를 반시계방향으로 12도 회전 (바깥쪽으로)
            index_finger_joint0_transform = self.joint_transforms[1][0]
            transform(index_finger_joint0_transform, rotate=(0, 0, 12))
            
            # 중지(finger_idx=2)를 시계방향으로 12도 회전 (바깥쪽으로)
            middle_finger_joint0_transform = self.joint_transforms[2][0]
            transform(middle_finger_joint0_transform, rotate=(0, 0, -12))
        
        # 엄지, 약지, 소지만 굽히기 (인덱스 0, 3, 4)
        for finger_idx in [0, 3, 4]:
            if finger_idx < len(self.joint_transforms):
                for joint_idx in range(len(self.joint_transforms[finger_idx])):
                    key = (finger_idx, joint_idx)
                    if not self.joint_state.get(key, False):
                        self.rotateJoint(finger_idx, joint_idx)
                        time.sleep(0.1)

    def curl_finger(self, finger_idx):
        """특정 손가락만 굽히기/펴기"""
        if not self.joint_transforms or finger_idx >= len(self.joint_transforms):
            return
            
        print(f"손가락 {finger_idx} 굽히기/펴기")
        
        # 검지(finger_idx=1)의 경우
        if finger_idx == 1:
            # 두 번째와 세 번째 관절을 동시에 굽히기
            max_angle = 90
            delta = -3  # 굽히는 방향
            
            # 애니메이션 단계
            for step in range(0, max_angle, abs(delta)):
                # 두 번째 관절 (joint_idx=1)
                if 1 < len(self.joint_transforms[finger_idx]):
                    transform(
                        self.joint_transforms[finger_idx][1],
                        rotate=(delta, 0, 0),
                    )
                
                # 세 번째 관절 (joint_idx=2)
                if 2 < len(self.joint_transforms[finger_idx]):
                    transform(
                        self.joint_transforms[finger_idx][2],
                        rotate=(delta, 0, 0),
                    )
                
                # 각 단계마다 화면 갱신
                self.render_window.Render()
                time.sleep(0.05)
            
            # 관절 상태 저장
            if 1 < len(self.joint_transforms[finger_idx]):
                self.joint_state[(finger_idx, 1)] = not self.joint_state.get((finger_idx, 1), False)
            if 2 < len(self.joint_transforms[finger_idx]):
                self.joint_state[(finger_idx, 2)] = not self.joint_state.get((finger_idx, 2), False)
        else:
            # 다른 손가락은 기존 방식대로 순차적으로 굽히기
            start_joint = 0
            for joint_idx in range(start_joint, len(self.joint_transforms[finger_idx])):
                self.rotateJoint(finger_idx, joint_idx)
                time.sleep(0.1)

    def apply_quaternion_rotation(self, transform_obj, axis, angle_deg):
        """
        임의의 축을 중심으로 회전 적용 (쿼터니언 방식)
        
        axis: 회전축 벡터 (x, y, z) - 정규화된 벡터여야 함
        angle_deg: 회전 각도 (도 단위)
        """
        # 먼저 축 벡터 정규화
        length = math.sqrt(axis[0]**2 + axis[1]**2 + axis[2]**2)
        if length < 1e-10:  # 길이가 0에 가까우면 회전 안함
            return
            
        norm_axis = (axis[0]/length, axis[1]/length, axis[2]/length)
        
        # VTK의 RotateWXYZ 함수 사용 - 내부적으로 쿼터니언으로 처리됨
        # (각도, x, y, z)를 매개변수로 받아 임의 축 회전 수행
        transform_obj.RotateWXYZ(angle_deg, norm_axis[0], norm_axis[1], norm_axis[2])
        
        return transform_obj
    
    def animate_quaternion_rotation(self, transform_obj, axis, target_angle, steps=20, delay=0.02):
        """
        쿼터니언 회전을 애니메이션으로 부드럽게 적용
        
        transform_obj: 회전할 vtkTransform 객체
        axis: 회전축 벡터 (x, y, z)
        target_angle: 목표 회전 각도 (도 단위)
        steps: 애니메이션 단계 수
        delay: 각 단계 사이의 지연 시간 (초)
        """
        angle_per_step = target_angle / steps
        
        for step in range(steps):
            self.apply_quaternion_rotation(transform_obj, axis, angle_per_step)
            self.render_window.Render()
            time.sleep(delay)
            
        return transform_obj

    def pinch_gesture(self):
        """간단하고 자연스러운 OK 제스처 (엄지와 검지로 원형 만들기) - 쿼터니언 회전 적용"""
        if not self.joint_transforms:
            return

        print("OK/핀치 제스처 실행 (쿼터니언 회전 적용)")
        self.reset_all_fingers()
        time.sleep(0.5)
        
        # 중지, 약지, 소지 모든 관절을 동시에 굽히기 - 동시 애니메이션
        # 애니메이션 단계 및 각도 준비
        steps = 15
        max_angle = 70
        angle_per_step = max_angle / steps
        
        # 각 애니메이션 단계마다 모든 관절을 동시에 회전
        for step in range(steps):
            for finger_idx in [2, 3, 4]:  # 중지, 약지, 소지
                if finger_idx < len(self.joint_transforms):
                    for joint_idx in range(len(self.joint_transforms[finger_idx])):
                        # 각 관절마다 약간 다른 각도 적용 (더 자연스러움)
                        joint_angle = angle_per_step * (1.0 if joint_idx == 0 else (1.2 if joint_idx == 1 else 1.3))
                        
                        # 쿼터니언 회전 한 단계 적용
                        self.apply_quaternion_rotation(
                            self.joint_transforms[finger_idx][joint_idx],
                            axis=(-1, 0, 0),  # X축 음의 방향 (손가락 구부리기)
                            angle_deg=joint_angle
                        )
            
            # 모든 관절을 한 단계 회전한 후 화면 갱신
            self.render_window.Render()
            time.sleep(0.02)  # 빠른 애니메이션을 위해 짧은 지연
        
        # 손가락 상태 업데이트
        for finger_idx in [2, 3, 4]:
            if finger_idx < len(self.joint_transforms):
                for joint_idx in range(len(self.joint_transforms[finger_idx])):
                    key = (finger_idx, joint_idx)
                    self.joint_state[key] = True
        
        self.render_window.Render()
        time.sleep(0.3)
        
        # 엄지와 검지 동시에 OK 형태로 만들기
        print("엄지와 검지 동시에 OK 형태로 굽히는 중...")
        
        # 각 관절의 회전 설정 (관절, 회전축, 회전각도)
        joints_to_rotate = []
        
        # 엄지 손가락 관절 설정
        if len(self.joint_transforms) > 0:
            # 첫 번째 관절
            joints_to_rotate.append((
                self.joint_transforms[0][0],  # 엄지 첫 번째 관절
                (-0.9, -0.8, 0.65),          # 회전축 (X,Y,Z 복합)
                80                           # 회전각
            ))
            
            # 두 번째 관절
            if len(self.joint_transforms[0]) > 1:
                joints_to_rotate.append((
                    self.joint_transforms[0][1],  # 엄지 두 번째 관절
                    (-0.5, 0.2, -0.3),           # 회전축
                    70                           # 회전각
                ))
            
            # 세 번째 관절
            if len(self.joint_transforms[0]) > 2:
                joints_to_rotate.append((
                    self.joint_transforms[0][2],  # 엄지 세 번째 관절
                    (0.4, 0.8, -0.8),            # 회전축
                    80                           # 회전각
                ))
        
        # 검지 손가락 관절 설정
        if len(self.joint_transforms) > 1:
            # 첫 번째 관절
            joints_to_rotate.append((
                self.joint_transforms[1][0],  # 검지 첫 번째 관절
                (-0.6, 0, 0.2),               # 회전축
                45                           # 회전각
            ))
            
            # 두 번째 관절
            if len(self.joint_transforms[1]) > 1:
                joints_to_rotate.append((
                    self.joint_transforms[1][1],  # 검지 두 번째 관절
                    (-1, 0, 0),                  # X축 회전
                    75                           # 회전각
                ))
            
            # 세 번째 관절
            if len(self.joint_transforms[1]) > 2:
                joints_to_rotate.append((
                    self.joint_transforms[1][2],  # 검지 세 번째 관절
                    (-1, 0, 0),                  # X축 회전
                    65                           # 회전각
                ))
        
        # 모든 관절을 동시에 애니메이션으로 회전
        steps = 50  # 애니메이션 단계 수
        delay = 0.02  # 단계 간 지연 시간
        
        # 각 관절별 회전각을 단계별로 나누기
        angle_per_step = {}
        for i, (joint, axis, angle) in enumerate(joints_to_rotate):
            angle_per_step[i] = angle / steps
        
        # 단계별로 모든 관절 동시에 회전
        for step in range(steps):
            for i, (joint, axis, _) in enumerate(joints_to_rotate):
                # 한 단계의 회전 적용
                self.apply_quaternion_rotation(joint, axis, angle_per_step[i])
            
            # 한 단계 완료 후 화면 갱신
            self.render_window.Render()
            time.sleep(delay)
        
        # 관절 상태 업데이트
        if len(self.joint_transforms) > 0:
            self.joint_state[(0, 0)] = True
            if len(self.joint_transforms[0]) > 1:
                self.joint_state[(0, 1)] = True
            if len(self.joint_transforms[0]) > 2:
                self.joint_state[(0, 2)] = True
                
        if len(self.joint_transforms) > 1:
            self.joint_state[(1, 0)] = True
            if len(self.joint_transforms[1]) > 1:
                self.joint_state[(1, 1)] = True
            if len(self.joint_transforms[1]) > 2:
                self.joint_state[(1, 2)] = True
            
           
        
        self.render_window.Render()
        time.sleep(0.5)

    def chopstick_gesture(self):
        """젓가락 제스처 (검지와 중지 V자로 시작해서 모으기/펴기)"""
        if not self.joint_transforms:
            return

        print("젓가락 제스처 실행")

        # 젓가락 모드 토글
        self.chopstick_mode_active = not self.chopstick_mode_active

        if not self.chopstick_mode_active:
            # 젓가락 모드 해제 시 - 모든 손가락 리셋
            self.reset_all_fingers()
            return

        # 젓가락 모드 활성화 시
        # 먼저 모든 손가락을 리셋
        self.reset_all_fingers()
        time.sleep(0.3)
        
        # 검지와 중지 사이 각도 벌리기 (2번 피스 제스처와 동일)
        if len(self.joint_transforms) > 2:
            # 검지(finger_idx=1)를 반시계방향으로 12도 회전 (바깥쪽으로)
            index_finger_joint0_transform = self.joint_transforms[1][0]
            transform(index_finger_joint0_transform, rotate=(0, 0, 12))
            
            # 중지(finger_idx=2)를 시계방향으로 12도 회전 (바깥쪽으로)
            middle_finger_joint0_transform = self.joint_transforms[2][0]
            transform(middle_finger_joint0_transform, rotate=(0, 0, -12))
        
        time.sleep(0.3)
        
        # 엄지, 약지, 소지만 굽히기 (젓가락 잡는 형태) - 동시에 굽히기
        for finger_idx in [0, 3, 4]:
            if finger_idx < len(self.joint_transforms):
                for joint_idx in range(len(self.joint_transforms[finger_idx])):
                    key = (finger_idx, joint_idx)
                    if not self.joint_state.get(key, False):
                        # 애니메이션 없이 바로 굽히기
                        max_angle = 80
                        delta = -5
                        # 엄지는 Y축 방향으로, 다른 손가락은 X축 방향으로 굽히기
                        if finger_idx == 0:  # 엄지손가락
                            if joint_idx == 0:
                                axis = (delta, 0, 0)  # 첫 번째 관절은 X축
                            else:
                                axis = (0, delta, 0)  # 두 번째, 세 번째 관절은 Y축
                        else:  # 다른 손가락들
                            axis = (delta, 0, 0)  # X축 방향으로 굽히기
                        
                        # 한 번에 전체 각도만큼 회전
                        for _ in range(0, max_angle, abs(delta)):
                            transform(
                                self.joint_transforms[finger_idx][joint_idx],
                                rotate=axis,
                            )
                        self.joint_state[key] = True
        
        # 화면 갱신하여 굽힌 상태 보여주기
        self.render_window.Render()
        print("손가락 굽히기 완료 - 2초 후 젓가락 모으기 시작")
        
        time.sleep(1.0)  # 딜레이를 2초로 설정
        
        # 마지막에 검지와 중지를 모아서 4도 간격으로 만들기 (애니메이션)
        if len(self.joint_transforms) > 2:
            # 현재 각각 12도씩 벌어진 상태에서 2도씩만 벌어지도록 조정
            # 검지: 12도 → 2도로 (10도 더 안쪽으로)
            # 중지: -12도 → -2도로 (10도 더 안쪽으로)
            
            # 애니메이션으로 부드럽게 좁히기 (총 10도를 20단계로 나누어서)
            total_angle = 17
            steps = 60
            angle_per_step = total_angle / steps
            
            for step in range(steps):
                # 검지를 시계방향으로 조금씩 회전
                transform(index_finger_joint0_transform, rotate=(0, 0, -angle_per_step))
                # 중지를 반시계방향으로 조금씩 회전  
                transform(middle_finger_joint0_transform, rotate=(0, 0, angle_per_step))
                
                # 각 단계마다 렌더링하여 애니메이션 효과
                self.render_window.Render()
                time.sleep(0.02)  # 20ms 간격으로 부드러운 애니메이션
        
        self.render_window.Render()

    def animate_hand_swing(self, target_angle, steps=20, delay=0.02):
        """
        손바닥(palm_transform)을 Y축 기준으로 target_angle까지 부드럽게 회전
        """
        global palm_transform
        if palm_transform is None:
            return
        if not hasattr(self, 'current_hand_angle'):
            self.current_hand_angle = 0
        delta = (target_angle - self.current_hand_angle) / steps
        for _ in range(steps):
            palm_transform.RotateX(delta)
            if self.render_window:
                self.render_window.Render()
            time.sleep(delay)
        self.current_hand_angle = target_angle
    
    def animate_hand_twist(self, target_angle, steps=20, delay=0.02):
        """
        손목(wrist_transform)을 Z축 기준으로 target_angle까지 부드럽게 회전
        """
        global wrist_transform
        if wrist_transform is None:
            return
        if not hasattr(self, 'current_wrist_twist_angle'):
            self.current_wrist_twist_angle = 0
        delta = (target_angle - self.current_wrist_twist_angle) / steps
        for _ in range(steps):
            wrist_transform.RotateZ(delta)
            if self.render_window:
                self.render_window.Render()
            time.sleep(delay)
        self.current_wrist_twist_angle = target_angle

    def animate_hand_flip(self, target_angle, steps=20, delay=0.02):
        """
        손목(wrist_transform)을 Y축 기준으로 target_angle까지 부드럽게 회전하여 palm/back을 반전시킵니다
        """
        global wrist_transform
        if wrist_transform is None:
            return
        if not hasattr(self, 'current_wrist_flip_angle'):
            self.current_wrist_flip_angle = 0
        delta = (target_angle - self.current_wrist_flip_angle) / steps
        for _ in range(steps):
            wrist_transform.RotateY(delta)
            if self.render_window:
                self.render_window.Render()
            time.sleep(delay)
        self.current_wrist_flip_angle = target_angle

    def animate_wrist_swing(self, target_angle, steps=20, delay=0.02):
        """
        팔뚝(wrist_transform)을 X축 기준으로 target_angle까지 부드럽게 회전
        손목이 움직이면 손과 손가락도 함께 자연스럽게 움직임
        """
        global wrist_transform
        try:
            if wrist_transform is None:
                return
        except NameError:
            return
            
        if not hasattr(self, 'current_wrist_angle'):
            self.current_wrist_angle = 0
            
        # 목표 각도와 현재 각도의 차이를 단계별로 나누기
        delta = (target_angle - self.current_wrist_angle) / steps
        
        # 단계별로 회전 적용
        for _ in range(steps):
            # 손목을 회전하면 계층 구조에 의해 손과 손가락이 자동으로 따라서 움직임
            wrist_transform.RotateX(delta)
            
            # 변경사항 화면에 렌더링
            if self.render_window:
                self.render_window.Render()
                
            time.sleep(delay)
            
        # 현재 각도 업데이트
        self.current_wrist_angle = target_angle


def create_hand_actors():
    global joint_actors, palm_transform, wrist_transform

    all_actors = []

    # 손목(wrist)을 먼저 생성 - 계층 구조의 최상위에 위치
    wrist_transform = vtkTransform()
    # 손목의 초기 위치 및 방향 설정 - 수평으로 눕히기
    transform(wrist_transform, translate=(0, 0, 0), rotate=(-90, 0, 0))  # X축 기준 -90도 회전하여 수평으로 눕히기
    wrist_actor, wrist_source, _ = create_wrist(transform=wrist_transform)
    all_actors.append(wrist_actor)
    
    # 손바닥(palm) 생성 - 손목의 자식 계층으로 설정
    palm_transform = vtkTransform()
    palm_transform.SetInput(wrist_transform)  # 손바닥을 손목에 연결
    # 손바닥 위치 조정 - 손목 끝부분에 정확하게 배치
    transform(palm_transform, translate=(0, 0.98, -0.15))  # 손목이 X축 기준으로 회전했으므로 Z 방향으로 위치 조정
    # 손바닥 X축으로 90도 회전
    transform(palm_transform, rotate=(90, 0, 0))  # X축 기준 90도 회전
    palm_actor, palm_source, _ = create_palm(transform=palm_transform)
    all_actors.append(palm_actor)

    # 팔목에 1자 선 추가 (Y축 방향, 팔목 표면에 위치)
    line_source = vtk.vtkLineSource()
    line_source.SetPoint1(0.05, -0.0, 0.16)
    line_source.SetPoint2(0.05, 0.1, 0.16)
    line_mapper = vtk.vtkPolyDataMapper()
    line_mapper.SetInputConnection(line_source.GetOutputPort())
    line_actor = vtk.vtkActor()
    line_actor.SetMapper(line_mapper)
    line_actor.GetProperty().SetColor(1, 0, 0)  # 검은색
    line_actor.GetProperty().SetLineWidth(5)
    line_actor.SetUserTransform(wrist_transform)
    all_actors.append(line_actor)

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
        {"pos": (-0.31, -0.01, -0.0), "angle": (0, 20, 30)},  # 각도 방향 변경
        # 검지 위치
        {"pos": (-0.19, 0.28, 0.0), "angle": (0, 0, 6)},
        # 중지 위치
        {"pos": (-0.06, 0.32, 0.0), "angle": (0, 0, 0)},
        # 약지 위치
        {"pos": (0.07, 0.28, 0.0), "angle": (0, 0, -5)},
        # 소지 위치
        {"pos": (0.22, 0.22, 0.0), "angle": (0, 0, -5)},
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
        joint0_transform = vtkTransform()
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
        phalanx1_transform = vtkTransform()
        phalanx1_transform.SetInput(joint0_transform)
        offset = joint_radius + height1 / 2 - 0.002
        transform(phalanx1_transform, translate=(0.0, offset, 0.0))
        phalanx1_actor, phalanx1_source, _ = create_phalanx(
            width=width1, height=height1, transform=phalanx1_transform
        )
        all_actors.append(phalanx1_actor)
        finger_actors[0].append((phalanx1_actor, phalanx1_transform))

        # 두 번째 관절 생성
        joint1_transform = vtkTransform()
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
        phalanx2_transform = vtkTransform()
        phalanx2_transform.SetInput(joint1_transform)
        offset = joint_radius + height2 / 2 - 0.002
        transform(phalanx2_transform, translate=(0.0, offset, 0.0))
        phalanx2_actor, phalanx2_source, _ = create_phalanx(
            width=width2, height=height2, transform=phalanx2_transform
        )
        all_actors.append(phalanx2_actor)
        finger_actors[1].append((phalanx2_actor, phalanx2_transform))

        # 세 번째 관절 생성
        joint2_transform = vtkTransform()
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
        phalanx3_transform = vtkTransform()
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


# 손 모델 초기화 및 위치 설정 함수
def init_hand_model():
    global palm_transform
    
    # 손바닥 위치 설정
    hand_center_x = 0.0  # 손바닥 중심의 x 좌표
    hand_center_y = 0.15  # 손바닥 중심의 y 좌표
    hand_center_z = 0.0  # 손바닥 중심의 z 좌표
    
    # 1. 먼저 손바닥 중심으로 이동
    palm_transform.Translate(hand_center_x, hand_center_y, hand_center_z)
    
    # 손바닥 회전 - 간단하게 직접 설정
    transform(palm_transform, rotate=(-90, 0, 0))  # X축 -90도 회전
    
    # 3. 다시 원래 위치로 이동
    palm_transform.Translate(-hand_center_x, -hand_center_y, -hand_center_z)

    # 손가락 제어에 대한 처리 - 웹소켓 관련 코드 제거
    # 기본 각도값 설정
    target_angle = 0  # 손가락을 펴진 상태로 유지

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
        {"pos": (-0.31, -0.01, -0.0), "angle": (0, 20, 30)},  # 각도 방향 변경
        # 검지 위치
        {"pos": (-0.19, 0.28, 0.0), "angle": (0, 0, 6)},
        # 중지 위치
        {"pos": (-0.06, 0.32, 0.0), "angle": (0, 0, 0)},
        # 약지 위치
        {"pos": (0.07, 0.28, 0.0), "angle": (0, 0, -5)},
        # 소지 위치
        {"pos": (0.22, 0.22, 0.0), "angle": (0, 0, -5)},
    ]

    # 웹소켓 관련 코드 제거 - 선택된 손가락 제어 코드
    for finger_idx in range(len(hand_joint_transforms)):
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
    render_window.SetWindowName("Hand Animation")

    interactor = vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)

    # 전체 창을 사용하는 렌더러 생성
    ren_right = vtkRenderer()
    ren_right.SetViewport(0.0, 0.0, 1.0, 1.0)
    ren_right.SetBackground(colors.GetColor3d("DarkSlateGray"))

    # 손 액터와 관절 변환 객체 생성
    hand_actors, hand_joint_transforms = create_hand_actors()
    
    # 손 모델 초기화
    init_hand_model()
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

    # 웹소켓 및 타이머 콜백 설정 제거

    print("프로그램 시작: 숫자 키를 눌러 다양한 손 제스처를 테스트하세요.")
    print("1: 포인팅 제스처, 2: 피스 제스처, 4: 검지 굽히기, 5: 핀치 제스처, 7: 모든 손가락 움직임")

    # 초기 렌더링
    render_window.Render()
    
    # 시작 애니메이션 - 손가락 움직임 표시
    animate_fingers(hand_joint_transforms, render_window)
    
    # 인터랙티브 이벤트 루프 시작
    interactor.Initialize()
    interactor.Start()


if __name__ == "__main__":
    main()
