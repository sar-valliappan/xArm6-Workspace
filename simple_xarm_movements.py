#!/usr/bin/env python3

import time
from xarm.wrapper import XArmAPI

arm = XArmAPI('192.168.1.209')
time.sleep(0.5)
arm.set_mode(0)
arm.set_state(0)
arm.reset(wait=True)

def adaptive_grip(open_pos=350, close_speed=500):
    """
    Close gripper until stall/contact, return gripped width.
    Returns 0 if nothing detected.
    """
    arm.set_gripper_position(open_pos, wait=True)
    time.sleep(0.2)

    arm.set_gripper_position(0, speed=close_speed, wait=False)

    prev_pos = open_pos
    stall_count = 0
    gripped_width = 0

    while True:
        time.sleep(0.05)
        code, pos = arm.get_gripper_position()
        if code != 0:
            break

        delta = abs(prev_pos - pos)
        if delta < 2:
            stall_count += 1
        else:
            stall_count = 0
            prev_pos = pos

        if stall_count >= 5:
            gripped_width = pos
            print(f"[Grip] Object contacted. Gripper width: {gripped_width:.1f}")
            break

        if pos <= 5:
            print("[Grip] Warning: Gripper fully closed, no object detected.")
            gripped_width = 0
            break

    return gripped_width


# open gripper
arm.set_gripper_position(500, wait=True)

# move to pick the object
arm.set_servo_angle(angle=[0, -30, 0, 0, 0, 0], wait=True)
arm.set_servo_angle(angle=[-120, -30, 0, 0, 0, 0], wait=True)
arm.set_servo_angle(angle=[-120, -18, -4, 0, 0, 0], wait=True)

gripped_width = adaptive_grip(open_pos=500, close_speed=500)

if gripped_width == 0:
    print("[Abort] Nothing gripped. Returning home.")
    arm.set_servo_angle(angle=[-120, -30, -4, 0, 0, 0], wait=True)
    arm.move_gohome(wait=True)
    exit()

# set tcp payload
arm.set_tcp_load(0.3, [0, 0, 30])
arm.set_state(0)

# move to place the object
arm.set_servo_angle(angle=[-120, -30, -4, 0, 0, 0], wait=True)
arm.set_servo_angle(angle=[-160, -30, -4, 0, 0, 0], wait=True)
arm.set_servo_angle(angle=[-160, -18, -4, 0, 0, 0], wait=True)
arm.set_gripper_position(850, wait=True)
arm.set_tcp_load(0, [0, 0, 30])
arm.set_state(0)

arm.set_servo_angle(angle=[-160, -40, -4, 0, 0, 0], wait=True)

# go back to home
arm.move_gohome(wait=True)