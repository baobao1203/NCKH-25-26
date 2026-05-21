#!/usr/bin/env python3

from builtin_interfaces.msg import Duration
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState
from visualization_msgs.msg import Marker, MarkerArray

ORDER = ["lf", "lm", "lr", "rf", "rm", "rr"]
WHEEL_TEXT_POSES = {
    "lf": (0.40, 0.30, 0.05),
    "lm": (0.00, 0.30, 0.05),
    "lr": (-0.40, 0.30, 0.05),
    "rf": (0.40, -0.30, 0.05),
    "rm": (0.00, -0.30, 0.05),
    "rr": (-0.40, -0.30, 0.05),
}


class WheelStatusVisualizer(Node):
    def __init__(self):
        super().__init__("wheel_status_visualizer")
        self.latest_joint_state = {}
        self.latest_imu = None

        self.create_subscription(JointState, "/joint_states", self._on_joint_states, 10)
        self.create_subscription(Imu, "/imu/data", self._on_imu, 10)
        self.marker_publisher = self.create_publisher(
            MarkerArray, "/robot_status_markers", 10
        )
        self.create_timer(0.2, self._publish_markers)

    def _on_joint_states(self, msg: JointState) -> None:
        for index, name in enumerate(msg.name):
            self.latest_joint_state[name] = {
                "velocity": msg.velocity[index] if index < len(msg.velocity) else 0.0,
                "effort": msg.effort[index] if index < len(msg.effort) else 0.0,
            }

    def _on_imu(self, msg: Imu) -> None:
        self.latest_imu = msg

    def _publish_markers(self) -> None:
        markers = []

        for index, wheel_name in enumerate(ORDER):
            joint_name = f"{wheel_name}_wheel_joint"
            state = self.latest_joint_state.get(
                joint_name, {"velocity": 0.0, "effort": 0.0}
            )

            marker = Marker()
            # Use base_link to keep marker visible even if wheel TF is late/missing.
            marker.header.frame_id = "base_link"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "wheel_info"
            marker.id = index
            marker.type = Marker.TEXT_VIEW_FACING
            marker.action = Marker.ADD
            x_pos, y_pos, z_pos = WHEEL_TEXT_POSES[wheel_name]
            marker.pose.position.x = x_pos
            marker.pose.position.y = y_pos
            marker.pose.position.z = z_pos
            marker.scale.z = 0.08
            marker.color.a = 1.0
            marker.color.r = 0.1
            marker.color.g = 1.0
            marker.color.b = 0.2
            marker.lifetime = Duration(sec=0, nanosec=300000000)
            marker.text = (
                f"{wheel_name}\n"
                f"w={state['velocity']:.2f} rad/s\n"
                f"e={state['effort']:.2f} Nm"
            )
            markers.append(marker)

        imu_marker = Marker()
        imu_marker.header.frame_id = "base_link"
        imu_marker.header.stamp = self.get_clock().now().to_msg()
        imu_marker.ns = "imu_info"
        imu_marker.id = 100
        imu_marker.type = Marker.TEXT_VIEW_FACING
        imu_marker.action = Marker.ADD
        imu_marker.pose.position.x = 0.0
        imu_marker.pose.position.y = 0.0
        imu_marker.pose.position.z = 0.45
        imu_marker.scale.z = 0.09
        imu_marker.color.a = 1.0
        imu_marker.color.r = 0.95
        imu_marker.color.g = 0.95
        imu_marker.color.b = 0.20
        imu_marker.lifetime = Duration(sec=0, nanosec=300000000)

        if self.latest_imu is None:
            imu_marker.text = "imu: waiting"
        else:
            imu_marker.text = (
                "imu\n"
                f"wz={self.latest_imu.angular_velocity.z:.2f} rad/s\n"
                f"az={self.latest_imu.linear_acceleration.z:.2f} m/s2"
            )
        markers.append(imu_marker)

        self.marker_publisher.publish(MarkerArray(markers=markers))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WheelStatusVisualizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
