from sense_hat import SenseHat
import time


sense = SenseHat()

def display_message(text="Hello!", color=[0, 255, 0], scroll_speed=0.05):
    """Display a message on the LED matrix."""
    sense.clear()
    sense.show_message(text, scroll_speed=scroll_speed, text_colour=color)
    sense.clear()

def read_environmental_data():
    """Read temperature, humidity, and pressure."""
    temperature = sense.get_temperature()
    humidity = sense.get_humidity()
    pressure = sense.get_pressure()

    return {
        "temperature": round(temperature, 2),
        "humidity": round(humidity, 2),
        "pressure": round(pressure, 2)
    }

def read_motion_data():
    """Read accelerometer, gyroscope, orientation, and compass."""
    orientation = sense.get_orientation()
    accel = sense.get_accelerometer_raw()
    gyro = sense.get_gyroscope_raw()
    compass = sense.get_compass()

    return {
        "orientation": {
            "pitch": round(orientation['pitch'], 2),
            "roll": round(orientation['roll'], 2),
            "yaw": round(orientation['yaw'], 2)
        },
        "accel_raw": {
            "x": round(accel['x'], 2),
            "y": round(accel['y'], 2),
            "z": round(accel['z'], 2)
        },
        "gyro_raw": {
            "x": round(gyro['x'], 2),
            "y": round(gyro['y'], 2),
            "z": round(gyro['z'], 2)
        },
        "compass": round(compass, 2)
    }
