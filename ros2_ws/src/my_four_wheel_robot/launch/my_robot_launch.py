import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('my_four_wheel_robot')
    urdf_path = os.path.join(pkg_share, 'urdf/my_robot.urdf.xacro')

    return LaunchDescription([
        # Robot state publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': os.popen(f'xacro {urdf_path}').read()}]
        ),
        # Joint state publisher GUI
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui'
        ),
        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', os.path.join(pkg_share, 'rviz/config.rviz')]
        ),
        # Gazebo (nếu muốn simulate)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')])
        ),
        # Bridge for TF
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=['/model/my_robot/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V]'],  # Corrected closing bracket
            output='screen'
        ),
        # Spawn robot vào Gazebo
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-name', 'my_robot',
                '-topic', 'robot_description',
                '-x', '0', '-y', '0', '-z', '0.1'  # Nhấc robot lên một chút để tránh dính sàn
            ],
            output='screen'
        )
    ])
