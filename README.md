[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/qT0oNHQU)
# Flask CRM System

## Setup

1. `python -m venv venv`
2. `source venv/bin/activate`
3. `pip install -r requirements.txt`
4. `python app.py`
5. Visit http://127.0.0.1:5000

## Datenbank und Migrationen
### Voraussetzungen
- Python 3.8+
- Virtuelle Umgebung (empfohlen)
- SQLite (wird automatisch mit Python installiert)

### Einrichtung der Datenbank
1. **Virtuelle Umgebung aktivieren:**
   ```bash
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows

### Migrationen initialisieren (nur beim ersten Mal): 
flask db init
### Erste Migration erstellen: 
flask db migrate -m "Initial migration"
### Migration anwenden, um die Datenbank zu erstellen: 
flask db upgrade
### Testdaten einfügen:
python -c "from app import init_sample_data; init_sample_data()"
### Migrationen durchführen (bei Änderungen an den Modellen)
flask db migrate -m "Beschreibung der Änderungen"
flask db upgrade

## Wichtige Hinweise
Die Datenbankdatei (crm.db) wird automatisch im Projektverzeichnis erstellt.
Migrationen ermöglichen kontrollierte Änderungen an der Datenbankstruktur.
