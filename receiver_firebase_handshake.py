from RF24 import RF24
from PIL import Image
import zlib
import time
import base64
import requests
import uuid
import os
import json

radio = RF24(22, 0)
radio.begin()
radio.setChannel(76)
radio.setPALevel(2, False)
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()
radio.openReadingPipe(1, b'1Node')
radio.startListening()

# ---------- Handshake ----------
print("Waiting for handshake...")
while True:
    if radio.available():
        msg = radio.read(4)
        if msg == b'SYNC':
            radio.stopListening()
            time.sleep(0.05)
            radio.writeAckPayload(1, b'ACK')
            print("Handshake complete.")
            radio.startListening()
            break

        else:
            continue

sensor_data = {}
image_base64 = None

# ---------- Wait for Sensor or Image ----------
while True:
    if radio.available():
        prefix = radio.read(4)

        # ---------- SENSOR BLOCK ----------
        if prefix == b'SENS':
            print("Receiving sensor data...")
            length_bytes = radio.read(2)
            total_len = int.from_bytes(length_bytes, "big")

            received = bytearray()
            while len(received) < total_len:
                if radio.available():
                    chunk = radio.read(32)
                    received.extend(chunk)
                time.sleep(0.002)

            try:
                sensor_json = zlib.decompress(received).decode()
                sensor_data = json.loads(sensor_json)
                print("✅ Sensor data received:")
                print(json.dumps(sensor_data, indent=2))
            except Exception as e:
                print("❌ Failed to decompress or parse sensor data:", e)

        # ---------- IMAGE BLOCK ----------
        elif prefix == b'IMAG':
            print("Receiving image...")
            length_bytes = radio.read(4)
            total_len = int.from_bytes(length_bytes, "big")

            received = bytearray()
            while len(received) < total_len:
                if radio.available():
                    chunk = radio.read(32)
                    received.extend(chunk)
                time.sleep(0.002)

            try:
                decompressed = zlib.decompress(received)
                image = Image.frombytes("RGB", (64, 64), decompressed)
                filename = f"received_{uuid.uuid4().hex}.jpg"
                image.save(filename)
                print(f"✅ Image saved as {filename}")

                with open(filename, "rb") as img_file:
                    image_base64 = base64.b64encode(img_file.read()).decode('utf-8')

                os.remove(filename)
            except Exception as e:
                print("❌ Failed to process image:", e)

    # ---------- Upload When Both Are Ready ----------
    if sensor_data and image_base64:
        firebase_url = "https://fire-authentic-f5c81-default-rtdb.firebaseio.com/image_log.json"

        data = {
            "timestamp": sensor_data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
            "sensor_data": sensor_data,
            "image_base64": image_base64
        }

        try:
            res = requests.post(firebase_url, json=data)
            if res.status_code == 200:
                print("✅ Sensor data + image uploaded to Firebase.")
            else:
                print("❌ Upload failed. Status code:", res.status_code)
        except Exception as e:
            print("❌ Firebase error:", e)

        # Reset for next transmission
        sensor_data = {}
        image_base64 = None
        print("\n🔄 Ready for next data block...")
