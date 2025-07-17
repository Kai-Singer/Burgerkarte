from django.shortcuts import render, redirect
from django.http import JsonResponse, FileResponse
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
import json
import os
import socket

#serverstatus
import platform
import psutil
import django
import time

# Globale Pfade Datenbank
BASE_DIR = '/var/www/django-project/burgerkarte/data'
USER_DATA_PATH = os.path.join(BASE_DIR, 'users')
ROLLEN_PATH = os.path.join(BASE_DIR, 'rollen.json')
TERMIN_DATA_PATH = os.path.join(BASE_DIR, 'termine_rathaus.json')
BUECHER_DATA_PATH = os.path.join(BASE_DIR, 'buecherkatalog.json')


###############################################################
########################### API ###############################
###############################################################


def getUserAPI(request, uid):
    file_path = os.path.join(USER_DATA_PATH, f"{uid}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding = 'utf-8') as file:
            user_data = json.loads(file.read())
        return JsonResponse(user_data, status = 200)
    else:
        return JsonResponse({"error": "User Data not found"}, status = 404)

@csrf_exempt
def changeUserAPI(request, uid):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST allowed"}, status = 405)
    file_path = os.path.join(USER_DATA_PATH, f"{uid}.json")
    if not os.path.exists(file_path):
        return JsonResponse({"error": "User Data not found"}, status = 404)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON uploaded"}, status = 400)
    with open(file_path, 'w', encoding = 'utf-8') as file:
        file.write(json.dumps(data, indent = 4, ensure_ascii = False))
    return JsonResponse({"status": "User Data updated successfully"}, status = 200)

def getBookAPI(request, isbn):
    try:
        file = open(BUECHER_DATA_PATH, "r", encoding = "utf-8")
        data = json.loads(file.read())
        file.close()
        book = next((elem for elem in data if elem.get("isbn") == isbn), None)
        if book:
            return JsonResponse(book, status = 200)
        else:
            return JsonResponse({"error": "Book not found"}, status = 404)
    except Exception as e:
        return JsonResponse({"error": "Failed to load 'buecherkatalog.json'", "error_msg": e}, status = 400)

@csrf_exempt
def borrowBookAPI(request, isbn):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST allowed"}, status = 405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON uploaded"}, status = 400)
    uid = data.get('user')
    if not uid:
        return JsonResponse({"error": "User ID not provided"}, status = 400)
    user_path = os.path.join(USER_DATA_PATH, f"{uid}.json")
    if not os.path.exists(user_path):
        return JsonResponse({"error": "User Data not found"}, status = 404)
    with open(user_path, 'r', encoding = 'utf-8') as file:
        user_data = json.loads(file.read())
        if any(book.get("isbn") == isbn for book in user_data.get("bibliothek", {}).get("ausgeliehen", [])):
            return JsonResponse({"error": "Book is already borrowed by this user"}, status = 400)
    try:
        with open(BUECHER_DATA_PATH, "r", encoding = "utf-8") as file:
            book_data = json.loads(file.read())
    except Exception as e:
        return JsonResponse({"error": "Failed to load 'buecherkatalog.json'", "error_msg": str(e)}, status = 500)
    book = next((elem for elem in book_data if elem.get("isbn") == isbn), None)
    if book:
        if not book["verfuegbar"]:
            return JsonResponse({"error": "Book is already borrowed by another user"}, status = 400)
        else:
            try:
                for elem in book_data:
                    if elem.get("isbn") == isbn:
                        elem["verfuegbar"] = False
                        break
                with open(BUECHER_DATA_PATH, "w", encoding = "utf-8") as file:
                    file.write(json.dumps(book_data, indent = 4, ensure_ascii = False))
                user_data["bibliothek"]["ausgeliehen"].append({
                    "isbn": book["isbn"],
                    "titel": book["titel"],
                    "autor": book["autor"],
                    "status": "ausgeliehen",
                    "beantragt_am": timezone.now().strftime("%Y-%m-%d"),
                    'rueckgabe_bis': (timezone.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                    'gebuehr': 0
                })
                with open(user_path, 'w', encoding = 'utf-8') as file:
                    file.write(json.dumps(user_data, indent = 4, ensure_ascii = False))
                return JsonResponse({"status": "Book borrowed successfully"}, status = 200)
            except Exception as e:
                return JsonResponse({"error": "Failed to update book data", "error_msg": str(e)}, status = 500)
    else:
        return JsonResponse({"error": "Book not found"}, status = 404)

@csrf_exempt
def returnBookAPI(request, isbn):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST allowed"}, status = 405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON uploaded"}, status = 400)
    uid = data.get('user')
    if not uid:
        return JsonResponse({"error": "User ID not provided"}, status = 400)
    user_path = os.path.join(USER_DATA_PATH, f"{uid}.json")
    if not os.path.exists(user_path):
        return JsonResponse({"error": "User Data not found"}, status = 404)
    with open(user_path, 'r', encoding = 'utf-8') as file:
        user_data = json.loads(file.read())
        if not any(book.get("isbn") == isbn for book in user_data.get("bibliothek", {}).get("ausgeliehen", [])):
            return JsonResponse({"error": "Book was not borrowed by this user"}, status = 400)
    try:
        with open(BUECHER_DATA_PATH, "r", encoding = "utf-8") as file:
            book_data = json.loads(file.read())
    except Exception as e:
        return JsonResponse({"error": "Failed to load 'buecherkatalog.json'", "error_msg": str(e)}, status = 500)
    book = next((elem for elem in book_data if elem.get("isbn") == isbn), None)
    if book:
        try:
            for elem in book_data:
                if elem.get("isbn") == isbn:
                    elem["verfuegbar"] = True
                    break
            with open(BUECHER_DATA_PATH, "w", encoding = "utf-8") as file:
                file.write(json.dumps(book_data, indent = 4, ensure_ascii = False))
            for elem in user_data["bibliothek"]["ausgeliehen"]:
                if elem.get("isbn") == isbn:
                    if elem.get('gebuehr', 0) > 0:
                        return JsonResponse({"error": "Book cannot be returned due to outstanding fees", "fee_problem": True}, status = 400)
                    else:
                        user_data["bibliothek"]["ausgeliehen"].remove(elem)
                    break
            with open(user_path, 'w', encoding = 'utf-8') as file:
                file.write(json.dumps(user_data, indent = 4, ensure_ascii = False))
            return JsonResponse({"status": "Book returned successfully"}, status = 200)
        except Exception as e:
            return JsonResponse({"error": "Failed to update book data", "error_msg": str(e)}, status = 500)
    else:
        return JsonResponse({"error": "Book not found"}, status = 404)

def viewPosterAPI(request, lang):
    if lang not in ('de', 'en'):
        return JsonResponse({"error": "Language not supported"}, status = 404)
    file_path = os.path.join(BASE_DIR, f"posters/poster_{lang}.pdf")
    if not os.path.exists(file_path):
        return JsonResponse({"error": "File not found"}, status = 404)
    return FileResponse(open(file_path, 'rb'), content_type='application/pdf')


###############################################################
#################### LOGIN + REGISTRIERUNG ####################
###############################################################

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        passwort = request.POST.get('passwort')

        for datei in os.listdir(USER_DATA_PATH):
            if datei.endswith('.json'):
                with open(os.path.join(USER_DATA_PATH, datei), 'r', encoding='utf-8') as f:
                    try:
                        user_data = json.load(f)
                        if user_data.get('email') == email and user_data.get('passwort') == passwort:
                            status = user_data.get('status', 'aktiv').lower()
                            if status == 'gesperrt':
                                messages.error(request, "Dein Benutzerkonto wurde gesperrt.")
                                return redirect('login')

                            request.session['user_id'] = user_data.get('id')
                            request.session['user_name'] = f"{user_data.get('vorname', '')} {user_data.get('nachname', '')}"
                            rolle = user_data.get('rolle', 'user').lower()
                            service_type = user_data.get('service_type')    #hier nochmal ansetzen beim service!
                            vorname = user_data.get('vorname', '')
                            messages.success(request, f"Willkommen {vorname}!")

                            if rolle == 'admin':
                                return redirect('admin_dashboard')
                            elif rolle == 'service':
                                service_name = user_data.get('service')
                                if service_name:
                                    return redirect(f'service_dashboard_{service_name}')
                                else:
                                    messages.error(request, "Kein Service zugewiesen.")
                                    return redirect('login')
                            else:  # default: user
                                return redirect('user_dashboard')

                    except json.JSONDecodeError:
                        continue

        messages.error(request, "Ungültige E-Mail oder Passwort.")
    return render(request, 'burgerkarte/login_burgerkarte.html')


def logout(request):
    request.session.flush()
    messages.success(request, "Du wurdest erfolgreich abgemeldet.")
    return redirect('login')

def registrierung(request):
    if request.method == 'POST':
        vorname = request.POST.get('vorname')
        nachname = request.POST.get('nachname')
        geburtsdatum = request.POST.get('geburtsdatum')
        strasse = request.POST.get('strasse')
        hausnummer = request.POST.get('hausnummer')
        plz = request.POST.get('plz')
        ort = request.POST.get('ort')
        email = request.POST.get('email')
        passwort = request.POST.get('passwort')
        rolle = request.POST.get('rolle', 'user')
        service_type = request.POST.get('service_type') if rolle == 'service' else None

        os.makedirs(USER_DATA_PATH, exist_ok=True)

        vorhandene_dateien = [
            f for f in os.listdir(USER_DATA_PATH)
            if f.endswith('.json') and f[:4].isdigit()
        ]
        nummern = [int(f[:4]) for f in vorhandene_dateien]
        neue_nummer = max(nummern) + 1 if nummern else 1
        benutzer_id = f"{neue_nummer:04d}"

        benutzer_daten = {
            "id": benutzer_id,
            "vorname": vorname,
            "nachname": nachname,
            "geburtsdatum": geburtsdatum,
            "adresse": {
                "strasse": strasse,
                "hausnummer": hausnummer,
                "plz": plz,
                "ort": ort
            },
            "email": email,
            "passwort": passwort,
            "rolle": rolle,
            "service": service_type,
            "status": "aktiv",
            "erstellungsdatum": str(timezone.now().date()),
            "name": f"{vorname} {nachname}",

            # NEUE Felder
            "bibliothek": {
                "ausgeliehen": []
            },
            "tickets": [],
            "bezahlkarte": {
                "kontostand": 0.0,
                "transaktionen": []
            },
            "termine": [],
            "historie": []
        }

        file_path = os.path.join(USER_DATA_PATH, f"{benutzer_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(benutzer_daten, f, indent=4, ensure_ascii=False)

        messages.success(request, f"Registrierung erfolgreich als Benutzer #{benutzer_id}.")
        return redirect('login')

    return render(request, 'burgerkarte/registrierung_burgerkarte.html')

##############################################
#################### HOME ####################
##############################################

def home(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user = json.load(f)
        rolle = user.get('rolle', '').lower()
        if rolle == 'admin':
            return redirect('admin_dashboard')
        elif rolle == 'user':
            return redirect('user_dashboard')

###############################################
#################### ADMIN ####################
###############################################

#########################
### Admin - Dashboard ###
#########################

def admin_dashboard(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Bitte melde dich an.")
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        messages.error(request, "Benutzerdaten nicht gefunden.")
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user = json.load(f)
        rolle = user.get('rolle', '').lower()
        if rolle != 'admin':
            messages.error(request, "Zugriff verweigert - Adminrechte erforderlich.")
            return redirect('login')

    users = load_users()
    heute = timezone.now().date()
    letzter_monat = heute - timedelta(days=30)

    # 1. Alle User
    gesamtzahl = len(users)

    # 2. Neu registriert (letzter Monat)
    neu_registriert = sum(
        1 for user in users
        if 'erstellungsdatum' in user and
        datetime.strptime(user['erstellungsdatum'], "%Y-%m-%d").date() >= letzter_monat
    )

    # 3. Gesperrte User
    gesperrt = sum(1 for user in users if user.get('status') == 'gesperrt')


    #Serverstatus
    uptime = time.time() - psutil.boot_time()
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    django_version = django.get_version()

    server_status = {
        "uptime_h": int(uptime // 3600),
        "cpu_percent": cpu,
        "ram_used_mb": int(ram.used / 1024 / 1024),
        "ram_total_mb": int(ram.total / 1024 / 1024),
        "hostname": hostname,
        "ip": ip,
        "django_version": django_version,
    }

    return render(request, 'burgerkarte/admin/dashboard_admin_interface.html', {
        "anzahl_aktive": gesamtzahl,
        "anzahl_neue": neu_registriert,
        "anzahl_gesperrte": gesperrt,
        "server_status": server_status,
    })

##############################
### Admin - Userverwaltung ###
##############################

def load_users():
    users = []
    if os.path.exists(USER_DATA_PATH):
        for filename in sorted(os.listdir(USER_DATA_PATH)):
            if filename.endswith('.json'):
                file_path = os.path.join(USER_DATA_PATH, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        user = json.load(f)
                        user.setdefault('id', filename.replace('.json', ''))
                        user.setdefault('name', f"{user.get('vorname', '')} {user.get('nachname', '')}".strip())
                        user.setdefault('rolle', 'Gast')
                        user.setdefault('email', 'N/A')
                        user.setdefault('status', 'aktiv')
                        user.setdefault('erstellungsdatum', 'N/A')
                        user.setdefault("bibliothek", { "ausgeliehen": [] })
                        user.setdefault("tickets", [])
                        user.setdefault("bezahlkarte", {
                            "kontostand": 0.0,
                            "transaktionen": []
                        })
                        user.setdefault("termine", [])
                        user.setdefault("historie", [])
                        users.append(user)
                except json.JSONDecodeError:
                    continue
    return users


def save_user(user):
    user_id = user.get('id')
    if not user_id:
        return
    file_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(user, f, indent=4, ensure_ascii=False)


def delete_user(user_id):
    file_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)


def load_rollen():
    try:
        with open(ROLLEN_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return ["admin", "service", "user"]


def user_verwaltung(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Bitte melde dich an.")
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        messages.error(request, "Benutzerdaten nicht gefunden.")
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user = json.load(f)
        rolle = user.get('rolle', '').lower()
        if rolle != 'admin':
            messages.error(request, "Zugriff verweigert – Adminrechte erforderlich.")
            return redirect('login')

    users = load_users()
    rollen = load_rollen()
    status_optionen = ["aktiv", "gesperrt"]

    suchbegriff = request.GET.get('Suchbegriff', '').lower()
    filter_rolle = request.GET.get('rollen', 'alle')
    filter_status = request.GET.get('status', 'alle')
    datum = request.GET.get('datum', '')

    if suchbegriff:
        users = [u for u in users if suchbegriff in u['name'].lower() or suchbegriff in u.get('email', '').lower()]
    if filter_rolle != "alle":
        users = [u for u in users if u.get('rolle') == filter_rolle]
    if filter_status != "alle":
        users = [u for u in users if u.get('status') == filter_status]
    if datum:
        users = [u for u in users if u.get('erstellungsdatum') == datum]

    for user in users:
        user_date = datetime.strptime(user["erstellungsdatum"], "%Y-%m-%d")
        user["erstellungsdatum"] = user_date.strftime("%d.%m.%Y")

    return render(request, 'burgerkarte/admin/userverwaltung_admin_interface.html', {
        'users': users,
        'rollen': rollen,
        'status_optionen': status_optionen,
        'suchbegriff': suchbegriff,
        'filter_rolle': filter_rolle,
        'filter_status': filter_status,
        'datum': datum,
    })


def user_bearbeiten(request, user_id):
    file_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(file_path):
        messages.error(request, "Benutzer nicht gefunden.")
        return redirect('userverwaltung')

    with open(file_path, 'r', encoding='utf-8') as f:
        user = json.load(f)

    if request.method == 'POST':
        user['rolle'] = request.POST.get('rolle')
        user['status'] = request.POST.get('status')
        user['vorname'] = request.POST.get('vorname')
        user['nachname'] = request.POST.get('nachname')
        user['name'] = f"{user['vorname']} {user['nachname']}" 
        print("DEBUG: Bearbeite User", user)
        save_user(user)
        messages.success(request, "Benutzer aktualisiert.")
        return redirect('user_verwaltung')


def user_loeschen(request, user_id):
    delete_user(user_id)
    messages.success(request, "Benutzer gelöscht.")
    return redirect('user_verwaltung')

################################
### Admin - Bücherverwaltung ###
################################

def buch_freigeben(request):
    if request.method == 'POST':
        isbn = request.POST.get('isbn')
        ausgeliehen_user_id = request.POST.get('ausgeliehen_user_id')

        if not isbn:
            messages.error(request, "Keine ISBN angegeben.")
            return redirect('libraryverwaltung')

        BUECHERKATALOG_PATH = os.path.join(BASE_DIR, 'buecherkatalog.json')
        if not os.path.exists(BUECHERKATALOG_PATH):
            messages.error(request, "Bücherkatalog nicht gefunden.")
            return redirect('libraryverwaltung')

        with open(BUECHERKATALOG_PATH, 'r', encoding='utf-8') as f:
            buecher = json.load(f)

        buch = next((b for b in buecher if b.get('isbn') == isbn), None)
        if buch:
            buch['verfuegbar'] = True
            with open(BUECHERKATALOG_PATH, 'w', encoding='utf-8') as f:
                json.dump(buecher, f, indent=4, ensure_ascii=False)
            messages.success(request, f"Buch '{buch['titel']}' erfolgreich freigegeben.")
        else:
            messages.error(request, "Buch nicht gefunden.")

        user_path = os.path.join(USER_DATA_PATH, ausgeliehen_user_id + '.json')
        with open(user_path, 'r', encoding = 'utf-8') as file:
            user_data = json.loads(file.read())
            for buch in user_data.get("bibliothek", {}).get("ausgeliehen", []):
                if buch.get("isbn") == isbn:
                    user_data["bibliothek"]["ausgeliehen"].remove(buch)
                    break
        with open(user_path, 'w', encoding = 'utf-8') as file:
            file.write(json.dumps(user_data, indent = 4, ensure_ascii = False))

    return redirect('libraryverwaltung')

def libraryverwaltung(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Bitte melde dich an.")
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        messages.error(request, "Benutzerdaten nicht gefunden.")
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user = json.load(f)
        rolle = user.get('rolle', '').lower()
        if rolle != 'admin':
            messages.error(request, "Zugriff verweigert - Adminrechte erforderlich.")
            return redirect('login')
        
    BUECHERKATALOG_PATH = os.path.join(BASE_DIR, 'buecherkatalog.json')

    def load_buecherkatalog():
        if os.path.exists(BUECHERKATALOG_PATH):
            with open(BUECHERKATALOG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
        
    suchbegriff = request.GET.get("search", "").strip().lower()
    genre_filter = request.GET.get("genre", "all").lower()

    # Buchkatalog laden
    buecher = load_buecherkatalog()

    for buch in buecher:
        if buch.get("verfuegbar", True) is False:
            ausgeliehen_user_id = None
            ausgeliehen_user_name = None
            for datei in os.listdir(USER_DATA_PATH):
                user_path = os.path.join(USER_DATA_PATH, datei)
                with open(user_path, 'r', encoding = 'utf-8') as file:
                    user_data = json.loads(file.read())
                    if any(book.get("isbn") == buch.get('isbn', '') for book in user_data.get("bibliothek", {}).get("ausgeliehen", [])):
                        ausgeliehen_user_id = user_data.get('id')
                        ausgeliehen_user_name = user_data.get('name')
                        break
            buch['ausgeliehen_user_id'] = ausgeliehen_user_id if ausgeliehen_user_id else None
            buch['ausgeliehen_user_name'] = ausgeliehen_user_name if ausgeliehen_user_name else None

    genre_set = set()
    for buch in buecher:
        genre_set.update([g.lower() for g in buch.get("genre", [])])
    genre_liste = sorted(genre_set)

    # Katalog-Filter
    if suchbegriff:
        buecher = [
            b for b in buecher
            if suchbegriff in b.get("titel", "").lower() or
               suchbegriff in b.get("autor", "").lower()
        ]

    if genre_filter != "all":
        buecher = [
            b for b in buecher
            if genre_filter in [g.lower() for g in b.get("genre", [])]
        ]

    return render(request, 'burgerkarte/admin/library_admin_interface.html', {
        'buecher': buecher,
        'genres': genre_liste,
        'selected_genre': genre_filter,
        'search_term': suchbegriff
    })

#################################################
#################### Service ####################
#################################################

def service_dashboard_library(request):
    return render(request, 'burgerkarte/services/library/dashboard.html')

def service_dashboard_transport(request):
    return render(request, 'burgerkarte/services/transport/dashboard.html')

def service_dashboard_payment(request):
    return render(request, 'burgerkarte/services/payment/dashboard.html')



##############################################
#################### USER ####################
##############################################

########################
### User - Dashboard ###
########################

def user_dashboard(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Bitte melde dich an.")
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        messages.error(request, "Benutzerdaten nicht gefunden.")
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user_data = json.load(f)
        rolle = user_data.get('rolle', '').lower()
        if rolle != 'user':
            messages.error(request, "Zugriff verweigert - User Account erforderlich.")
            return redirect('login')

    heute = timezone.now().date()
    start_of_week = heute - timedelta(days=heute.weekday())
    end_of_week = start_of_week + timedelta(days=4)

    # Wochentage initialisieren
    wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
    termine_der_woche = {tag: [] for tag in wochentage}

    for termin in user_data.get("termine", []):
        try:
            termin_datum = datetime.strptime(termin["datum"], "%Y-%m-%d").date()
            if start_of_week <= termin_datum <= end_of_week:
                tag = termin.get("wochentag", "")
                if tag in termine_der_woche:
                    eintrag = f"{termin['zeit']} {termin['anliegen']}"
                    termine_der_woche[tag].append(eintrag)
        except Exception:
            continue

    # Kontostand & letzte Aufladung
    bezahlkarte = user_data.get("bezahlkarte", {})
    kontostand = bezahlkarte.get("kontostand", 0.0)
    letzte_aufladung = "N.a."
    for t in bezahlkarte.get("transaktionen", []):
        if t.get("typ", "").lower() == "einzahlung":
            letzte_aufladung = t.get("datum", "N.a.")

    # Aktives Ticket
    aktuelles_ticket = None
    for t in user_data.get("tickets", []):
        if t.get("status") == "aktiv":
            aktuelles_ticket = t
            break
    if aktuelles_ticket:
        aktuelles_ticket['preis'] = f"{aktuelles_ticket['preis']:.2f}".replace('.', ',') + " €"
        ticket_gültigkeit = datetime.strptime(aktuelles_ticket['gültigkeit'], "%Y-%m-%d")
        aktuelles_ticket['gültigkeit'] = ticket_gültigkeit.strftime("%d.%m.%Y")

    # Bücher & Gebühren
    ausgeliehen = user_data.get("bibliothek", {}).get("ausgeliehen", [])
    anzahl_buecher = len(ausgeliehen)
    gebuehren = sum(float(b.get("gebuehr", 0)) for b in ausgeliehen)

    return render(request, 'burgerkarte/user/dashboard.html', {
        'active': 'dashboard',
        'termine_der_woche': termine_der_woche,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
        'kontostand': f"{kontostand:.2f}".replace('.', ',') + " €",
        'kontostand_status': 'danger' if kontostand < 0 else 'success',
        'letzte_aufladung': letzte_aufladung,
        'aktuelles_ticket': aktuelles_ticket,
        'anzahl_buecher': anzahl_buecher,
        'gebuehren': f"{gebuehren:.2f}".replace('.', ',') + " €",
        'gebuehren_status': 'danger' if gebuehren > 0 else 'success'
    })



##########################
### User-Terminbuchung ###
##########################

WOCHENTERMINE_PATH = os.path.join(BASE_DIR, 'wochentermine.json')


def load_termine():
    if os.path.exists(WOCHENTERMINE_PATH):
        try:
            with open(WOCHENTERMINE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def get_date_for_wochentag(tagname):
    """Gibt das Datum (YYYY-MM-DD) des nächsten angegebenen Wochentags zurück."""
    wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    tag_index = wochentage.index(tagname)
    return (start_of_week + timedelta(days=tag_index)).isoformat()

def save_termine(termine):
    with open(WOCHENTERMINE_PATH, 'w', encoding='utf-8') as f:
        json.dump(termine, f, indent=4, ensure_ascii=False)


def buchung_abschicken(request):
    if request.method != 'POST':
        return redirect('termine')

    wochentag = request.POST.get('wochentag')
    uhrzeit = request.POST.get('uhrzeit')
    anliegen = request.POST.get('anliegen')
    datum = request.POST.get('datum')
    user_id = request.session.get('user_id')

    if not all([wochentag, uhrzeit, datum, user_id]):
        messages.error(request, "Ungültige Eingabe oder nicht eingeloggt.")
        return redirect('termine')

    termine = load_termine()

    if wochentag not in termine:
        messages.error(request, f"Ungültiger Wochentag: {wochentag}")
        return redirect('termine')

    slots = termine[wochentag].get("slots", [])
    slot_gefunden = False

    for slot in slots:
        if slot["zeit"] == uhrzeit:
            if slot["blockiert_durch"]:
                messages.error(request, "Dieser Slot ist bereits gebucht.")
                return redirect('termine')

            # Termin im Slot speichern
            slot["blockiert_durch"] = user_id
            slot["anliegen"] = anliegen
            slot_gefunden = True
            break

    if not slot_gefunden:
        messages.error(request, "Slot nicht gefunden.")
        return redirect('termine')

    # Termin in die User-Datei eintragen
    user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            try:
                user_data = json.load(f)
            except json.JSONDecodeError:
                messages.error(request, "Fehler beim Laden deiner Benutzerdaten.")
                return redirect('termine')

        neuer_termin = {
            "datum": datum,
            "zeit": uhrzeit,
            "wochentag": wochentag,
            "anliegen": anliegen
        }

        user_data.setdefault("termine", []).append(neuer_termin)
        user_data.setdefault("historie", []).append({
            "typ": "termin_buchung",
            "zeitpunkt": timezone.now().isoformat(),
            "beschreibung": f"Termin am {datum} um {uhrzeit} gebucht"
        })

        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4, ensure_ascii=False)

    save_termine(termine)
    messages.success(request, f"Termin um {uhrzeit} am {datum} erfolgreich gebucht.")
    return redirect('termine')



def termine(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Bitte melde dich an.")
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        messages.error(request, "Benutzerdaten nicht gefunden.")
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user = json.load(f)
        rolle = user.get('rolle', '').lower()
        if rolle != 'user':
            messages.error(request, "Zugriff verweigert - User Account erforderlich.")
            return redirect('login')
    
    zeitslots = load_termine()

    heute = timezone.now().date()
    start_of_week = heute - timedelta(days=heute.weekday())
    wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]

    view_data = []

    for i, tag in enumerate(wochentage):
        datum = (start_of_week + timedelta(days=i)).isoformat()

        if tag not in zeitslots:
            zeitslots[tag] = {
                "datum": datum,
                "slots": []
            }
        else:
            zeitslots[tag]["datum"] = datum
            if "slots" not in zeitslots[tag]:
                zeitslots[tag]["slots"] = []

        view_data.append({
            "tag": tag,
            "datum": zeitslots[tag]["datum"],
            "slots": zeitslots[tag]["slots"]
        })

    save_termine(zeitslots)

    gebuchte_termine = []
    if user_id:
        user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
        if os.path.exists(user_file):
            with open(user_file, 'r', encoding='utf-8') as f:
                user = json.load(f)
                gebuchte_termine = user.get('termine', [])
                for termin in gebuchte_termine:
                    termin["name"] = user.get("name", "Unbekannt")

    heute = timezone.now().date()
    start_of_week = heute - timedelta(days=heute.weekday())
    end_of_week = start_of_week + timedelta(days=4)

    return render(request, 'burgerkarte/user/terminbuchung_terminverwaltung.html', {
        'view_data': view_data,
        'gebuchte_termine': gebuchte_termine,
        'active': 'termine',
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
    })

def termin_absagen(request):
    if request.method != 'POST':
        return redirect('termine')

    user_id = request.session.get('user_id')
    datum = request.POST.get('datum')
    zeit = request.POST.get('zeit')

    if not all([user_id, datum, zeit]):
        messages.error(request, "Fehlende Daten zum Absagen des Termins.")
        return redirect('termine')

    # Termin aus wochentermine.json entfernen
    termine = load_termine()
    geändert = False

    for tagname, tag in termine.items():
        if tag.get('datum') == datum:
            for slot in tag.get('slots', []):
                if slot.get('zeit') == zeit and slot.get('blockiert_durch') == user_id:
                    slot['blockiert_durch'] = None
                    slot['anliegen'] = ""
                    geändert = True
                    break
            break


    if geändert:
        save_termine(termine)

    # Termin aus Benutzerdatei entfernen
    user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if os.path.exists(user_file):
        with open(user_file, 'r', encoding='utf-8') as f:
            user = json.load(f)

        user['termine'] = [t for t in user.get('termine', []) if not (t['datum'] == datum and t['zeit'] == zeit)]
        user.setdefault("historie", []).append({
            "typ": "termin_absage",
            "zeitpunkt": timezone.now().isoformat(),
            "beschreibung": f"Termin am {datum} um {zeit} abgesagt"
        })

        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user, f, indent=4, ensure_ascii=False)

    messages.success(request, "Termin wurde erfolgreich abgesagt.")
    return redirect('termine')



#########################
### User - Bibliothek ###
#########################

BUECHERKATALOG_PATH = os.path.join(BASE_DIR, 'buecherkatalog.json')

def load_buecherkatalog():
    if os.path.exists(BUECHERKATALOG_PATH):
        with open(BUECHERKATALOG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def buch_ausleihen(request):
    if request.method != 'POST':
        messages.error(request, "Ungültige Anforderung.")
        return redirect('bibliothek')

    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Nicht eingeloggt.")
        return redirect('login')

    isbn = request.POST.get('isbn')
    if not isbn:
        messages.error(request, "Fehlende ISBN.")
        return redirect('bibliothek')

    # Buchkatalog laden
    try:
        with open(BUECHERKATALOG_PATH, 'r', encoding='utf-8') as f:
            katalog = json.load(f)
    except:
        messages.error(request, "Fehler beim Laden des Katalogs.")
        return redirect('bibliothek')

    buch = next((b for b in katalog if b.get('isbn') == isbn), None)
    if not buch:
        messages.error(request, "Buch nicht gefunden.")
        return redirect('bibliothek')

    if not buch.get("verfuegbar", True):
        messages.error(request, "Das Buch ist bereits ausgeliehen.")
        return redirect('bibliothek')

    # Benutzerdaten laden
    user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_file):
        messages.error(request, "Benutzerdatei nicht gefunden.")
        return redirect('bibliothek')

    with open(user_file, 'r', encoding='utf-8') as f:
        user_data = json.load(f)

    # Prüfen ob schon ausgeliehen
    ausgeliehen = user_data.get("bibliothek", {}).get("ausgeliehen", [])
    if any(e.get("isbn") == isbn for e in ausgeliehen):
        messages.warning(request, "Du hast dieses Buch bereits ausgeliehen oder beantragt.")
        return redirect('bibliothek')

    eintrag = {
        "isbn": buch.get("isbn"),
        "titel": buch.get("titel"),
        "autor": buch.get("autor"),
        "status": "zur ausleihe beantragt",
        "beantragt_am": timezone.now().strftime("%Y-%m-%d"),
        'rueckgabe_bis': (timezone.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        'gebuehr': 0
    }

    user_data.setdefault("bibliothek", {}).setdefault("ausgeliehen", []).append(eintrag)

    # Speichern beim Benutzer
    with open(user_file, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, indent=4, ensure_ascii=False)

    # Katalog aktualisieren
    for b in katalog:
        if b.get('isbn') == isbn:
            b['verfuegbar'] = False
            break

    with open(BUECHERKATALOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(katalog, f, indent=4, ensure_ascii=False)

    messages.success(request, f"Buch '{buch.get('titel')}' zur Ausleihe beantragt.")
    return redirect('bibliothek')


def buch_verlaengern(request):
    if request.method != 'POST':
        messages.error(request, "Ungültige Anforderung.")
        return redirect('bibliothek')

    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Nicht eingeloggt.")
        return redirect('login')

    isbn = request.POST.get('isbn')
    if not isbn:
        messages.error(request, "Fehlende ISBN.")
        return redirect('bibliothek')

    # Benutzerdaten laden
    user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_file):
        messages.error(request, "Benutzerdatei nicht gefunden.")
        return redirect('bibliothek')

    with open(user_file, 'r', encoding='utf-8') as f:
        user_data = json.load(f)

    # Prüfen ob schon ausgeliehen
    ausgeliehen = user_data.get("bibliothek", {}).get("ausgeliehen", [])
    b_index, buch = next(((i, b) for i, b in enumerate(ausgeliehen) if b.get('isbn') == isbn), (None, None))
    if not buch:
        messages.error(request, "Buch nicht gefunden oder nicht ausgeliehen.")
        return redirect('bibliothek')
    
    if buch.get('bereits_verlaengert', False):
        messages.warning(request, "Dieses Buch wurde bereits verlängert.")
        return redirect('bibliothek')
    else:
        old_rueckgabe = datetime.strptime(buch['rueckgabe_bis'], "%Y-%m-%d")
        user_data["bibliothek"]["ausgeliehen"][b_index]['rueckgabe_bis'] = (old_rueckgabe + timedelta(days=30)).strftime("%Y-%m-%d")
        user_data["bibliothek"]["ausgeliehen"][b_index]['bereits_verlaengert'] = True

    with open(user_file, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, indent=4, ensure_ascii=False)

    return redirect('bibliothek')

def gebuehren_begleichen(request):
    if request.method != 'POST':
        messages.error(request, "Ungültige Anforderung.")
        return redirect('bibliothek')

    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Nicht eingeloggt.")
        return redirect('login')

    # Benutzerdaten laden
    user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_file):
        messages.error(request, "Benutzerdatei nicht gefunden.")
        return redirect('bibliothek')

    with open(user_file, 'r', encoding='utf-8') as f:
        user_data = json.load(f)

    gebuehren = sum(float(b.get("gebuehr", 0)) for b in user_data['bibliothek'].get('ausgeliehen', []))
    gebuehren -= sum(float(b.get("bereits_gezahlt", 0)) for b in user_data['bibliothek'].get('ausgeliehen', []))
    if gebuehren <= 0:
        messages.info(request, "Keine ausstehenden Gebühren.")
        return redirect('bibliothek')
    
    if not user_data.get("bezahlkarte", {}).get("kontostand", 0) >= gebuehren:
        messages.error(request, f"Nicht genügend Guthaben auf der Bezahlkarte.")
        return redirect('bibliothek')
    
    user_data["bezahlkarte"]["kontostand"] -= gebuehren
    user_data["bezahlkarte"]["transaktionen"].append({
        "datum": timezone.now().strftime("%d.%m.%Y"),
        "betrag": gebuehren,
        "typ": "ausgabe",
        "beschreibung": "Bibliothek Gebühren beglichen"
    })

    for b in user_data["bibliothek"]["ausgeliehen"]:
        b['bereits_gezahlt'] = b["gebuehr"]

    with open(user_file, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, indent=4, ensure_ascii=False)

    return redirect('bibliothek')

def aktualisiere_bib_gebuehren(user_data):
    heute = timezone.now().date()
    buecher = user_data['bibliothek'].get('ausgeliehen', [])

    if not buecher:
        return user_data
    
    for book in buecher:
        rueckgabe_date = datetime.strptime(book['rueckgabe_bis'], "%Y-%m-%d").date()

        if heute > rueckgabe_date:
            tage_ueberfaellig = (heute - rueckgabe_date).days
            book['gebuehr'] = tage_ueberfaellig * 0.50
        else:
            book['gebuehr'] = 0

    user_data['bibliothek']['ausgeliehen'] = buecher
    return user_data


def bibliothek(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Bitte melde dich an.")
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        messages.error(request, "Benutzerdaten nicht gefunden.")
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user = json.load(f)
        rolle = user.get('rolle', '').lower()
        if rolle != 'user':
            messages.error(request, "Zugriff verweigert - User Account erforderlich.")
            return redirect('login')
        
    suchbegriff = request.GET.get("search", "").strip().lower()
    genre_filter = request.GET.get("genre", "all").lower()
    ausgeliehen_suchbegriff = request.GET.get("ausgeliehenSearch", "").strip().lower()

    # Buchkatalog laden
    buecher = load_buecherkatalog()
    buecher_verfuegbar = len(buecher)

    genre_set = set()
    for buch in buecher:
        genre_set.update([g.lower() for g in buch.get("genre", [])])
    genre_liste = sorted(genre_set)

    # Katalog-Filter
    if suchbegriff:
        buecher = [
            b for b in buecher
            if suchbegriff in b.get("titel", "").lower() or
               suchbegriff in b.get("autor", "").lower()
        ]

    if genre_filter != "all":
        buecher = [
            b for b in buecher
            if genre_filter in [g.lower() for g in b.get("genre", [])]
        ]

    # Benutzer & ausgeliehene Bücher laden
    ausgeliehen = []

    if user_id:
        user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
        if os.path.exists(user_file):
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)

            user_data = aktualisiere_bib_gebuehren(user_data)

            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=4, ensure_ascii=False)

            for b in user_data.get("bibliothek", {}).get("ausgeliehen", []):
                beantragt_date = datetime.strptime(b['beantragt_am'], "%Y-%m-%d")
                b['beantragt_am'] = beantragt_date.strftime("%d.%m.%Y")
                rueckgabe_date = datetime.strptime(b['rueckgabe_bis'], "%Y-%m-%d")
                b['rueckgabe_bis'] = rueckgabe_date.strftime("%d.%m.%Y")
                ausgeliehen.append(b)

            # Filter für ausgeliehene Bücher
            if ausgeliehen_suchbegriff:

                ausgeliehen = [
                    b for b in ausgeliehen
                    if ausgeliehen_suchbegriff in b.get("titel", "").lower() or
                        ausgeliehen_suchbegriff in b.get("autor", "").lower()
                ]
            
            gebuehren = sum(float(b.get("gebuehr", 0)) for b in ausgeliehen)
            gebuehren -= sum(float(b.get("bereits_gezahlt", 0)) for b in ausgeliehen)

    return render(request, 'burgerkarte/user/bibliothek.html', {
        'active': 'bibliothek',
        'buecher': buecher,
        'genres': genre_liste,
        'selected_genre': genre_filter,
        'search_term': suchbegriff,
        'ausgeliehen': ausgeliehen,
        'ausgeliehen_search': ausgeliehen_suchbegriff,
        'anzahl_buecher': len(ausgeliehen),
        'gebuehren': f"{gebuehren:.2f}".replace('.', ',') + " €",
        'gebuehren_status': 'danger' if gebuehren > 0 else 'success',
        'buecher_verfuegbar': buecher_verfuegbar
    })






##########################
### User - Bezahlkarte ###
##########################


def aufladen(request):
    if request.method != 'POST':
        return redirect('bezahlkarte')

    user_id = request.session.get('user_id')
    betrag = request.POST.get('betrag')

    if not user_id or not betrag:
        messages.error(request, "Fehlende Angaben.")
        return redirect('bezahlkarte')

    try:
        betrag = round(float(betrag), 2)
        if betrag < 1:
            raise ValueError()
    except ValueError:
        messages.error(request, "Ungültiger Betrag.")
        return redirect('bezahlkarte')

    user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if os.path.exists(user_file):
        with open(user_file, 'r', encoding='utf-8') as f:
            user = json.load(f)

        user["bezahlkarte"]["kontostand"] += betrag
        user["bezahlkarte"]["transaktionen"].append({
            "datum": timezone.now().strftime("%d.%m.%Y"),
            "betrag": betrag,
            "typ": "einzahlung",
            "beschreibung": "Aufladung"
        })


        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user, f, indent=4, ensure_ascii=False)

        messages.success(request, f"{betrag:.2f} € erfolgreich aufgeladen.")
        return redirect('bezahlkarte')


    


def bezahlkarte(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Bitte melde dich an.")
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        messages.error(request, "Benutzerdaten nicht gefunden.")
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user = json.load(f)
        rolle = user.get('rolle', '').lower()
        if rolle != 'user':
            messages.error(request, "Zugriff verweigert - User Account erforderlich.")
            return redirect('login')
    
    user_data = {}
    transaktionen = []
    kontostand = 0.0
    letzte_aufladung = "N.a."

    if user_id:
        user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
        if os.path.exists(user_file):
            with open(user_file, "r", encoding="utf-8") as f:
                user_data = json.load(f)
                kontostand = user_data.get("bezahlkarte", {}).get("kontostand", 0.0)
                transaktionen = user_data.get("bezahlkarte", {}).get("transaktionen", [])

    #Filter
    typ_filter = request.GET.get("typeFilter", "all").lower()
    suchbegriff = request.GET.get("transSearch", "").strip().lower()

    if typ_filter != "all":
        transaktionen = [t for t in transaktionen if t.get("typ", "").lower() == typ_filter]

    if suchbegriff:
        transaktionen = [
            t for t in transaktionen
            if suchbegriff in str(t.get("betrag", "")).lower() or suchbegriff in t.get("beschreibung", "").lower()
        ]

    #Datum der letzten Einzahlung ermitteln
    einzahlungen = [t for t in user_data.get("bezahlkarte", {}).get("transaktionen", []) if t.get("typ") == "einzahlung"]
    if einzahlungen:
        letzte_aufladung = max(t.get("datum") for t in einzahlungen)
    for t in transaktionen:
        betrag = t.get("betrag", 0)
        try:
            betrag_float = float(betrag)
        except ValueError:
            betrag_float = 0.0
        vorzeichen = "+" if t.get("typ", "").lower() == "einzahlung" else "-"
        t["betrag_formatiert"] = f"{vorzeichen} " + f"{betrag_float:.2f}".replace('.', ',') + " €"

    return render(request, 'burgerkarte/user/bezahlkarte.html', {
        'active': 'bezahlkarte',
        'kontostand': f"{kontostand:.2f}".replace('.', ',') + " €",
        'kontostand_status': 'danger' if kontostand < 0 else 'success',
        'transaktionen': transaktionen,
        'letzte_aufladung': letzte_aufladung,
        'typeFilter': typ_filter,
        'transSearch': suchbegriff
    })



######################
### User - Tickets ###
######################

TICKET_ARTEN_PATH = os.path.join(BASE_DIR, 'ticket_arten.json')

def load_ticket_arten():
    if os.path.exists(TICKET_ARTEN_PATH):
        with open(TICKET_ARTEN_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def aktualisiere_ticket_status(user_data):
    heute = timezone.now().date()
    active_ticket_set = False
    tickets = user_data.get("tickets", [])
    neue_tickets = []

    for ticket in tickets:
        gültigkeit_str = ticket.get("gültigkeit")
        ticket_typ = ticket.get("typ", "").lower()
        status = "inaktiv"

        if ticket_typ == "einzelfahrt":
            neue_tickets.append(ticket)
            continue

        try:
            gültig_ab = datetime.strptime(gültigkeit_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            gültig_ab = None

        # Gültigkeitsdauer je nach Tickettyp
        gültig_bis = None
        if gültig_ab:
            if ticket_typ == "tageskarte":
                gültig_bis = gültig_ab + timedelta(days=1)
            elif ticket_typ == "wochenkarte":
                gültig_bis = gültig_ab + timedelta(weeks=1)
            elif ticket_typ == "monatskarte":
                gültig_bis = gültig_ab + timedelta(days=30)
            else:
                gültig_bis = gültig_ab  # Einzelfahrt oder unbekannt

        if gültig_bis and gültig_bis < heute:
            status = "abgelaufen"
        elif gültig_bis and not active_ticket_set:
            status = "aktiv"
            active_ticket_set = True

        ticket["status"] = status
        neue_tickets.append(ticket)

    user_data["tickets"] = neue_tickets
    return user_data



def ticket_kaufen(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, "Nicht eingeloggt.")
            return redirect('tickets')

        ticket_typ = request.POST.get('ticket_typ')
        gültig_ab = request.POST.get('gültig_ab')
        start = request.POST.get('start')
        ziel = request.POST.get('ziel')

        ticket_arten = load_ticket_arten()
        ticket_info = next((t for t in ticket_arten if t['typ'] == ticket_typ), None)
        if not ticket_info:
            messages.error(request, "Ungültiger Tickettyp.")
            return redirect('tickets')

        preis = float(ticket_info['preis'])

        if ticket_typ == 'Einzelfahrt' and (not start or not ziel):
            messages.error(request, "Bitte Start und Ziel angeben.")
            return redirect('tickets')

        ticketnummer = f"T{int(time.time())}"

        ticket = {
            "ticketnummer": ticketnummer,
            "typ": ticket_typ,
            "start": start if ticket_typ == 'Einzelfahrt' else None,
            "ziel": ziel if ticket_typ == 'Einzelfahrt' else None,
            "gültigkeit": gültig_ab,
            "preis": preis,
            "status": "aktiv"
        }

        user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
        if os.path.exists(user_file):
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)

            # Bezahlkarte prüfen
            kontostand = user_data.get("bezahlkarte", {}).get("kontostand", 0.0)
            if kontostand < preis:
                messages.error(request, "Nicht genügend Guthaben auf der Bezahlkarte.")
                return redirect('tickets')

            # Betrag abziehen und Transaktion speichern
            user_data["bezahlkarte"]["kontostand"] -= preis
            user_data["bezahlkarte"].setdefault("transaktionen", []).append({
                "datum": timezone.now().strftime("%d.%m.%Y"),
                "betrag": preis,
                "typ": "ausgabe",
                "beschreibung": f"{ticket_typ} gekauft"
            })

            # Ticket speichern
            user_data.setdefault("tickets", []).append(ticket)

            # Historie ergänzen
            user_data.setdefault("historie", []).append({
                "typ": "ticket_kauf",
                "zeitpunkt": timezone.now().isoformat(),
                "beschreibung": f"{ticket_typ} gekauft für {preis:.2f}€"
            })

            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=4, ensure_ascii=False)

            messages.success(request, f"{ticket_typ} erfolgreich gekauft.")

        return redirect('tickets')
    else:
        return redirect('tickets')

def ticket_loeschen(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, "Nicht eingeloggt.")
            return redirect('login')

        ticketnr = request.POST.get('ticketnr')

        user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
        if not os.path.exists(user_path):
            messages.error(request, "Benutzerdaten nicht gefunden.")
            return redirect('login')

        with open(user_path, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        tickets = user_data.get("tickets", [])
        ticket_to_delete = next((t for t in tickets if t.get("ticketnummer") == ticketnr), None)
        if not ticket_to_delete:
            messages.error(request, "Ticket nicht gefunden.")
            return redirect('tickets')  
        else:
            user_data["tickets"] = [t for t in tickets if t.get("ticketnummer") != ticketnr]

            user_data.setdefault("historie", []).append({
                "typ": "ticket_loeschen",
                "zeitpunkt": timezone.now().isoformat(),
                "beschreibung": f"{ticket_to_delete.get('typ', 'Unbekannt')} Ticket gelöscht"
            })

            with open(user_path, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=4, ensure_ascii=False)

            messages.success(request, "Ticket erfolgreich gelöscht.")

        return redirect('tickets')
    else:
        return redirect('tickets')

def tickets(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Bitte melde dich an.")
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        messages.error(request, "Benutzerdaten nicht gefunden.")
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user = json.load(f)
        rolle = user.get('rolle', '').lower()
        if rolle != 'user':
            messages.error(request, "Zugriff verweigert - User Account erforderlich.")
            return redirect('login')
    
    filter_typ = request.GET.get('filter', 'all').strip().lower()
    gekaufte_tickets = []
    aktuelles_ticket = None

    ticket_arten = []
    for art in load_ticket_arten():
        art['preis'] = f"{art['preis']:.2f}".replace('.', ',') + " €"
        ticket_arten.append(art)

    if user_id:
        user_file = os.path.join(USER_DATA_PATH, f"{user_id}.json")
        if os.path.exists(user_file):
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)

            # Ticket-Status aktualisieren
            user_data = aktualisiere_ticket_status(user_data)

            # Speichern nach Änderung
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=4, ensure_ascii=False)

            alle = []
            for ticket in user_data.get("tickets", []):
                ticket['preis'] = f"{ticket['preis']:.2f}".replace('.', ',') + " €"
                ticket_gültigkeit = datetime.strptime(ticket['gültigkeit'], "%Y-%m-%d")
                ticket['gültigkeit'] = ticket_gültigkeit.strftime("%d.%m.%Y")
                alle.append(ticket)

            kontostand = user_data.get("bezahlkarte", {}).get("kontostand", 0.0)

            for ticket in alle:
                if ticket.get("status") == "aktiv":
                    aktuelles_ticket = ticket
                    break

            if filter_typ != "all":
                gekaufte_tickets = [t for t in alle if t.get("typ", "").lower() == filter_typ]
            else:
                gekaufte_tickets = alle


    return render(request, 'burgerkarte/user/tickets.html', {
        'active': 'tickets',
        'tickets': gekaufte_tickets,
        'ticket_arten': ticket_arten,
        'aktuelles_ticket': aktuelles_ticket,
        'kontostand': f"{kontostand:.2f}".replace('.', ',') + " €",
        'kontostand_status': 'danger' if kontostand < 0 else 'success'
    })



########################
### User - historie ###
########################

def historie(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Bitte melde dich an.")
        return redirect('login')

    user_path = os.path.join(USER_DATA_PATH, f"{user_id}.json")
    if not os.path.exists(user_path):
        messages.error(request, "Benutzerdaten nicht gefunden.")
        return redirect('login')

    with open(user_path, 'r', encoding='utf-8') as f:
        user_data = json.load(f)
        rolle = user_data.get('rolle', '').lower()
        if rolle != 'user':
            messages.error(request, "Zugriff verweigert - User Account erforderlich.")
            return redirect('login')
        
    history = user_data.get("historie", [])

        
    suchbegriff = request.GET.get("search", "").strip().lower()

    # Katalog-Filter
    if suchbegriff:
        history = [h for h in history if suchbegriff in h.get("beschreibung", "").lower()]

    for h in history:
        h['datum'] = datetime.fromisoformat(h['zeitpunkt']).strftime("%d.%m.%Y")
        h['zeit'] = datetime.fromisoformat(h['zeitpunkt']).strftime("%H:%M")

    history.reverse()
    
    return render(request, 'burgerkarte/user/historie.html', {
        'aktivitaeten': history,
        'search_term': suchbegriff
    })