from RF24 import RF24
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
radio = RF24(22, 0)
address = b"Node1"  # Make sure this is IDENTICAL to the sender's address

if not radio.begin():
    raise RuntimeError("Radio hardware not responding")

radio.openReadingPipe(1, address)
radio.setPALevel(RF24.PA_LOW)
radio.startListening()
print("Listening...")

while True:
    if radio.available():
        payload = radio.read(radio.getDynamicPayloadSize())
        message = payload.decode("utf-8")
        print(f"Received message: '{message}' (ACK was auto-sent)")

Receiver code