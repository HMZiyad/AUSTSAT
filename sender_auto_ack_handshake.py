# sender_fixed.py
from RF24 import RF24
from PIL import Image
import zlib
import time
import json
# Assuming you have these helper files
from camera import capture_photo 
from sense import read_environmental_data, read_motion_data

# ---------- NRF24 Setup ----------
radio = RF24(22, 0) # CE = GPIO 22, CSN = SPI CE0
if not radio.begin():
    raise RuntimeError("radio hardware is not responding")
radio.setChannel(76)
radio.setPALevel(RF24.PA_LOW)
radio.setDataRate(RF24.DR_1MBPS)
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.openWritingPipe(b'1Node')
radio.stopListening()

# ---------- Handshake ----------
print("Sending SYNC for handshake...")
radio.write(b'SYNC')
radio.startListening()
start = time.time()
handshake_ok = False
while time.time() - start < 2:
    if radio.available():
        response = radio.read(radio.getDynamicPayloadSize())
        if response == b'ACK':
            print("ACK received, handshake complete.")
            handshake_ok = True
            break
radio.stopListening()

if not handshake_ok:
    print("Handshake failed. Exiting.")
    exit()

# ---------- 1. Read Sensors and Send in One Packet ----------
timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
env_data = read_environmental_data()
motion_data = read_motion_data()

sensor_payload = {
    "timestamp": timestamp,
    "temperature": env_data["temperature"],
    "humidity": env_data["humidity"],
    "pressure": env_data["pressure"],
    "orientation": motion_data["orientation"],
    "accel_raw": motion_data["accel_raw"],
    "gyro_raw": motion_data["gyro_raw"],
    "compass": motion_data["compass"]
}

sensor_json = json.dumps(sensor_payload)
sensor_compressed = zlib.compress(sensor_json.encode())

# Construct a single packet: 4-byte prefix + compressed data
# The total payload must be <= 32 bytes for a single packet.
# If compressed data is > 28 bytes, this simple method will fail.
# For this lab, zlib will likely make it small enough.
sensor_packet = b'SENS' + sensor_compressed
if len(sensor_packet) > 32:
    print("❌ Compressed sensor data is too large for a single packet!")
else:
    print(f"Sending sensor data: {len(sensor_packet)} bytes")
    if radio.write(sensor_packet):
        print("Sensor data sent ✅")
    else:
        print("Sensor data send failed ❌")

time.sleep(0.5) # Give receiver time to process

# ---------- 2. Capture & Send Image ----------
filename = capture_photo()
img = Image.open(filename).convert("RGB").resize((64, 64))
raw_bytes = img.tobytes()
compressed = zlib.compress(raw_bytes)

print(f"\nOriginal Img: {len(raw_bytes)} bytes, Compressed: {len(compressed)} bytes")
print("Sending image...")

# Send prefix and total size in the first packet
size_packet = b'IMAG' + len(compressed).to_bytes(4, 'big')
radio.write(size_packet)

# Wait for receiver to acknowledge it got the size
radio.startListening()
start = time.time()
size_ack_ok = False
while time.time() - start < 2:
    if radio.available():
        if radio.read(radio.getDynamicPayloadSize()) == b'GOTSIZE':
            print("Receiver acknowledged image size. Starting chunk transfer.")
            size_ack_ok = True
            break
radio.stopListening()

if not size_ack_ok:
    print("Receiver did not acknowledge image size. Aborting image transfer.")
else:
    # Send image in chunks
    chunk_size = 28 # Leave space for potential headers in the future
    chunks = [compressed[i:i + chunk_size] for i in range(0, len(compressed), chunk_size)]
    for i, chunk in enumerate(chunks):
        if radio.write(chunk):
            print(f"  -> Sent chunk {i+1}/{len(chunks)} ✅")
        else:
            print(f"  -> Sent chunk {i+1}/{len(chunks)} ❌ - RETRYING")
            if not radio.write(chunk): # Simple retry
                 print(f"  -> Sent chunk {i+1}/{len(chunks)} ❌ - FAILED")
        time.sleep(0.005) # Small delay between chunks

    print("\nImage transfer complete ✅")
