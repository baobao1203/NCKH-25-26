#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    delete_db = LaunchConfiguration("delete_db")

    rgb_topic = "/camera/rgb/image_raw"
    depth_topic = "/camera/depth/image_raw"
    camera_info_topic = "/camera/rgb/camera_info"
    odom_topic = "/odom"  # ⭐ Topic odom từ hybrid_odometry_publisher

    # ===== Tham số RTAB-Map dùng chung =====
    rtabmap_parameters = {
        # Frame configuration
        "frame_id": "base_footprint",
        "map_frame_id": "map",
        "odom_frame_id": "odom",
        "publish_tf": True,
        
        # ⭐ QUAN TRỌNG: Subscribe vào odom topic
        "subscribe_depth": True,
        "subscribe_rgb": True,
        "subscribe_odom": True,        # ⭐ BẬT odom subscription
        "subscribe_odom_info": False,
        "subscribe_scan": False,
        "subscribe_scan_cloud": False,
        
        # Synchronization
        "approx_sync": True,
        "approx_sync_max_interval": 0.5,
        "queue_size": 100,
        "wait_for_transform": 1.0,     # Tăng để chờ TF
        
        # ⭐ THRESHOLD THẤP để tạo node thường xuyên hơn
        "RGBD/AngularUpdate": "0.1",   # rad - tạo node mỗi 0.1 rad xoay (~6 độ)
        "RGBD/LinearUpdate": "0.1",    # m - tạo node mỗi 0.1m di chuyển
        
        # Memory
        "Mem/IncrementalMemory": "true",
        "Mem/InitWMWithAllNodes": "false",
        "Mem/UseOdomGravity": "true",
        "Mem/STMSize": "30",           # Short-term memory size
        
        # Loop closure
        "RGBD/NeighborLinkRefining": "true",
        "RGBD/ProximityBySpace": "true",
        "RGBD/ProximityByTime": "false",
        "RGBD/ProximityMaxGraphDepth": "50",
        "RGBD/ProximityPathMaxNeighbors": "10",
        
        # ⭐ Visual features - giảm threshold để dễ tracking
        "Vis/MinInliers": "10",        # Giảm từ 15 → 10
        "Vis/InlierDistance": "0.2",   # Tăng tolerance
        "Vis/MaxFeatures": "1000",     # Nhiều features hơn
        "Vis/CorType": "0",            # Features Matching
        "Vis/EstimationType": "1",     # 0=3D->3D, 1=3D->2D (PnP)
        
        # Registration
        "Reg/Force3DoF": "true",       # 2D SLAM
        "Reg/Strategy": "0",           # 0=Vis only (không cần ICP cho RGBD)
        
        # Optimization
        "Optimizer/Strategy": "1",     # 1=g2o (ổn định hơn TORO)
        "Optimizer/Iterations": "20",
        "Optimizer/Epsilon": "0.0001",
        "Optimizer/Robust": "true",
        "RGBD/OptimizeFromGraphEnd": "false",
        "RGBD/OptimizeMaxError": "3.0",
        
        # Detection rate
        "Rtabmap/TimeThr": "0",
        "Rtabmap/MemoryThr": "0",
        "Rtabmap/DetectionRate": "2.0",  # ⭐ 2Hz - tạo map nhanh hơn
        "Rtabmap/CreateIntermediateNodes": "true",  # ⭐ Tạo nodes trung gian
        
        # Keypoint detector
        "Kp/DetectorStrategy": "6",    # ORB
        "Kp/MaxFeatures": "500",
        "Kp/MinDepth": "0.2",
        "Kp/MaxDepth": "8.0",
        
        # Grid map (cho 2D occupancy grid)
        "Grid/FromDepth": "true",
        "Grid/DepthDecimation": "2",
        "Grid/RangeMax": "5.0",
        "Grid/RangeMin": "0.3",
        "Grid/MaxObstacleHeight": "1.5",
        "Grid/MaxGroundHeight": "0.05",
        "Grid/NormalsSegmentation": "false",
        "Grid/CellSize": "0.05",
        "Grid/RayTracing": "true",
    }

    # ===== Common remappings =====
    rtabmap_remappings = [
        ("rgb/image", rgb_topic),
        ("depth/image", depth_topic),
        ("rgb/camera_info", camera_info_topic),
        ("odom", odom_topic),  # ⭐ QUAN TRỌNG: remap odom
    ]

    return LaunchDescription(
        [
            # ============== ARGUMENTS ==============
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("delete_db", default_value="true"),
            SetParameter(name="use_sim_time", value=use_sim_time),
            
            # ============== HYBRID ODOMETRY ==============
            Node(
                package="six_ws_robot",
                executable="hybrid_odometry_publisher.py",
                name="hybrid_odometry_publisher",
                output="screen",
                parameters=[{"use_sim_time": use_sim_time}],
            ),
            
            # ============== RTAB-MAP SLAM (delete_db=true) ==============
            Node(
                package="rtabmap_slam",
                executable="rtabmap",
                name="rtabmap",
                output="screen",
                condition=IfCondition(delete_db),
                parameters=[rtabmap_parameters],
                arguments=["--delete_db_on_start"],
                remappings=rtabmap_remappings,
            ),
            
            # ============== RTAB-MAP SLAM (delete_db=false) ==============
            Node(
                package="rtabmap_slam",
                executable="rtabmap",
                name="rtabmap",
                output="screen",
                condition=UnlessCondition(delete_db),
                parameters=[rtabmap_parameters],
                remappings=rtabmap_remappings,
            ),
            
            # ============== VISUALIZATION ==============
            Node(
                package="rtabmap_viz",
                executable="rtabmap_viz",
                name="rtabmap_viz",
                output="screen",
                parameters=[
                    {
                        "frame_id": "base_footprint",
                        "odom_frame_id": "odom",
                        "subscribe_odom_info": False,
                        "subscribe_rgb": True,
                        "subscribe_depth": True,
                        "approx_sync": True,
                        "queue_size": 100,
                    }
                ],
                remappings=[
                    ("rgb/image", rgb_topic),
                    ("depth/image", depth_topic),
                    ("rgb/camera_info", camera_info_topic),
                    ("odom", odom_topic),
                ],
            ),
        ]
    )
