# ECL Modbus for Home Assistant
A custom Home Assistant integration for reading data from **Danfoss ECL 120 and ECL 220 heating controllers** using **Modbus RTU**.

This integration is created by an enthusiast (not a professional developer) and is actively evolving.
It is tested on **ECL 120**, but **ECL 220 uses the same register map**, so it *should* work identically — feedback is welcome!

## 🔧 Features
Current supported features:

### Temperature Sensors
| Sensor | Register | Description |
|--------|----------|-------------|
| **S1 Temperature** | 4000 | Current value of temperature sensor S1 |
| **S2 Temperature** | 4010 | Current value of temperature sensor S2 |
| **S3 Temperature** | 4020 | Current value of temperature sensor S3 |
| **S4 Temperature** | 4030 | Current value of temperature sensor S4 |
| **S5 Temperature** | 4040 | Current value of temperature sensor S5 |
| **S6 Temperature** | 4050 | Current value of temperature sensor S6 |

### Additional Calculated Values
| Name | Register | Type | Description |
|------|----------|-------|-------------|
| **Valve Position** | 21700 | Float (%) | Actual valve opening position |
| **Heat Flow Temperature Reference** | 21200 | Float (°C) | Calculated heat flow reference |
| **Heat Return Temperature Reference** | 21210 | Float (°C) | Reference for Return Limiter |

### Fully configurable
- Enable/disable each sensor individually  
- Auto reconnect Modbus if the USB adapter restarts  
- Friendly naming and unified device info in Home Assistant  

## 🚀 Installation

### Install via HACS

If you want to use this code with Home Assistant, you should be able to install it with HACS by adding this repo

### Manual installation
1. Download the latest release ZIP  
2. Extract it into:  
   ```
   /config/custom_components/ecl_modbus/
   ```
3. Restart Home Assistant  
4. Add integration via:  
   **Settings → Devices & Services → Add Integration → ECL Modbus**

## ⚙️ Configuration
During setup you specify:

- Serial Port (example: `/dev/ttyUSB0` or `/dev/serial/by-id/...`)
- Baudrate (default: 38400)
- Slave ID (default: 5)

### Options
- Enable/disable sensors

No YAML required.

## 🧩 How it works
- Uses Modbus RTU via `pymodbus`
- Each sensor polls individually using HA's update engine
- Automatic reconnect on USB/serial failures
- Groups all sensors under one device

## 🧪 Compatibility
| Controller | Status |
|------------|--------|
| **ECL 120** | ✔ Tested |
| **ECL 220** | ⚠ Untested, but register-compatible |

## 🛠️ Planned Features
- This integration is actively evolving. The goal is to continuously expand which ECL registers and parameters can be read and eventually controlled.
If you have suggestions, missing registers, or special needs for your ECL setup, you are very welcome to contact me — contributions and ideas are highly appreciated!

## ❤️ Contributions
This project is community-driven — PRs and feedback are welcome!

GitHub: https://github.com/nichlasrohde/ha-ecl-modbus

## 📄 License
MIT License
