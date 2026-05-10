from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    params_file = os.path.join(
        get_package_share_directory("xtion_rtabmap_test"),
        "config",
        "rtabmap_params.yaml",
    )
    default_gui_cfg = os.path.expanduser("~/.ros/xtion_rtabmap_gui.ini")
    rgb_topic = LaunchConfiguration("rgb_topic")
    depth_topic = LaunchConfiguration("depth_topic")
    camera_info_topic = LaunchConfiguration("camera_info_topic")
    gui_cfg = LaunchConfiguration("gui_cfg")

    rgb_topic_arg = DeclareLaunchArgument(
        "rgb_topic", default_value="/camera/rgb/image_raw"
    )
    depth_topic_arg = DeclareLaunchArgument(
        "depth_topic", default_value="/camera/depth/image"
    )
    camera_info_topic_arg = DeclareLaunchArgument(
        "camera_info_topic", default_value="/camera/rgb/camera_info"
    )
    gui_cfg_arg = DeclareLaunchArgument("gui_cfg", default_value=default_gui_cfg)
    camera_driver = ComposableNodeContainer(
        name="container",
        namespace="camera",
        package="rclcpp_components",
        executable="component_container",
        composable_node_descriptions=[
            ComposableNode(
                package="openni2_camera",
                plugin="openni2_wrapper::OpenNI2Driver",
                name="driver",
                namespace="camera",
                parameters=[
                    {"depth_registration": True},
                    {"color_depth_synchronization": True},
                    {"use_device_time": True},
                    {"rgb_frame_id": "camera_rgb_optical_frame"},
                    {"depth_frame_id": "camera_depth_optical_frame"},
                    {"ir_frame_id": "camera_ir_optical_frame"},
                ],
            ),
        ],
        output="screen",
    )

    camera_tfs = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("openni2_camera"),
                "launch",
                "tfs.launch.py",
            )
        ),
        launch_arguments={"namespace": "camera", "tf_prefix": ""}.items(),
    )

    rgbd_odom = Node(
        package="rtabmap_odom",
        executable="rgbd_odometry",
        name="rgbd_odometry",
        output="screen",
        parameters=[params_file],
        remappings=[
            ("rgb/image", rgb_topic),
            ("depth/image", depth_topic),
            ("rgb/camera_info", camera_info_topic),
            ("odom", "/visual_odom"),
        ],
    )

    rtabmap = Node(
        package="rtabmap_slam",
        executable="rtabmap",
        name="rtabmap",
        output="screen",
        parameters=[params_file],
        remappings=[
            ("rgb/image", rgb_topic),
            ("depth/image", depth_topic),
            ("rgb/camera_info", camera_info_topic),
            ("odom", "/visual_odom"),
        ],
    )

    rtabmap_viz = Node(
        package="rtabmap_viz",
        executable="rtabmap_viz",
        name="rtabmap_viz",
        output="screen",
        arguments=[gui_cfg],
        parameters=[params_file],
        remappings=[
            ("rgb/image", rgb_topic),
            ("depth/image", depth_topic),
            ("rgb/camera_info", camera_info_topic),
            ("odom", "/visual_odom"),
        ],
    )

    return LaunchDescription(
        [
            rgb_topic_arg,
            depth_topic_arg,
            camera_info_topic_arg,
            gui_cfg_arg,
            camera_driver,
            camera_tfs,
            rgbd_odom,
            rtabmap,
            rtabmap_viz,
        ]
    )
