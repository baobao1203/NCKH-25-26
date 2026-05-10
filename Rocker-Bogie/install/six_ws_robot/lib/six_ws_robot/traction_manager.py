#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

ORDER = ["lf", "lm", "lr", "rf", "rm", "rr"]
TORQUE_MIN = 0.2
TORQUE_MAX = 5.0


class TractionManager(Node):
    def __init__(self):
        super().__init__("traction_manager")
        self.latest_effort = {}

        self.create_subscription(JointState, "/joint_states", self._on_joint_states, 10)
        self.create_subscription(
            Float64MultiArray,
            "/wheel_velocity_controller/commands_raw",
            self._on_raw_commands,
            10,
        )
        self.publisher = self.create_publisher(
            Float64MultiArray, "/wheel_velocity_controller/commands", 10
        )

    def _on_joint_states(self, msg: JointState) -> None:
        for name, effort in zip(msg.name, msg.effort):
            if name.endswith("_wheel_joint"):
                wheel_name = name[: -len("_wheel_joint")]
                self.latest_effort[wheel_name] = effort

    def _on_raw_commands(self, msg: Float64MultiArray) -> None:
        if len(msg.data) != len(ORDER):
            self.get_logger().warning(
                f"Expected {len(ORDER)} wheel commands, got {len(msg.data)}"
            )
            return

        adjusted = []
        for index, wheel_name in enumerate(ORDER):
            command = msg.data[index]
            effort = self.latest_effort.get(wheel_name)

            if effort is None:
                adjusted.append(command)
                continue

            if abs(effort) < TORQUE_MIN:
                command *= 0.3
            elif abs(effort) > TORQUE_MAX:
                command *= 0.6

            adjusted.append(command)

        self.publisher.publish(Float64MultiArray(data=adjusted))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TractionManager()
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
