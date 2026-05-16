cmake_minimum_required(VERSION 3.8)
project(six_ws_robot)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch urdf worlds
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/six_ws_teleop_controller.py
    scripts/traction_manager.py
    scripts/wheel_status_visualizer.py
    scripts/hybrid_odometry_publisher.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
