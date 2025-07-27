from RF24 import RF24
from PIL import Image
import time
import camera
import uuid
import os

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
print("📡 Sent SYNC, waiting for ACK...")
time.sleep(1)

radio.startListening()
start = time.time()
while time.time() - start < 3:
    if radio.available():
        response = radio.read(radio.getDynamicPayloadSize())
        if response == b'ACK':
            print("🤝 ACK received, starting image transfer.")
            break
radio.stopListening()

# ---------- Capture & Compress Image ----------
filename = camera.capture_photo()
img = Image.open(filename).convert("RGB").resize((64, 64))
jpeg_filename = f"/tmp/compressed_{uuid.uuid4().hex}.jpg"
img.save(jpeg_filename, format="JPEG", quality=50)

with open(jpeg_filename, "rb") as f:
    jpeg_bytes = f.read()
os.remove(jpeg_filename)

print(f"📦 JPEG size: {len(jpeg_bytes)} bytes")

# ---------- Send Image Metadata ----------
radio.write(b'IMAG')
time.sleep(0.01)
radio.write(len(jpeg_bytes).to_bytes(4, 'big'))
time.sleep(0.01)

# ---------- Send Image in 32-byte Chunks ----------
chunk_size = 32
chunks = [jpeg_bytes[i:i+chunk_size] for i in range(0, len(jpeg_bytes), chunk_size)]

for i, chunk in enumerate(chunks):
    if len(chunk) < chunk_size:
        chunk += b'\x00' * (chunk_size - len(chunk))
    radio.write(chunk)
    print(f"📤 Sent chunk {i+1}/{len(chunks)}")
    time.sleep(0.005)

print("✅ Compressed image sent.")
