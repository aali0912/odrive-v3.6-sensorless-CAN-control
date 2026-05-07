import sys
import time
import struct
import can

sys.path.insert(0, '/home/ahsan')
from waveshare_bus import WaveshareBus

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
CAN_PORT   = '/dev/ttyUSB0'
NODE_ID    = 0
BITRATE    = 1000000  # 1Mbps - must match ODrive

# ODrive CANSimple command IDs
CMD_HEARTBEAT      = 0x01
CMD_SET_AXIS_STATE = 0x07
CMD_SET_INPUT_VEL  = 0x0D
CMD_GET_ENCODER    = 0x09

# ODrive axis states
AXIS_STATE_IDLE              = 1
AXIS_STATE_MOTOR_CALIBRATION = 4
AXIS_STATE_CLOSED_LOOP       = 8

def get_arb_id(node_id, cmd_id):
    return (node_id << 5) | cmd_id

def set_axis_state(bus, node_id, state):
    arb_id = get_arb_id(node_id, CMD_SET_AXIS_STATE)
    data = struct.pack('<I', state)
    msg = can.Message(
        arbitration_id=arb_id,
        data=data,
        is_extended_id=False
    )
    bus.send(msg)
    print(f"  Sent axis state: {state}")

def set_velocity(bus, node_id, velocity, torque_ff=0.0):
    arb_id = get_arb_id(node_id, CMD_SET_INPUT_VEL)
    data = struct.pack('<ff', velocity, torque_ff)
    msg = can.Message(
        arbitration_id=arb_id,
        data=data,
        is_extended_id=False
    )
    bus.send(msg)
    print(f"  Sent velocity: {velocity} turns/sec")

def wait_for_heartbeat(bus, node_id, timeout=5.0):
    print("Waiting for ODrive heartbeat...")
    target_id = get_arb_id(node_id, CMD_HEARTBEAT)
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=1.0)
        if msg is None:
            continue
        print(f"  Raw msg ID: {hex(msg.arbitration_id)}")
        if msg.arbitration_id == target_id:
            error = struct.unpack('<I', bytes(msg.data[:4]))[0]
            state = msg.data[4]
            print(f"  Heartbeat! State: {state}, Error: {error}")
            return state
    print("No heartbeat received!")
    return None

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("=" * 45)
    print("  ODrive CAN Motor Control")
    print("  Waveshare USB-CAN-A | Node ID: 0")
    print("=" * 45)

    print(f"\nConnecting to CAN bus on {CAN_PORT}...")
    bus = WaveshareBus(channel=CAN_PORT, bitrate=BITRATE)
    print("CAN bus connected!")

    # Wait for heartbeat
    state = wait_for_heartbeat(bus, NODE_ID, timeout=5.0)
    if state is None:
        print("ODrive not responding on CAN. Check wiring!")
        bus.shutdown()
        return

    print(f"\nODrive alive! Current state: {state}")

    # Calibrate
    print("\nCalibrating motor...")
    set_axis_state(bus, NODE_ID, AXIS_STATE_MOTOR_CALIBRATION)
    print("Waiting 8 seconds for calibration...")
    time.sleep(8)

    # Enter closed loop
    print("\nEntering closed loop control...")
    set_axis_state(bus, NODE_ID, AXIS_STATE_CLOSED_LOOP)
    time.sleep(3)

    # Spin
    print("\nTest 1: 2 turns/sec for 5 seconds...")
    set_velocity(bus, NODE_ID, 2.0)
    time.sleep(5)

    print("Test 2: 4 turns/sec for 5 seconds...")
    set_velocity(bus, NODE_ID, 4.0)
    time.sleep(5)

    # Stop
    print("\nStopping motor...")
    set_velocity(bus, NODE_ID, 0.0)
    time.sleep(1)
    set_axis_state(bus, NODE_ID, AXIS_STATE_IDLE)

    bus.shutdown()
    print("\n" + "=" * 45)
    print("  Done! Motor stopped safely.")
    print("=" * 45)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted!")
