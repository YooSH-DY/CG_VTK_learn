import math
import vtkmodules.vtkInteractionStyle
import vtkmodules.vtkRenderingOpenGL2

from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import vtkQuadric
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkFiltersModeling import vtkOutlineFilter
from vtkmodules.vtkImagingHybrid import vtkSampleFunction
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkCamera,
    vtkPolyDataMapper,
    vtkProperty,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)
from vtkmodules.vtkCommonTransforms import vtkTransform  # 수정된 부분
from vtkmodules.vtkFiltersSources import vtkCubeSource, vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera


def create_quadric_actors(colors):
    # Quadric: 생성 및 샘플링
    quadric = vtkQuadric()
    quadric.SetCoefficients(0.5, 1, 0.2, 0, 0.1, 0, 0, 0.2, 0, 0)

    sample = vtkSampleFunction()
    sample.SetSampleDimensions(50, 50, 50)
    sample.SetImplicitFunction(quadric)

    # 등고선 필터
    contour = vtkContourFilter()
    contour.SetInputConnection(sample.GetOutputPort())
    contour.GenerateValues(5, 0, 1.2)

    contourMapper = vtkPolyDataMapper()
    contourMapper.SetInputConnection(contour.GetOutputPort())
    contourMapper.SetScalarRange(0, 1.2)

    contourActor = vtkActor()
    contourActor.SetMapper(contourMapper)

    # 아웃라인 필터
    outline = vtkOutlineFilter()
    outline.SetInputConnection(sample.GetOutputPort())

    outlineMapper = vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtkActor()
    outlineActor.SetMapper(outlineMapper)
    outlineActor.GetProperty().SetColor(colors.GetColor3d("Brown"))
    outlineActor.GetProperty().SetLineWidth(3.0)

    return contourActor, outlineActor


def create_hand_actors(colors):
    all_actors = []
    # 손 파이프라인을 위한 기본 변환 생성 (손 전체의 부모)
    hand_parent_transform = vtkTransform()
    hand_parent_transform.Identity()

    # ── 손바닥 ──
    palm_source = vtkCubeSource()
    palm_source.SetXLength(6.0)
    palm_source.SetYLength(5.0)
    palm_source.SetZLength(1.0)
    palm_source.SetCenter(0.0, 0.0, 0.0)

    palm_mapper = vtkPolyDataMapper()
    palm_mapper.SetInputConnection(palm_source.GetOutputPort())

    palm_actor = vtkActor()
    # 손바닥은 hand_parent_transform을 그대로 사용합니다.
    palm_actor.SetUserTransform(hand_parent_transform)
    palm_actor.SetMapper(palm_mapper)
    palm_actor.GetProperty().SetColor(colors.GetColor3d("Wheat"))
    palm_actor.RotateX(-10)
    all_actors.append(palm_actor)

    # ── 엄지: 파이프라인 방식으로 연결 ──
    # 첫 번째 엄지 관절/마디의 변환: 부모는 손바닥 변환(hand_parent_transform)
    thumb_transform1 = vtkTransform()
    thumb_transform1.SetInput(hand_parent_transform)

    # 엄지 첫번째 마디 (phalanx1)
    def create_phalanx(x_length, y_length, z_length):
        source = vtkCubeSource()
        source.SetXLength(x_length)
        source.SetYLength(y_length)
        source.SetZLength(z_length)
        # phalanx를 원점에서 생성한 후 transform으로 배치합니다.
        source.SetCenter(0, y_length / 2 - 0.05, 0)
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(source.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(colors.GetColor3d("Wheat"))
        actor.GetProperty().SetSpecular(0.3)
        actor.GetProperty().SetSpecularPower(20)
        return actor

    # 엄지 첫번째 마디를 생성하고, user transform 적용
    thumb_actor1 = create_phalanx(1.2, 1.4, 0.8)
    # thumb_actor1의 transform은 thumb_transform1에 추가 변경을 수행할 수 있습니다.
    thumb_actor1.SetUserTransform(thumb_transform1)
    # thumb_transform1의 위치 및 회전 (예시: 엄지 첫번째 마디 배치)
    thumb_transform1.Translate(-2.8, 1.0, 0.0)
    thumb_transform1.RotateZ(120)
    all_actors.append(thumb_actor1)

    # 두 번째 엄지 마디: 부모는 첫번째 엄지 마디의 transform
    thumb_transform2 = vtkTransform()
    thumb_transform2.SetInput(thumb_transform1)
    thumb_actor2 = create_phalanx(1.1, 1.2, 0.7)
    thumb_actor2.SetUserTransform(thumb_transform2)
    # 첫번째 마디 끝에서 이어지도록 (예시)
    thumb_transform2.Translate(1.1, 0.0, 0.0)
    all_actors.append(thumb_actor2)

    # 추가: 엄지의 세 번째 마디는 같은 방식으로 파이프라인 연결 가능
    thumb_transform3 = vtkTransform()
    thumb_transform3.SetInput(thumb_transform2)
    thumb_actor3 = create_phalanx(1.0, 1.0, 0.6)
    thumb_actor3.SetUserTransform(thumb_transform3)
    thumb_transform3.Translate(1.0, 0.0, 0.0)
    all_actors.append(thumb_actor3)

    # ── 나머지 손가락 (검지, 중지, 약지, 소지)도 유사한 방식으로
    # 각 손가락별로 기본 변환을 생성하고, 부모의 변환 체인을 이용하여 배치하면 됩니다.
    # 예시) 아래는 검지의 간단한 스텁 코드입니다.
    def create_index_finger():
        finger_actors = []
        index_transform1 = vtkTransform()
        index_transform1.SetInput(hand_parent_transform)
        index_actor1 = create_phalanx(1.0, 1.6, 0.7)
        index_actor1.SetUserTransform(index_transform1)
        index_transform1.Translate(-1.8, 2.5, 0.0)
        finger_actors.append(index_actor1)
        # 추가 마디들도 마찬가지로 체인 연결
        return finger_actors

    all_actors.extend(create_index_finger())
    # 다른 손가락들도 필요에 따라 추가 구현하세요.

    return all_actors


def main():
    colors = vtkNamedColors()

    # 렌더 윈도우 및 인터랙터 생성
    renWin = vtkRenderWindow()
    renWin.SetSize(1200, 600)
    renWin.SetWindowName("Quadric + Hand Pipeline Example")

    interactor = vtkRenderWindowInteractor()
    interactor.SetRenderWindow(renWin)

    # 왼쪽 렌더러: Quadric
    ren_left = vtkRenderer()
    ren_left.SetViewport(0.0, 0.0, 0.5, 1.0)
    ren_left.SetBackground(colors.GetColor3d("SlateGray"))
    contourActor, outlineActor = create_quadric_actors(colors)
    ren_left.AddActor(contourActor)
    ren_left.AddActor(outlineActor)

    # 오른쪽 렌더러: Hand (파이프라인 방식)
    ren_right = vtkRenderer()
    ren_right.SetViewport(0.5, 0.0, 1.0, 1.0)
    ren_right.SetBackground(colors.GetColor3d("DarkSlateGray"))
    hand_actors = create_hand_actors(colors)
    for actor in hand_actors:
        ren_right.AddActor(actor)

    # 카메라 설정
    cam_left = ren_left.GetActiveCamera()
    cam_left.SetPosition(0, -40, 30)
    cam_left.SetFocalPoint(0, 0, 0)
    cam_left.Azimuth(30)
    cam_left.Elevation(20)
    ren_left.ResetCamera()

    cam_right = ren_right.GetActiveCamera()
    cam_right.SetPosition(0, -5, 20)
    cam_right.SetFocalPoint(0, 0, 0)
    cam_right.SetViewUp(0, 1, 0)
    cam_right.Elevation(20)
    ren_right.ResetCamera()

    renWin.AddRenderer(ren_left)
    renWin.AddRenderer(ren_right)

    style = vtkInteractorStyleTrackballCamera()
    interactor.SetInteractorStyle(style)

    renWin.Render()
    interactor.Initialize()
    interactor.Start()


if __name__ == "__main__":
    main()
