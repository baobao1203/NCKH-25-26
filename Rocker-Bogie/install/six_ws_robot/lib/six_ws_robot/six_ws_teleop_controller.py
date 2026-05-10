#!/usr/bin/env python3

import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

ORDER = ["lf", "lm", "lr", "rf", "rm", "rr"]
WHEEL_RADIUS = 0.15
TRACK_WIDTH = 0.60
CENTER_WHEEL_RATIO = 0.65
MAX_WHEEL_LINEAR_SPEED = 2.5
COMMAND_HZ = 20.0
DEADBAND = 1e-4


class SixWheelDiffController(Node):
    def __init__(self):
        super().__init__("six_ws_diff_controller")
        self.linear_x = 0.0
        self.angular_z = 0.0

        self.create_subscription(Twist, "/cmd_vel", self._on_cmd_vel, 10)
        self.wheel_publisher = self.create_publisher(
            Float64MultiArray, "/wheel_velocity_controller/commands_raw", 10
        )
        self.create_timer(1.0 / COMMAND_HZ, self._publish_commands)

    def _on_cmd_vel(self, msg: Twist) -> None:
        self.linear_x = msg.linear.x
        self.angular_z = msg.angular.z

    def _publish_commands(self) -> None:
        if abs(self.linear_x) < DEADBAND and abs(self.angular_z) < DEADBAND:
            self.wheel_publisher.publish(Float64MultiArray(data=[0.0] * len(ORDER)))
            return

        left_linear = self.linear_x - self.angular_z * TRACK_WIDTH * 0.5
        right_linear = self.linear_x + self.angular_z * TRACK_WIDTH * 0.5

        if abs(self.angular_z) < DEADBAND:
            center_ratio = 1.0
        else:
            center_ratio = CENTER_WHEEL_RATIO

        wheel_linear = [
            left_linear,
            left_linear * center_ratio,
            left_linear,
            right_linear,
            right_linear * center_ratio,
            right_linear,
        ]

        max_linear = max(abs(speed) for speed in wheel_linear)
        if max_linear > MAX_WHEEL_LINEAR_SPEED:
            scale = MAX_WHEEL_LINEAR_SPEED / max_linear
            wheel_linear = [speed * scale for speed in wheel_linear]

        wheel_rad_s = [speed / WHEEL_RADIUS for speed in wheel_linear]
        self.wheel_publisher.publish(Float64MultiArray(data=wheel_rad_s))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SixWheelDiffController()
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
