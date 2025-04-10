import vtk
import os


def main():
    # 현재 스크립트가 있는 디렉토리에서 파일 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    subsetFn = os.path.join(current_dir, "subset.vtk")
    densityFn = os.path.join(current_dir, "density.vtk")

    # 파일 존재 확인
    if not os.path.exists(subsetFn):
        print(f"오류: 파일을 찾을 수 없습니다: {subsetFn}")
        return

    if not os.path.exists(densityFn):
        print(f"오류: 파일을 찾을 수 없습니다: {densityFn}")
        return

    print(f"파일 로드 중: {subsetFn}, {densityFn}")

    # 기존 코드는 그대로 유지
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfColors(257)
    lut.SetHueRange(0.0, 0.667)
    lut.Build()

    # =====================================================================

    reader = vtk.vtkStructuredGridReader()
    reader.SetFileName(subsetFn)
    reader.Update()

    contour = vtk.vtkContourFilter()
    contour.SetInputConnection(reader.GetOutputPort())
    contour.SetValue(0, 0.26)
    contourmapper = vtk.vtkPolyDataMapper()
    contourmapper.SetInputConnection(contour.GetOutputPort())
    eval = contourmapper.SetScalarRange((reader.GetOutput()).GetScalarRange())

    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputConnection(reader.GetOutputPort())
    mapper.SetLookupTable(lut)
    mapper.SetScalarRange(0.0, 0.7)
    mapper.ScalarVisibilityOn()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    # actor.GetProperty().SetRepresentationToWireframe()

    conactor = vtk.vtkActor()
    conactor.SetMapper(contourmapper)

    ren = vtk.vtkRenderer()
    ren.AddActor(actor)
    ren.AddActor(conactor)
    ren.SetBackground(1, 1, 1)
    ren.SetViewport(0.0, 0.5, 0.25, 1.0)
    ren.GetActiveCamera().SetPosition(0, 0, -1)
    ren.ResetCamera()
    # =====================================================================

    reader1 = vtk.vtkStructuredGridReader()
    reader1.SetFileName(subsetFn)
    reader1.Update()

    contour1 = vtk.vtkContourFilter()
    contour1.SetInputConnection(reader1.GetOutputPort())
    # �̺κ��� ���̴�
    eval = contour1.GenerateValues(100, (reader1.GetOutput()).GetScalarRange())
    # contour.SetValue(0,0.26)

    contourmapper1 = vtk.vtkPolyDataMapper()
    contourmapper1.SetInputConnection(contour1.GetOutputPort())
    eval = contourmapper1.SetScalarRange((reader1.GetOutput()).GetScalarRange())

    # contourmapper1.ScalarVisibilityOff()
    conactor1 = vtk.vtkActor()
    conactor1.SetMapper(contourmapper1)

    ren1 = vtk.vtkRenderer()
    ren1.AddActor(conactor1)
    ren1.SetBackground(1, 1, 1)
    ren1.SetViewport(0.25, 0.5, 0.5, 1.0)
    ren1.GetActiveCamera().SetPosition(0, 0, -1)
    ren1.ResetCamera()

    # ==========================================================================

    # ===========================================================================

    renWin = vtk.vtkRenderWindow()
    renWin.AddRenderer(ren)
    renWin.AddRenderer(ren1)

    renWin.SetSize(1250, 800)

    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renWin)

    iren.Initialize()
    renWin.Render()
    iren.Start()


def get_program_parameters():
    import argparse

    description = "Demonstrates the use and manipulation of lookup tables."
    epilogue = """
    First create a simple pipeline that reads a structured grid
    and then extracts a plane from the grid. The plane will be colored
    differently by using different lookup tables.
    
    Note: The Update method is manually invoked because it causes the
    reader to read; later on we use the output of the reader to set
    a range for the scalar values.
    """
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilogue,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("subsetFilename", help="subset.vtk")
    parser.add_argument("densityFilename", help="density.vtk")
    args = parser.parse_args()
    return args.subsetFilename, args.densityFilename


if __name__ == "__main__":
    main()
