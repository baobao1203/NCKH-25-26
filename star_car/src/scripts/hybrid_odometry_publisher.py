#!/usr/bin/env python3
"""
Hybrid Odometry Publisher với Slip Detection
=============================================
- Tính odometry từ wheel encoder (joint_states)
- Phát hiện trượt bánh (kẹt/sa lầy/mất lực kéo)
- Publish TF: odom -> base_footprint
- Publish nav_msgs/Odometry trên /odom

⭐ QUAN TRỌNG: Node này dùng callback-driven thay vì timer
   để tránh lỗi khi use_sim_time=true.
"""

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Twist
from tf2_ros import TransformBroadcaster
from std_msgs.msg import Float64MultiArray

# ====== CẤU HÌNH ROBOT - CHỈNH CHO ĐÚNG VỚI URDF ======
WHEEL_RADIUS = 0.15      # m (từ URDF: wheel_radius)
TRACK_WIDTH  = 0.60      # m (từ URDF: base_width = 2 * wheel y offset)
ORDER = ["lf", "lm", "lr", "rf", "rm", "rr"]

# ====== NGƯỠNG PHÁT HIỆN TRƯỢT ======
SLIP_EFFORT_HIGH     = 4.5   # Nm - effort > threshold → kẹt
SLIP_VEL_RATIO       = 0.3   # actual/commanded < 0.3 → trượt
SLIP_EFFORT_LOW      = 0.2   # effort thấp bất thường → mất tiếp xúc


class HybridOdometryPublisher(Node):
    def __init__(self):
        super().__init__("hybrid_odometry_publisher")

        # Pose tích lũy
        self.x     = 0.0
        self.y     = 0.0
        self.theta = 0.0

        # Dữ liệu bánh xe
        self.wheel_vel    = {}   # rad/s thực tế từ encoder
        self.wheel_effort = {}   # Nm từ joint_states
        self.wheel_cmd    = {}   # rad/s lệnh

        # Slip
        self.slip_wheels = set()

        # Thời gian
        self.prev_stamp = None

        # Debug
        self.odom_count   = 0
        self.js_count     = 0

        # ---- Publishers ----
        self.tf_br       = TransformBroadcaster(self)
        self.odom_pub    = self.create_publisher(Odometry, "/odom", 50)
        self.slip_pub    = self.create_publisher(Twist,    "/slip_status", 10)

        # ---- Subscribers ----
        # ⭐ Odometry được tính MỖI KHI nhận joint_states (100 Hz từ controller_manager)
        self.create_subscription(JointState,        "/joint_states",
                                 self._on_joint_states, 10)
        self.create_subscription(Float64MultiArray, "/wheel_velocity_controller/commands",
                                 self._on_commands, 10)

        # Timer log debug 2 giây 1 lần
        self.create_timer(2.0, self._log_debug)

        self.get_logger().info("="*55)
        self.get_logger().info("  Hybrid Odometry Publisher  (callback-driven)")
        self.get_logger().info(f"  WHEEL_RADIUS = {WHEEL_RADIUS} m")
        self.get_logger().info(f"  TRACK_WIDTH  = {TRACK_WIDTH} m")
        self.get_logger().info("="*55)

    # ------------------------------------------------------------------ #
    #  CALLBACKS                                                          #
    # ------------------------------------------------------------------ #
    def _on_commands(self, msg: Float64MultiArray):
        if len(msg.data) == len(ORDER):
            for i, name in enumerate(ORDER):
                self.wheel_cmd[name] = msg.data[i]

    def _on_joint_states(self, msg: JointState):
        """Mỗi lần nhận joint_states → cập nhật wheel data → tính odom → publish."""
        self.js_count += 1

        # 1. Lưu velocity + effort
        for idx, jname in enumerate(msg.name):
            if not jname.endswith("_wheel_joint"):
                continue
            wname = jname.replace("_wheel_joint", "")
            if idx < len(msg.velocity):
                self.wheel_vel[wname] = msg.velocity[idx]
            if idx < len(msg.effort):
                self.wheel_effort[wname] = msg.effort[idx]

        # 2. Tính dt từ header stamp
        stamp = msg.header.stamp
        now_sec = stamp.sec + stamp.nanosec * 1e-9

        if self.prev_stamp is None:
            self.prev_stamp = now_sec
            # Publish identity TF ngay để RTAB-Map có frame
            self._publish(stamp, 0.0, 0.0)
            return

        dt = now_sec - self.prev_stamp
        if dt <= 0.0 or dt > 1.0:
            self.prev_stamp = now_sec
            return

        # 3. Slip detection
        slip, confidence = self._detect_slip()

        # 4. Tính velocity (weighted)
        lin_vel, ang_vel = self._calc_velocity()

        # 5. Scale nếu trượt
        if slip and confidence > 0.7:
            scale = 0.3
        elif slip:
            scale = 0.6
        else:
            scale = 1.0

        # 6. Cập nhật pose
        dtheta = ang_vel * dt
        dx = lin_vel * math.cos(self.theta + dtheta / 2.0) * dt * scale
        dy = lin_vel * math.sin(self.theta + dtheta / 2.0) * dt * scale

        self.x     += dx
        self.y     += dy
        self.theta += dtheta
        self.theta  = math.atan2(math.sin(self.theta), math.cos(self.theta))

        # 7. Publish
        self._publish(stamp, lin_vel, ang_vel)

        # 8. Slip status
        sm = Twist()
        sm.linear.x = 1.0 if slip else 0.0
        sm.linear.y = confidence
        sm.linear.z = float(len(self.slip_wheels))
        self.slip_pub.publish(sm)

        self.prev_stamp = now_sec
        self.odom_count += 1

    # ------------------------------------------------------------------ #
    #  SLIP DETECTION                                                     #
    # ------------------------------------------------------------------ #
    def _detect_slip(self):
        count = 0
        severity = 0.0
        self.slip_wheels.clear()

        for wn in ORDER:
            vel = self.wheel_vel.get(wn, 0.0)
            eff = self.wheel_effort.get(wn, 0.0)
            cmd = self.wheel_cmd.get(wn, 0.0)
            hit = False

            # Kẹt: effort cao + velocity thấp
            if abs(eff) > SLIP_EFFORT_HIGH and abs(vel) < 0.5:
                hit = True
                severity += 0.8
            # Trượt: velocity thực << lệnh
            elif abs(cmd) > 0.1:
                ratio = abs(vel) / abs(cmd)
                if ratio < SLIP_VEL_RATIO:
                    hit = True
                    severity += (1.0 - ratio)
            # Mất tiếp xúc: có lệnh nhưng effort gần 0
            elif abs(cmd) > 0.1 and abs(eff) < SLIP_EFFORT_LOW:
                hit = True
                severity += 0.5

            if hit:
                count += 1
                self.slip_wheels.add(wn)

        detected = count >= 2
        conf = min(1.0, severity / max(1, count)) if count else 0.0
        return detected, conf

    # ------------------------------------------------------------------ #
    #  VELOCITY CALCULATION                                               #
    # ------------------------------------------------------------------ #
    def _calc_velocity(self):
        lv, rv = [], []
        lw, rw = [], []

        for wn in ORDER:
            v = self.wheel_vel.get(wn, 0.0)
            w = 0.2 if wn in self.slip_wheels else 1.0
            if wn.startswith("l"):
                lv.append(v); lw.append(w)
            else:
                rv.append(v); rw.append(w)

        left  = sum(a*b for a,b in zip(lv,lw)) / sum(lw) if sum(lw) else 0.0
        right = sum(a*b for a,b in zip(rv,rw)) / sum(rw) if sum(rw) else 0.0

        left_lin  = left  * WHEEL_RADIUS
        right_lin = right * WHEEL_RADIUS

        linear  = (left_lin + right_lin) / 2.0
        angular = (right_lin - left_lin) / TRACK_WIDTH
        return linear, angular

    # ------------------------------------------------------------------ #
    #  PUBLISH TF + ODOM                                                  #
    # ------------------------------------------------------------------ #
    def _publish(self, stamp, lin_vel, ang_vel):
        qz = math.sin(self.theta / 2.0)
        qw = math.cos(self.theta / 2.0)

        # TF: odom -> base_footprint
        tf = TransformStamped()
        tf.header.stamp          = stamp
        tf.header.frame_id       = "odom"
        tf.child_frame_id        = "base_footprint"
        tf.transform.translation.x = self.x
        tf.transform.translation.y = self.y
        tf.transform.translation.z = 0.0
        tf.transform.rotation.x    = 0.0
        tf.transform.rotation.y    = 0.0
        tf.transform.rotation.z    = qz
        tf.transform.rotation.w    = qw
        self.tf_br.sendTransform(tf)

        # Odom msg
        odom = Odometry()
        odom.header.stamp    = stamp
        odom.header.frame_id = "odom"
        odom.child_frame_id  = "base_footprint"

        odom.pose.pose.position.x    = self.x
        odom.pose.pose.position.y    = self.y
        odom.pose.pose.position.z    = 0.0
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw

        odom.pose.covariance[0]  = 0.01   # x
        odom.pose.covariance[7]  = 0.01   # y
        odom.pose.covariance[14] = 1e6    # z (2D → infinite)
        odom.pose.covariance[21] = 1e6    # roll
        odom.pose.covariance[28] = 1e6    # pitch
        odom.pose.covariance[35] = 0.05   # yaw

        odom.twist.twist.linear.x  = lin_vel
        odom.twist.twist.angular.z = ang_vel
        odom.twist.covariance[0]  = 0.01
        odom.twist.covariance[35] = 0.05

        self.odom_pub.publish(odom)

    # ------------------------------------------------------------------ #
    #  DEBUG LOG                                                          #
    # ------------------------------------------------------------------ #
    def _log_debug(self):
        self.get_logger().info(
            f"[ODOM] x={self.x:.3f} y={self.y:.3f} "
            f"th={math.degrees(self.theta):.1f}deg | "
            f"odom_msgs={self.odom_count} js_msgs={self.js_count} | "
            f"slip={len(self.slip_wheels)}"
        )
        self.odom_count = 0
        self.js_count   = 0


def main(args=None):
    rclpy.init(args=args)
    node = HybridOdometryPublisher()
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
