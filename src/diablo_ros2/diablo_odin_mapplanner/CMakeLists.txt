cmake_minimum_required(VERSION 3.5)
project(diablo_odin_mapplanner)

if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/PlanPath.srv"
  DEPENDENCIES geometry_msgs nav_msgs
)

include_directories(include)

add_executable(map_planner_node
  src/map_planner.cpp
)

ament_target_dependencies(map_planner_node
  rclcpp
  geometry_msgs
  nav_msgs
  std_msgs
  tf2
  tf2_ros
  tf2_geometry_msgs
)

add_executable(goal_state_machine_node
  src/goal_state_machine.cpp
)

ament_target_dependencies(goal_state_machine_node
  rclcpp
  geometry_msgs
  std_msgs
  tf2
  tf2_ros
  tf2_geometry_msgs
)

rosidl_target_interfaces(map_planner_node
  ${PROJECT_NAME} "rosidl_typesupport_cpp")
rosidl_target_interfaces(goal_state_machine_node
  ${PROJECT_NAME} "rosidl_typesupport_cpp")

install(TARGETS
  map_planner_node
  goal_state_machine_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY maps
  DESTINATION share/${PROJECT_NAME}
)

ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
