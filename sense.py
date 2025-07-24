from sense_hat import SenseHat
import time

sense = SenseHat()
sense.clear()

# ---------- 1. LED MATRIX DISPLAY ----------
sense.show_message("Hello!", scroll_speed=0.05, text_colour=[0, 255, 0])
time.sleep(1)

# ---------- 2. TEMPERATURE & HUMIDITY SENSOR ----------
temperature = sense.get_temperature()
humidity = sense.get_humidity()
print(f"Temperature: {temperature:.2f} C")
print(f"Humidity: {humidity:.2f} %")

# ---------- 3. PRESSURE SENSOR ----------
pressure = sense.get_pressure()
print(f"Pressure: {pressure:.2f} hPa")

# ---------- 4. ACCELEROMETER, GYROSCOPE & MAGNETOMETER ----------
orientation = sense.get_orientation()
accel = sense.get_accelerometer_raw()
gyro = sense.get_gyroscope_raw()
compass = sense.get_compass()

print("\nOrientation:")
print(f"Pitch: {orientation['pitch']:.2f}, Roll: {orientation['roll']:.2f}, Yaw: {orientation['yaw']:.2f}")

print("\nAccelerometer (Raw):")
print(f"x: {accel['x']:.2f}, y: {accel['y']:.2f}, z: {accel['z']:.2f}")

print("\nGyroscope (Raw):")
print(f"x: {gyro['x']:.2f}, y: {gyro['y']:.2f}, z: {gyro['z']:.2f}")

print(f"\nCompass Heading: {compass:.2f} degrees")

# ---------- 5. JOYSTICK EVENT HANDLING ----------
print("\nMove the joystick (Up/Down/Left/Right/Enter)... Press Ctrl+C to stop.")
try:
    while True:
        for event in sense.stick.get_events():
            if event.action == "pressed":
                print(f"Joystick {event.direction.upper()} was pressed")
                # Flash a color on press
                color = {
                    "up": [255, 0, 0],
                    "down": [0, 255, 0],
                    "left": [0, 0, 255],
                    "right": [255, 255, 0],
                    "middle": [255, 0, 255]
                }.get(event.direction, [255, 255, 255])
                sense.clear(color)
                time.sleep(0.2)
                sense.clear()

except KeyboardInterrupt:
    sense.clear()
    print("Program stopped.")
