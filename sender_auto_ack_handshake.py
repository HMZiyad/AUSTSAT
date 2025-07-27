from RF24 import RF24,RF24_1MBPS
from PIL import Image
import zlib
import time
import camera
import json
from sensehat_sensors import read_environmental_data, read_motion_data

# NRF24 Setup
radio = RF24(22, 0)  # CE = GPIO 22 (or change to 26), CSN = SPI CE0
radio.begin()
radio.setChannel(76)
radio.setPALevel(2, False)
radio.setDataRate(RF24_1MBPS)
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()
radio.openWritingPipe(b'1Node')
radio.stopListening()

# Handshake
radio.write(b'SYNC')
print("Sent SYNC, waiting for ACK...")
time.sleep(1)
radio.startListening()

start = time.time()
while time.time() - start < 3:
    if radio.available():
        response = radio.read(radio.getDynamicPayloadSize())
        if response == b'ACK':
            print("ACK received, starting transfer.")
            break
radio.stopListening()

# ---------- 1. Read Sensors ----------
timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
env_data = read_environmental_data()
motion_data = read_motion_data()

sensor_payload = {
    "timestamp": timestamp,
    "temperature": env_data["temperature"],
    "humidity": env_data["humidity"],
    "pressure": env_data["pressure"],
    "pitch": motion_data["orientation"]["pitch"],
    "roll": motion_data["orientation"]["roll"],
    "yaw": motion_data["orientation"]["yaw"],
    "accel": motion_data["accel_raw"],
    "gyro": motion_data["gyro_raw"],
    "compass": motion_data["compass"]
}

sensor_json = json.dumps(sensor_payload)
sensor_compressed = zlib.compress(sensor_json.encode())

print(f"Sending sensor data: {sensor_json}")
radio.write(b'SENS')  # Prefix for sensor packet
time.sleep(0.01)
radio.write(len(sensor_compressed).to_bytes(2, 'big'))
time.sleep(0.01)
for i in range(0, len(sensor_compressed), 32):
    chunk = sensor_compressed[i:i + 32]
    if len(chunk) < 32:
        chunk += b'\x00' * (32 - len(chunk))
    radio.write(chunk)
    time.sleep(0.002)

print("Sensor data sent ✅")

# ---------- 2. Capture & Send Image ----------
filename = camera.capture_photo()
img = Image.open(filename).convert("RGB").resize((64, 64))
raw_bytes = img.tobytes()
compressed = zlib.compress(raw_bytes)

print(f"Original: {len(raw_bytes)} bytes, Compressed: {len(compressed)} bytes")
print("Sending image...")

chunk_size = 32
chunks = [compressed[i:i + chunk_size] for i in range(0, len(compressed), chunk_size)]

# Notify receiver
radio.write(b'IMAG')
time.sleep(0.01)
radio.write(len(compressed).to_bytes(4, 'big'))  # Send image size
time.sleep(0.01)

for i, chunk in enumerate(chunks):
    if len(chunk) < chunk_size:
        chunk += b'\x00' * (chunk_size - len(chunk))
    success = radio.write(chunk)
    if success:
        print(f"Sent chunk {i+1}/{len(chunks)} ✅")
    else:
        print(f"Sent chunk {i+1}/{len(chunks)} ❌")
    time.sleep(0.002)

print("Image transfer complete ✅")
