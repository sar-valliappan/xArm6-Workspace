#!/usr/bin/env python3
import os
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time

from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from tf2_ros import Buffer, TransformListener, TransformException


class PickAndPlaceNode(Node):
    def __init__(self):
        super().__init__('pick_and_place_node')
        self.physical_mode = os.getenv('XARM_PHYSICAL_MODE', '0').lower() in ('1', 'true', 'yes')
        self.physical_confirm = os.getenv('XARM_PHYSICAL_CONFIRM', '').strip()
        self.step_confirm = os.getenv('XARM_STEP_CONFIRM', '0').lower() in ('1', 'true', 'yes')
        if self.physical_mode and self.physical_confirm != 'I_UNDERSTAND_RISKS':
            raise RuntimeError(
                'Physical mode requires XARM_PHYSICAL_CONFIRM=I_UNDERSTAND_RISKS before any motion is allowed'
            )

        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']
        self.gripper_joint_name = ['drive_joint']
        self.last_joint_goal = None
        self.base_frame = 'link_base'
        self.eef_frame = 'link_eef'
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.trajectory_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/xarm6_traj_controller/follow_joint_trajectory',
        )
        self.gripper_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/xarm_gripper_traj_controller/follow_joint_trajectory',
        )
        self.get_logger().info('Waiting for trajectory action server...')
        if not self.trajectory_client.wait_for_server(timeout_sec=15.0):
            raise RuntimeError('xarm6 trajectory action server is not available')

        self.has_gripper = self.gripper_client.wait_for_server(timeout_sec=3.0)
        if self.has_gripper:
            self.get_logger().info('Gripper action server detected')
        else:
            self.get_logger().warning('Gripper action server not available, skipping gripper commands')
        self.get_logger().info('Pick and place node ready')

    def confirm_step(self, label):
        if not self.step_confirm:
            return True

        prompt = f"\n[SAFETY] About to execute step '{label}'. Type YES to continue: "
        try:
            user_value = input(prompt).strip()
        except EOFError:
            self.get_logger().error('No interactive input available for safety confirmation')
            return False

        if user_value != 'YES':
            self.get_logger().error("Step '%s' aborted by operator", label)
            return False
        return True

    def _waypoint_limits(self):
        if self.physical_mode:
            return [
                (-1.20, 1.20),
                (-1.35, 0.20),
                (-0.85, 0.85),
                (-0.20, 1.35),
                (-1.20, 1.20),
                (-1.20, 1.20),
            ]
        return [
            (-2.20, 2.20),
            (-2.20, 1.20),
            (-2.20, 2.20),
            (-2.20, 2.20),
            (-2.20, 2.20),
            (-2.20, 2.20),
        ]

    def _max_joint_step(self):
        return 0.25 if self.physical_mode else 0.6

    def _validate_joint_goal(self, positions):
        limits = self._waypoint_limits()
        if len(positions) != len(self.joint_names):
            self.get_logger().error('Expected 6 joint values, got %d', len(positions))
            return False

        for index, value in enumerate(positions):
            lower, upper = limits[index]
            if value < lower or value > upper:
                self.get_logger().error(
                    'Unsafe joint target for joint%d: %.3f not in [%.3f, %.3f]',
                    index + 1,
                    value,
                    lower,
                    upper,
                )
                return False

        if self.last_joint_goal is not None:
            for index, (previous, current) in enumerate(zip(self.last_joint_goal, positions)):
                if abs(current - previous) > self._max_joint_step():
                    self.get_logger().error(
                        'Unsafe step for joint%d: %.3f rad exceeds maximum %.3f rad',
                        index + 1,
                        abs(current - previous),
                        self._max_joint_step(),
                    )
                    return False

        return True

    def log_end_effector_pose(self, label):
        try:
            transform = self.tf_buffer.lookup_transform(self.base_frame, self.eef_frame, Time())
        except TransformException as exc:
            self.get_logger().warning('Could not read %s pose: %s', label, exc)
            return False

        translation = transform.transform.translation
        rotation = transform.transform.rotation
        self.get_logger().info(
            f"{label} EEF pose in {self.base_frame} -> {self.eef_frame}: "
            f"position=({translation.x:.3f}, {translation.y:.3f}, {translation.z:.3f}), "
            f"orientation=({rotation.x:.3f}, {rotation.y:.3f}, {rotation.z:.3f}, {rotation.w:.3f})"
        )
        return True

    def send_joint_goal(self, positions, move_time=3.0):
        if not self._validate_joint_goal(positions):
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

        self.last_joint_goal = list(positions)
        return True

    def send_gripper_goal(self, position, move_time=1.5):
        if not self.has_gripper:
            return False

        if position < 0.0 or position > 1.0:
            self.get_logger().error('Unsafe gripper target: %.3f outside [0.0, 1.0]', position)
            return False

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = self.gripper_joint_name

        point = JointTrajectoryPoint()
        point.positions = [float(position)]
        point.time_from_start = Duration(seconds=float(move_time)).to_msg()
        goal.trajectory.points = [point]

        send_future = self.gripper_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error('Gripper goal rejected')
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result()
        if result is None or result.result.error_code != 0:
            code = result.result.error_code if result else -1
            self.get_logger().error('Gripper execution failed, error_code=%d', code)
            return False
        return True

    def run(self):
        if self.physical_mode:
            self.get_logger().warn(
                'Physical mode enabled. Motion is heavily constrained and requires manual confirmation.'
            )

        # Conservative joint-space waypoints designed to stay close to a safe posture.
        home = [0.0, -0.55, 0.0, 0.55, 0.0, 0.0]
        pick_approach = [0.08, -0.70, 0.12, 0.70, -0.05, 0.0]
        pick_down = [0.08, -0.80, 0.16, 0.82, -0.05, 0.0]
        place_approach = [0.18, -0.66, 0.10, 0.66, -0.05, 0.05]
        place_down = [0.18, -0.76, 0.14, 0.78, -0.05, 0.05]

        move_time = 5.0 if self.physical_mode else 3.0
        fine_move_time = 4.0 if self.physical_mode else 2.5

        self.get_logger().info('=== Starting Pick and Place Sequence ===')
        if not self.confirm_step('pre-open gripper'):
            return
        self.send_gripper_goal(0.80, move_time=1.5)  # open

        if not self.confirm_step('move home'):
            return
        self.send_joint_goal(home, move_time=move_time)
        self.log_end_effector_pose('Home')

        if not self.confirm_step('move pick approach'):
            return
        self.send_joint_goal(pick_approach, move_time=move_time)
        self.log_end_effector_pose('Pick approach')

        if not self.confirm_step('move pick down'):
            return
        self.send_joint_goal(pick_down, move_time=fine_move_time)
        self.log_end_effector_pose('Pick down')

        self.get_logger().info('Closing gripper')
        if not self.confirm_step('close gripper'):
            return
        self.send_gripper_goal(0.15, move_time=1.5)  # close lightly

        if not self.confirm_step('retreat from pick'):
            return
        self.send_joint_goal(pick_approach, move_time=fine_move_time)
        self.log_end_effector_pose('Post-grasp retreat')

        if not self.confirm_step('move place approach'):
            return
        self.send_joint_goal(place_approach, move_time=move_time)
        self.log_end_effector_pose('Place approach')

        if not self.confirm_step('move place down'):
            return
        self.send_joint_goal(place_down, move_time=fine_move_time)
        self.log_end_effector_pose('Place down')

        self.get_logger().info('Opening gripper')
        if not self.confirm_step('open gripper'):
            return
        self.send_gripper_goal(0.80, move_time=1.5)  # open

        if not self.confirm_step('retreat from place'):
            return
        self.send_joint_goal(place_approach, move_time=fine_move_time)
        self.log_end_effector_pose('Post-place retreat')

        if not self.confirm_step('return home'):
            return
        self.send_joint_goal(home, move_time=move_time)
        self.log_end_effector_pose('Final home')
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
