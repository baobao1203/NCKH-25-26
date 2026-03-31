import os

"""
===========================================================
LAUNCH FILE CHO ROBOT 4 BÁNH - BẢN DỄ ĐỌC, DỄ DEBUG
===========================================================

THỨ TỰ CHẠY:
1. publish robot_description
2. mở RViz
3. mở Gazebo Sim
4. bridge /clock
5. spawn robot vào Gazebo
6. spawn controller
7. bridge camera / imu
8. teleop

LƯU Ý:
- Không dùng joint_state_publisher khi đang debug ros2_control
- Camera bridge dùng topic ngắn theo đúng xacro mới
===========================================================
"""

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory("my_four_wheel_robot")

    urdf_path = os.path.join(pkg_share, "urdf", "my_robot.urdf.xacro")
    world_path = os.path.join(pkg_share, "worlds", "custom_empty.sdf")
    rviz_config = os.path.join(pkg_share, "rviz", "config.rviz")
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

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            # -------------------------------------------------
            # robot_state_publisher
            # -------------------------------------------------
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[
                    {
                        "robot_description": ParameterValue(
                            robot_description, value_type=str
                        )
                    },
                    {"use_sim_time": LaunchConfiguration("use_sim_time")},
                    {"ignore_timestamp": True},  # ← dòng mới
                ],
            ),
            # -------------------------------------------------
            # RViz
            # -------------------------------------------------
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", rviz_config],
                parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
            ),
            # -------------------------------------------------
            # Gazebo Sim
            # -------------------------------------------------
            IncludeLaunchDescription(
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
            ),
            # -------------------------------------------------
            # Clock bridge
            # -------------------------------------------------
            # Node(
            #     package="ros_gz_bridge",
            #     executable="parameter_bridge",
            #     name="clock_bridge",
            #     arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock]"],
            #     parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
            #     output="screen",
            # ),
            # -------------------------------------------------
            # Spawn robot
            # -------------------------------------------------
            TimerAction(
                period=3.0,
                actions=[
                    Node(
                        package="ros_gz_sim",
                        executable="create",
                        name="spawn_my_robot",
                        arguments=[
                            "-name",
                            "my_robot",
                            "-topic",
                            "robot_description",
                            "-x",
                            "0",
                            "-y",
                            "0",
                            "-z",
                            "0.20",
                        ],
                        output="screen",
                        parameters=[
                            {"use_sim_time": LaunchConfiguration("use_sim_time")}
                        ],
                    )
                ],
            ),
            # -------------------------------------------------
            # Spawn joint_state_broadcaster
            # -------------------------------------------------
            TimerAction(
                period=12.0,
                actions=[
                    Node(
                        package="controller_manager",
                        executable="spawner",
                        name="spawner_joint_state_broadcaster",
                        arguments=[
                            "joint_state_broadcaster",
                            "--controller-manager",
                            "/controller_manager",
                            "--controller-manager-timeout",
                            "20",
                        ],
                        output="screen",
                    )
                ],
            ),
            # -------------------------------------------------
            # Spawn diff_drive_controller
            # -------------------------------------------------
            TimerAction(
                period=14.0,
                actions=[
                    Node(
                        package="controller_manager",
                        executable="spawner",
                        name="spawner_diff_drive_base_controller",
                        arguments=[
                            "diff_drive_base_controller",
                            "--controller-manager",
                            "/controller_manager",
                            "--controller-manager-timeout",
                            "20",
                        ],
                        output="screen",
                    )
                ],
            ),
            # -------------------------------------------------
            # RGB image bridge
            # -------------------------------------------------
            TimerAction(
                period=10.0,
                actions=[
                    Node(
                        package="ros_gz_image",
                        executable="image_bridge",
                        name="rgb_image_bridge",
                        arguments=["camera/rgb/image_raw"],
                        remappings=[("camera/rgb/image_raw", "/camera/rgb/image_raw")],
                        parameters=[
                            {"use_sim_time": LaunchConfiguration("use_sim_time")}
                        ],
                        output="screen",
                    )
                ],
            ),
            # -------------------------------------------------
            # Depth image bridge
            # -------------------------------------------------
            TimerAction(
                period=10.0,
                actions=[
                    Node(
                        package="ros_gz_image",
                        executable="image_bridge",
                        name="depth_image_bridge",
                        arguments=["camera/depth/image_raw"],
                        remappings=[
                            ("camera/depth/image_raw", "/camera/depth/image_raw")
                        ],
                        parameters=[
                            {"use_sim_time": LaunchConfiguration("use_sim_time")}
                        ],
                        output="screen",
                    )
                ],
            ),
            # -------------------------------------------------
            # IMU bridge
            # -------------------------------------------------
            TimerAction(
                period=10.0,
                actions=[
                    Node(
                        package="ros_gz_bridge",
                        executable="parameter_bridge",
                        name="imu_bridge",
                        arguments=["/imu@sensor_msgs/msg/Imu[gz.msgs.IMU]"],
                        remappings=[("/imu", "/imu/data")],
                        parameters=[
                            {"use_sim_time": LaunchConfiguration("use_sim_time")}
                        ],
                        output="screen",
                    )
                ],
            ),
            # -------------------------------------------------
            # Teleop
            # -------------------------------------------------
            Node(
                package="teleop_twist_keyboard",
                executable="teleop_twist_keyboard",
                name="teleop",
                prefix="gnome-terminal --",
                remappings=[
                    ("/cmd_vel", "/diff_drive_base_controller/cmd_vel_unstamped")
                ],
                output="screen",
            ),
        ]
    )
