# ECL 120/220 Modbus for Home Assistant

A custom Home Assistant integration for reading data from **Danfoss ECL 120 and ECL 220 heating controllers** using **Modbus RTU or Modbus TCP**.

This integration is created by an enthusiast (not a professional developer) and is actively evolving.
It is tested on **ECL 120**, but **ECL 220 uses the same register map**, so it *should* work identically — feedback is welcome!

---

## 🔧 Features
Current supported features:

The list of supported registers is continuously expanding.

The authoritative source for supported registers is:
- `custom_components/ecl_modbus/registers.py`

Each register definition includes:
- Modbus address
- Read / Write support
- Data type
- Unit
- Scaling
- Min / Max / Step (where applicable)                                   |

### Fully configurable
- Enable/disable each sensor individually  
- Supports **USB (Modbus RTU)** and **IP (Modbus TCP)**  
- Automatic reconnect if connection is lost  
- Friendly naming and unified device info in Home Assistant  

---

## 🚀 Installation

### Install via HACS

The easiest way to install this integration is through HACS.

Click the button below:

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nichlasrohde&repository=ha-ecl-modbus&category=integration)

---

### Manual installation
1. Download the latest release ZIP  
2. Extract it into: /config/custom_components/ecl_modbus/
3. Restart Home Assistant  
4. Add integration via:  
**Settings → Devices & Services → Add Integration → ECL Modbus**

---

## ⚙️ Configuration

During setup you choose **how the controller is connected**:

### 🔌 Connection type

#### Serial (USB / Modbus RTU)
- Direct USB-to-RS485 adapter
- Typical port: `/dev/ttyUSB0` or `/dev/serial/by-id/...`
- Baudrate: **38400**
- Parity: **Even**
- Stop bits: **1**
- Slave ID: **5** (default)

#### 🌐 TCP (Modbus TCP via gateway)
- Uses a Modbus TCP ⇄ Modbus RTU gateway
- Typical port: **502**
- Unit ID = ECL Modbus slave address (default: **5**)

---

### Options
- Enable/disable individual registers
- Configure global polling interval

No YAML required.

---

## 🧩 How it works
- Uses `pymodbus` for Modbus communication
- Supports both **Modbus RTU** and **Modbus TCP**
- One shared coordinator polls enabled registers
- Automatic reconnect on communication errors
- Groups all sensors under a single device in Home Assistant

---

## 🧪 Compatibility
| Controller | Status |
|------------|--------|
| **ECL 120** | ✔ Tested |
| **ECL 220** | ⚠ Untested, but register-compatible |

---

## 🧰 Tested hardware

This integration has been built and tested with the following hardware setups:

### USB → RS485 (Modbus RTU)
- **Industrial USB to RS485 Bidirectional Converter**  
  Vendor: raspberrypi.dk  
  Link: https://raspberrypi.dk/en/product/industrial-usb-to-rs485-bidirectional-converter/

Used for direct Modbus RTU communication via USB (e.g. `/dev/ttyUSB0` or `/dev/serial/by-id/...`).

---

### Ethernet / WiFi → RS485 (Modbus TCP via gateway)
- **WaveShare Industrial Grade Serial Server RS232/485 to WiFi/Ethernet**  
  Vendor: raspberrypi.dk  
  Link: https://raspberrypi.dk/en/product/waveshare-industrial-grade-serial-server-rs232-485-to-wifi-ethernet/

Used as a **Modbus TCP ⇄ Modbus RTU gateway**.  
Configured in *Modbus TCP ↔ Modbus RTU* mode and connected to the ECL controller via RS485.

> When using a gateway, ensure that the RS485 parameters (baudrate, parity, stop bits) match the ECL controller configuration.

---

## 🛠️ Planned Features
This integration is actively evolving. Planned and possible future improvements include:
- Additional ECL registers and writable parameters
- Improved multi-controller support
- More advanced connection diagnostics

Suggestions, missing registers, and pull requests are very welcome!

---

## ❤️ Contributions
This project is community-driven — PRs, testing, and feedback are highly appreciated.

GitHub:  
👉 https://github.com/nichlasrohde/ha-ecl-modbus

---

## 📘 Official Danfoss Modbus Documentation

This integration is based on the official Modbus register list from Danfoss.

📄 **Download PDF:**  
👉 [ECL120 & ECL220 Modbus Specification (Rev 023)](./docs/IS2007%2C%20ECL120%20and%20ECL220%20Modbus%20Specification%2C%20rev%20023.pdf)

The document is shared with permission from Danfoss.

---

## 📄 License
MIT License

## ⚠️ Disclaimer

This integration is provided **as-is**, without any guarantees or warranties of any kind.

- The author is **not affiliated with Danfoss**.
- The author is **not a professional developer**.
- This integration may contain bugs, incorrect register mappings, or incomplete implementations.
- Writing values to the controller **may affect system behavior** and could potentially cause malfunction or damage if used incorrectly.

**You are fully responsible for:**
- Verifying register addresses and values
- Testing changes in a safe environment
- Ensuring that critical heating functions remain safe and operational

The author takes **no responsibility or liability** for:
- Damaged equipment
- Incorrect heating behavior
- Increased energy consumption
- Loss of comfort or system downtime

If you are unsure about a parameter or register — **do not write to it**.

Use this integration **at your own risk**.