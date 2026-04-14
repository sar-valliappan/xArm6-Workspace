#!/usr/bin/env python3
import rclpy
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node

from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class PickAndPlaceNode(Node):
    def __init__(self):
        super().__init__('pick_and_place_node')
        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']
        self.trajectory_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/xarm6_traj_controller/follow_joint_trajectory',
        )
        self.get_logger().info('Waiting for trajectory action server...')
        if not self.trajectory_client.wait_for_server(timeout_sec=15.0):
            raise RuntimeError('xarm6 trajectory action server is not available')
        self.get_logger().info('Pick and place node ready')

    def send_joint_goal(self, positions, move_time=3.0):
        if len(positions) != 6:
            self.get_logger().error('Expected 6 joint values, got %d', len(positions))
            return False

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = self.joint_names

        point = JointTrajectoryPoint()
        point.positions = [float(v) for v in positions]
        point.time_from_start = Duration(seconds=float(move_time)).to_msg()
        goal.trajectory.points = [point]

        send_future = self.trajectory_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error('Trajectory goal rejected')
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result()
        if result is None or result.result.error_code != 0:
            code = result.result.error_code if result else -1
            self.get_logger().error('Trajectory execution failed, error_code=%d', code)
            return False
        return True

    def run(self):
        # Joint-space waypoints to make visible motion in RViz fake mode.
        home = [0.0, -0.75, 0.0, 0.75, 0.0, 0.0]
        pick_approach = [0.10, -0.95, 0.25, 0.95, -0.10, 0.0]
        pick_down = [0.10, -1.10, 0.35, 1.20, -0.10, 0.0]
        place_approach = [0.55, -0.90, 0.20, 0.90, -0.20, 0.10]
        place_down = [0.55, -1.05, 0.32, 1.15, -0.20, 0.10]

        self.get_logger().info('=== Starting Pick and Place Sequence ===')
        self.send_joint_goal(home, move_time=3.0)
        self.send_joint_goal(pick_approach, move_time=3.0)
        self.send_joint_goal(pick_down, move_time=2.5)
        self.get_logger().info('Closing gripper (placeholder)')
        self.send_joint_goal(pick_approach, move_time=2.5)
        self.send_joint_goal(place_approach, move_time=3.5)
        self.send_joint_goal(place_down, move_time=2.5)
        self.get_logger().info('Opening gripper (placeholder)')
        self.send_joint_goal(place_approach, move_time=2.5)
        self.send_joint_goal(home, move_time=3.0)
        self.get_logger().info('=== Pick and Place Complete ===')


def main():
    rclpy.init()
    node = PickAndPlaceNode()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
