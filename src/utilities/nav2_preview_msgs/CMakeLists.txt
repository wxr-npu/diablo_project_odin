cmake_minimum_required(VERSION 3.5)
project(nav2_preview_msgs)

find_package(ament_cmake REQUIRED)
find_package(nav2_common REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geographic_msgs)
find_package(action_msgs REQUIRED)

nav2_package()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  # TODO(jwallace42): This is a work around for https://github.com/ros2/rosidl_typesupport_fastrtps/issues/28
  add_compile_options(-Wno-error=deprecated)
endif()

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/BackUp.action"
  "action/DriveOnHeading.action"
  DEPENDENCIES builtin_interfaces geometry_msgs std_msgs action_msgs nav_msgs geographic_msgs
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
