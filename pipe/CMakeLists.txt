cmake_minimum_required(VERSION 3.12)

project(RoboticArm)

find_package(VTK COMPONENTS 
  CommonColor
  CommonCore
  FiltersSources
  InteractionStyle
  RenderingContextOpenGL2
  RenderingCore
  RenderingFreeType
  RenderingGL2PSOpenGL2
  RenderingOpenGL2
)

if (NOT VTK_FOUND)
  message(FATAL_ERROR "VTK not found. Please specify VTK_DIR.")
endif()

include(${VTK_USE_FILE})

add_executable(RoboticArm 2.cpp)
target_link_libraries(RoboticArm ${VTK_LIBRARIES})