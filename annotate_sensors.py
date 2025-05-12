import time
from datetime import datetime
import Adafruit_ADS1x15
import os

# --- Configuration ---
ADC_GAIN = 1                # For +/-4.096V range
VOLTAGE_REF = 4.096
DIVIDER_BATTERY = 2.0       # 10kΩ / 10kΩ voltage divider
DIVIDER_PRESSURE = 2.0

# Pressure sensor characteristics
PRESSURE_V_MIN = 0.5        # Volts at 0 psi
PRESSURE_V_MAX = 4.5        # Volts at 1000 psi
PRESSURE_PSI_RANGE = 1000.0

# Physical constants
PSI_TO_PASCAL = 6894.76     # 1 psi in Pascals
GRAVITY = 9.80665           # m/s²

# Seawater salinity in PSU (typical ocean = 35)
SALINITY_PSU = 35.0

# Paths
ANNOTATION_FILE = "/dev/shm/mjpeg/user_annotate.txt"
TEMPERATURE_SENSOR_PATH = "/sys/bus/w1/devices/28-000000c59f72/w1_slave"  # <-- Updated sensor address

# --- Functions ---
def get_seawater_density(salinity_psu=35.0):
    return 1000.0 + 0.77 * salinity_psu

def read_voltage(channel):
    adc = Adafruit_ADS1x15.ADS1115()
    raw = adc.read_adc(channel, gain=ADC_GAIN)
    volts = raw * (VOLTAGE_REF / 32767.0)
    return raw, volts

def get_battery_voltage():
    raw, v_adc = read_voltage(2)  # Battery on AIN2
    voltage = v_adc * DIVIDER_BATTERY
    return round(voltage, 2)

def get_battery_percentage(voltage):
    min_v = 3.0
    max_v = 4.2
    percent = ((voltage - min_v) / (max_v - min_v)) * 100
    return round(max(0, min(100, percent)), 2)

def get_temperature():
    try:
        with open(TEMPERATURE_SENSOR_PATH, "r") as f:
            lines = f.readlines()
        if lines[0].strip()[-3:] == "YES":
            temp_string = lines[1].split("t=")[-1]
            temperature_c = float(temp_string) / 1000.0
            return round(temperature_c, 2)
    except Exception as e:
        print(f"Error reading temperature: {e}")
    return None

def get_pressure_and_depth():
    raw, v_adc = read_voltage(3)  # Pressure sensor on AIN3
    v_sensor = v_adc * DIVIDER_PRESSURE
    v_sensor = max(PRESSURE_V_MIN, min(PRESSURE_V_MAX, v_sensor))

    psi = ((v_sensor - PRESSURE_V_MIN) / (PRESSURE_V_MAX - PRESSURE_V_MIN)) * PRESSURE_PSI_RANGE
    pressure_pa = psi * PSI_TO_PASCAL
    rho = get_seawater_density(SALINITY_PSU)
    depth_m = pressure_pa / (rho * GRAVITY)

    return round(psi, 2), round(depth_m, 2)

def write_annotation(battery_v, battery_percent, pressure_psi, depth_m, temperature_c):
    text = (
        f"Battery: {battery_v:.2f}V ({battery_percent}% charge) | "
        f"Pressure: {pressure_psi:.2f} psi | "
        f"Depth: {depth_m:.2f} m | "
        f"Temperature: {temperature_c}C"
    )
    try:
        with open(ANNOTATION_FILE, "w") as f:
            f.write(text)
        print(f"[{datetime.now()}] {text}")
    except Exception as e:
        print(f"Error writing annotation: {e}")

# --- Main loop ---
if __name__ == "__main__":
    while True:
        battery = get_battery_voltage()
        battery_percent = get_battery_percentage(battery)
        pressure, depth = get_pressure_and_depth()
        temperature = get_temperature()
        write_annotation(battery, battery_percent, pressure, depth, temperature)
        time.sleep(2)

