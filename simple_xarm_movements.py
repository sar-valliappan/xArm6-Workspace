#!/usr/bin/env python3

import time
from xarm.wrapper import XArmAPI

arm = XArmAPI('192.168.1.209')
time.sleep(0.5)
arm.set_mode(0)
arm.set_state(0)
arm.reset(wait=True)

#move to pick the object
arm.set_gripper_position(850, wait=True)
arm.set_position(*[300, 0, 300, 180, 0, 0], wait=True)
arm.set_position(*[300, 0, 200, 180, 0, 0], wait=True)
arm.set_gripper_position(0, wait=True)

#set tcp payload
arm.set_tcp_load(0.3, [0, 0, 30])
arm.set_state(0)

#move to place the object
arm.set_position(*[300, 0, 300, 180, 0, 0], wait=True)
arm.set_position(*[300, -150, 300, 180, 0, 0], wait=True)
arm.set_position(*[300, -150, 200, 180, 0, 0], wait=True)
arm.set_gripper_position(850, wait=True)
arm.set_tcp_load(0, [0, 0, 30])
arm.set_state(0)
arm.set_position(*[300, -150, 300, 180, 0, 0], wait=True)
arm.set_gripper_position(0, wait=True)

#go back to home
arm.move_gohome(wait=True)