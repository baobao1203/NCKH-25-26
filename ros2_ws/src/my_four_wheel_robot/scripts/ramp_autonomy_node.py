#!/usr/bin/env python3

import math
from typing import Optional, Tuple

import numpy as np
import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32, String


class RampAutonomyNode(Node):
    def __init__(self) -> None:
        super().__init__("ramp_autonomy")

        self.declare_parameter("depth_topic", "/camera/depth/image_raw")
        self.declare_parameter("rgb_topic", "/camera/rgb/image_raw")
        self.declare_parameter("cmd_topic", "/diff_drive_base_controller/cmd_vel")
        self.declare_parameter("min_valid_depth", 0.15)
        self.declare_parameter("max_valid_depth", 6.0)
        self.declare_parameter("drive_speed", 0.20)
        self.declare_parameter("climb_speed", 0.12)
        self.declare_parameter("turn_speed", 0.35)
        self.declare_parameter("stop_distance", 0.35)
        self.declare_parameter("warn_distance", 0.80)
        self.declare_parameter("max_climb_angle_deg", 18.0)

        self.depth_topic = self.get_parameter("depth_topic").get_parameter_value().string_value
        self.rgb_topic = self.get_parameter("rgb_topic").get_parameter_value().string_value
        self.cmd_topic = self.get_parameter("cmd_topic").get_parameter_value().string_value

        self.min_valid_depth = float(self.get_parameter("min_valid_depth").value)
        self.max_valid_depth = float(self.get_parameter("max_valid_depth").value)
        self.drive_speed = float(self.get_parameter("drive_speed").value)
        self.climb_speed = float(self.get_parameter("climb_speed").value)
        self.turn_speed = float(self.get_parameter("turn_speed").value)
        self.stop_distance = float(self.get_parameter("stop_distance").value)
        self.warn_distance = float(self.get_parameter("warn_distance").value)
        self.max_climb_angle_deg = float(self.get_parameter("max_climb_angle_deg").value)

        self.latest_depth: Optional[Image] = None
        self.latest_rgb: Optional[Image] = None
        self.baseline_angle_deg: Optional[float] = None
        self.baseline_samples = []

        self.create_subscription(Image, self.depth_topic, self.depth_cb, 10)
        self.create_subscription(Image, self.rgb_topic, self.rgb_cb, 10)

        self.cmd_pub = self.create_publisher(TwistStamped, self.cmd_topic, 10)
        self.angle_pub = self.create_publisher(Float32, "/autonomy/ramp_angle_deg", 10)
        self.climbable_pub = self.create_publisher(Bool, "/autonomy/climbable", 10)
        self.status_pub = self.create_publisher(String, "/autonomy/status", 10)

        self.create_timer(0.1, self.control_loop)
        self.get_logger().info(
            f"Ramp autonomy started. depth={self.depth_topic}, rgb={self.rgb_topic}, cmd={self.cmd_topic}"
        )

    def depth_cb(self, msg: Image) -> None:
        self.latest_depth = msg

    def rgb_cb(self, msg: Image) -> None:
        self.latest_rgb = msg

    def control_loop(self) -> None:
        if self.latest_depth is None:
            self.publish_status("WAITING_DEPTH", 0.0, False)
            self.publish_cmd(0.0, 0.0)
            return

        depth = self.depth_image_to_meters(self.latest_depth)
        if depth is None:
            return

        slope_angle, front_distance = self.estimate_slope_and_distance(depth)
        if slope_angle is None or front_distance is None:
            self.publish_status("NO_DEPTH", 0.0, False)
            self.publish_cmd(0.0, 0.2)
            return

        if self.baseline_angle_deg is None and len(self.baseline_samples) < 25:
            self.baseline_samples.append(slope_angle)
            self.publish_status("CALIBRATING", slope_angle, False)
            self.publish_cmd(0.0, 0.0)
            if len(self.baseline_samples) == 25:
                self.baseline_angle_deg = float(np.median(np.array(self.baseline_samples)))
                self.get_logger().info(
                    f"Baseline slope calibrated at {self.baseline_angle_deg:.2f} deg"
                )
            return

        baseline = self.baseline_angle_deg if self.baseline_angle_deg is not None else 0.0
        relative_slope = slope_angle - baseline

        ramp_candidate = self.is_ramp_color_candidate(self.latest_rgb)

        climbable = (
            front_distance < self.warn_distance
            and relative_slope > 2.0
            and relative_slope <= self.max_climb_angle_deg
            and ramp_candidate
        )

        blocked = front_distance < self.stop_distance and not climbable

        if blocked:
            self.publish_status("BLOCKED_BOX", relative_slope, False)
            self.publish_cmd(0.0, self.turn_speed)
        elif climbable:
            self.publish_status("CLIMBABLE_RAMP", relative_slope, True)
            self.publish_cmd(self.climb_speed, 0.0)
        else:
            self.publish_status("CRUISE", relative_slope, False)
            self.publish_cmd(self.drive_speed, 0.0)

    def depth_image_to_meters(self, msg: Image) -> Optional[np.ndarray]:
        h = msg.height
        w = msg.width
        if h == 0 or w == 0:
            return None

        enc = msg.encoding.upper()
        arr = None

        try:
            if enc == "32FC1":
                arr = np.frombuffer(msg.data, dtype=np.float32).reshape((h, w))
            elif enc == "16UC1":
                arr = np.frombuffer(msg.data, dtype=np.uint16).reshape((h, w)).astype(np.float32) / 1000.0
            else:
                self.get_logger().warn(f"Unsupported depth encoding: {msg.encoding}")
                return None
        except Exception as ex:
            self.get_logger().warn(f"Depth decode failed: {ex}")
            return None

        arr = np.where(np.isfinite(arr), arr, np.nan)
        arr[(arr < self.min_valid_depth) | (arr > self.max_valid_depth)] = np.nan
        return arr

    def estimate_slope_and_distance(self, depth: np.ndarray) -> Tuple[Optional[float], Optional[float]]:
        h, w = depth.shape
        cx0 = int(w * 0.40)
        cx1 = int(w * 0.60)

        roi = depth[int(h * 0.40): int(h * 0.85), cx0:cx1]
        if roi.size == 0:
            return None, None

        front_band = depth[int(h * 0.62): int(h * 0.75), cx0:cx1]
        front_distance = np.nanmedian(front_band)
        if np.isnan(front_distance):
            return None, None

        # Use two horizontal bands and simple geometry in camera frame to estimate incline.
        near_r0 = int(h * 0.70)
        near_r1 = int(h * 0.78)
        far_r0 = int(h * 0.50)
        far_r1 = int(h * 0.58)

        near_d = np.nanmedian(depth[near_r0:near_r1, cx0:cx1])
        far_d = np.nanmedian(depth[far_r0:far_r1, cx0:cx1])

        if np.isnan(near_d) or np.isnan(far_d):
            return None, float(front_distance)

        # Approximate slope from depth variation along look-ahead direction.
        run = max(float(far_d - near_d), 1e-3)
        rise_proxy = float((near_d + far_d) * 0.5 * 0.12)
        slope_deg = math.degrees(math.atan2(rise_proxy, run))
        slope_deg = float(np.clip(slope_deg, 0.0, 45.0))

        return slope_deg, float(front_distance)

    def is_ramp_color_candidate(self, rgb_msg: Optional[Image]) -> bool:
        if rgb_msg is None or rgb_msg.height == 0 or rgb_msg.width == 0:
            return False

        if rgb_msg.encoding.upper() not in ("RGB8", "BGR8"):
            return False

        try:
            img = np.frombuffer(rgb_msg.data, dtype=np.uint8).reshape((rgb_msg.height, rgb_msg.width, 3))
        except Exception:
            return False

        h, w, _ = img.shape
        patch = img[int(h * 0.55): int(h * 0.75), int(w * 0.40): int(w * 0.60), :]
        if patch.size == 0:
            return False

        mean = patch.mean(axis=(0, 1))
        if rgb_msg.encoding.upper() == "BGR8":
            b, g, r = mean
        else:
            r, g, b = mean

        return bool(r > 95 and g > 85 and b > 65 and r >= g >= b)

    def publish_cmd(self, linear_x: float, angular_z: float) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        msg.twist.linear.x = float(linear_x)
        msg.twist.angular.z = float(angular_z)
        self.cmd_pub.publish(msg)

    def publish_status(self, status: str, angle_deg: float, climbable: bool) -> None:
        angle_msg = Float32()
        angle_msg.data = float(angle_deg)
        self.angle_pub.publish(angle_msg)

        climb_msg = Bool()
        climb_msg.data = bool(climbable)
        self.climbable_pub.publish(climb_msg)

        status_msg = String()
        status_msg.data = status
        self.status_pub.publish(status_msg)


def main() -> None:
    rclpy.init()
    node = RampAutonomyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
