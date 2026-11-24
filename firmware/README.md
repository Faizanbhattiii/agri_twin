# AgriTwin Pakistan — ESP32 Field Sensor Node (Hardware & Firmware Guide)

Low-cost IoT ground-truth field node built around the **ESP32 DevKit V1 (30-pin)** for real-time soil moisture, air temperature, relative humidity, and optional soil temperature monitoring.

---

## 1. Bill of Materials (BOM)

| Component | Specification | Purpose | Est. Cost (PKR) |
|---|---|---|---|
| **Microcontroller** | ESP32 DevKit V1 (30-pin) | Wi-Fi, ADC1, Deep Sleep | Rs. 1,200 – 1,500 |
| **Soil Moisture Sensor** | Capacitive Soil Moisture v1.2 | Non-corrosive volumetric moisture | Rs. 300 – 450 |
| **Air Temp & Humidity** | DHT22 (AM2302) | Micro-climate & rust pest risk | Rs. 600 – 800 |
| **Soil Temp Probe** *(Optional)* | DS18B20 Waterproof + 4.7kΩ resistor | Root-zone temperature | Rs. 350 – 500 |
| **Pull-up Resistors** | 10kΩ (DHT22) + 2× 100kΩ (Battery divider) | Signal stability & battery read | Rs. 20 |
| **Power Supply** | 18650 Li-Ion + TP4056 + 5V Solar Panel | Off-grid autonomous operation | Rs. 800 – 1,200 |
| **Enclosure** | IP65 Waterproof Junction Box | Field protection | Rs. 400 |

---

## 2. Pinout & Wiring Table

> **⚠️ Critical Note on ADC Pins:** Always connect analog sensors to **ADC1** (`GPIO32–GPIO39`) on the ESP32. **ADC2** pins conflict with the Wi-Fi radio and fail to read when Wi-Fi is active.

| Sensor / Module | Sensor Pin | ESP32 Pin | Notes |
|---|---|---|---|
| **Capacitive Soil v1.2** | VCC | `3V3` | Operates cleanly at 3.3V |
| | GND | `GND` | Common ground |
| | AOUT | `GPIO34` (ADC1_CH6) | Input-only analog pin |
| **DHT22** | VCC | `3V3` | |
| | DATA | `GPIO4` | Add `10kΩ` pull-up to `3V3` |
| | GND | `GND` | |
| **DS18B20** *(Optional)* | Red (VCC) | `3V3` | |
| | Yellow (DATA) | `GPIO16` | Add `4.7kΩ` pull-up to `3V3` |
| | Black (GND) | `GND` | |
| **Battery Monitor** *(Optional)* | VBAT+ | `GPIO35` (ADC1_CH7) | Via 100kΩ / 100kΩ 1:1 divider |

---

## 3. Two-Point Soil Sensor Calibration

Capacitive sensors vary slightly between units and soil types. Before deploying to the field:
1. Flash the firmware and open Serial Monitor at `115200` baud.
2. **Dry Point (`SOIL_DRY_ADC`):** Wipe the sensor completely dry and hold it in open air. Record the raw ADC value (typically `~3100–3350`).
3. **Wet Point (`SOIL_WET_ADC`):** Submerge the sensor up to the marked white line in a cup of water (do **not** submerge the top electronics). Record the raw ADC value (typically `~1350–1550`).
4. Update `SOIL_DRY_ADC` and `SOIL_WET_ADC` in `firmware/src/config.h`.

---

## 4. Field Waterproofing Tips
- Coat the exposed SMD components at the top of the Capacitive Soil Moisture v1.2 PCB with **conformal coating, clear nail polish, or marine-grade silicone sealant**, leaving the sensing blade uncoated.
- Route cables out of the **bottom** of the IP65 box using a drip loop so rainwater cannot run along the wire into the enclosure.
- Place the DHT22 inside a small perforated **radiation shield** (white PVC cap) shaded from direct sunlight; otherwise solar heating artificially inflates air temperature readings.

---

## 5. Flashing Instructions (PlatformIO)
1. Install **VS Code** and the **PlatformIO IDE** extension.
2. Open the `firmware/` folder in VS Code.
3. Copy `firmware/src/config.h.example` to `firmware/src/config.h` and enter your Wi-Fi SSID, password, and server IP.
4. Connect the ESP32 via USB and run **PlatformIO: Upload**.
