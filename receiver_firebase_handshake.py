from RF24 import RF24
from PIL import Image
import time
import base64
import requests
import uuid
import os
import json

# Setup NRF24L01
radio = RF24(22, 0)
radio.begin()
radio.setChannel(76)
radio.setPALevel(2, False)
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()
radio.openReadingPipe(1, b'1Node')
radio.startListening()

sensor_data = None
image_base64 = None

# ---------- Handshake ----------
print("📡 Waiting for handshake...")
while True:
    if radio.available():
        msg = radio.read(4)
        if msg == b'SYNC':
            radio.writeAckPayload(1, b'ACK')
            print("🤝 Handshake complete.")
            break

# ---------- Receive Loop ----------
while True:
    if radio.available():
        prefix = radio.read(4)

        # ---------- SENSOR DATA ----------
        if prefix == b'SENS':
            while not radio.available():
                time.sleep(0.001)

            chunk_count = int.from_bytes(radio.read(1), "big")
            print(f"📥 Receiving {chunk_count} sensor chunks...")

            received = bytearray()
            for i in range(chunk_count):
                while not radio.available():
                    time.sleep(0.001)
                chunk = radio.read(32)
                received.extend(chunk)
                print(f"📦 Sensor chunk {i+1}/{chunk_count}", end="\r")

            try:
                sensor_text = received.rstrip(b'\x00').decode()
                print("\n✅ Sensor data received:")
                print(sensor_text)
                sensor_data = sensor_text
            except Exception as e:
                print("❌ Sensor decode error:", e)

        # ---------- IMAGE DATA ----------
        elif prefix == b'IMAG':
            print("\n🖼️ Receiving image...")

            while not radio.available():
                time.sleep(0.001)

            # Step 1: Read total image length
            length_bytes = radio.read(2)
            total_len = int.from_bytes(length_bytes, "big")
            print(f"🗂 Expected image size: {total_len} bytes")

            # Step 2: Calculate how many 32-byte chunks
            chunk_count = (total_len + 31) // 32
            print(f"🔢 Receiving {chunk_count} image chunks...")

            received = bytearray()
            for i in range(chunk_count):
                while not radio.available():
                    time.sleep(0.001)
                chunk = radio.read(32)
                received.extend(chunk)
                print(f"🧩 Image chunk {i+1}/{chunk_count}", end="\r")

            try:
                # Step 3: Trim and save image
                image_bytes = bytes(received[:total_len])
                img = Image.frombytes("RGB", (64, 64), image_bytes)

                filename = f"received_{uuid.uuid4().hex}.jpg"
                img.save(filename)
                print(f"\n✅ Image saved as {filename}")

                with open(filename, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode()

                os.remove(filename)
            except Exception as e:
                print("❌ Image decode error:", e)

    # ---------- Upload When Both Are Ready ----------
    if sensor_data and image_base64:
        firebase_url = "https://fire-authentic-f5c81-default-rtdb.firebaseio.com/image_log.json"

        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sensor_data": sensor_data,
            "image_base64": image_base64
        }

        try:
            res = requests.post(firebase_url, json=data)
            if res.status_code == 200:
                print("✅ Uploaded to Firebase.")
            else:
                print("❌ Upload failed. Status code:", res.status_code)
        except Exception as e:
            print("❌ Firebase error:", e)

        # Reset state
        sensor_data = None
        image_base64 = None
        print("🔄 Ready for next data set.")
