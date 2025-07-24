
from RF24 import RF24
from PIL import Image
import zlib
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

# Handshake before receiving
print("Waiting for handshake...")
while True:
    if radio.available():
        msg = radio.read(4)
        if msg == b'SYNC':
            radio.writeAckPayload(1, b'ACK')
            print("Handshake complete.")
            break

while True:
    print("Listening for image...")

    while True:
        if radio.available():
            header = radio.read(2)
            num_chunks = int.from_bytes(header, "big")
            print(f"Expecting {num_chunks} chunks...")
            break
        time.sleep(0.01)

    received = bytearray()
    chunks_received = 0

    while chunks_received < num_chunks:
        if radio.available():
            chunk = radio.read(32)
            received.extend(chunk)
            chunks_received += 1
            print(f"Received chunk {chunks_received}/{num_chunks}", end="\r")
            radio.writeAckPayload(1, b'OK')
        time.sleep(0.002)

    try:
        decompressed = zlib.decompress(received)
        image = Image.frombytes("RGB", (64, 64), decompressed)
        filename = f"received_{uuid.uuid4().hex}.jpg"
        image.save(filename)
        print(f"\n✅ Image saved as {filename}")

        with open(filename, "rb") as img_file:
            b64_string = base64.b64encode(img_file.read()).decode('utf-8')

        firebase_url = "https://fire-authentic-f5c81-default-rtdb.firebaseio.com/image_log.json"
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "image_base64": b64_string
        }

        res = requests.post(firebase_url, json=data)
        if res.status_code == 200:
            print("✅ Image uploaded to Firebase Realtime Database.")
        else:
            print("❌ Failed to upload. Status code:", res.status_code)

        os.remove(filename)
    except Exception as e:
        print("\n❌ Error decompressing or uploading image:", e)
