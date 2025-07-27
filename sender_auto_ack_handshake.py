from RF24 import RF24,RF24_1MBPS
from PIL import Image
import time
import camera
from sense import read_environmental_data
import uuid

radio = RF24(22, 0)
radio.begin()
radio.setChannel(76)
radio.setPALevel(2, False)
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()
radio.openWritingPipe(b'1Node')
radio.stopListening()

# ---------- Handshake ----------
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

# ---------- Send Sensor Data ----------
timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
env = read_environmental_data()

sensor_text = f"{timestamp}|T:{env['temperature']}C|H:{env['humidity']}%|P:{env['pressure']}hPa"
sensor_bytes = sensor_text.encode()

# Send prefix
radio.write(b'SENS')
time.sleep(0.01)

# Chunk sensor data
chunk_size = 32
chunks = [sensor_bytes[i:i+chunk_size] for i in range(0, len(sensor_bytes), chunk_size)]

# Send number of chunks
radio.write(len(chunks).to_bytes(1, 'big'))
time.sleep(0.01)

# Send each chunk
for i, chunk in enumerate(chunks):
    if len(chunk) < chunk_size:
        chunk += b'\x00' * (chunk_size - len(chunk))  # Pad last chunk
    radio.write(chunk)
    print(f"Sent sensor chunk {i+1}/{len(chunks)}")
    time.sleep(0.01)


# ---------- Send Image ----------
filename = camera.capture_photo()
img = Image.open(filename).convert("RGB").resize((64, 64))
img_bytes = img.tobytes()

print(f"Sending image of {len(img_bytes)} bytes")
radio.write(b'IMAG')
time.sleep(0.01)
radio.write(len(img_bytes).to_bytes(4, 'big'))
time.sleep(0.01)

img_chunks = [img_bytes[i:i+32] for i in range(0, len(img_bytes), 32)]
for i, chunk in enumerate(img_chunks):
    if len(chunk) < 32:
        chunk += b'\x00' * (32 - len(chunk))
    radio.write(chunk)
    print(f"Sent image chunk {i+1}/{len(img_chunks)}")
    time.sleep(0.005)

print("✅ Sensor data and image sent.")
