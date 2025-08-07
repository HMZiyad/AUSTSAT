from RF24 import RF24
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
radio = RF24(22, 0)
address = b"Node1"  # Use a consistent 5-byte address

if not radio.begin():
    raise RuntimeError("Radio hardware not responding")

radio.openWritingPipe(address)
radio.setPALevel(RF24.PA_LOW) # Use the library constant for clarity
radio.stopListening()

print("Sender is ready...")
counter = 0
while True:
    msg = f"Test packet {counter}"
    payload = msg.encode("utf-8")
    
    # radio.write() returns True if it gets an ACK
    ack_received = radio.write(payload)
    
    if ack_received:
        print(f"Sent: '{msg}'. ACK received.")
        counter += 1
    else:
        print("Transmission failed. No ACK received.")
        
    time.sleep(1)
