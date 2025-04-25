import vtk
import os


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    subset = os.path.join(current_dir, "subset.vtk")
    density = os.path.join(current_dir, "density.vtk")
    combq = os.path.join(current_dir, "combq.bin")
    combxyz = os.path.join(current_dir, "combxyz.bin")

    if not os.path.exists(subset):
        print(f"오류: 파일을 찾을 수 없습니다: {subset}")
        return

    if not os.path.exists(density):
        print(f"오류: 파일을 찾을 수 없습니다: {density}")
        return

    print(f"파일 로드 중: {subset}, {density}")

    lut = vtk.vtkLookupTable()
    lut.SetNumberOfColors(257)
    lut.SetHueRange(0.0, 0.667)
    lut.Build()

    reader = vtk.vtkStructuredGridReader()
    reader.SetFileName(subset)
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

    conactor = vtk.vtkActor()
    conactor.SetMapper(contourmapper)

    ren = vtk.vtkRenderer()
    ren.AddActor(actor)
    ren.AddActor(conactor)
    ren.SetBackground(0.7, 0.7, 0.7)
    ren.SetViewport(0.0, 0.5, 0.25, 1.0)
    ren.GetActiveCamera().SetPosition(0, -2, 1)
    ren.ResetCamera()
    # =====================================================================

    reader1 = vtk.vtkStructuredGridReader()
    reader1.SetFileName(subset)
    reader1.Update()

    contour1 = vtk.vtkContourFilter()
    contour1.SetInputConnection(reader1.GetOutputPort())
    eval = contour1.GenerateValues(100, (reader1.GetOutput()).GetScalarRange())

    contourmapper1 = vtk.vtkPolyDataMapper()
    contourmapper1.SetInputConnection(contour1.GetOutputPort())
    eval = contourmapper1.SetScalarRange((reader1.GetOutput()).GetScalarRange())

    conactor1 = vtk.vtkActor()
    conactor1.SetMapper(contourmapper1)

    ren1 = vtk.vtkRenderer()
    ren1.AddActor(conactor1)
    ren1.SetBackground(0.7, 0.7, 0.7)
    ren1.SetViewport(0.25, 0.5, 0.5, 1.0)
    ren1.GetActiveCamera().SetPosition(0, -2, 1)
    ren1.ResetCamera()

    # ==========================================================================
    reader2 = vtk.vtkStructuredGridReader()
    reader2.SetFileName(density)
    reader2.Update()

    outline = vtk.vtkStructuredGridOutlineFilter()
    outline.SetInputConnection(reader2.GetOutputPort())

    outlineMapper = vtk.vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(outlineMapper)

    iso = vtk.vtkContourFilter()
    iso.SetInputConnection(reader2.GetOutputPort())
    iso.SetValue(0, 0.30)

    isoMapper = vtk.vtkPolyDataMapper()
    isoMapper.SetInputConnection(iso.GetOutputPort())
    isoMapper.SetScalarRange(reader2.GetOutput().GetScalarRange())

    isoActor = vtk.vtkActor()
    isoActor.SetMapper(isoMapper)

    ren2 = vtk.vtkRenderer()
    ren2.AddActor(outlineActor)
    ren2.AddActor(isoActor)
    ren2.SetBackground(0.7, 0.7, 0.7)
    ren2.SetViewport(0.5, 0.5, 0.75, 1.0)
    ren2.GetActiveCamera().SetPosition(0, -2, 1)
    ren2.ResetCamera()
    # ===========================================================================
    reader3 = vtk.vtkStructuredGridReader()
    reader3.SetFileName(density)
    reader3.Update()

    outline = vtk.vtkStructuredGridOutlineFilter()
    outline.SetInputConnection(reader3.GetOutputPort())

    outlineMapper = vtk.vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(outlineMapper)

    hhog = vtk.vtkHedgeHog()
    hhog.SetInputData(reader3.GetOutput())
    hhog.SetScaleFactor(0.001)

    hhogMapper = vtk.vtkPolyDataMapper()
    hhogMapper.SetInputConnection(hhog.GetOutputPort())
    hhogMapper.ScalarVisibilityOn()
    hhogMapper.SetScalarRange(reader3.GetOutput().GetScalarRange())

    hhogLut = vtk.vtkLookupTable()
    hhogLut.SetHueRange(0.0, 0.667)
    hhogLut.Build()
    hhogMapper.SetLookupTable(hhogLut)

    hhogActor = vtk.vtkActor()
    hhogActor.SetMapper(hhogMapper)

    ren3 = vtk.vtkRenderer()
    ren3.AddActor(hhogActor)
    ren3.AddActor(outlineActor)
    ren3.SetBackground(0.7, 0.7, 0.7)
    ren3.SetViewport(0.75, 0.5, 1.0, 1.0)
    ren3.GetActiveCamera().SetPosition(0, -2, 1)
    ren3.ResetCamera()
    # ===========================================================================
    reader4 = vtk.vtkStructuredGridReader()
    reader4.SetFileName(density)
    reader4.Update()

    outline = vtk.vtkStructuredGridOutlineFilter()
    outline.SetInputConnection(reader4.GetOutputPort())

    outlineMapper = vtk.vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(outlineMapper)

    seeds = vtk.vtkPointSource()
    seeds.SetRadius(3.0)
    seeds.SetCenter(reader4.GetOutput().GetCenter())
    seeds.SetNumberOfPoints(100)

    integ = vtk.vtkRungeKutta4()

    streamer = vtk.vtkStreamTracer()
    streamer.SetInputConnection(reader4.GetOutputPort())
    streamer.SetSourceConnection(seeds.GetOutputPort())
    streamer.SetMaximumPropagation(100)
    streamer.SetInitialIntegrationStep(0.1)
    streamer.SetIntegrationDirectionToBoth()
    streamer.SetIntegrator(integ)

    mapStreamLines = vtk.vtkPolyDataMapper()
    mapStreamLines.SetInputConnection(streamer.GetOutputPort())
    mapStreamLines.SetScalarRange(reader4.GetOutput().GetScalarRange())

    streamLineActor = vtk.vtkActor()
    streamLineActor.SetMapper(mapStreamLines)

    ren4 = vtk.vtkRenderer()
    ren4.AddActor(streamLineActor)
    ren4.AddActor(outlineActor)
    ren4.SetBackground(0.7, 0.7, 0.7)
    ren4.SetViewport(0.0, 0.0, 0.25, 0.5)
    ren4.GetActiveCamera().SetPosition(0, -2, 1)
    ren4.ResetCamera()
    # ===========================================================================
    reader5 = vtk.vtkStructuredGridReader()
    reader5.SetFileName(density)
    reader5.Update()

    outline = vtk.vtkStructuredGridOutlineFilter()
    outline.SetInputConnection(reader5.GetOutputPort())

    outlineMapper = vtk.vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(outlineMapper)

    arrow = vtk.vtkArrowSource()
    arrow.SetTipResolution(6)
    arrow.SetTipRadius(0.1)
    arrow.SetTipLength(0.35)
    arrow.SetShaftResolution(6)
    arrow.SetShaftRadius(0.03)

    glyph = vtk.vtkGlyph3D()
    glyph.SetInputConnection(reader5.GetOutputPort())
    glyph.SetSourceConnection(arrow.GetOutputPort())
    glyph.SetVectorModeToUseVector()
    glyph.SetColorModeToColorByScalar()
    glyph.SetScaleModeToDataScalingOff()
    glyph.OrientOn()
    glyph.SetScaleFactor(0.2)

    glyphMapper = vtk.vtkPolyDataMapper()
    glyphMapper.SetInputConnection(glyph.GetOutputPort())
    glyphMapper.SetLookupTable(lut)
    glyphMapper.ScalarVisibilityOn()
    glyphMapper.SetScalarRange(reader5.GetOutput().GetScalarRange())

    glyphActor = vtk.vtkActor()
    glyphActor.SetMapper(glyphMapper)

    ren5 = vtk.vtkRenderer()
    ren5.AddActor(glyphActor)
    ren5.AddActor(outlineActor)
    ren5.SetBackground(0.7, 0.7, 0.7)
    ren5.SetViewport(0.25, 0.0, 0.5, 0.5)
    ren5.GetActiveCamera().SetPosition(0, -2, 1)
    ren5.ResetCamera()
    # ===========================================================================
    reader6 = vtk.vtkStructuredGridReader()
    reader6.SetFileName(density)
    reader6.Update()

    outline = vtk.vtkStructuredGridOutlineFilter()
    outline.SetInputConnection(reader2.GetOutputPort())

    outlineMapper = vtk.vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(outlineMapper)

    plane = vtk.vtkPlane()
    plane.SetOrigin(reader6.GetOutput().GetCenter())
    plane.SetNormal(-0.287, 0, 0.9579)

    planeCut = vtk.vtkCutter()
    planeCut.SetInputConnection(reader6.GetOutputPort())
    planeCut.SetCutFunction(plane)

    cutMapper = vtk.vtkPolyDataMapper()
    cutMapper.SetInputConnection(planeCut.GetOutputPort())
    cutMapper.SetScalarRange(reader6.GetOutput().GetScalarRange())

    cutActor = vtk.vtkActor()
    cutActor.SetMapper(cutMapper)

    ren6 = vtk.vtkRenderer()
    ren6.AddActor(cutActor)
    ren6.AddActor(outlineActor)
    ren6.SetBackground(0.7, 0.7, 0.7)
    ren6.SetViewport(0.5, 0.0, 0.75, 0.5)
    ren6.GetActiveCamera().SetPosition(0, -2, 1)
    ren6.ResetCamera()
    # ===========================================================================
    reader7 = vtk.vtkStructuredGridReader()
    reader7.SetFileName(density)
    reader7.Update()

    outline = vtk.vtkStructuredGridOutlineFilter()
    outline.SetInputConnection(reader2.GetOutputPort())

    outlineMapper = vtk.vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(outlineMapper)

    plane7 = vtk.vtkPlane()
    plane7.SetOrigin(reader7.GetOutput().GetCenter())
    plane7.SetNormal(-0.287, 0, 0.9579)

    clip = vtk.vtkClipDataSet()
    clip.SetInputConnection(reader7.GetOutputPort())
    clip.SetClipFunction(plane7)
    clip.InsideOutOn()

    clipMapper = vtk.vtkDataSetMapper()
    clipMapper.SetInputConnection(clip.GetOutputPort())
    clipMapper.SetScalarRange(reader7.GetOutput().GetScalarRange())

    clipActor = vtk.vtkActor()
    clipActor.SetMapper(clipMapper)

    ren7 = vtk.vtkRenderer()
    ren7.AddActor(clipActor)
    ren7.AddActor(outlineActor)
    ren7.SetBackground(0.7, 0.7, 0.7)
    ren7.SetViewport(0.75, 0.0, 1.0, 0.5)
    ren7.GetActiveCamera().SetPosition(0, -2, 1)
    ren7.ResetCamera()

    # ===========================================================================

    renWin = vtk.vtkRenderWindow()
    renWin.AddRenderer(ren)
    renWin.AddRenderer(ren1)
    renWin.AddRenderer(ren2)
    renWin.AddRenderer(ren3)
    renWin.AddRenderer(ren6)
    renWin.AddRenderer(ren7)
    renWin.AddRenderer(ren4)
    renWin.AddRenderer(ren5)

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
