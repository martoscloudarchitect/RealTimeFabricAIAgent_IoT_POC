import platform
import time
import json
import threading
import random
from azure.iot.device import IoTHubDeviceClient, Message
from gpiozero import LED
from gpiozero.pins.mock import MockFactory
from gpiozero.devices import Device
import tkinter as tk
from tkinter import messagebox
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
CONNECTION_STRING = os.getenv("IOT_HUB_CONNECTION_STRING")

if not CONNECTION_STRING:
    raise ValueError("IOT_HUB_CONNECTION_STRING is not set in the .env file")

# Constants
LED_PIN = 4
TEMPERATURE_ALERT_THRESHOLD = 30

# Configurable ranges for temperature and humidity
TEMPERATURE_RANGE = (10.0, 45.0)  # Min and max temperature
HUMIDITY_RANGE = (33.0, 85.0)     # Min and max humidity

# Global variables
sending_message = False
client = None

# Use mock pin factory on non-Raspberry Pi systems
if platform.system() != "Linux":
    Device.pin_factory = MockFactory()

# Initialize LED
led = LED(LED_PIN)

# Blink LED function
def blink_led():
    if platform.system() == "Linux":
        led.on()
        threading.Timer(0.5, led.off).start()
    else:
        print("Blink LED simulated (no GPIO hardware).")

# Get message function
def get_message():
    # Generate random temperature and humidity within the defined ranges
    temperature = round(random.uniform(*TEMPERATURE_RANGE), 2)  # Generate float values with 2 decimals
    humidity = round(random.uniform(*HUMIDITY_RANGE), 2)        # Generate float values with 2 decimals
    content = json.dumps({
        "deviceId": "Raspberry Pi Web Client 1",
        "temperature": temperature,
        "humidity": humidity
    })
    temperature_alert = temperature > TEMPERATURE_ALERT_THRESHOLD
    return content, temperature_alert

# Send message function
def send_message():
    global sending_message
    while sending_message:
        # Generate the message content
        content, temperature_alert = get_message()

        # Print the message content to the terminal
        print(f"Sending message: {content}")

        # Create the Message object with the content
        message = Message(content)

        # Add custom properties to the message
        message.custom_properties["temperatureAlert"] = str(temperature_alert)

        # Send the message to the IoT Hub
        try:
            client.send_message(message)
            print("Message successfully sent to Azure IoT Hub")
        except Exception as e:
            print(f"Failed to send message: {e}")

        # Blink the LED to indicate a message was sent
        blink_led()

        # Wait for 2 seconds before sending the next message
        time.sleep(4)

# Start sending messages
def start_sending():
    global sending_message
    if not sending_message:
        sending_message = True
        threading.Thread(target=send_message, daemon=True).start()
        print("Started sending messages to Azure IoT Hub")

# Stop sending messages
def stop_sending():
    global sending_message
    sending_message = False
    print("Stopped sending messages to Azure IoT Hub")

# GUI setup
def setup_gui():
    def on_start():
        start_sending()
        messagebox.showinfo("Info", "Started sending messages to Azure IoT Hub")

    def on_stop():
        stop_sending()
        messagebox.showinfo("Info", "Stopped sending messages to Azure IoT Hub")

    root = tk.Tk()
    root.title("Device Control GUI")

    tk.Label(root, text="Device Message Control", font=("Arial", 16)).pack(pady=10)

    start_button = tk.Button(root, text="Start", command=on_start, width=10, bg="green", fg="white")
    start_button.pack(pady=5)

    stop_button = tk.Button(root, text="Stop", command=on_stop, width=10, bg="red", fg="white")
    stop_button.pack(pady=5)

    root.mainloop()

# Main function
def main():
    global client
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)

    try:
        client.connect()
        print("Connected to Azure IoT Hub")

        # Start GUI
        setup_gui()

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        client.disconnect()
        if platform.system() == "Linux":
            led.off()

if __name__ == "__main__":
    main()