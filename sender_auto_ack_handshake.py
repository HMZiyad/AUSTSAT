
from RF24 import RF24
from PIL import Image
import zlib
import time
import camera
import os

# GPIOs used by Sense HAT joystick and potentially reserved
sensehat_pins = [17, 22, 23, 24, 27]  # Joystick directions (Up, Down, Left, Right, Press)

def disable_gpio(pin):
    gpio_path = f"/sys/class/gpio/gpio{pin}"
    
    # Export if not already exported
    if not os.path.exists(gpio_path):
        try:
            with open("/sys/class/gpio/export", "w") as f:
                f.write(str(pin))
        except Exception:
            pass  # Already exported or permission denied

    # Set direction to input and disable pull-up/down
    try:
        with open(f"{gpio_path}/direction", "w") as f:
            f.write("in")
    except Exception:
        pass

    # Optional: Unexport to fully release it (not strictly needed)
    try:
        with open("/sys/class/gpio/unexport", "w") as f:
            f.write(str(pin))
    except Exception:
        pass

# Run disable logic
for pin in sensehat_pins:
    disable_gpio(pin)

radio = RF24(22, 0)
radio.begin()
radio.setChannel(76)
radio.setPALevel(2, False)
radio.setDataRate(RF24.BPS1MBPS)
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()
radio.openWritingPipe(b'1Node')
radio.stopListening()

# Handshake initiation
radio.write(b'SYNC')
print("Sent SYNC, waiting for ACK...")
time.sleep(1)

radio.startListening()
start = time.time()
while time.time() - start < 3:
    if radio.available():
        response = radio.read(radio.getDynamicPayloadSize())
        if response == b'ACK':
            print("ACK received, starting image transfer.")
            break
radio.stopListening()

filename = camera.capture_photo()
img = Image.open(filename).convert("RGB").resize((64, 64))
raw_bytes = img.tobytes()
compressed = zlib.compress(raw_bytes)

print(f"Original: {len(raw_bytes)} bytes, Compressed: {len(compressed)} bytes")
print("Sending image...")

chunk_size = 32
chunks = [compressed[i:i + chunk_size] for i in range(0, len(compressed), chunk_size)]

num_chunks = len(chunks)
radio.write(num_chunks.to_bytes(2, 'big'))
time.sleep(0.01)

for i, chunk in enumerate(chunks):
    if len(chunk) < chunk_size:
        chunk += b'\x00' * (chunk_size - len(chunk))

    success = radio.write(chunk)
    if success:
        print(f"Sent chunk {i+1}/{num_chunks} ✅")
    else:
        print(f"Sent chunk {i+1}/{num_chunks} ❌")
    time.sleep(0.002)
