#!/usr/bin/env python3
import os
import threading
from math import atan2, cos, sin

import numpy as np
import rclpy
import yaml
from geometry_msgs.msg import PoseStamped, Quaternion, Twist
from nav_msgs.msg import Path
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Empty, Float32
from tf2_ros import Buffer, TransformException, TransformListener
from visualization_msgs.msg import Marker, MarkerArray

try:
    from neupan import neupan
    from neupan.util import get_transform
except Exception as exc:  # pragma: no cover
    neupan = None
    get_transform = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class NeuPANCoreROS2(Node):
    def __init__(self) -> None:
        super().__init__("neupan_node")

        self.declare_parameter("config_file", "")
        config_file = self.get_parameter("config_file").get_parameter_value().string_value
        if not config_file:
            raise RuntimeError("Parameter 'config_file' is required")
        if not os.path.isfile(config_file):
            raise RuntimeError(f"Config file not found: {config_file}")

        with open(config_file, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        if neupan is None or get_transform is None:
            raise RuntimeError(
                "Python package 'neupan' is unavailable. Install NeuPAN first. "
                f"Import error: {IMPORT_ERROR}"
            )

        planner_cfg = self.config["planner_config_file"]
        if not os.path.isabs(planner_cfg):
            planner_cfg = os.path.normpath(os.path.join(os.path.dirname(config_file), planner_cfg))

        pan = {"dune_checkpoint": self.config["dune_checkpoint"]}
        self.neupan_planner = neupan.init_from_yaml(planner_cfg, pan=pan)

        self.scan_angle_range = np.array(self.config["scan_angle"], dtype=np.float32)
        self.scan_range = np.array(self.config["scan_range"], dtype=np.float32)

        self.obstacle_points = None
        self.robot_state = None
        self.stop = False
        self.arrive = False
        self.last_arrive_flag = False
        self._lock = threading.Lock()

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        topic_cfg = self.config["topic"]

        self.vel_pub = self.create_publisher(Twist, topic_cfg["cmd_vel"], 10)
        self.plan_pub = self.create_publisher(Path, "/neupan_plan", 10)
        self.ref_state_pub = self.create_publisher(Path, "/neupan_ref_state", 10)
        self.ref_path_pub = self.create_publisher(Path, "/neupan_initial_path", 10)
        self.arrive_pub = self.create_publisher(Empty, topic_cfg["arrive"], 1)
        self.point_markers_pub_dune = self.create_publisher(MarkerArray, "/dune_point_markers", 10)
        self.point_markers_pub_nrmp = self.create_publisher(MarkerArray, "/nrmp_point_markers", 10)
        self.robot_marker_pub = self.create_publisher(Marker, "/robot_marker", 10)

        self.create_subscription(LaserScan, topic_cfg["scan"], self.scan_callback, 10)
        self.create_subscription(Path, topic_cfg["path"], self.path_callback, 10)
        self.create_subscription(Path, topic_cfg["waypoints"], self.waypoints_callback, 10)
        self.create_subscription(PoseStamped, topic_cfg["goal"], self.goal_callback, 10)
        self.create_subscription(Float32, "/neupan/q_s", self.qs_callback, 10)
        self.create_subscription(Float32, "/neupan/p_u", self.pu_callback, 10)

        self.create_timer(0.02, self.run_once)
        self.get_logger().info(f"NeuPAN ROS2 initialized with config: {config_file}")

    def qs_callback(self, msg: Float32) -> None:
        self.neupan_planner.update_adjust_parameters(q_s=float(msg.data))
        self.get_logger().info(f"Update q_s to {msg.data:.3f}")

    def pu_callback(self, msg: Float32) -> None:
        self.neupan_planner.update_adjust_parameters(p_u=float(msg.data))
        self.get_logger().info(f"Update p_u to {msg.data:.3f}")

    def _lookup_robot_state(self):
        try:
            tf_msg = self.tf_buffer.lookup_transform(
                self.config["frame"]["map"],
                self.config["frame"]["base"],
                rclpy.time.Time(),
            )
        except TransformException:
            return None

        t = tf_msg.transform.translation
        q = tf_msg.transform.rotation
        yaw = self.quat_to_yaw_list([q.x, q.y, q.z, q.w])
        return np.array([t.x, t.y, yaw], dtype=np.float32).reshape(3, 1)

    def run_once(self) -> None:
        robot_state = self._lookup_robot_state()
        if robot_state is None:
            return

        with self._lock:
            self.robot_state = robot_state

            if len(self.neupan_planner.waypoints) >= 1 and self.neupan_planner.initial_path is None:
                self.neupan_planner.set_initial_path_from_state(self.robot_state)

            if self.neupan_planner.initial_path is None:
                return

            obstacle_points = self.obstacle_points

        self.ref_path_pub.publish(self.generate_path_msg(self.neupan_planner.initial_path))

        action, info = self.neupan_planner(self.robot_state, obstacle_points)
        self.stop = info["stop"]
        self.arrive = info["arrive"]

        if info["arrive"] and not self.last_arrive_flag:
            self.arrive_pub.publish(Empty())
            self.get_logger().info("arrive at target")

        self.last_arrive_flag = info["arrive"]

        self.plan_pub.publish(self.generate_path_msg(info["opt_state_list"]))
        self.ref_state_pub.publish(self.generate_path_msg(info["ref_state_list"]))

        if not self.arrive:
            self.vel_pub.publish(self.generate_twist_msg(action))

        self.point_markers_pub_dune.publish(self.generate_points_markers_msg(self.neupan_planner.dune_points, 0.63, 0.12, 0.94))
        self.point_markers_pub_nrmp.publish(self.generate_points_markers_msg(self.neupan_planner.nrmp_points, 1.0, 0.5, 0.0))
        self.robot_marker_pub.publish(self.generate_robot_marker_msg())

    def scan_callback(self, scan_msg: LaserScan) -> None:
        with self._lock:
            if self.robot_state is None:
                return

        ranges = np.array(scan_msg.ranges, dtype=np.float32)
        angles = np.linspace(scan_msg.angle_min, scan_msg.angle_max, len(ranges), dtype=np.float32)
        if self.config.get("flip_angle", False):
            angles = np.flip(angles)

        pts = []
        downsample = int(self.config.get("scan_downsample", 1))
        for i, (distance, angle) in enumerate(zip(ranges, angles)):
            if i % downsample != 0:
                continue
            if not np.isfinite(distance):
                continue
            if not (self.scan_range[0] <= distance <= self.scan_range[1]):
                continue
            if not (self.scan_angle_range[0] < angle < self.scan_angle_range[1]):
                continue
            pts.append(np.array([[distance * cos(angle)], [distance * sin(angle)]], dtype=np.float32))

        if not pts:
            with self._lock:
                self.obstacle_points = None
            return

        point_array = np.hstack(pts)
        try:
            tf_msg = self.tf_buffer.lookup_transform(
                self.config["frame"]["map"],
                self.config["frame"]["lidar"],
                rclpy.time.Time(),
            )
        except TransformException:
            return

        t = tf_msg.transform.translation
        q = tf_msg.transform.rotation
        yaw = self.quat_to_yaw_list([q.x, q.y, q.z, q.w])
        trans_matrix, rot_matrix = get_transform(np.array([t.x, t.y, yaw], dtype=np.float32).reshape(3, 1))

        with self._lock:
            self.obstacle_points = rot_matrix @ point_array + trans_matrix

    def path_callback(self, path: Path) -> None:
        if not path.poses:
            return
        initial_point_list = []
        for i, pose_stamped in enumerate(path.poses):
            x = pose_stamped.pose.position.x
            y = pose_stamped.pose.position.y
            if self.config.get("include_initial_path_direction", False):
                theta = self.quat_to_yaw(pose_stamped.pose.orientation)
            else:
                if i + 1 < len(path.poses):
                    p2 = path.poses[i + 1].pose.position
                    theta = atan2(p2.y - y, p2.x - x)
                elif initial_point_list:
                    theta = initial_point_list[-1][2, 0]
                else:
                    theta = 0.0
            initial_point_list.append(np.array([x, y, theta, 1.0], dtype=np.float32).reshape(4, 1))

        if self.neupan_planner.initial_path is None or self.config.get("refresh_initial_path", True):
            self.neupan_planner.set_initial_path(initial_point_list)
            self.neupan_planner.reset()

    def waypoints_callback(self, path: Path) -> None:
        with self._lock:
            if self.robot_state is None:
                return
            waypoints_list = [self.robot_state.copy()]

        for i, pose_stamped in enumerate(path.poses):
            x = pose_stamped.pose.position.x
            y = pose_stamped.pose.position.y
            if self.config.get("include_initial_path_direction", False):
                theta = self.quat_to_yaw(pose_stamped.pose.orientation)
            else:
                if i + 1 < len(path.poses):
                    p2 = path.poses[i + 1].pose.position
                    theta = atan2(p2.y - y, p2.x - x)
                else:
                    theta = waypoints_list[-1][2, 0]
            waypoints_list.append(np.array([x, y, theta, 1.0], dtype=np.float32).reshape(4, 1))

        if self.neupan_planner.initial_path is None or self.config.get("refresh_initial_path", True):
            self.neupan_planner.update_initial_path_from_waypoints(waypoints_list)
            self.neupan_planner.reset()

    def goal_callback(self, goal: PoseStamped) -> None:
        with self._lock:
            if self.robot_state is None:
                return
            robot_state = self.robot_state

        x = goal.pose.position.x
        y = goal.pose.position.y
        theta = self.quat_to_yaw(goal.pose.orientation)
        goal_np = np.array([[x], [y], [theta]], dtype=np.float32)
        self.neupan_planner.update_initial_path_from_goal(robot_state, goal_np)
        self.neupan_planner.reset()
        self.get_logger().info(f"Set neupan goal: [{x:.3f}, {y:.3f}, {theta:.3f}]")

    def generate_path_msg(self, path_list) -> Path:
        path = Path()
        path.header.frame_id = self.config["frame"]["map"]
        path.header.stamp = self.get_clock().now().to_msg()
        for i, point in enumerate(path_list):
            ps = PoseStamped()
            ps.header.frame_id = self.config["frame"]["map"]
            ps.header.stamp = path.header.stamp
            ps.header.seq = i
            ps.pose.position.x = float(point[0, 0])
            ps.pose.position.y = float(point[1, 0])
            ps.pose.orientation = self.yaw_to_quat(float(point[2, 0]))
            path.poses.append(ps)
        return path

    def generate_twist_msg(self, vel) -> Twist:
        cmd = Twist()
        if vel is None or self.stop or self.arrive:
            return cmd
        cmd.linear.x = float(vel[0, 0])
        cmd.angular.z = float(vel[1, 0])
        return cmd

    def generate_points_markers_msg(self, points, r: float, g: float, b: float) -> MarkerArray:
        arr = MarkerArray()
        if points is None:
            return arr
        stamp = self.get_clock().now().to_msg()
        for i, point in enumerate(points.T):
            marker = Marker()
            marker.header.frame_id = self.config["frame"]["map"]
            marker.header.stamp = stamp
            marker.ns = "neupan_points"
            marker.id = i
            marker.type = Marker.CUBE
            marker.action = Marker.ADD
            marker.scale.x = self.config.get("marker_size", 0.05)
            marker.scale.y = self.config.get("marker_size", 0.05)
            marker.scale.z = self.config.get("marker_size", 0.05)
            marker.color.a = 1.0
            marker.color.r = r
            marker.color.g = g
            marker.color.b = b
            marker.pose.position.x = float(point[0])
            marker.pose.position.y = float(point[1])
            marker.pose.position.z = float(self.config.get("marker_z", 0.3))
            marker.pose.orientation.w = 1.0
            arr.markers.append(marker)
        return arr

    def generate_robot_marker_msg(self) -> Marker:
        marker = Marker()
        marker.header.frame_id = self.config["frame"]["map"]
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "neupan_robot"
        marker.id = 0
        marker.type = Marker.CUBE
        marker.action = Marker.ADD
        marker.color.a = 1.0
        marker.color.g = 1.0

        length = float(getattr(self.neupan_planner.robot, "length", 0.2))
        width = float(getattr(self.neupan_planner.robot, "width", 0.2))
        marker.scale.x = length
        marker.scale.y = width
        marker.scale.z = float(self.config.get("marker_z", 0.3))

        if self.robot_state is not None:
            marker.pose.position.x = float(self.robot_state[0, 0])
            marker.pose.position.y = float(self.robot_state[1, 0])
            marker.pose.orientation = self.yaw_to_quat(float(self.robot_state[2, 0]))
        else:
            marker.pose.orientation.w = 1.0
        return marker

    @staticmethod
    def yaw_to_quat(yaw: float) -> Quaternion:
        quat = Quaternion()
        quat.x = 0.0
        quat.y = 0.0
        quat.z = sin(yaw / 2.0)
        quat.w = cos(yaw / 2.0)
        return quat

    @staticmethod
    def quat_to_yaw(quat: Quaternion) -> float:
        return atan2(2 * (quat.w * quat.z + quat.x * quat.y), 1 - 2 * (quat.z ** 2 + quat.y ** 2))

    @staticmethod
    def quat_to_yaw_list(quat_xyzw) -> float:
        x, y, z, w = quat_xyzw
        return atan2(2 * (w * z + x * y), 1 - 2 * (z ** 2 + y ** 2))


def main(args=None):
    rclpy.init(args=args)
    node = NeuPANCoreROS2()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
