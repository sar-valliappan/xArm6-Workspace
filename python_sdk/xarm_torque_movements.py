#!/usr/bin/env python3

import time
import threading
from xarm.wrapper import XArmAPI

arm = XArmAPI('192.168.1.209')
time.sleep(0.5)
arm.motion_enable(enable=True)
arm.set_mode(0)
arm.set_state(0)
arm.reset(wait=True)

stop_monitor = threading.Event()

print([method for method in dir(arm) if 'torque' in method])

def monitor(duration=60, interval=0.1):
    print(f"{'Time':>6} | {'J1':>7} {'J2':>7} {'J3':>7} {'J4':>7} {'J5':>7} {'J6':>7}")
    print("-" * 60)
    start = time.time()
    while time.time() - start < duration and not stop_monitor.is_set():
        t = time.time() - start
        code_a, angles  = arm.get_servo_angle()
        # Note: get_joint_states returns [angles, velocities, efforts]
        code_s, states  = arm.get_joint_states()
        code_t, torques = arm.get_joints_torque()
        
        if code_a == 0 and code_t == 0:
            print(f"[Angles ] {t:5.1f}s | " + " ".join(f"{a:7.2f}" for a in angles))
            print(f"[Torque ] {t:5.1f}s | " + " ".join(f"{tr:7.2f}" for tr in torques))
            print()
        time.sleep(interval)

monitor_thread = threading.Thread(target=monitor, kwargs={'duration': 60, 'interval': 0.1})
monitor_thread.daemon = True
monitor_thread.start()

# ── Torque-control helpers ──────────────────────────────────────────────────

# NOTE: 30Nm is very high for J4-J6. Reduced for safety.
DRIVE_TORQUES  = [5.0, 10.0, 6.0, 2.0, 2.0, 1.0]   
HOLD_TORQUES   = [1.0, 4.0, 2.0, 0.5, 0.5, 0.3]   

ANGLE_TOL      = 1.5      
SETTLE_CYCLES  = 10       
TIMEOUT        = 15.0     

def _enter_torque_mode():
    arm.set_mode(2) # Mode 2 is for Joint Velocity/Torque
    arm.set_state(0)
    time.sleep(0.1)

def _enter_position_mode():
    arm.set_mode(0) # Position mode
    arm.set_state(0)
    time.sleep(0.1)

def move_by_torque(target_angles, timeout=TIMEOUT):
    _enter_torque_mode()
    settle = 0
    start  = time.time()

    while True:
        if time.time() - start > timeout:
            print("[Torque] WARNING: move timed out.")
            break

        code, current = arm.get_servo_angle()
        if code != 0 or current is None:
            time.sleep(0.01)
            continue

        torques = []
        all_close = True

        for j in range(6):
            err = target_angles[j] - current[j]
            if abs(err) > ANGLE_TOL:
                all_close = False
                # Direct torque application based on error direction
                torques.append(DRIVE_TORQUES[j] * (1.0 if err > 0 else -1.0))
            else:
                torques.append(HOLD_TORQUES[j] * (1.0 if err >= 0 else -1.0))

        # CORRECTED METHOD NAME
        arm.vc_set_joint_torque(torques)

        if all_close:
            settle += 1
            if settle >= SETTLE_CYCLES:
                break
        else:
            settle = 0

        time.sleep(0.02) # 50Hz control loop

    arm.vc_set_joint_torque([0.0] * 6)
    _enter_position_mode()

# ── Gripper and Sequence (Logic remains same, using corrected move function) ──

try:
    arm.set_gripper_position(500, wait=True)
    
    # Sequence
    move_by_torque([0, -30, 0, 0, 0, 0])
    # ... rest of your sequence ...

except Exception as e:
    print(f"Error: {e}")
finally:
    arm.set_mode(0)
    arm.set_state(0)
    stop_monitor.set()
    monitor_thread.join()