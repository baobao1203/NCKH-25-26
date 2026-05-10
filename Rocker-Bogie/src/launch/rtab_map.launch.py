#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # ============== THAM SỐ CÓ THỂ CHỈNH ==============
    use_sim_time = False  # Đặt False vì bạn đang chạy real robot
    delete_db = True  # Xóa database cũ mỗi lần chạy

    rgb_topic = "/camera/rgb/image_raw"
    depth_topic = "/camera/depth/image_raw"
    camera_info_topic = "/camera/rgb/camera_info"

    # Nếu camera frame của bạn là rgb_camera hoặc camera_link, sửa ở đây
    camera_base_frame = "rgb_camera"  # Thường là "camera_link" hoặc "rgb_camera"

    return LaunchDescription(
        [
            # ============== ARGUMENTS ==============
            DeclareLaunchArgument("use_sim_time", default_value=str(use_sim_time)),
            DeclareLaunchArgument("delete_db", default_value=str(delete_db)),
            # ============== RTAB-MAP ==============
            Node(
                package="rtabmap_odom",
                executable="rgbd_odometry",
                name="rgbd_odometry",
                output="screen",
                parameters=[
                    {
                        "frame_id": "base_link",
                        "odom_frame_id": "odom",
                        "base_frame_id": "base_link",
                        "approx_sync": True,
                        "approx_sync_max_interval": 0.1,  # Giúp fix warning time diff
                        "queue_size": 10,
                    }
                ],
                remappings=[
                    ("rgb/image", rgb_topic),
                    ("depth/image", depth_topic),
                    ("rgb/camera_info", camera_info_topic),
                ],
            ),
            Node(
                package="rtabmap_slam",
                executable="rtabmap",
                name="rtabmap",
                output="screen",
                parameters=[
                    {
                        "frame_id": "base_link",
                        "map_frame_id": "map",
                        "odom_frame_id": "odom",
                        "base_frame_id": "base_link",
                        "approx_sync": True,
                        "approx_sync_max_interval": 0.1,
                        "Mem/IncrementalMemory": True,
                        "Mem/InitWMWithAllNodes": True,
                        "RGBD/NeighborLinkRefine": True,
                        "RGBD/ProximityBySpace": True,
                        "Optimizer/Strategy": 1,  # 1 = G2O, 2 = TORO
                        "Kp/DetectorStrategy": 6,  # ORB
                    }
                ],
                arguments=["--delete_db_on_start"] if delete_db else [],
                remappings=[
                    ("rgb/image", rgb_topic),
                    ("depth/image", depth_topic),
                    ("rgb/camera_info", camera_info_topic),
                ],
            ),
            # ============== VISUALIZATION ==============
            Node(
                package="rtabmap_viz",
                executable="rtabmap_viz",
                name="rtabmap_viz",
                output="screen",
                parameters=[
                    {
                        "frame_id": "base_link",
                        "approx_sync": True,
                    }
                ],
                remappings=[
                    ("rgb/image", rgb_topic),
                    ("depth/image", depth_topic),
                    ("rgb/camera_info", camera_info_topic),
                ],
            ),
            # Optional: RViz
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=[
                    "-d",
                    os.path.join(
                        get_package_share_directory("rtabmap_launch"),
                        "rviz",
                        "rtabmap.rviz",
                    ),
                ],
            ),
        ]
    )
