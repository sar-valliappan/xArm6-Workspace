#!/bin/bash
# =============================================================================
# xArm6 Real Hardware Launcher (Safety-First)
# Launches realmove stack, waits for controllers, and runs pick-place node with
# mandatory physical safety confirmation and step-by-step operator approval.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ROBOT_IP="${ROBOT_IP:-}"
XARM_ADD_GRIPPER="${XARM_ADD_GRIPPER:-true}"
XARM_STEP_CONFIRM="${XARM_STEP_CONFIRM:-1}"
XARM_PHYSICAL_MODE="${XARM_PHYSICAL_MODE:-1}"
XARM_PHYSICAL_CONFIRM="${XARM_PHYSICAL_CONFIRM:-}"

if [[ -z "$ROBOT_IP" ]]; then
  echo "ERROR: ROBOT_IP is required for real hardware runs."
  echo "Example: ROBOT_IP=192.168.1.240 XARM_PHYSICAL_CONFIRM=I_UNDERSTAND_RISKS ./start_real.sh"
  exit 1
fi

if [[ "$XARM_PHYSICAL_MODE" != "1" ]]; then
  echo "ERROR: XARM_PHYSICAL_MODE must be 1 for this script."
  exit 1
fi

if [[ "$XARM_PHYSICAL_CONFIRM" != "I_UNDERSTAND_RISKS" ]]; then
  echo "ERROR: Set XARM_PHYSICAL_CONFIRM=I_UNDERSTAND_RISKS to continue."
  exit 1
fi

check_tcp_port() {
  local host="$1"
  local port="$2"

  # BSD nc (macOS) and GNU nc use different timeout flags; try both.
  if nc -z -w 2 "$host" "$port" >/dev/null 2>&1; then
    return 0
  fi
  if nc -z -G 2 "$host" "$port" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

echo "--> Prechecking robot network reachability..."

PING_OK=0
if ping -c 1 -W 1000 "$ROBOT_IP" >/dev/null 2>&1; then
  PING_OK=1
elif ping -c 1 "$ROBOT_IP" >/dev/null 2>&1; then
  PING_OK=1
fi

if [[ "$PING_OK" != "1" ]]; then
  echo "ERROR: Robot IP $ROBOT_IP is not reachable from this host (ping failed)."
  echo "Fix network first (same subnet, cable/Wi-Fi routing, robot powered on), then retry."
  exit 1
fi

PORT_OK=0
for port in 30001 502; do
  if check_tcp_port "$ROBOT_IP" "$port"; then
    PORT_OK=1
    break
  fi
done

if [[ "$PORT_OK" != "1" ]]; then
  echo "ERROR: Robot IP $ROBOT_IP responds to ping but control ports are not reachable (30001/502)."
  echo "Check robot control mode, firewall/VLAN rules, and whether remote control is enabled."
  exit 1
fi

echo "--> Network precheck passed (IP reachable and control port open)."

echo ""
echo "=============================================="
echo "  xArm6 REAL HARDWARE MODE"
echo "  ROBOT_IP: $ROBOT_IP"
echo "  Gripper:  $XARM_ADD_GRIPPER"
echo "=============================================="
echo ""

echo "Preflight safety checklist:"
echo "1. E-stop reachable"
echo "2. Workspace clear"
echo "3. Payload removed or minimal"
echo "4. Correct robot IP and network connectivity"
read -r -p "Type START_REAL to continue: " START_REAL_ACK
if [[ "$START_REAL_ACK" != "START_REAL" ]]; then
  echo "Aborted by operator."
  exit 1
fi

docker compose run --rm \
  -e ROBOT_IP="$ROBOT_IP" \
  -e XARM_ADD_GRIPPER="$XARM_ADD_GRIPPER" \
  -e XARM_PHYSICAL_MODE="$XARM_PHYSICAL_MODE" \
  -e XARM_PHYSICAL_CONFIRM="$XARM_PHYSICAL_CONFIRM" \
  -e XARM_STEP_CONFIRM="$XARM_STEP_CONFIRM" \
  xarm6_sim bash -lc '
    set -euo pipefail
    cd /home/ws

    # ROS setup scripts may read optional unset vars; disable nounset while sourcing.
    set +u
    source /opt/ros/humble/setup.bash
    [ -f /home/ws/install/setup.bash ] && source /home/ws/install/setup.bash
    set -u

    echo "--> Launching xArm6 realmove stack..."
    ros2 launch xarm_moveit_config xarm6_moveit_realmove.launch.py \
      robot_ip:=${ROBOT_IP} add_gripper:=${XARM_ADD_GRIPPER} &
    REAL_LAUNCH_PID=$!

    echo "--> Waiting for arm trajectory action server..."
    ARM_READY=0
    for _ in $(seq 1 120); do
      if ros2 action list | grep -q "/xarm6_traj_controller/follow_joint_trajectory"; then
        ARM_READY=1
        break
      fi
      sleep 1
    done

    if [[ "$ARM_READY" != "1" ]]; then
      echo "ERROR: Arm trajectory action server did not become ready in time."
      kill $REAL_LAUNCH_PID >/dev/null 2>&1 || true
      exit 1
    fi

    if [[ "${XARM_ADD_GRIPPER}" == "true" ]]; then
      echo "--> Waiting for gripper trajectory action server..."
      GRIPPER_READY=0
      for _ in $(seq 1 60); do
        if ros2 action list | grep -q "/xarm_gripper_traj_controller/follow_joint_trajectory"; then
          GRIPPER_READY=1
          break
        fi
        sleep 1
      done
      if [[ "$GRIPPER_READY" != "1" ]]; then
        echo "WARNING: Gripper action server not detected; demo can run arm-only."
      fi
    fi

    echo ""
    echo "--> Controllers ready."
    read -r -p "Type RUN_DEMO to execute pick-and-place: " RUN_DEMO_ACK
    if [[ "$RUN_DEMO_ACK" != "RUN_DEMO" ]]; then
      echo "Demo cancelled by operator."
      kill $REAL_LAUNCH_PID >/dev/null 2>&1 || true
      exit 1
    fi

    ros2 run xarm_pick_place pick_place_node.py

    echo "--> Demo finished. Stopping realmove launch..."
    kill $REAL_LAUNCH_PID >/dev/null 2>&1 || true
  '