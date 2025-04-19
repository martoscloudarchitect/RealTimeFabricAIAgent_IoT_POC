# filepath: c:\GitHub\IoT\IoTSimulatorPoC\mock_smbus.py
class SMBus:
    def __init__(self, bus):
        print(f"Mock SMBus initialized for bus {bus}")

    def read_byte_data(self, i2c_addr, register):
        print(f"Mock read_byte_data from addr {i2c_addr}, register {register}")
        return 0

    def write_byte_data(self, i2c_addr, register, value):
        print(f"Mock write_byte_data to addr {i2c_addr}, register {register}, value {value}")