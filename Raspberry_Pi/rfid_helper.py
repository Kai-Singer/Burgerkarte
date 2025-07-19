import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

try:
  while True:
    option = input("read or write? ")
    if option.lower() == "r":
      id, data = reader.read()
      print(f"ID:\t{id}")
      print(f"Data:\t{data}")
    elif option.lower() == "w":
      text = input("Enter data: ")
      reader.write(text)
      print(f"ok, wrote: '{text}'")
    else:
      GPIO.cleanup()
      break
finally:
  GPIO.cleanup()