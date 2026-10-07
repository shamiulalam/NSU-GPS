# Portable IoT GPS Tracking System

A MicroPython GPS tracker built around a Raspberry Pi Pico W. It reads location and navigation data from a GPS receiver, presents the data locally on OLED displays, and connects to a Blynk dashboard over Wi-Fi for remote monitoring.

The project specifies a GY-GPS6MV2 GPS module using a NEO-6M chip, an SSD1306 OLED, and the Pico W. The source code implements the two display and remote dashboard paths.

## Project goals

- Read GPS NMEA data over UART and parse position and navigation fields.
- Convert coordinates to decimal degrees and show live information locally.
- Connect the Pico W to Wi-Fi and make GPS readings available through a cloud dashboard.
- Let the user control the local display with physical buttons to reduce display power when it is not needed.
- Provide a portable, low-cost GPS tracking platform for asset monitoring and embedded-systems learning.

## System overview

```text
GY-GPS6MV2 GPS (NEO-6M)
        | UART / NMEA
        v
Raspberry Pi Pico W running MicroPython
        |                         |
        | I2C                     | Wi-Fi
        v                         v
Two SSD1306 OLEDs             Blynk Cloud dashboard
```

The firmware reads `GPGGA`, `GPGSA`, `GPRMC`, and `GPVTG` NMEA sentences. It derives latitude, longitude, fix status, satellite count, speed, heading, altitude, and time/date. The main application sends latitude and longitude as decimal degrees, converts speed from knots to miles per hour, and estimates a time-zone offset from longitude.

## Hardware 

| Component | Connection in `main.py` | Purpose |
| --- | --- | --- |
| Raspberry Pi Pico W (RP2040) | Wi-Fi-capable MicroPython board | Reads GPS data, updates displays, and connects to Blynk. |
| GY-GPS6MV2 with NEO-6M | UART0, 9600 baud; Pico TX GP16, RX GP17 | Sends NMEA data to the Pico. Connect TX to RX, RX to TX, and share GND. |
| SSD1306 OLED 1 | I2C1, SDA GP10, SCL GP11; 128x64 | Shows location or navigation details. |
| SSD1306 OLED 2 | I2C0, SDA GP0, SCL GP1; 128x64 | Shows navigation details. |
| Page button | GP12, input with internal pull-up | Toggles the first OLED between its two pages; connect the button between GP12 and GND. |
| OLED power button | GP8, input with internal pull-up | Turns both OLEDs on or off; connect the button between GP8 and GND. |
| Power Source | - | Need a constant 3V/5V power source to turn on Raspberry Pi Pico W. |

Use SSD1306 displays supported by the driver and confirm their I2C addresses and wiring for your use.

## Circuit Diagrams

`Will be added later. Stay tuned.`

## Project structure

```text
.
|-- main.py       # GPS parsing, OLED UI, buttons, Wi-Fi, and Blynk application
|-- blynklib.py   # Local MicroPython Blynk client
|-- configs.py    # Wi-Fi and Blynk configuration; contains credentials
`-- README.md     # Project documentation
```

## Blynk cloud setup

Import `blynklib.py` and writes values to Blynk virtual pins using the Blynk protocol over TCP (port 80, with `insecure=True`). The configured Blynk dashboard is the cloud interface used by this code. You can setup Blynk interface just by watching a tutorial video on youtube.

Configure these Blynk virtual pins to match the code:

| Virtual pin | Data |
| --- | --- |
| V0 | Latitude in decimal degrees |
| V1 | Longitude in decimal degrees |
| V2 | Speed in miles per hour (text) |
| V3 | Satellite count |
| V4 | Heading in degrees (text) |
| V5 | Altitude in meters (text) |
| V6 | OLED power state (`1` on, `0` off); accepts a dashboard value to control display power |

The displays show an acquiring-fix message until the GPS reports a valid fix. After a fix, the first OLED can show time/date, latitude, longitude, and satellite count, or speed, heading, and altitude. The second OLED shows time/date and navigation details. GP8 controls both displays; GP12 changes the first display's page.

When there is no GPS fix, the current code writes zero values to V0-V5. `NO_FIX` status is shown on the cloud.

## Software and setup

Requirements:

- MicroPython firmware for Raspberry Pi Pico W.
- The firmware modules used by the code: `machine`, `network`, `time`, and `_thread`, plus socket support.
- A compatible `ssd1306.py` MicroPython I2C display driver.
- A Blynk Cloud project with the virtual datastreams above.
- A GPS sensor configured for 9600 baud and outputting the NMEA sentence types consumed by the code.

To run it:

1. Wire the Pico W, GPS module, OLED displays, and buttons using the pin table. Check the GPS module's voltage requirements before connecting it.
2. Set your Wi-Fi and Blynk settings in `configs.py` (see the variable names below).
3. Copy `main.py`, `blynklib.py`, `configs.py`, and a compatible `ssd1306.py` onto the Pico W filesystem.
4. Configure Blynk datastreams V0-V6 and run `main.py` from the REPL or save it as the device's boot `main.py`.
5. Give the GPS receiver a clear view of the sky while it acquires a fix. Press GP8 to enable the OLEDs and GP12 to switch the first OLED's page.

`configs.py` must define:

```python
WIFI_NAME = "your-wifi-name"
WIFI_PASS = "your-wifi-password"
BLYNK_AUTH_TOKEN = "your-device-auth-token"
BLYNK_SERVER = "blynk.cloud"
```

## Advantages

- **Portable and compact:** The Raspberry Pi Pico W, GPS module, and small OLED displays form a compact tracker that can be carried with an asset or used in field demonstrations.
- **Local and remote monitoring:** GPS details are shown on the OLED displays and are also sent to a Blynk dashboard over Wi-Fi, so readings can be checked at the device or remotely when network access is available.
- **Useful live navigation data:** The firmware parses GPS NMEA messages and derives latitude, longitude, fix status, satellite count, speed, heading, altitude, and time/date.
- **Readable information at the device:** The OLED interface provides a direct status and navigation view without requiring a phone or computer beside the tracker.
- **Simple physical controls:** Buttons control the OLED power state and switch the first display's page, making common interactions available on the device.
- **Low-cost and adaptable platform:** Pico W and common GPS/OLED modules provide a practical base for learning and prototyping location-aware IoT devices.

## Limitations

- GPS fails to acquire a fix indoors/long TTFF: Conduct testing in open environments; implement code logic to display a clear "Acquiring Fix..." message locally and publish a "NO_FIX" status to the cloud
- The time-zone is set to UTC+6. It is not globally optimum. No dynamic time zone is set. For specific country, just change the utc offset. 
- Wi-Fi/MQTT Connection Instability: Implement an aggressive reconnection logic in MicroPython for both Wi-Fi and MQTT; use the deep sleep cycle to force a clean, periodic restart of the network stack.

## Project gains

- **Embedded systems experience:** The project brings together MicroPython, GPIO, UART, I2C, threading, and Wi-Fi in one application.
- **GPS data-processing experience:** It demonstrates reading NMEA sentences, checking for a location fix, converting coordinates to decimal degrees, and preparing navigation values for display and transmission.
- **IoT dashboard integration:** It connects device readings to Blynk virtual pins, giving the project a remote visualization path as well as a local display.
- **End-to-end system integration:** The implementation combines a sensor, microcontroller, user controls, displays, network connectivity, and a cloud service.
- **A foundation for asset-tracking prototypes:** The design can be adapted for demonstrations or experiments involving location-aware equipment, packages, or vehicles, subject to GPS coverage and Wi-Fi availability.
- **A clear path for future development:** Solving the limitations would make this a robust and simple GPS tracker ready for production at a cheap cost.
