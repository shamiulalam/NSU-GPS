from machine import Pin, I2C, UART
import network
import time
import _thread
from blynklib import Blynk
import configs
from ssd1306 import SSD1306_I2C

utc_offset = 6

i2c0 = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
dsp2 = SSD1306_I2C(128, 64, i2c0)
i2c1 = I2C(1, sda=Pin(10), scl=Pin(11), freq=400000)
dsp1 = SSD1306_I2C(128, 64, i2c1)

def connect_to_internet(ssid, password, timeout=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            print("WiFi failed. Running offline mode.")
            return False
        print("Connecting to WiFi...")
        time.sleep(.1)

    print("WiFi connected:", wlan.ifconfig())
    time.sleep(.1)
    return True

time.sleep(1)
wifi_ok = False

while not wifi_ok:
    # Show connecting message
    dsp1.fill(0)
    dsp2.fill(0)
    dsp1.text("CONNECTING WIFI...", 10, 28)
    dsp2.text("CONNECTING WIFI...", 10, 28)
    dsp1.show()
    dsp2.show()

    # Attempt to connect
    wifi_ok = connect_to_internet(configs.WIFI_NAME, configs.WIFI_PASS)

    if not wifi_ok:
        # Wait a bit before retrying
        time.sleep(1)

# WiFi is now connected
dsp1.fill(0)
dsp2.fill(0)
dsp1.text("WI-FI CONNECTED...", 10, 28)
dsp2.text("WI-FI CONNECTED...", 10, 28)
dsp1.show()
dsp2.show()
time.sleep(1)

BLYNK = Blynk(
    configs.BLYNK_AUTH_TOKEN,
    server=configs.BLYNK_SERVER,
    port=80,
    insecure=True
)
print("Blynk started")

    
# GPS setup
dataLock = _thread.allocate_lock()
keepRunning = True
GPS = UART(0, baudrate=9600, tx=Pin(16), rx=Pin(17))
# Reset GPS
GPS.write(b'$PMTK314,-1*04\r\n')
GPS.write(b"$PMTK314,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0*28\r\n")

NMEAdata = {
    'GPGGA': "",
    'GPGSA': "",
    'GPRMC': "",
    'GPVTG': ""
}
GPSdata = {
    'latDD'  : 0,
    'lonDD'  : 0,
    'heading': 0.0,
    'fix'    : False,
    'sats'   : 0,
    'knots'  : 0,
    'time'   : '00:00:00',
    'date'   : '00/00/0000',
    'alt'    : 0.0
}

def gpsThread(uart):
    global GPS, keepRunning, NMEAdata
    print("GPS Thread Running")
    GPGGA = ""
    GPGSA = ""
    GPRMC = ""
    GPVTG = ""
    
    while not uart.any():
        pass
    while uart.any():
        junk = uart.read()
        print(junk)
    print("\nPress the green button to know your location\n")
    myNMEA = ""
    while keepRunning:
        if uart.any():
            myChar = uart.read(1).decode('utf-8')
            myNMEA += myChar
            if myChar == '\n':
                myNMEA = myNMEA.strip()
                if myNMEA[1:6] == "GPGGA":
                    GPGGA = myNMEA
                if myNMEA[1:6] == "GPGSA":
                    GPGSA = myNMEA
                if myNMEA[1:6] == "GPRMC":
                    GPRMC = myNMEA
                if myNMEA[1:6] == "GPVTG":
                    GPVTG = myNMEA
                if GPGGA and GPGSA and GPRMC and GPVTG:
                    dataLock.acquire()
                    NMEAdata = {'GPGGA': GPGGA, 'GPGSA': GPGSA, 'GPRMC': GPRMC, 'GPVTG': GPVTG}
                    dataLock.release()
                myNMEA = ""
        else:
            time.sleep(0.01)
    print("\nGPS Thread Stopped")

def parseGPS():
    global utc_offset
    try:
        fixField = NMEAmain['GPGGA'].split(',')[6]
        if not fixField.isdigit(): 
            GPSdata['fix'] = False
            return
        readFix = int(fixField)
        if readFix == 0:
            GPSdata['fix'] = False
            return

        GPSdata['fix'] = True

        latRAW = NMEAmain['GPGGA'].split(',')[2]
        latDD = int(latRAW[0:2]) + float(latRAW[2:])/60
        if NMEAmain['GPGGA'].split(',')[3] == 'S':
            latDD = -latDD
        GPSdata['latDD'] = latDD

        lonRAW = NMEAmain['GPGGA'].split(',')[4]
        lonDD = int(lonRAW[0:3]) + float(lonRAW[3:])/60
        if NMEAmain['GPGGA'].split(',')[5] == 'W':
            lonDD = -lonDD
        GPSdata['lonDD'] = lonDD

        utc_offset = max(-12, min(14, round(lonDD / 15)))

        headingField = NMEAmain['GPRMC'].split(',')[8]
        GPSdata['heading'] = float(headingField) if headingField else 0.0

        knotsField = NMEAmain['GPRMC'].split(',')[7]
        GPSdata['speed'] = float(knotsField) * 1.15078 if knotsField else 0.0

        sats = int(NMEAmain['GPGGA'].split(',')[7])
        GPSdata['sats'] = sats

        # UTC Time and Date
        utcTime = NMEAmain['GPGGA'].split(',')[1]
        utcDate = NMEAmain['GPRMC'].split(',')[9]

        myYear = '20' + utcDate[4:]
        myMonth = utcDate[2:4]
        myDay = utcDate[0:2]
        myHours = str(int(utcTime[0:2]) + utc_offset)
        myMin = utcTime[2:4]
        mySec = utcTime[4:6]

        maxDays = ['31','28','31','30','31','30','31','31','30','31','30','31']
        if int(myYear) % 4 == 0:
            maxDays[1] = '29'

        # Handle hours overflow
        if int(myHours) >= 24:
            myHours = str(int(myHours) - 24)
            if len(myHours) < 2: myHours = '0'+myHours
            myDay = str(int(myDay)+1)
            if int(myDay) > int(maxDays[int(myMonth)-1]):
                myDay = '01'
                myMonth = str(int(myMonth)+1)
                if int(myMonth) > 12:
                    myMonth = '01'
                    myYear = str(int(myYear)+1)
            if len(myDay) < 2: myDay = '0'+myDay
            if len(myMonth) < 2: myMonth = '0'+myMonth

        # Handle negative hours
        if int(myHours) < 0:
            myHours = str(int(myHours)+24)
            if len(myHours) < 2: myHours = '0'+myHours
            myDay = str(int(myDay)-1)
            if int(myDay) < 1:
                myMonth = str(int(myMonth)-1)
                if int(myMonth) < 1:
                    myMonth = '12'
                    myYear = str(int(myYear)-1)
                myDay = maxDays[int(myMonth)-1]
            if len(myDay) < 2: myDay = '0'+myDay
            if len(myMonth) < 2: myMonth = '0'+myMonth

        GPSdata['time'] = myHours + ':' + myMin + ':' + mySec
        GPSdata['date'] = myMonth + '/' + myDay + '/' + myYear
        GPSdata['alt'] = float(NMEAmain['GPGGA'].split(',')[9])

    except Exception as e:
        GPSdata['fix'] = False

def dispOLED1():
    dsp1.fill(0)
    if not GPSdata['fix']:
        text = "Acquiring Fix..."
        x = (128 - len(text)*8)//2
        y = (64-8)//2
        dsp1.text(text, x, y)
    else:
        text2 = "NSU GPS"
        x2 = (128 - len(text2)*8)//2
        dsp1.text(text2, x2, 0)
        if screenOne:
            dsp1.text(GPSdata['time'] + ' ' + GPSdata['date'][0:5],0,16)
            dsp1.text("LAT: "+str(GPSdata['latDD']),0,26)
            dsp1.text("LON: "+str(GPSdata['lonDD']),0,36)
            dsp1.text("SAT: "+str(GPSdata['sats']),0,46)
        else:
            dsp1.text(GPSdata['time'] + ' ' + GPSdata['date'][0:5],0,16)
            dsp1.text(f"SPD: {GPSdata['speed']:.3f} Mph", 0, 26)
            dsp1.text("HDG: "+str(GPSdata['heading'])+' deg',0,36)
            dsp1.text("ALT: "+str(GPSdata['alt'])+' M',0,46)
    dsp1.show()

def dispOLED2():
    dsp2.fill(0)
    if not GPSdata['fix']:
        text = "Acquiring Fix..."
        x = (128 - len(text)*8)//2
        y = (64-8)//2
        dsp2.text(text, x, y)
    else:
        text2 = "NSU GPS"
        x2 = (128 - len(text2)*8)//2
        dsp2.text(text2, x2, 0)
        dsp2.text(GPSdata['time'] + ' ' + GPSdata['date'][0:5],0,16)
        dsp2.text(f"SPD: {GPSdata['speed']:.3f} Mph", 0, 26)
        dsp2.text("HDG: "+str(GPSdata['heading'])+' deg',0,36)
        dsp2.text("ALT: "+str(GPSdata['alt'])+' M',0,46)
    dsp2.show()

butOnePin = 12
butOne = Pin(butOnePin, Pin.IN, Pin.PULL_UP)
butOneOld = 1
screenOne = True

def butOneIRQ(pin):
    global butOneOld, screenOne
    val = butOne.value()
    if butOneOld == 1 and val == 0:
        screenOne = not screenOne
        print("Screen toggled")
    butOneOld = val

butOne.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=butOneIRQ)

powerButPin = 8
powerButton = Pin(powerButPin, Pin.IN, Pin.PULL_UP)
powerButOld = 1
oledOn = False
lastPressTime = 0 
welcomeMsg = False
welcomeDone = False
welcomeActive = False
  
def typewriter_welcome():
    global welcomeDone, welcomeActive
    
    welcomeActive = True # disable power button
    text="WELCOME TO NSU GPS"
    visible=""
    start=time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(),start)<5000:
        if len(visible)<len(text):
            visible+=text[len(visible)]
            print(visible)

        text_px=len(visible)*8
        x=64-text_px//2 if text_px<=128 else 128-text_px

        dsp1.fill(0)
        dsp2.fill(0)
        dsp1.text(visible,x,28)
        dsp2.text(visible,x,28)
        dsp1.show()
        dsp2.show()

        time.sleep(0.2)

    welcomeDone=True
    welcomeActive = False  # enable power button again

def powerButIRQ(pin):
    global oledOn, powerButOld, lastPressTime, welcomeMsg
    val = powerButton.value()
    
    if welcomeActive:
        powerButOld = val
        return   # completely ignore button during welcome
    
    currentTime = time.ticks_ms()
    if powerButOld == 1 and val == 0 and time.ticks_diff(currentTime, lastPressTime) > 200:
        lastPressTime = currentTime
        toggle_oled_power()
        if oledOn:
            print("OLED is turned ON.")
            welcomeMsg=True
        else:
            print("OLED is turned OFF.")
    powerButOld = val

powerButton.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=powerButIRQ)

def toggle_oled_power():
    global oledOn
    oledOn = not oledOn

    if oledOn:
        print("OLED IS ON")
        global welcomeMsg
        welcomeMsg = True
        if BLYNK:
            BLYNK.virtual_write(6, 1)
    else:
        print("OLED IS OFF")
        dsp1.fill(0); dsp1.show()
        dsp2.fill(0); dsp2.show()
        if BLYNK:
            BLYNK.virtual_write(6, 0)
            
if BLYNK:
    @BLYNK.on("V6")
    def blynk_power(value):
        if welcomeActive:
            return
        state = int(value[0])
        if state == 1 and not oledOn:
            toggle_oled_power()
        elif state == 0 and oledOn:
            toggle_oled_power()

_thread.start_new_thread(gpsThread, (GPS,))
while True:
    dataLock.acquire()
    gps_ready = NMEAdata['GPGGA'] != ""
    dataLock.release()
    if gps_ready:
        break
    time.sleep(0.1)

try:
    while True:
        if BLYNK:
            BLYNK.run()
        if not oledOn:
            # Clear OLEDs while waiting
            dsp1.fill(0)
            dsp1.show()
            dsp2.fill(0)
            dsp2.show()
            time.sleep(0.1)
            continue  # skip all GPS parsing and printing
        
        if welcomeMsg and not welcomeDone:
            typewriter_welcome()
            welcomeMsg = False
            continue
    
        dataLock.acquire()
        NMEAmain = NMEAdata.copy()
        dataLock.release()

        parseGPS()

        if not GPSdata['fix']:
            if BLYNK:
                print("Acquiring Fix. . .")
                BLYNK.virtual_write(0, 0)
                BLYNK.virtual_write(1, 0)
                BLYNK.virtual_write(2, 0)
                BLYNK.virtual_write(3, 0)
                BLYNK.virtual_write(4, 0)
                BLYNK.virtual_write(5, 0)
        else:
            if BLYNK:
                print("NSU GPS Tracker Navigation:")
                print(GPSdata['time'], GPSdata['date'])
                print("Lat and Lon:", GPSdata['latDD'], GPSdata['lonDD'])
                print("Speed:", f"{GPSdata['speed']:.3f}")
                print("Heading:", GPSdata['heading'])
                print("Altitude:", GPSdata['alt'])
                print("Sats:", GPSdata['sats'])
                print()
            
                BLYNK.virtual_write(0, GPSdata['latDD'])
                BLYNK.virtual_write(1, GPSdata['lonDD'])
                BLYNK.virtual_write(2, f"{GPSdata['speed']:.3f} Mph")
                BLYNK.virtual_write(3, GPSdata['sats'])
                BLYNK.virtual_write(4, f"{GPSdata['heading']} Deg")
                BLYNK.virtual_write(5, f"{GPSdata['alt']} M")
            
        dispOLED1()
        dispOLED2()
        time.sleep(.1)

except KeyboardInterrupt:
    keepRunning = False
    time.sleep(1)
    GPS.deinit()
    dsp1.fill(0)
    dsp1.show()
    dsp2.fill(0)
    dsp2.show()
    print("Program Stopped Cleanly")
