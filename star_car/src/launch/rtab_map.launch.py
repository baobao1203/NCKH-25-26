#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    delete_db    = LaunchConfiguration("delete_db")

    rgb_topic         = "/camera/rgb/image_raw"
    depth_topic       = "/camera/depth/image_raw"
    camera_info_topic = "/camera/rgb/camera_info"
    odom_topic        = "/odom"

    # ===== Tham số RTAB-Map =====
    rtabmap_params = {
        # ----- Frames -----
        "frame_id":     "base_footprint",
        "map_frame_id": "map",
        "odom_frame_id": "odom",
        "publish_tf":    True,

        # ----- Subscriptions -----
        "subscribe_depth":     True,
        "subscribe_rgb":       True,
        "subscribe_odom":      True,
        "subscribe_odom_info": False,
        "subscribe_scan":      False,
        "subscribe_scan_cloud": False,

        # ----- Sync -----
        "approx_sync":              True,
        "approx_sync_max_interval": 0.5,
        "queue_size":               100,
        "wait_for_transform":       1.0,

        # ----- Khi nào tạo node mới -----
        "RGBD/AngularUpdate": "0.1",       # mỗi ~6 độ
        "RGBD/LinearUpdate":  "0.1",       # mỗi 10 cm
        "Rtabmap/DetectionRate":        "2.0",
        "Rtabmap/CreateIntermediateNodes": "true",

        # ----- Memory -----
        "Mem/IncrementalMemory":  "true",
        "Mem/InitWMWithAllNodes": "false",
        "Mem/STMSize":            "30",

        # ----- Loop closure -----
        "RGBD/NeighborLinkRefining":      "true",
        "RGBD/ProximityBySpace":          "true",
        "RGBD/ProximityMaxGraphDepth":    "50",
        "RGBD/ProximityPathMaxNeighbors": "10",
        "RGBD/OptimizeFromGraphEnd":      "false",
        "RGBD/OptimizeMaxError":          "3.0",

        # ----- Visual features -----
        "Vis/MinInliers":      "10",
        "Vis/InlierDistance":  "0.2",
        "Vis/MaxFeatures":     "1000",
        "Vis/CorType":         "0",
        "Vis/EstimationType":  "1",

        # ----- Registration -----
        "Reg/Force3DoF": "true",
        "Reg/Strategy":  "0",

        # ----- Optimizer -----
        "Optimizer/Strategy":   "1",
        "Optimizer/Iterations": "20",
        "Optimizer/Epsilon":    "0.0001",
        "Optimizer/Robust":     "true",

        # ----- Feature detector -----
        "Kp/DetectorStrategy": "6",
        "Kp/MaxFeatures":      "500",
        "Kp/MinDepth":         "0.2",
        "Kp/MaxDepth":         "8.0",

        # ----- 2-D occupancy grid -----
        "Grid/FromDepth":          "true",
        "Grid/DepthDecimation":    "2",
        "Grid/RangeMax":           "5.0",
        "Grid/RangeMin":           "0.3",
        "Grid/MaxObstacleHeight":  "1.5",
        "Grid/MaxGroundHeight":    "0.05",
        "Grid/NormalsSegmentation": "false",
        "Grid/CellSize":           "0.05",
        "Grid/RayTracing":         "true",

        # ----- Misc -----
        "Rtabmap/TimeThr":   "0",
        "Rtabmap/MemoryThr": "0",
    }

    rtabmap_remaps = [
        ("rgb/image",      rgb_topic),
        ("depth/image",    depth_topic),
        ("rgb/camera_info", camera_info_topic),
        ("odom",            odom_topic),
    ]

    return LaunchDescription([

        # ===== Arguments =====
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        DeclareLaunchArgument("delete_db",    default_value="true"),
        SetParameter(name="use_sim_time", value=use_sim_time),

        # ===== Hybrid Odometry =====
        Node(
            package="six_ws_robot",
            executable="hybrid_odometry_publisher.py",
            name="hybrid_odometry_publisher",
            output="screen",
            parameters=[{"use_sim_time": use_sim_time}],
        ),

        # ===== RTAB-Map (delete DB) =====
        Node(
            package="rtabmap_slam",
            executable="rtabmap",
            name="rtabmap",
            output="screen",
            condition=IfCondition(delete_db),
            parameters=[rtabmap_params],
            arguments=["--delete_db_on_start"],
            remappings=rtabmap_remaps,
        ),

        # ===== RTAB-Map (keep DB) =====
        Node(
            package="rtabmap_slam",
            executable="rtabmap",
            name="rtabmap",
            output="screen",
            condition=UnlessCondition(delete_db),
            parameters=[rtabmap_params],
            remappings=rtabmap_remaps,
        ),

        # ===== rtabmap_viz =====
        Node(
            package="rtabmap_viz",
            executable="rtabmap_viz",
            name="rtabmap_viz",
            output="screen",
            parameters=[{
                "frame_id":           "base_footprint",
                "odom_frame_id":      "odom",
                "subscribe_odom_info": False,
                "subscribe_rgb":       True,
                "subscribe_depth":     True,
                "approx_sync":         True,
                "queue_size":          100,
            }],
            remappings=[
                ("rgb/image",       rgb_topic),
                ("depth/image",     depth_topic),
                ("rgb/camera_info", camera_info_topic),
                ("odom",            odom_topic),
            ],
        ),
    ])
