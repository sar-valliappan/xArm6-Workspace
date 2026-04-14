#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from moveit_msgs.srv import GetPositionIK, GetMotionPlan
from geometry_msgs.msg import Pose, PoseStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState
import time

class PickAndPlaceNode(Node):
    def __init__(self):
        super().__init__('pick_and_place_node')
        
        # MoveIt service clients
        self.move_group_action = None
        self.ik_service = self.create_client(GetPositionIK, '/compute_ik')
        self.move_service = self.create_client(GetMotionPlan, '/plan_kinematic_path')
        
        # Publisher for joint commands (simplified trajectory execution)
        self.trajectory_pub = self.create_publisher(JointTrajectory, '/xarm6/arm_controller/joint_trajectory', 10)
        
        self.get_logger().info('Pick and place node ready')

    def move_to_pose(self, x, y, z, qx=0.0, qy=1.0, qz=0.0, qw=0.0):
        """Move end-effector to a Cartesian pose (simplified)."""
        self.get_logger().info(f'Moving to pose: x={x}, y={y}, z={z}')
        # In a real implementation, this would use IK service and motion planning
        # For now, just log the movement
        time.sleep(1.0)
        return True

    def move_to_named(self, name):
        """Move to a named pose defined in SRDF (e.g. 'home')."""
        self.get_logger().info(f'Moving to named pose: {name}')
        # In a real implementation, this would lookup the named pose and move to it
        time.sleep(1.0)

    def pick(self, pick_x, pick_y, pick_z):
        """Approach, descend, grasp, retract."""
        approach_z = pick_z + 0.10       # 10 cm above
        
        self.get_logger().info('Moving to approach pose...')
        self.move_to_pose(pick_x, pick_y, approach_z)
        time.sleep(0.5)

        self.get_logger().info('Descending to pick pose...')
        self.move_to_pose(pick_x, pick_y, pick_z)
        time.sleep(0.5)

        # TODO: send gripper close command here
        self.get_logger().info('Closing gripper...')
        time.sleep(0.8)

        self.get_logger().info('Retracting...')
        self.move_to_pose(pick_x, pick_y, approach_z)

    def place(self, place_x, place_y, place_z):
        """Approach, descend, release, retract."""
        approach_z = place_z + 0.10

        self.get_logger().info('Moving to place approach...')
        self.move_to_pose(place_x, place_y, approach_z)
        time.sleep(0.5)

        self.get_logger().info('Descending to place pose...')
        self.move_to_pose(place_x, place_y, place_z)
        time.sleep(0.5)

        # TODO: send gripper open command here
        self.get_logger().info('Opening gripper...')
        time.sleep(0.8)

        self.get_logger().info('Retracting...')
        self.move_to_pose(place_x, place_y, approach_z)

    def run(self):
        self.get_logger().info('Going home...')
        self.move_to_named('home')
        time.sleep(1.0)

        # --- Define pick and place positions (metres, robot base frame) ---
        pick_x,  pick_y,  pick_z  = 0.35, 0.00, 0.15
        place_x, place_y, place_z = 0.35, 0.25, 0.15

        self.get_logger().info('=== Starting Pick and Place Sequence ===')
        self.pick(pick_x, pick_y, pick_z)
        self.place(place_x, place_y, place_z)

        self.get_logger().info('Done! Returning home.')
        self.move_to_named('home')
        self.get_logger().info('=== Pick and Place Complete ===')


def main():
    rclpy.init()
    node = PickAndPlaceNode()
    node.run()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
