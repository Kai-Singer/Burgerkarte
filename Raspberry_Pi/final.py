from datetime import datetime, timedelta
from time import sleep
from rich import print
from threading import Thread
from RPLCD.gpio import CharLCD
from pad4pi import rpi_gpio
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO
import json, sys, requests

lcd = CharLCD(
    cols = 16,
    rows = 2,
    pin_rs = 26,
    pin_e = 19,
    pins_data = [13, 6, 5, 12],
    numbering_mode = GPIO.BCM
)

char_ae = [
    0b01010,
    0b00000,
    0b01110,
    0b00001,
    0b01111,
    0b10001,
    0b01111,
    0b00000
]

char_AE = [
    0b01010,
    0b00000,
    0b01110,
    0b10001,
    0b11111,
    0b10001,
    0b10001,
    0b00000
]

char_oe = [
    0b01010,
    0b00000,
    0b01110,
    0b10001,
    0b10001,
    0b10001,
    0b01110,
    0b00000
]

char_OE = [
    0b01010,
    0b00000,
    0b01110,
    0b10001,
    0b10001,
    0b10001,
    0b01110,
    0b00000
]

char_ue = [
    0b01010,
    0b00000,
    0b10001,
    0b10001,
    0b10001,
    0b10011,
    0b01101,
    0b00000
]

char_UE = [
    0b01010,
    0b00000,
    0b10001,
    0b10001,
    0b10001,
    0b10001,
    0b01110,
    0b00000
]

char_ss = [
    0b01110,
    0b10001,
    0b10001,
    0b10110,
    0b10001,
    0b10001,
    0b10110,
    0b00000
]

char_euro = [
    0b00111,
    0b01000,
    0b11111,
    0b01000,
    0b11111,
    0b01000,
    0b00111,
    0b00000
]

lcd.create_char(0, char_ae)
lcd.create_char(1, char_AE)
lcd.create_char(2, char_oe)
lcd.create_char(3, char_OE)
lcd.create_char(4, char_ue)
lcd.create_char(5, char_UE)
lcd.create_char(6, char_ss)
lcd.create_char(7, char_euro)

RATHAUS_MOTOR_PIN = 21
OEPNV_LED_PIN = 20
SWITCH_MENU_PIN = 1

RGB_RED_PIN = 2
RGB_GREEN_PIN = 3
RGB_BLUE_PIN = 4

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RATHAUS_MOTOR_PIN, GPIO.OUT)
GPIO.setup(OEPNV_LED_PIN, GPIO.OUT)
GPIO.setup(SWITCH_MENU_PIN, GPIO.IN, pull_up_down = GPIO.PUD_UP)

GPIO.setup(RGB_RED_PIN, GPIO.OUT)
GPIO.setup(RGB_GREEN_PIN, GPIO.OUT)
GPIO.setup(RGB_BLUE_PIN, GPIO.OUT)

rgbRedPwm = GPIO.PWM(RGB_RED_PIN, 100)
rgbGreenPwm = GPIO.PWM(RGB_GREEN_PIN, 100)
rgbBluePwm = GPIO.PWM(RGB_BLUE_PIN, 100)
rathausMotorPwm = GPIO.PWM(RATHAUS_MOTOR_PIN, 50)

rgbRedPwm.start(0)
rgbGreenPwm.start(0)
rgbBluePwm.start(0)
rathausMotorPwm.start(0)

KEYPAD_MATRIX = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]

KEYBOARD_ROW_PINS = [14, 16, 18, 23]
KEYBOARD_COL_PINS = [24, 17, 27, 22]

factory = rpi_gpio.KeypadFactory()
keypad = factory.create_keypad(
    keypad = KEYPAD_MATRIX,
    row_pins = KEYBOARD_ROW_PINS,
    col_pins = KEYBOARD_COL_PINS
)

reader = SimpleMFRC522()

def rgbSetColor(r, g, b):
    rgbRedPwm.ChangeDutyCycle(r)
    rgbGreenPwm.ChangeDutyCycle(g)
    rgbBluePwm.ChangeDutyCycle(b)

def setServoAngle(angle, pwm, pin):
    duty = 2 + (angle / 18)
    GPIO.output(pin, True)
    pwm.ChangeDutyCycle(duty)
    sleep(0.5)
    GPIO.output(pin, False)
    pwm.ChangeDutyCycle(0)

def startAction(name):
    if name == 'rathaus':
        print('Aktion "rathaus" ausgeführt')
        setServoAngle(90, rathausMotorPwm, RATHAUS_MOTOR_PIN)
        sleep(0.5)
        setServoAngle(180, rathausMotorPwm, RATHAUS_MOTOR_PIN)
        sleep(3)
        setServoAngle(90, rathausMotorPwm, RATHAUS_MOTOR_PIN)
    elif name == 'oepnv':
        GPIO.output(OEPNV_LED_PIN, GPIO.HIGH)
        print('Aktion "oepnv" ausgeführt')
        sleep(2)
        GPIO.output(OEPNV_LED_PIN, GPIO.LOW)

apiAdress = 'http://[2001:7c0:2320:2:f816:3eff:feb6:6731]:8000/api'

def getData(id):
    try:
        response = requests.get(f"{apiAdress}/user/get/{id[1:]}/")
    except Exception as e:
        print('[red]Verbindung mit dem Server ist fehlgeschlagen[/red]')
        print(f'[yellow]Fehlernachricht:[/yellow]\n{e}')
        return False
    if response.status_code == 200:
        print(f'[green]Der User mit der ID {id} wurde in der Datenbank gefunden[/green]')
        return response.json()
    else:
        print(f'[red]Der User mit der ID {id} konnte in der Datenbank nicht gefunden werden[/red]')
        print(f'[yellow]Fehlercode: {response.status_code}[/yellow]')
        try: print(f'[yellow]Servernachricht:[/yellow]\n{response.json()}')
        except Exception: pass
        return False

def changeData(id, dataName, newData):
    userData = getData(id)
    if userData:
        if dataName in userData:
            userData[dataName] = newData
            try:
                response = requests.post(f'{apiAdress}/user/edit/{id[1:]}/', json = userData)
            except Exception as e:
                print('[red]Verbindung mit dem Server ist fehlgeschlagen[/red]')
                print(f'[yellow]Fehlernachricht:[/yellow]\n{e}')
                return False
            if response.status_code == 200:
                print(f'[green]Die Variable {dataName} wurde erfolgreich im Datenset des Users mit der ID {id} geändert[/green]')
                try: print(f'[yellow]Servernachricht:[/yellow]\n{response.json()}')
                except Exception: pass
                return True
            else:
                print(f'[red]Ein unbekannter Fehler ist aufgetreten[/red]')
                print(f'[yellow]Fehlercode: {response.status_code}[/yellow]')
                try: print(f'[yellow]Servernachricht:[/yellow]\n{response.json()}')
                except Exception: pass
                return False
        else:
            print(f'[red]Die Variable {dataName} konnte nicht im Datenset des Users mit der ID {id} gefunden werden[/red]')
            return False
    else:
        print(f'[red]Der User mit der ID {id} konnte in der Datenbank nicht gefunden werden[/red]')
        return False
    
def bookAction(isbn, action, usr = None):
    if action == 'check':
        try:
            response = requests.get(f"{apiAdress}/book/get/{isbn}/")
        except Exception as e:
            print('[red]Verbindung mit dem Server ist fehlgeschlagen[/red]')
            print(f'[yellow]Fehlernachricht:[/yellow]\n{e}')
            return False
        if response.status_code == 200:
            print(f'[green]Das Buch mit der ISBN {isbn} wurde in der Datenbank gefunden[/green]')
            return response.json()
        else:
            print(f'[red]Das Buch mit der ISBN {isbn} konnte in der Datenbank nicht gefunden werden[/red]')
            print(f'[yellow]Fehlercode: {response.status_code}[/yellow]')
            try: print(f'[yellow]Servernachricht:[/yellow]\n{response.json()}')
            except Exception: pass
            return False
    elif action == 'borrow' and usr is not None:
        try:
            response = requests.post(f"{apiAdress}/book/borrow/{isbn}/", json = {'user': usr[1:]})
        except Exception as e:
            print('[red]Verbindung mit dem Server ist fehlgeschlagen[/red]')
            print(f'[yellow]Fehlernachricht:[/yellow]\n{e}')
            return False
        if response.status_code == 200:
            print(f'[green]Das Buch mit der ISBN {isbn} wurde erfolgreich ausgeliehen[/green]')
            try: print(f'[yellow]Servernachricht:[/yellow]\n{response.json()}')
            except Exception: pass
            return True
        else:
            print(f'[red]Ein unbekannter Fehler ist aufgetreten[/red]')
            print(f'[yellow]Fehlercode: {response.status_code}[/yellow]')
            try: print(f'[yellow]Servernachricht:[/yellow]\n{response.json()}')
            except Exception: pass
            return False
    elif action == 'return' and usr is not None:
        try:
            response = requests.post(f"{apiAdress}/book/return/{isbn}/", json = {'user': usr[1:]})
        except Exception as e:
            print('[red]Verbindung mit dem Server ist fehlgeschlagen[/red]')
            print(f'[yellow]Fehlernachricht:[/yellow]\n{e}')
            return 'failed'
        if response.status_code == 200:
            print(f'[green]Das Buch mit der ISBN {isbn} wurde zurückgegeben[/green]')
            try: print(f'[yellow]Servernachricht:[/yellow]\n{response.json()}')
            except Exception: pass
            return 'success'
        elif response.status_code == 400 and 'fee_problem' in response.json():
            print(f'[red]Das Buch kann nicht zurückgegeben werden, da noch Gebühren offen sind[/red]')
            try: print(f'[yellow]Servernachricht:[/yellow]\n{response.json()}')
            except Exception: pass
            return 'fee_problem'
        else:
            print(f'[red]Ein unbekannter Fehler ist aufgetreten[/red]')
            print(f'[yellow]Fehlercode: {response.status_code}[/yellow]')
            try: print(f'[yellow]Servernachricht:[/yellow]\n{response.json()}')
            except Exception: pass
            return 'failed'
    else:
        print(f'[red]Unbekannte Book-Aktion "{action}" oder Nutzer nicht übergeben[/red]')
        return False
    
def formatString(string):
    replacementChars = {
        'ä': '\x00',
        'Ä': '\x01',
        'ö': '\x02',
        'Ö': '\x03',
        'ü': '\x04',
        'Ü': '\x05',
        'ß': '\x06',
        '€': '\x07'
    }
    if len(string) > 16:
        string = f'{string[:13]}...'
    newString = ''
    for char in string:
        if char in replacementChars:
            newString += replacementChars[char]
        else:
            newString += char
    return newString

currentPage = ''
inputAction = ''
currentUser = ''
switchPossible = False
rfidPossible = False
inputPossible = False

def rathausMenu():
    global currentPage, switchPossible, rfidPossible, inputPossible, currentUser
    currentUser = ''
    currentPage = 'rathaus'
    switchPossible = False
    rfidPossible = False
    inputPossible = False
    lcd.clear()
    rgbSetColor(100, 0, 0)
    lcd.write_string(formatString('Willkommen'))
    lcd.cursor_pos = (1, 0)
    lcd.write_string(formatString('im Rathaus'))
    sleep(3)
    lcd.clear()
    lcd.write_string(formatString('Bitte Karte'))
    lcd.cursor_pos = (1, 0)
    lcd.write_string(formatString('anlegen'))
    switchPossible = True
    rfidPossible = True

def buechereiMenu():
    global currentPage, switchPossible, rfidPossible, inputPossible, currentUser
    currentUser = ''
    currentPage = 'buecherei'
    switchPossible = False
    rfidPossible = False
    inputPossible = False
    lcd.clear()
    rgbSetColor(0, 100, 0)
    lcd.write_string(formatString('Willkommen'))
    lcd.cursor_pos = (1, 0)
    lcd.write_string(formatString('in der Bücherei'))
    sleep(3)
    lcd.clear()
    lcd.write_string(formatString('Bitte Karte'))
    lcd.cursor_pos = (1, 0)
    lcd.write_string(formatString('anlegen'))
    switchPossible = True
    rfidPossible = True

def bezahlfunktionMenu():
    global currentPage, switchPossible, rfidPossible, inputPossible, currentUser
    currentUser = ''
    currentPage = 'bezahlfunktion'
    switchPossible = False
    rfidPossible = False
    inputPossible = False
    lcd.clear()
    rgbSetColor(0, 0, 100)
    lcd.write_string(formatString('Bankautomat'))
    lcd.cursor_pos = (1, 0)
    lcd.write_string(formatString('Burgerkarte'))
    sleep(3)
    lcd.clear()
    lcd.write_string(formatString('Bitte Karte'))
    lcd.cursor_pos = (1, 0)
    lcd.write_string(formatString('anlegen'))
    switchPossible = True
    rfidPossible = True

def oepnvMenu():
    global currentPage, switchPossible, rfidPossible, inputPossible, currentUser
    currentUser = ''
    currentPage = 'oepnv'
    switchPossible = False
    rfidPossible = False
    inputPossible = False
    lcd.clear()
    rgbSetColor(80, 0, 100)
    lcd.write_string(formatString('Willkommen'))
    lcd.cursor_pos = (1, 0)
    lcd.write_string(formatString('beim ÖPNV'))
    sleep(3)
    lcd.clear()
    lcd.write_string(formatString('Bitte Karte'))
    lcd.cursor_pos = (1, 0)
    lcd.write_string(formatString('anlegen'))
    switchPossible = True
    rfidPossible = True

def handleRFIDDetect(rfid):
    global currentPage, switchPossible, rfidPossible, inputPossible, inputAction, currentUser
    if currentPage == 'rathaus':
        switchPossible = False
        rfidPossible = False
        inputPossible = False
        usr = getData(rfid)
        if usr is False:
            lcd.clear()
            lcd.write_string(formatString('Fehler: Benutzer'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('nicht gefunden'))
        elif usr['rolle'] != 'user':
            lcd.clear()
            lcd.write_string(formatString('Nicht verfügbar'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('für Admin-Rolle'))
        elif 'termine' not in usr or len(usr['termine']) == 0:
            lcd.clear()
            lcd.write_string(formatString('Keine Termine'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('in der Zukunft'))
        else:
            currentAppointment = None
            currentAppointmentDateTime = datetime.now() + timedelta(days = 1000)
            for appointment in usr['termine']:
                dateTimeFormatted = datetime.strptime(f'{appointment["datum"]} {appointment["zeit"]}', '%Y-%m-%d %H:%M')
                if currentAppointmentDateTime > dateTimeFormatted >= datetime.now():
                    currentAppointmentDateTime = dateTimeFormatted
                    currentAppointment = appointment
            if currentAppointment == None:
                lcd.clear()
                lcd.write_string(formatString('Keine Termine'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString('in der Zukunft'))
            elif currentAppointmentDateTime - timedelta(minutes = 15) <= datetime.now():
                lcd.clear()
                lcd.write_string(formatString(currentAppointment['name']))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString(currentAppointmentDateTime.strftime('%d.%m.%Y %H:%M')))
                startAction('rathaus')
            else:
                lcd.clear()
                lcd.write_string(formatString('Nächster Termin'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString(currentAppointmentDateTime.strftime('%d.%m.%Y %H:%M')))
        sleep(3)
        rathausMenu()
    elif currentPage == 'buecherei':
        switchPossible = False
        rfidPossible = False
        inputPossible = False
        if rfid.startswith('u'):
            usr = getData(rfid)
            if usr is False:
                lcd.clear()
                lcd.write_string(formatString('Fehler: Benutzer'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString('nicht gefunden'))
                sleep(3)
                buechereiMenu()
            elif usr['rolle'] != 'user':
                lcd.clear()
                lcd.write_string(formatString('Nicht verfügbar'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString('für Admin-Rolle'))
                sleep(3)
                buechereiMenu()
            elif 'bibliothek' not in usr or usr['bibliothek'] is False:
                lcd.clear()
                lcd.write_string(formatString('Büchereikarte'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString('gesperrt'))
                sleep(3)
                buechereiMenu()
            else:
                currentUser = rfid
                lcd.clear()
                lcd.write_string(formatString('Bitte Buch'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString('vorhalten'))
                sleep(3)
                switchPossible = True
                rfidPossible = True
        else:
            if currentUser == '' or currentUser is None:
                lcd.clear()
                lcd.write_string(formatString('Kein Benutzer'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString('angemeldet'))
                sleep(3)
                buechereiMenu()
                return
            book = bookAction(rfid, 'check')
            if book is False:
                lcd.clear()
                lcd.write_string(formatString('Buch nicht'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString('registriert'))
                sleep(3)
                buechereiMenu()
            elif book['verfuegbar'] is False:
                usr = getData(currentUser)
                if any(elem.get("isbn") == rfid for elem in usr['bibliothek']['ausgeliehen']):
                    res = bookAction(rfid, 'return', usr = currentUser)
                    if res == 'success':
                        lcd.clear()
                        lcd.write_string(formatString(book["titel"]))
                        lcd.cursor_pos = (1, 0)
                        lcd.write_string(formatString('zurückgegeben'))
                        sleep(3)
                        buechereiMenu()
                    elif res == 'fee_problem':
                        lcd.clear()
                        lcd.write_string(formatString('Offene Gebühren'))
                        lcd.cursor_pos = (1, 0)
                        lcd.write_string(formatString('zu begleichen'))
                        sleep(3)
                        buechereiMenu()
                    else:
                        lcd.clear()
                        lcd.write_string(formatString('Ein Fehler ist'))
                        lcd.cursor_pos = (1, 0)
                        lcd.write_string(formatString('aufgetreten'))
                        sleep(3)
                        buechereiMenu()
                else:
                    lcd.clear()
                    lcd.write_string(formatString('Buch bereits'))
                    lcd.cursor_pos = (1, 0)
                    lcd.write_string(formatString('ausgeliehen'))
                    sleep(3)
                    buechereiMenu()
            else:
                res = bookAction(rfid, 'borrow', usr = currentUser)
                if res:
                    lcd.clear()
                    lcd.write_string(formatString(book["titel"]))
                    lcd.cursor_pos = (1, 0)
                    lcd.write_string(formatString('ausgeliehen'))
                    sleep(3)
                    buechereiMenu()
                else:
                    lcd.clear()
                    lcd.write_string(formatString('Ein Fehler ist'))
                    lcd.cursor_pos = (1, 0)
                    lcd.write_string(formatString('aufgetreten'))
                    sleep(3)
                    buechereiMenu()
    elif currentPage == 'bezahlfunktion':
        switchPossible = False
        rfidPossible = False
        inputPossible = False
        usr = getData(rfid)
        if usr is False or 'name' not in usr:
            lcd.clear()
            lcd.write_string(formatString('Fehler: Benutzer'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('nicht gefunden'))
            sleep(3)
            bezahlfunktionMenu()
        elif usr['rolle'] != 'user':
            lcd.clear()
            lcd.write_string(formatString('Nicht verfügbar'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('für Admin-Rolle'))
            sleep(3)
            bezahlfunktionMenu()
        elif 'bezahlkarte' not in usr or usr['bezahlkarte'] is False:
            lcd.clear()
            lcd.write_string(formatString('Bezahlfunktion'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('nicht verfügbar'))
            sleep(3)
            bezahlfunktionMenu()
        else:
            lcd.clear()
            lcd.write_string(formatString(usr['name']))
            lcd.cursor_pos = (1, 0)
            currentBalance = usr['bezahlkarte']['kontostand']
            lcd.write_string(formatString(f'{currentBalance:.2f}'.replace('.', ',') + ' €'))
            sleep(3)
            lcd.clear()
            lcd.write_string(formatString('A: Einzahlen'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('B: Auszahlen'))
            inputPossible = True
            switchPossible = True
            inputAction = 'bezahlfunktionEinAuszahlen'
            currentUser = rfid
    elif currentPage == 'oepnv':
        switchPossible = False
        rfidPossible = False
        inputPossible = False
        usr = getData(rfid)
        if usr is False:
            lcd.clear()
            lcd.write_string(formatString('Fehler: Benutzer'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('nicht gefunden'))
        elif usr['rolle'] != 'user':
            lcd.clear()
            lcd.write_string(formatString('Nicht verfügbar'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('für Admin-Rolle'))
        else:
            for index, elem in enumerate(usr['tickets']):
                if elem.get('status') == 'aktiv':
                    if elem.get('typ') == 'Einzelfahrt':
                        if datetime.strptime(elem['gültigkeit'], '%Y-%m-%d').date() == datetime.now().date():
                            usr['tickets'][index]['status'] = 'abgelaufen'
                            changeData(rfid, 'tickets', usr['tickets'])
                            lcd.clear()
                            lcd.write_string(formatString('Einzelfahrt'))
                            lcd.cursor_pos = (1, 0)
                            lcd.write_string(formatString('Ticket eingelöst'))
                            startAction('oepnv')
                            sleep(3)
                            oepnvMenu()
                            return
                    elif elem.get('typ') in ('Tageskarte', 'Wochenkarte', 'Monatskarte'):
                        endDate = datetime.strptime(elem['gültigkeit'], '%Y-%m-%d') + timedelta(days = 0 if elem['typ'] == 'Tageskarte' else 6 if elem['typ'] == 'Wochenkarte' else 29)
                        if datetime.strptime(elem['gültigkeit'], '%Y-%m-%d').date() <= datetime.now().date() <= endDate.date():
                            lcd.clear()
                            lcd.write_string(formatString(elem['typ']))
                            lcd.cursor_pos = (1, 0)
                            lcd.write_string(formatString('Zutritt erlaubt'))
                            startAction('oepnv')
                            sleep(3)
                            oepnvMenu()
                            return
            lcd.clear()
            lcd.write_string(formatString('Keine aktuellen'))
            lcd.cursor_pos = (1, 0)
            lcd.write_string(formatString('Tickets aktiv'))
            sleep(3)
            oepnvMenu()

def inputUpdateDisplay(content, action):
    if action in ('einzahlen', 'auszahlen'):
        symbol = '+'
        lcd.clear()
        if action == 'einzahlen':
            lcd.write_string('Einzahlen:')
        else:
            lcd.write_string('Auszahlen:')
            symbol = '-'
        lcd.cursor_pos = (1, 0)
        amount = content.zfill(3)
        amountEuro = amount[:-2]
        amountCent = amount[-2:]
        amountEuroReversed = amountEuro[::-1]
        formattedEuro = '.'.join([amountEuroReversed[i:i+3] for i in range(0, len(amountEuroReversed), 3)])
        formattedEuro = formattedEuro[::-1]
        lcd.write_string(formatString(f'{symbol} {formattedEuro},{amountCent} €'))
        if len(content) < 4:
            lcd.cursor_pos = (1, 5)
            lcd.cursor_mode = 'blink'
        elif len(content) < 6:
            lcd.cursor_pos = (1, len(content) + 2)
            lcd.cursor_mode = 'blink'
        else:
            lcd.cursor_mode = 'hide'
    else:
        lcd.write_string(content)

def handleKeyPress(key):
    global inputPossible, inputAction, currentUser
    if inputPossible:
        args = inputAction.split('; ')
        if args[0] == 'bezahlfunktionEinAuszahlen':
            if key == 'A':
                inputPossible = False
                inputUpdateDisplay('', 'einzahlen')
                inputAction = 'bezahlfunktionBetragEingeben; einzahlen'
                inputPossible = True
            elif key == 'B':
                inputPossible = False
                inputUpdateDisplay('', 'auszahlen')
                inputAction = 'bezahlfunktionBetragEingeben; auszahlen'
                inputPossible = True
        elif args[0] == 'bezahlfunktionBetragEingeben':
            inputPossible = False
            amount = ''
            if len(args) >= 3:
                amount = args[2]
            if key == 'A':
                lcd.cursor_mode = 'hide'
                inputAction = ''
                amount = int(amount) / 100
                userData = getData(currentUser)
                if not userData or 'bezahlkarte' not in userData:
                    lcd.clear()
                    lcd.write_string(formatString('Ein Fehler ist'))
                    lcd.cursor_pos = (1, 0)
                    lcd.write_string(formatString('aufgetreten'))
                    sleep(3)
                    bezahlfunktionMenu()
                    return
                newBalance = 0
                if args[1] == 'einzahlen':
                    newBalance = round(userData['bezahlkarte']['kontostand'] + amount, 2)
                else:
                    if userData['bezahlkarte']['kontostand'] >= amount:
                        newBalance = round(userData['bezahlkarte']['kontostand'] - amount, 2)
                    else:
                        lcd.clear()
                        lcd.write_string(formatString('Guthaben reicht'))
                        lcd.cursor_pos = (1, 0)
                        lcd.write_string(formatString('nicht aus'))
                        sleep(3)
                        bezahlfunktionMenu()
                        return
                userData['bezahlkarte']['kontostand'] = newBalance
                if 'transaktionen' not in userData['bezahlkarte']:
                    userData['bezahlkarte']['transaktionen'] = []
                userData['bezahlkarte']['transaktionen'].append({
                    'datum': datetime.now().strftime('%Y-%m-%d'),
                    'betrag': amount,
                    'typ': 'einzahlung' if args[1] == 'einzahlen' else 'ausgabe',
                    'beschreibung': f'{"Einzahlung" if args[1] == "einzahlen" else "Auszahlung"} am Burgerkarte Bankomaten'
                })
                changeData(currentUser, 'bezahlkarte', userData['bezahlkarte'])
                lcd.clear()
                lcd.write_string(formatString('Neues Guthaben:'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString(f'{newBalance:.2f}'.replace('.', ',') + ' €'))
                sleep(3)
                bezahlfunktionMenu()
                return
            elif key == 'B':
                lcd.cursor_mode = 'hide'
                inputAction = ''
                lcd.clear()
                lcd.write_string(formatString('Transaktion'))
                lcd.cursor_pos = (1, 0)
                lcd.write_string(formatString('abgebrochen'))
                sleep(3)
                bezahlfunktionMenu()
                return
            elif key == '#':
                amount = ''
            elif key == '*':
                amount = amount[:-1]
            elif key == '0' and len(amount) == 0:
                pass
            elif key in '0123456789' and len(amount) < 6:
                amount += key
            inputAction = f'bezahlfunktionBetragEingeben; { args[1] }; { amount }'
            inputUpdateDisplay(amount, args[1])
            inputPossible = True

def switchMenu(pin):
    global currentPage, switchPossible, currentUser
    if not switchPossible:
        return
    currentUser = ''
    if currentPage == 'rathaus':
        Thread(target = buechereiMenu, daemon = True).start()
    elif currentPage == 'buecherei':
        Thread(target = bezahlfunktionMenu, daemon = True).start()
    elif currentPage == 'bezahlfunktion':
        Thread(target = oepnvMenu, daemon = True).start()
    elif currentPage == 'oepnv':
        Thread(target = rathausMenu, daemon = True).start()

def resetPi():
    print('[red]Programm wird beendet...[/red]')
    lcd.clear()
    lcd.write_string(formatString('Auf Wiedersehen'))
    sleep(3)
    rgbRedPwm.stop()
    rgbGreenPwm.stop()
    rgbBluePwm.stop()
    lcd.clear()
    keypad.cleanup()
    GPIO.cleanup()

print('[green]Programm gestartet...[/green]')
Thread(target = rathausMenu, daemon = True).start()

GPIO.add_event_detect(SWITCH_MENU_PIN, GPIO.FALLING, callback = switchMenu, bouncetime = 200)
keypad.registerKeyPressHandler(handleKeyPress)

try:
    while True:
        id, data = reader.read()
        if data.strip() == 'exitToken':
            resetPi()
            sys.exit(0)
        elif rfidPossible and data is not None and data.strip() != '':
            print(f'[green]RFID-Chip mit den Daten "{data.strip()}" wurde eingelesen[/green]')
            Thread(target = handleRFIDDetect(data.strip()), daemon = True).start()
        sleep(0.1)

except KeyboardInterrupt:
    pass

finally:
    resetPi()