[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/qT0oNHQU)

# CRM-System mit Adressvalidierung und Kartenintegration

1. `python -m venv venv`
2. `source venv/Scripts/activate`
3. `pip install -r requirements.txt`
4. `python app.py`
5. Visit http://127.0.0.1:5000

---

## 📋 Inhaltsverzeichnis
- [Setup](#setup)
- [Datenbank und Migrationen](#datenbank-und-migrationen)
- [Funktionen](#funktionen)
- [Projektstruktur](#projektstruktur)
- [Abhängigkeiten](#abhängigkeiten)
- [Wichtige Hinweise](#wichtige-hinweise)
- [Fehlerbehebung](#fehlerbehebung)

---

## Setup
### Voraussetzungen
- Python 3.8+
- Virtuelle Umgebung (empfohlen)
- SQLite (wird automatisch mit Python installiert)

## Installation
1. **Virtuelle Umgebung erstellen und aktivieren:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Anwendung starten:**
   ```bash
   python app.py
   ```

Die Anwendung ist dann unter http://127.0.0.1:5000 erreichbar.

---

## Datenbank und Migrationen
### Einrichtung der Datenbank
1. **Migrationen initialisieren (nur beim ersten Mal):**
   ```bash
   flask db init
   ```

2. **Erste Migration erstellen:**
   ```bash
   flask db migrate -m "Initial migration"
   ```

3. **Migration anwenden, um die Datenbank zu erstellen:**
   ```bash
   flask db upgrade
   ```

4. **(Optional) Testdaten einfügen:**
   ```bash
   python -c "from app import init_sample_data; init_sample_data()"
   ```

5. **(Optional) Test-Benutzer anlegen:**
   ```bash
   python -c "from app import init_user_data; init_user_data()"
   ```

## Migrationen bei Änderungen an Modellen
Falls Änderungen an den Datenbankmodellen (models.py) vorgenommen werden
### Migration:
   ```bash
   flask db migrate -m "Beschreibung der Änderungen"
   flask db upgrade
   ```

### Datenbank zurücksetzen
Falls die Datenbank komplett zurückgesetzt werden soll:
   ```bash
   rm crm.db
   flask db upgrade
   ```

## Funktionen

### Adressvalidierung
- Validierung von Adressen über die **Nominatim-API** von OpenStreetMap.
- Automatische Speicherung der Koordinaten (Latitude, Longitude) für Kunden und Leads.

### Kartenintegration
- Interaktive Kartenansicht mit **Leaflet.js** für Kunden- und Lead-Standorte.
- Marker mit Popups zeigen die Adressinformationen an.
- Link zur externen Kartenansicht (OpenStreetMap).

### Benutzerverwaltung
- Registrierung und Anmeldung von Benutzern.
- Schutz von Routen mit `@login_required`.

### Benutzerrollen
- Rollenbasierte Zugriffskontrolle (Rolle User und Admin)
- Admin Dashboard
- Rollen ändern

### Weitere Funktionen
- Übersichtliche Darstellung von Kunden und Leads.
- Bearbeitung und Löschung von Einträgen.
- Filter- und Suchfunktionen (können noch implementiert werden).

## Projektstruktur
```
crm_erweiterung/
├── api/
│   ├── external/
│   │   └── adress_validator.py  # Adressvalidierung mit Nominatim-API
│   └── routes.py                 # API-Routen
├── migrations/                  # Datenbankmigrationen
├── static/                      # Statische Dateien (CSS, JS)
├── templates/
│   ├── auth/                    # Authentifizierungs-Templates
│   │   ├── login.html
│   │   └── register.html
│   ├── admin/                   # Admin-Templates
│   │   └── admin_dashboard.html # Admin-Dashboard
│   ├── customers/               # Kunden-Templates
│   ├── leads/                   # Lead-Templates
│   └── base.html                # Basis-Template
├── app.py                       # Hauptanwendung
├── models.py                    # Datenbankmodelle
├── requirements.txt             # Abhängigkeiten
└── README.md                    # Diese Datei
```
## Abhängigkeiten
```bash
	pip install -r requirements.txt
```
___

## Wichtige Hinweise

Die Datenbankdatei (crm.db) wird automatisch im Projektverzeichnis erstellt.
Migrationen ermöglichen kontrollierte Änderungen an der Datenbankstruktur.
Die Adressvalidierung benötigt eine Internetverbindung, um die Nominatim-API von OpenStreetMap zu erreichen.
Die Kartenansicht verwendet Leaflet.js und OpenStreetMap-Kacheln.
Standardmäßig haben neue Benutzer die Rolle user.
Nur Benutzer mit der Rolle admin haben Zugriff auf das Admin-Dashboard.

___

## Fehlerbehebung
### Datenbankfehler:
Wurde die Datenmigrationen korrekt durchgeführt?
Löschen der Datenbankdatei (crm.db) und Migrationen erneut durchführen.

### Adressvalidierung schlägt fehl:
Überprüfe die Internetverbindung.
Stellen Sie sicher, dass die Adressdaten korrekt sind.

### Karte wird nicht angezeigt:
Überprüfe, ob Leaflet.js korrekt geladen wird (siehe Browser-Konsole).
Stellen Sie sicher, dass die Koordinaten (lat, lng) für den Kunden/Lead vorhanden sind.

### Zugriff verweigert (403 Fehler)
Stelle sicher, dass du als Admin angemeldet bist, um auf das Admin-Dashboard zuzugreifen.
Überprüfe, ob die Rolle des Benutzers korrekt in der Datenbank gespeichert ist.

