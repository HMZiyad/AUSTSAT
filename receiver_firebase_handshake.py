from RF24 import RF24
from PIL import Image
import time
import base64
import requests
import uuid
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

sensor_data = None
image_base64 = None

# ---------- Handshake ----------
print("Waiting for handshake...")
while True:
    if radio.available():
        msg = radio.read(4)
        if msg == b'SYNC':
            radio.writeAckPayload(1, b'ACK')
            print("Handshake complete.")
            break

# ---------- Receive Loop ----------
while True:
    if radio.available():
        prefix = radio.read(4)

        # ---------- SENSOR DATA ----------
        if prefix == b'SENS':
            chunk_count = int.from_bytes(radio.read(1), "big")
            print(f"Receiving {chunk_count} sensor chunks...")

            received = bytearray()
            for i in range(chunk_count):
                while not radio.available():
                    time.sleep(0.001)
                chunk = radio.read(32)
                received.extend(chunk)
                print(f"Received chunk {i+1}/{chunk_count}", end="\r")

            try:
                sensor_data = received.rstrip(b'\x00').decode()
                print("\n✅ Sensor data received:")
                print(sensor_data)
            except Exception as e:
                print("❌ Sensor decode error:", e)

        # ---------- IMAGE DATA ----------
        elif prefix == b'IMAG':
            length_bytes = radio.read(4)
            total_len = int.from_bytes(length_bytes, "big")
            print(f"Receiving image ({total_len} bytes)...")

            received = bytearray()
            while len(received) < total_len:
                if radio.available():
                    chunk = radio.read(32)
                    received.extend(chunk)
                time.sleep(0.002)

            try:
                img = Image.frombytes("RGB", (64, 64), received[:64*64*3])
                filename = f"received_{uuid.uuid4().hex}.jpg"
                img.save(filename)
                print(f"✅ Image saved as {filename}")

                with open(filename, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode()

                os.remove(filename)
            except Exception as e:
                print("❌ Image error:", e)

    # ---------- Upload if Both Received ----------
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
                print("❌ Upload failed:", res.status_code)
        except Exception as e:
            print("❌ Firebase error:", e)

        sensor_data = None
        image_base64 = None
        print("🔄 Ready for next data set.")
