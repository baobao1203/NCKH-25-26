#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory("six_ws_robot")
    urdf_path = os.path.join(pkg_share, "urdf", "six_ws_robot.xacro")
    rviz_path = os.path.join(pkg_share, "urdf", "rviz", "six_ws_view.rviz")
    world_path = os.path.join(pkg_share, "worlds", "custom_empty.sdf")
    controllers_file = os.path.join(pkg_share, "config", "controllers.yaml")

    robot_description = Command(
        [
            FindExecutable(name="xacro"),
            " ",
            urdf_path,
            " ",
            "controllers_file:=",
            controllers_file,
        ]
    )

    use_sim_time = LaunchConfiguration("use_sim_time")

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": ParameterValue(robot_description, value_type=str),
                "use_sim_time": use_sim_time,
            }
        ],
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_path],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                os.path.join(
                    get_package_share_directory("ros_gz_sim"),
                    "launch",
                    "gz_sim.launch.py",
                )
            ]
        ),
        launch_arguments={
            "gz_args": f"-r {world_path}",
            "on_exit_shutdown": "true",
        }.items(),
    )

    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        # /clock must be GZ->ROS only (avoid Gazebo switching to /world/<name>/clock)
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    imu_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        arguments=["/imu@sensor_msgs/msg/Imu[gz.msgs.IMU"],
        remappings=[("/imu", "/imu/data")],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    rgb_bridge = Node(
        package="ros_gz_image",
        executable="image_bridge",
        output="screen",
        arguments=["camera/rgb/image_raw"],
        remappings=[("camera/rgb/image_raw", "/camera/rgb/image_raw")],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    depth_bridge = Node(
        package="ros_gz_image",
        executable="image_bridge",
        output="screen",
        arguments=["camera/depth/image_raw"],
        remappings=[("camera/depth/image_raw", "/camera/depth/image_raw")],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    rgb_info_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        arguments=[
            "/camera/rgb/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo"
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    depth_info_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        arguments=[
            "/camera/depth/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo"
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-name",
            "six_ws_robot",
            "-topic",
            "robot_description",
            "-x",
            "0",
            "-y",
            "0",
            "-z",
            "0.35",
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=["joint_state_broadcaster"],
    )

    wheel_controller = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=["wheel_velocity_controller"],
    )

    teleop = Node(
        package="six_ws_robot",
        executable="six_ws_teleop_controller.py",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    traction = Node(
        package="six_ws_robot",
        executable="traction_manager.py",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    status_visualizer = Node(
        package="six_ws_robot",
        executable="wheel_status_visualizer.py",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            robot_state_publisher,
            rviz,
            gazebo,
            clock_bridge,
            imu_bridge,
            rgb_bridge,
            depth_bridge,
            rgb_info_bridge,
            depth_info_bridge,
            RegisterEventHandler(
                OnProcessExit(
                    target_action=spawn_robot,
                    on_exit=[joint_state_broadcaster],
                )
            ),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=joint_state_broadcaster,
                    on_exit=[wheel_controller],
                )
            ),
            spawn_robot,
            teleop,
            traction,
            status_visualizer,
        ]
    )
