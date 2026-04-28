#!/usr/bin/env python3

import time
import threading
from xarm.wrapper import XArmAPI

arm = XArmAPI('192.168.1.209')
time.sleep(0.5)
arm.set_mode(0)
arm.set_state(0)
arm.reset(wait=True)

stop_monitor = threading.Event()

def monitor(duration=60, interval=0.1):
    print(f"{'Time':>6} | {'J1':>7} {'J2':>7} {'J3':>7} {'J4':>7} {'J5':>7} {'J6':>7}")
    print("-" * 60)
    start = time.time()
    while time.time() - start < duration and not stop_monitor.is_set():
        t = time.time() - start
        code_a, angles  = arm.get_servo_angle()
        code_s, states  = arm.get_joint_states()
        code_t, torques = arm.get_joints_torque()
        if code_a == 0:
            print(f"[Angles  ] {t:5.1f}s | " + " ".join(f"{a:7.2f}" for a in angles))
        if code_s == 0:
            vels = states[1]
            print(f"[Velocity] {t:5.1f}s | " + " ".join(f"{v:7.2f}" for v in vels))
        if code_t == 0:
            print(f"[Torque  ] {t:5.1f}s | " + " ".join(f"{t:7.2f}" for t in torques))
        print()
        time.sleep(interval)

monitor_thread = threading.Thread(target=monitor, kwargs={'duration': 60, 'interval': 0.1})
monitor_thread.daemon = True
monitor_thread.start()


# ── Velocity-based torque-like control ─────────────────────────────────────
KP = [4.0, 6.0, 4.0, 3.0, 2.5, 2.0]   # [J1..J6]  deg/s per degree of error

# Maximum velocity per joint [deg/s] — acts as a saturation / safety clamp.
V_MAX = [30.0, 25.0, 30.0, 30.0, 30.0, 30.0]

ANGLE_TOL    = 1.0    # degrees — "close enough" per joint
SETTLE_COUNT = 6      # consecutive 20 ms ticks inside tolerance → done
TIMEOUT      = 15.0   # seconds before giving up on a move
DT           = 0.02   # control loop period [s]


def _enter_velocity_mode():
    arm.set_mode(4)   # joint velocity control
    arm.set_state(0)
    time.sleep(0.1)


def _enter_position_mode():
    arm.set_mode(0)   # position control
    arm.set_state(0)
    time.sleep(0.1)


def move_by_velocity(target_angles, timeout=TIMEOUT):
    """
    Drive each joint toward *target_angles* (degrees, 6-element list) using
    mode-4 joint velocity control with a proportional controller.

    Each tick:
      - Read current angles.
      - Compute velocity command = KP * error, clamped to ±V_MAX.
      - Joints already inside ANGLE_TOL are commanded to 0 (hold).
      - Once SETTLE_COUNT consecutive ticks have all joints inside tolerance,
        send zero velocities and return.
    """
    _enter_velocity_mode()

    settle = 0
    start  = time.time()

    while True:
        if time.time() - start > timeout:
            print("[Velocity] WARNING: move timed out.")
            break

        code, current = arm.get_servo_angle()
        if code != 0:
            time.sleep(DT)
            continue

        vels      = []
        all_close = True

        for j in range(6):
            err = target_angles[j] - current[j]
            if abs(err) > ANGLE_TOL:
                all_close = False
                v = KP[j] * err
                # Saturate to ±V_MAX
                v = max(-V_MAX[j], min(V_MAX[j], v))
                vels.append(v)
            else:
                vels.append(0.0)

        arm.vc_set_joint_velocity(vels)

        if all_close:
            settle += 1
            if settle >= SETTLE_COUNT:
                break
        else:
            settle = 0

        time.sleep(DT)

    # Stop all motion before switching back to position mode
    arm.vc_set_joint_velocity([0.0] * 6)
    _enter_position_mode()


def adaptive_grip(open_pos=350, close_speed=500):
    """
    Close gripper until stall/contact, return gripped width.
    Returns 0 if nothing detected.
    """
    arm.set_gripper_position(open_pos, wait=True)
    time.sleep(0.2)

    arm.set_gripper_position(0, speed=close_speed, wait=False)

    prev_pos      = open_pos
    stall_count   = 0
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
            prev_pos    = pos

        if stall_count >= 5:
            gripped_width = pos
            print(f"[Grip] Object contacted. Gripper width: {gripped_width:.1f}")
            break

        if pos <= 5:
            print("[Grip] Warning: Gripper fully closed, no object detected.")
            gripped_width = 0
            break

    return gripped_width


# ── Main sequence ────────────────────────────────────────────────────────────

# Open gripper (position mode)
arm.set_gripper_position(500, wait=True)

# Move to pick the object
move_by_velocity([  0, -30,  0, 0, 0, 0])
move_by_velocity([-120, -30,  0, 0, 0, 0])
move_by_velocity([-120, -18, -4, 0, 0, 0])

gripped_width = adaptive_grip(open_pos=500, close_speed=500)

if gripped_width == 0:
    print("[Abort] Nothing gripped. Returning home.")
    move_by_velocity([-120, -30, -4, 0, 0, 0])
    arm.move_gohome(wait=True)
    stop_monitor.set()
    monitor_thread.join()
    exit()

# Set TCP payload
arm.set_tcp_load(0.3, [0, 0, 30])
arm.set_state(0)

# Move to place the object
move_by_velocity([-120, -30, -4, 0, 0, 0])
move_by_velocity([-160, -30, -4, 0, 0, 0])
move_by_velocity([-160, -18, -4, 0, 0, 0])

arm.set_gripper_position(850, wait=True)

arm.set_tcp_load(0, [0, 0, 30])
arm.set_state(0)

move_by_velocity([-160, -40, -4, 0, 0, 0])

# Go back to home
arm.move_gohome(wait=True)
stop_monitor.set()
monitor_thread.join()