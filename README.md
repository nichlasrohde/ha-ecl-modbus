# ECL 120/220 Modbus for Home Assistant
A custom Home Assistant integration for reading data from **Danfoss ECL 120 and ECL 220 heating controllers** using **Modbus RTU**.

This integration is created by an enthusiast (not a professional developer) and is actively evolving.
It is tested on **ECL 120**, but **ECL 220 uses the same register map**, so it *should* work identically — feedback is welcome!

## 🔧 Features
Current supported features:

| **Addr** | **RW** | **Name**                               | **Type** | **Unit** | **Min** | **Max** | **Description**                                                                   |
|----------|--------|----------------------------------------|----------|----------|---------|---------|-----------------------------------------------------------------------------------|
| 4000     |    R   | **Value of Temperature Sensor S1**     | Float    | °C       | -64     | 192     | Current value of temperature sensor S1                                            |
| 4010     |    R   | **Value of Temperature Sensor S2**     | Float    | °C       | -64     | 192     | Current value of temperature sensor S2                                            |
| 4020     |    R   | **Value of Temperature Sensor S3**     | Float    | °C       | -64     | 192     | Current value of temperature sensor S3                                            |
| 4030     |    R   | **Value of Temperature Sensor S4**     | Float    | °C       | -64     | 192     | Current value of temperature sensor S4                                            |
| 4040     |    R   | **Value of Temperature Sensor S5**     | Float    | °C       | -64     | 192     | Current value of temperature sensor S5                                            |
| 4050     |    R   | **Value of Temperature Sensor S6**     | Float    | °C       | -64     | 192     | Current value of temperature sensor S6                                            |
| 2100     |    R   | **Ethernet IP Address**                | String16 |          |         |         | Ethernet IP Address                                                               |
| 2110     |    R   | **Ethernet MAC Address**               | String32 |          |         |         | Ethernet MAC Address                                                              |
| 21000    |   RW   | **Operation Mode**                     | UInt16   |          | 0       | 10      | Current operation mode: 0 = Automatic 1 = Comfort 2 = Saving 3 = Frost protection |
| 21001    |    R   | **Operation Status**                   | UInt16   |          | 0       | 10      | Current operation status: 0 = Comfort 1 = Saving 2 = Frost Protection             |
| 21200    |    R   | **Heat Flow Temperature Reference**    | Float    | °C       | 0       | 150     | Calculated heat flow reference                                                    |
| 21206    |    R   | **Heat Weather Compensated Reference** | Float    | °C       | -150    | 150     | Calculated value from the weather compensator                                     |
| 21210    |   RW   | **Heat Return Temperature Reference**  | Float    | °C       | 5       | 150     | Reference for Return Limiter                                                      |
| 21700    |    R   | **Heat Valve Position**                | Float    | %        | 0       | 1       | Scale 100 – Estimated position of motor                                           |

### Fully configurable
- Enable/disable each sensor individually  
- Auto reconnect Modbus if the USB adapter restarts  
- Friendly naming and unified device info in Home Assistant  

## 🚀 Installation

### Install via HACS

The easiest way to install this integration is through HACS.

Click the button below:

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nichlasrohde&repository=ha-ecl-modbus&category=integration)

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

## 📘 Official Danfoss Modbus Documentation

This integration is based on the official Modbus register list from Danfoss.

📄 **Download PDF:**  
👉 [ECL120 & ECL220 Modbus Specification (Rev 023)](./docs/IS2007%2C%20ECL120%20and%20ECL220%20Modbus%20Specification%2C%20rev%20023.pdf)

The document is shared with permission from Danfoss.


## 📄 License
MIT License
