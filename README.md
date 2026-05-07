# ODrive v3.6 Sensorless BLDC Motor Control over CAN Bus

Step-by-step guide: from hardware setup to motor spinning over CAN bus

**Hardware:** ODrive v3.6-56V | **Motor:** 350KV BLDC | **CAN adapter:** Waveshare USB-CAN-A | **OS:** Ubuntu 22.04

---

## What you need

| Item | Detail |
|------|--------|
| ODrive v3.6-56V | With firmware v0.5.6 |
| BLDC motor | 350KV, 7 pole pairs, 3 phase wires |
| Power supply | 24V DC, at least 5A |
| Brake resistor | 50W, 2 ohm — connect to AUX terminals |
| USB cable | Micro-USB to USB-A, for configuration |
| Waveshare USB-CAN-A | With CANH, CANL, GND wires |
| Jumper wires | 3 wires: CANH, CANL, GND |
| Linux machine | Ubuntu 22.04 with Python 3 |

---

## Part 1 — Hardware Wiring

### Step 1 — Connect motor phases

Plug the 3 motor phase wires into the M0 screw terminals on the ODrive. The terminals are labelled A, B, C at the bottom of the board. Tighten each screw firmly — a loose connection will cause calibration to fail.

> ⚠️ Do not use alligator clips or loose connections. The ODrive measures phase resistance during calibration and loose wires will give wrong readings.

### Step 2 — Connect power supply

Connect DC+ and DC- from your 24V power supply to the DC terminals on the ODrive. Connect the brake resistor to the AUX terminals. Do not power on yet.

### Step 3 — Connect Waveshare USB-CAN-A to ODrive

Find the J3 header on the top edge of the ODrive board. The pins from left to right are: 3.3V, GND, H, L, GND. Connect three jumper wires:

| ODrive J3 pin | Waveshare terminal |
|---------------|-------------------|
| H (CAN_H) | CAN_H |
| L (CAN_L) | CAN_L |
| GND | GND |

> ⚠️ GND must be connected. Without a common ground the CAN bus will not communicate even if CANH and CANL are correct.

### Step 4 — Enable CAN termination on ODrive

Find the small DIP switch on the ODrive board near the J3 header. It is labelled CAN NO R on the left and CAN 120R on the right. Flip the right switch to the ON position. This enables the 120 ohm termination resistor required for CAN bus communication.

> ℹ️ The Waveshare adapter has its own built-in termination. With both ends terminated the CAN bus is correctly set up.

### Step 5 — Connect USB and power on

Connect the USB cable from the ODrive to your laptop. Then turn on the 24V power supply. The green PWR LED on the ODrive should light up.

---

## Part 2 — Configure ODrive over USB

This part is done once. The configuration is saved to the ODrive flash memory and survives power cycles.

### Step 6 — Install odrivetool

```bash
sudo pip3 install --upgrade odrive
```

### Step 7 — Add udev rules so odrivetool can connect

```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="1209", ATTR{idProduct}=="0d32", MODE="0666"' | sudo tee /etc/udev/rules.d/91-odrive.rules

sudo udevadm control --reload-rules && sudo udevadm trigger
```

Unplug and replug the USB cable, then launch odrivetool:

```bash
odrivetool
```

You should see:
```
Connected to ODrive v3.6-56V ... as odrv0
```

### Step 8 — Clear errors and disable watchdog

```python
odrv0.clear_errors()
odrv0.axis0.config.enable_watchdog = False
odrv0.axis1.config.enable_watchdog = False
```

### Step 9 — Configure motor parameters

```python
odrv0.axis0.motor.config.motor_type = 0
odrv0.axis0.motor.config.pole_pairs = 7
odrv0.axis0.motor.config.current_lim = 10
odrv0.axis0.motor.config.calibration_current = 10
odrv0.axis0.motor.config.resistance_calib_max_voltage = 4
odrv0.axis0.controller.config.vel_limit = 30
odrv0.axis0.controller.config.control_mode = 2
odrv0.axis0.controller.config.input_mode = 1
```

### Step 10 — Configure sensorless mode

```python
odrv0.axis0.sensorless_estimator.config.pm_flux_linkage = 5.51328895422 / (7 * 350)
odrv0.axis0.config.enable_sensorless_mode = True
odrv0.axis0.config.sensorless_ramp.current = 5
odrv0.axis0.config.sensorless_ramp.vel = 400
odrv0.axis0.config.sensorless_ramp.accel = 200
odrv0.axis0.config.sensorless_ramp.finish_distance = 100
odrv0.axis0.config.sensorless_ramp.finish_on_vel = True
```

### Step 11 — Configure CAN interface

```python
odrv0.axis0.config.can.node_id = 0
odrv0.axis1.config.can.node_id = 1
odrv0.can.config.baud_rate = 1000000
```

### Step 12 — Save configuration

```python
odrv0.save_configuration()
```

The board reboots automatically. Reconnect odrivetool and verify:

```python
odrv0.axis0.config.can.node_id   # should return 0
odrv0.can.config.baud_rate        # should return 1000000
```

> ✅ Configuration is done. You only need to do this once. Exit odrivetool before running the Python scripts.

---

## Part 3 — Python Files

### waveshare_bus.py

This file handles communication with the Waveshare USB-CAN-A adapter. See `waveshare_bus.py` in this repo.

### odrive_can_motor_control.py

This is the main motor control script. See `odrive_can_motor_control.py` in this repo.

> ⚠️ Edit line `sys.path.insert(0, '/home/ahsan')` — replace `ahsan` with your Linux username.

---

## Part 4 — Run the test

### Step 15 — Check the Waveshare port

```bash
ls /dev/ttyUSB*
```

Should show `/dev/ttyUSB0`. If not, unplug and replug the Waveshare adapter.

### Step 16 — Make sure odrivetool is closed

The Waveshare and odrivetool cannot use the port at the same time. Close odrivetool completely before running the script.

### Step 17 — Run the script

```bash
python3 ~/odrive_can_motor_control.py
```

Expected output:
```
CAN connected
Waiting for heartbeat...
  ODrive alive — state: 1
Calibrating...
  State → 4
Entering closed loop...
  State → 8
Spinning at 2 turns/sec...
  Velocity → 2.0 turns/sec
Stopping...
Done!
```

> ✅ The motor should beep during calibration and spin for 5 seconds. That means CAN communication is working end to end.

---

## Quick Reference — State Numbers

| Number | State name | What it does |
|--------|-----------|--------------|
| 1 | IDLE | Motor off, no current. Safe resting state. |
| 4 | MOTOR_CALIBRATION | Measures phase resistance and inductance. You hear a beep. |
| 8 | CLOSED_LOOP_CONTROL | Active control. In sensorless mode this triggers the ramp then spins. |

> ℹ️ Always follow this order: state 4 (calibrate) → clear errors → state 8 (spin) → state 1 (stop). Skipping calibration will fail.

---

## Common Problems

> ℹ️ For each problem: first run `dump_errors(odrv0)` in odrivetool to see the exact error. Then apply the fix below.

### No heartbeat received

The script connects to the Waveshare but times out waiting for the ODrive heartbeat.

- Check CANH and CANL wires are not swapped
- Check GND wire is connected between ODrive J3 and Waveshare GND terminal
- Check CAN 120R DIP switch is ON on the ODrive board
- Verify node_id: `odrv0.axis0.config.can.node_id` should return `0`
- Verify baudrate: `odrv0.can.config.baud_rate` should return `1000000`
- Make sure odrivetool is closed — it blocks the USB port and can interfere

### PHASE_RESISTANCE_OUT_OF_RANGE

Motor calibration fails. The ODrive measured a resistance outside the expected range.

- Tighten all 3 motor phase wire screws on the M0 terminals
- Make sure no insulation is caught under the screw — bare wire must make contact
- In odrivetool run: `odrv0.axis0.motor.config.calibration_current = 10`
- Then: `odrv0.axis0.motor.config.resistance_calib_max_voltage = 4`
- Clear errors and retry: `odrv0.clear_errors()` then `odrv0.axis0.requested_state = 4`

### MODULATION_IS_NAN

This appears after the motor stops. It is normal behavior in sensorless mode — the estimator loses lock when speed drops to zero. It is not a hardware problem.

- Clear errors with `odrv0.clear_errors()`
- Recalibrate with `requested_state = 4` before each new spin session
- Never command velocity to 0 while in closed loop sensorless mode — go to IDLE state instead

### WATCHDOG_TIMER_EXPIRED

Appears on every fresh connection. Leftover from a previous session.

```python
odrv0.axis0.config.enable_watchdog = False
odrv0.axis1.config.enable_watchdog = False
odrv0.clear_errors()
```

### OVERSPEED

Motor enters closed loop then immediately errors. The velocity limit is too low for the sensorless ramp.

```python
odrv0.axis0.controller.config.vel_limit = 30
odrv0.save_configuration()
```

### ttyUSB0 not found

The Waveshare adapter is not detected by Linux.

- Unplug and replug the USB cable
- Check with: `lsusb` — look for QinHeng Electronics CH340
- Add permissions: `sudo chmod 666 /dev/ttyUSB0`

### ODrive not found by odrivetool

lsusb shows the ODrive (1209:0d32) but odrivetool says 'Please connect your ODrive'.

```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="1209", ATTR{idProduct}=="0d32", MODE="0666"' | sudo tee /etc/udev/rules.d/91-odrive.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Unplug and replug the USB cable.

### Disk full — odrivetool won't launch

Ubuntu throws FileNotFoundError about /tmp when the root partition is 100% full.

```bash
df -h /
sudo apt clean
sudo apt autoremove --purge
sudo journalctl --vacuum-size=100M
```

---

## License

MIT
