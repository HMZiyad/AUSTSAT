from RF24 import RF24
import time
from PIL import Image
import uuid
import base64
import requests
import os

radio = RF24(22, 0)
radio.begin()
radio.setChannel(76)
radio.setPALevel(2, False)
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()
radio.openReadingPipe(1, b'1Node')
radio.startListening()

print("📡 Waiting for SYNC...")
while True:
    if radio.available():
        msg = radio.read(4)
        if msg == b'SYNC':
            radio.writeAckPayload(1, b'ACK')
            print("🤝 Handshake complete.")
            break

# ---------- Listen for Image ----------
while True:
    if radio.available():
        prefix = radio.read(4)

        if prefix == b'IMAG':
            print("🖼️ Receiving compressed JPEG...")

            length_bytes = radio.read(4)
            total_len = int.from_bytes(length_bytes, "big")
            print(f"🔢 Expected size: {total_len} bytes")

            received = bytearray()
            while len(received) < total_len:
                if radio.available():
                    chunk = radio.read(32)
                    received.extend(chunk)
                time.sleep(0.002)

            try:
                jpeg_data = bytes(received[:total_len])
                file_name = f"received_{uuid.uuid4().hex}.jpg"
                with open(file_name, "wb") as f:
                    f.write(jpeg_data)
                print(f"✅ JPEG saved as {file_name}")

                # Optional: Convert to base64 and send to Firebase
                with open(file_name, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()

                firebase_url = "https://fire-authentic-f5c81-default-rtdb.firebaseio.com/image_log.json"
                data = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "image_base64": b64
                }
                res = requests.post(firebase_url, json=data)
                if res.status_code == 200:
                    print("✅ Uploaded to Firebase.")
                else:
                    print("❌ Firebase error:", res.status_code)

                os.remove(file_name)

            except Exception as e:
                print("❌ JPEG receive error:", e)
