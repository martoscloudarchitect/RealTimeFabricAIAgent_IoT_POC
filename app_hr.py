import platform
import time
import json
import threading
import random
import pandas as pd
import uuid
from datetime import datetime
from azure.iot.device import IoTHubDeviceClient, Message
from gpiozero import LED
from gpiozero.pins.mock import MockFactory
from gpiozero.devices import Device
import tkinter as tk
from tkinter import messagebox, StringVar, ttk, Label, Frame
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
CONNECTION_STRING = os.getenv("IOT_HUB_CONNECTION_STRING")

if not CONNECTION_STRING:
    raise ValueError("IOT_HUB_CONNECTION_STRING is not set in the .env file")

# Constants
LED_PIN = 4
HR_CONSUMER_GROUP = "hrdata"
HR_DATA_PATH = 'data/HRdata.csv'
EVENT_TYPES = ["CLOCK_IN", "CLOCK_OUT", "NO_SHOW"]

# Global variables
sending_message = False
client = None
hr_data = None
interval_seconds = 5

# Use mock pin factory on non-Raspberry Pi systems
if platform.system() != "Linux":
    Device.pin_factory = MockFactory()

# Initialize LED
led = LED(LED_PIN)

# Load HR data from CSV file
def load_hr_data():
    global hr_data
    try:
        hr_data = pd.read_csv(HR_DATA_PATH)
        print(f"Loaded {len(hr_data)} employee records from {HR_DATA_PATH}")
        return True
    except Exception as e:
        print(f"Error loading HR data: {e}")
        return False

# Blink LED function
def blink_led():
    if platform.system() == "Linux":
        led.on()
        threading.Timer(0.5, led.off).start()
    else:
        print("Blink LED simulated (no GPIO hardware).")

# Generate HR event message
def get_hr_message(employee_row, event_type):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = json.dumps({
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "eventTime": current_time,
        "employeeData": {
            "employeeNumber": int(employee_row['Employee_Number']),
            "age": int(employee_row['Age']),
            "jobRole": str(employee_row['Job_Role']),
            "department": str(employee_row['Department']),
            "yearsWithManager": int(employee_row['Years_With_Curr_Manager'])
        }
    })
    return content

# Send message function
def send_hr_message(employee_row, event_type):
    content = get_hr_message(employee_row, event_type)
    print(f"Sending HR event: {content}")
    message = Message(content)
    message.custom_properties["eventType"] = event_type
    message.custom_properties["consumerGroup"] = HR_CONSUMER_GROUP
    try:
        client.send_message(message)
        print(f"HR event successfully sent to Azure IoT Hub (Consumer Group: {HR_CONSUMER_GROUP})")
    except Exception as e:
        print(f"Failed to send message: {e}")
    blink_led()

# Start continuous message sending (random employee and event)
def start_sending():
    global sending_message, interval_seconds
    if not sending_message:
        sending_message = True
        def send_continuous():
            while sending_message:
                if hr_data is not None and not hr_data.empty:
                    employee_row = hr_data.sample(1).iloc[0]
                    event_type = random.choice(EVENT_TYPES)
                    send_hr_message(employee_row, event_type)
                time.sleep(interval_seconds)
        threading.Thread(target=send_continuous, daemon=True).start()
        print("Started sending HR events to Azure IoT Hub")

# Stop sending messages
def stop_sending():
    global sending_message
    sending_message = False
    print("Stopped sending HR events to Azure IoT Hub")

# GUI setup
def setup_gui():
    global hr_data, interval_seconds

    def on_send():
        selected_index = employee_listbox.curselection()
        if selected_index:
            employee_row = hr_data.iloc[selected_index[0]]
            event_type = event_type_var.get()
            send_hr_message(employee_row, event_type)
            messagebox.showinfo("Info", f"Sent {event_type} event for Employee #{employee_row['Employee_Number']}")
        else:
            messagebox.showwarning("Warning", "Please select an employee")

    def on_start_auto():
        interval = interval_var.get()
        if interval < 1:
            messagebox.showwarning("Warning", "Interval must be at least 1 second")
            return
        global interval_seconds
        interval_seconds = interval
        start_sending()
        messagebox.showinfo("Info", "Started auto-sending HR events to Azure IoT Hub")

    def on_stop_auto():
        stop_sending()
        messagebox.showinfo("Info", "Stopped auto-sending HR events to Azure IoT Hub")

    root = tk.Tk()
    root.title("HR Clock System")
    root.geometry("600x400")

    # Main title
    Label(root, text="HR Payroll Clock System", font=("Arial", 16, "bold")).pack(pady=10)
    Label(root, text=f"Consumer Group: {HR_CONSUMER_GROUP}", font=("Arial", 10)).pack()

    # Employee list
    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True, padx=20, pady=10)
    Label(frame, text="Select Employee:", font=("Arial", 12)).pack(anchor="w")
    employee_listbox = tk.Listbox(frame, height=10)
    employee_listbox.pack(fill="both", expand=True)
    if hr_data is not None:
        for _, emp in hr_data.iterrows():
            employee_listbox.insert(tk.END, f"{emp['Employee_Number']}: {emp['Job_Role']} - {emp['Department']}")

    # Event type selection
    event_type_var = StringVar(value=EVENT_TYPES[0])
    Label(root, text="Event Type:").pack()
    event_type_combo = ttk.Combobox(root, textvariable=event_type_var, values=EVENT_TYPES, width=15)
    event_type_combo.pack()

    # Interval configuration
    interval_var = tk.IntVar(value=interval_seconds)
    Label(root, text="Auto-Send Interval (sec):").pack()
    interval_scale = tk.Scale(root, from_=1, to=30, orient=tk.HORIZONTAL, variable=interval_var)
    interval_scale.pack()

    # Buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    send_button = tk.Button(button_frame, text="Send Event", command=on_send, bg="#4CAF50", fg="white", width=15)
    send_button.pack(side=tk.LEFT, padx=5)
    auto_start_button = tk.Button(button_frame, text="Start Auto-Send", command=on_start_auto, bg="#2196F3", fg="white", width=15)
    auto_start_button.pack(side=tk.LEFT, padx=5)
    auto_stop_button = tk.Button(button_frame, text="Stop Auto-Send", command=on_stop_auto, bg="#F44336", fg="white", width=15)
    auto_stop_button.pack(side=tk.LEFT, padx=5)

    root.mainloop()

# Main function
def main():
    global client
    if not load_hr_data():
        print("Failed to load HR data. Exiting.")
        return
    try:
        client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        client.connect()
        print("Connected to Azure IoT Hub")
        setup_gui()
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if client:
            client.disconnect()
        if platform.system() == "Linux":
            led.off()

if __name__ == "__main__":
    main()