from RF24 import RF24
from PIL import Image
import time
import base64
import requests
import uuid
import os
import json

# Initialize the radio
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
handshake_timeout = time.time() + 10  # wait up to 10 seconds
while time.time() < handshake_timeout:
    if radio.available():
        msg = radio.read(4)
        if msg == b'SYNC':
            radio.writeAckPayload(1, b'ACK')
            print("🤝 Handshake complete.")
            break
    time.sleep(0.01)
else:
    print("❌ Handshake timeout. No 'SYNC' received.")
    exit(1)

# ---------- Main Receive Loop ----------
while True:
    try:
        if radio.available():
            prefix = radio.read(4)
            # Debug: show received prefix in hex form
            print(f"DEBUG: Received prefix: {prefix.hex()}")

            # ---------- SENSOR DATA ----------
            if prefix == b'SENS':
                print("📥 Receiving sensor data...")
                # Wait for the chunk count byte
                while not radio.available():
                    time.sleep(0.001)
                chunk_count = int.from_bytes(radio.read(1), "big")
                print(f"Expecting {chunk_count} sensor chunks.")

                received = bytearray()
                for i in range(chunk_count):
                    while not radio.available():
                        time.sleep(0.001)
                    chunk = radio.read(32)
                    received.extend(chunk)
                    print(f"Received sensor chunk {i+1}/{chunk_count}", end="\r")
                print()  # newline

                try:
                    sensor_text = received.rstrip(b'\x00').decode('utf-8')
                    print("✅ Sensor data received:")
                    print(sensor_text)
                    sensor_data = sensor_text
                except Exception as e:
                    print("❌ Failed to decode sensor data:", e)

            # ---------- IMAGE DATA ----------
            elif prefix == b'IMAG':
                print("🖼️ Receiving image data...")
                # Read 4 bytes for the total image length
                while not radio.available():
                    time.sleep(0.001)
                length_bytes = radio.read(4)
                total_len = int.from_bytes(length_bytes, "big")
                print(f"Expecting image length: {total_len} bytes.")

                received = bytearray()
                start_time = time.time()
                while len(received) < total_len:
                    if radio.available():
                        chunk = radio.read(32)
                        received.extend(chunk)
                        print(f"Received image bytes: {len(received)}/{total_len}", end="\r")
                    # Timeout if taking too long
                    if time.time() - start_time > 5:
                        print("\n❌ Image receive timeout.")
                        break
                    time.sleep(0.002)
                print()  # newline

                try:
                    # Because image is raw RGB data for 64x64, total expected size = 64*64*3
                    expected_size = 64 * 64 * 3
                    if len(received) < expected_size:
                        print("❌ Received image data is smaller than expected!")
                    else:
                        img = Image.frombytes("RGB", (64, 64), received[:expected_size])
                        filename = f"received_{uuid.uuid4().hex}.jpg"
                        img.save(filename)
                        print(f"✅ Image saved as {filename}")

                        with open(filename, "rb") as f:
                            image_base64 = base64.b64encode(f.read()).decode('utf-8')
                        os.remove(filename)
                except Exception as e:
                    print("❌ Image processing error:", e)

            else:
                # Unknown prefix: dump out for debugging
                print(f"❌ Received unknown prefix: {prefix}")

        # ---------- Upload When Both Are Ready ----------
        if sensor_data and image_base64:
            firebase_url = "https://fire-authentic-f5c81-default-rtdb.firebaseio.com/image_log.json"
            payload = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "sensor_data": sensor_data,
                "image_base64": image_base64
            }
            print("Uploading data to Firebase...")
            try:
                res = requests.post(firebase_url, json=payload)
                if res.status_code == 200:
                    print("✅ Data uploaded to Firebase.")
                else:
                    print("❌ Firebase upload failed. Status code:", res.status_code)
            except Exception as e:
                print("❌ Firebase error:", e)

            # Reset for the next transmission
            sensor_data = None
            image_base64 = None
            print("🔄 Ready for next data set.")

    except Exception as e:
        print("❌ Error in main receive loop:", e)
    time.sleep(0.005)
