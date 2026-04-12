from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from werkzeug.security import check_password_hash
from models import db, Customer, Lead, User
from api.routes import api_bp
from api.external.adress_validator import AdressValidator
import logging
import sys

# --- App erstellen und Grundkonfiguration ---
"""
Erstellt die Flask-Anwendung und konfiguriert grundlegende Einstellungen.
"""
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Geheimschlüssel für Sessions und CSRF-Schutz
CORS(app)  # CORS (Cross-Origin Resource Sharing) für alle Routen aktivieren

# --- Logging-Konfiguration ---
"""
Konfiguriert das Logging-System, um Debug-Informationen in die Konsole zu schreiben.
"""
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)  # Logger-Instanz für diese Anwendung

# --- Datenbankkonfiguration ---
"""
Konfiguriert die Datenbankverbindung und initialisiert SQLAlchemy.
"""
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'  # SQLite-Datenbankdatei
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Deaktiviert das Tracking von Änderungen (Performance-Optimierung)
db.init_app(app)  # Initialisiert SQLAlchemy mit der Flask-Anwendung

# --- Flask-Erweiterungen initialisieren ---
"""
Initialisiert Flask-Erweiterungen wie Migrate für Datenbankmigrationen und LoginManager für Benutzerauthentifizierung.
"""
migrate = Migrate(app, db)  # Initialisiert Flask-Migrate für Datenbankmigrationen
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Route, die für nicht angemeldete Benutzer aufgerufen wird

# --- Login-Manager Konfiguration ---
@login_manager.user_loader
def load_user(user_id):
    """
    Lädt einen Benutzer für Flask-Login.

    Args:
        user_id (str): Die Benutzer-ID aus der Session

    Returns:
        User: Das Benutzerobjekt oder None, wenn der Benutzer nicht gefunden wird
    """
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Fehler beim Laden des Benutzers: {e}")
        return None

# --- Testdaten initialisieren ---
def init_sample_data():
    """
    Fügt Beispieldaten in die Datenbank ein, falls diese leer ist.
    Erstellt einen Beispielkunden und einen Beispiel-Lead mit validierten Adressen.
    """
    try:
        with app.app_context():
            validator = AdressValidator()
            if not Customer.query.first():
                # Beispielkunden mit validierter Adresse erstellen
                validation_result = validator.validate_adress('Opernring 1', '1010', 'Wien', 'Österreich')

                customer1 = Customer(
                    name='John Doe',
                    email='john@example.com',
                    company='Acme Corp',
                    phone='555-0001',
                    status='active',
                    street='Opernring 1',
                    postal_code='1010',
                    city='Wien',
                    country='Österreich',
                    lat=validation_result['lat'],
                    lng=validation_result['lng']
                )
                db.session.add(customer1)

                # Beispiel-Lead mit validierter Adresse erstellen
                validation_result = validator.validate_adress('Hauptstraße 1', '1010', 'Wien', 'Österreich')
                lead1 = Lead(
                    name='Jane Smith',
                    email='jane@example.com',
                    company='Tech Solutions',
                    value=1000,
                    source='Website',
                    customer_id=customer1.id,
                    street='Hauptstraße 1',
                    postal_code='1010',
                    city='Wien',
                    country='Österreich',
                    lat=validation_result['lat'],
                    lng=validation_result['lng']
                )
                db.session.add(lead1)
                db.session.commit()
                logger.info("Beispieldaten wurden eingefügt.")
    except Exception as e:
        logger.error(f"Fehler beim Einfügen der Beispieldaten: {e}")
        db.session.rollback()  # Rollback bei Fehlern

def init_user_data():
    """
    Erstellt einen Test-Benutzer, falls noch keiner existiert.
    Benutzername: 'test', Passwort: 'test'
    """
    try:
        with app.app_context():
            if not User.query.first():
                admin = User(username='test')
                admin.set_password('test')
                db.session.add(admin)
                db.session.commit()
                logger.info("Test-Benutzer 'test' mit Passwort 'test' angelegt!")
    except Exception as e:
        logger.error(f"Fehler beim Anlegen des Test-Benutzers: {e}")
        db.session.rollback()

# --- API-Routen registrieren ---
"""
Registriert den API-Blueprint unter dem Präfix '/api'.
Alle API-Routen sind unter diesem Präfix erreichbar.
"""
app.register_blueprint(api_bp, url_prefix="/api")

# --- API-spezifische Fehlerhandler ---
@api_bp.errorhandler(404)
def api_not_found(error):
    """
    Behandelt 404-Fehler (Nicht gefunden) für API-Routen.

    Args:
        error: Der aufgetretene Fehler

    Returns:
        JSON: Fehlermeldung mit Statuscode 404
    """
    logger.error(f"404 Fehler: {error}")
    return jsonify({"error": "Endpoint nicht gefunden"}), 404

@api_bp.errorhandler(500)
def api_internal_error(error):
    """
    Behandelt 500-Fehler (Interner Serverfehler) für API-Routen.

    Args:
        error: Der aufgetretene Fehler

    Returns:
        JSON: Fehlermeldung mit Statuscode 500
    """
    logger.error(f"500 Fehler: {error}")
    return jsonify({"error": "Interner Serverfehler"}), 500

# --- Globale Fehlerhandler ---
@app.errorhandler(404)
def page_not_found(error):
    """
    Behandelt 404-Fehler (Nicht gefunden) für die gesamte Anwendung.

    Args:
        error: Der aufgetretene Fehler

    Returns:
        Template: 404-Fehlerseite
    """
    logger.error(f"404 Fehler: {error}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """
    Behandelt 500-Fehler (Interner Serverfehler) für die gesamte Anwendung.

    Args:
        error: Der aufgetretene Fehler

    Returns:
        Template: 500-Fehlerseite
    """
    logger.error(f"500 Fehler: {error}")
    return render_template('500.html'), 500

# --- Startseite ---
@app.route('/')
@login_required  # Stelle sicher, dass nur angemeldete Benutzer die Startseite sehen
def index():
    """Zeigt die Startseite mit Statistiken und den neuesten Einträgen an."""
    try:
        total_customers = len(Customer.query.all())
        total_leads = len(Lead.query.all())

        # Hole die 5 neuesten Kunden und Leads, sortiert nach Erstellungsdatum
        newest_customers = Customer.query.order_by(Customer.created_at.desc()).limit(5).all()
        newest_leads = Lead.query.order_by(Lead.created_at.desc()).limit(5).all()

        return render_template(
            'index.html',
            total_customers=total_customers,
            total_leads=total_leads,
            newest_customers=newest_customers,
            newest_leads=newest_leads
        )
    except Exception as e:
        logger.error(f"Fehler in der Index-Route: {e}")
        return render_template('500.html'), 500

# --- Kunden-Route ---
@app.route('/customers')
@login_required
def customers():
    """
    Zeigt alle Kunden an. Erfordert angemeldeten Benutzer.

    Returns:
        Template: Liste aller Kunden
    """
    try:
        customers_list = Customer.query.all()
        return render_template('customers.html', customers=customers_list)
    except Exception as e:
        logger.error(f"Fehler in der Customers-Route: {e}")
        return render_template('500.html'), 500

# Add Customer Route
@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    """
    Route zum Hinzufügen eines neuen Kunden.
    GET: Zeigt das Formular an.
    POST: Verarbeitet das Formular und speichert den Kunden mit validierter Adresse.

    Returns:
        Template: Formular zum Hinzufügen eines Kunden oder Redirect zur Kundenliste
    """
    validator = AdressValidator()

    if request.method == 'POST':
        # Formulardaten abrufen
        name = request.form.get('name')
        email = request.form.get('email')
        company = request.form.get('company')
        phone = request.form.get('phone')
        status = request.form.get('status', 'prospect')
        street = request.form.get('street')
        postal_code = request.form.get('postal_code')
        city = request.form.get('city')
        country = request.form.get('country')

        # Adressvalidierung
        validation_result = validator.validate_adress(street, postal_code, city, country)
        if not validation_result:
            flash('Adresse konnte nicht validiert werden. Bitte überprüfe die Angaben.', 'error')
            return render_template('add_customer.html',
                                   name=name, email=email, company=company, phone=phone,
                                   status=status, street=street, postal_code=postal_code,
                                   city=city, country=country)

        # Neuen Kunden erstellen und speichern
        new_customer = Customer(
            name=name,
            email=email,
            company=company,
            phone=phone,
            status=status,
            street=street,
            postal_code=postal_code,
            city=city,
            country=country,
            lat=validation_result['lat'],
            lng=validation_result['lng']
        )
        db.session.add(new_customer)
        db.session.commit()

        flash('Kunde erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('customers'))

    # Formular anzeigen
    return render_template('add_customer.html')

# Customer Detail Route
@app.route('/customers/<int:customer_id>')
@login_required
def customer_detail(customer_id):
    """
    Zeigt die Details eines bestimmten Kunden an.

    Args:
        customer_id (int): ID des Kunden

    Returns:
        Template: Detailansicht des Kunden
    """
    customer = Customer.query.get_or_404(customer_id)
    return render_template('customer_detail.html', customer=customer)

# Edit Customer Route
@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    """
    Route zum Bearbeiten eines Kunden.
    GET: Zeigt das Bearbeitungsformular an.
    POST: Verarbeitet das Formular und aktualisiert den Kunden mit validierter Adresse.

    Args:
        customer_id (int): ID des zu bearbeitenden Kunden

    Returns:
        Template: Bearbeitungsformular oder Redirect zur Kundendetailansicht
    """
    customer = Customer.query.get_or_404(customer_id)
    validator = AdressValidator()

    if request.method == 'POST':
        # Formulardaten abrufen und Kunden aktualisieren
        customer.name = request.form.get('name')
        customer.email = request.form.get('email')
        customer.company = request.form.get('company')
        customer.phone = request.form.get('phone')
        customer.status = request.form.get('status', 'prospect')
        street = request.form.get('street')
        postal_code = request.form.get('postal_code')
        city = request.form.get('city')
        country = request.form.get('country')

        # Adressvalidierung
        validation_result = validator.validate_adress(street, postal_code, city, country)
        if not validation_result:
            flash('Adresse konnte nicht validiert werden. Bitte überprüfe die Angaben.', 'error')
            return render_template('edit_customer.html', customer=customer)

        # Adressdaten aktualisieren
        customer.street = street
        customer.postal_code = postal_code
        customer.city = city
        customer.country = country
        customer.lat = validation_result['lat']
        customer.lng = validation_result['lng']

        db.session.commit()
        flash('Kunde erfolgreich aktualisiert!', 'success')
        return redirect(url_for('customer_detail', customer_id=customer.id))

    # Bearbeitungsformular anzeigen
    return render_template('edit_customer.html', customer=customer)

# Delete Customer Route
@app.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
def delete_customer(customer_id):
    """
    Löscht einen Kunden aus der Datenbank.

    Args:
        customer_id (int): ID des zu löschenden Kunden

    Returns:
        Redirect: Zur Kundenliste mit Erfolgsmeldung
    """
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()

    flash('Kunde erfolgreich gelöscht!', 'success')
    return redirect(url_for('customers'))

# --- Leads-Route ---
@app.route('/leads')
@login_required
def leads():
    """
    Zeigt alle Leads an. Erfordert angemeldeten Benutzer.

    Returns:
        Template: Liste aller Leads
    """
    try:
        leads_list = Lead.query.all()
        return render_template('leads.html', leads=leads_list)
    except Exception as e:
        logger.error(f"Fehler in der Leads-Route: {e}")
        return render_template('500.html'), 500

@app.route('/leads/add', methods=['GET', 'POST'])
@login_required
def add_lead():
    """
    Route zum Hinzufügen eines neuen Leads.
    GET: Zeigt das Formular an.
    POST: Verarbeitet das Formular und speichert den Lead mit validierter Adresse.

    Returns:
        Template: Formular zum Hinzufügen eines Leads oder Redirect zur Lead-Liste
    """
    if request.method == 'POST':
        # Formulardaten abrufen
        name = request.form.get('name')
        email = request.form.get('email')
        company = request.form.get('company')
        value = request.form.get('value')
        source = request.form.get('source')
        customer_id = request.form.get('customer_id')
        street = request.form.get('street')
        postal_code = request.form.get('postal_code')
        city = request.form.get('city')
        country = request.form.get('country')

        # Adressvalidierung
        validator = AdressValidator()
        validation_result = validator.validate_adress(street, postal_code, city, country)

        if validation_result:
            # Lead mit validierten Koordinaten erstellen
            new_lead = Lead(
                name=name,
                email=email,
                company=company,
                value=value,
                source=source,
                customer_id=customer_id,
                street=street,
                postal_code=postal_code,
                city=city,
                country=country,
                lat=validation_result['lat'],
                lng=validation_result['lng']
            )
        else:
            # Lead ohne Koordinaten erstellen
            new_lead = Lead(
                name=name,
                email=email,
                company=company,
                value=value,
                source=source,
                customer_id=customer_id,
                street=street,
                postal_code=postal_code,
                city=city,
                country=country
            )

        db.session.add(new_lead)
        db.session.commit()

        flash('Lead erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('leads'))

    # Formular anzeigen
    customers = Customer.query.all()
    return render_template('add_lead.html', customers=customers)

@app.route('/leads/<int:lead_id>')
@login_required
def lead_detail(lead_id):
    """
    Zeigt die Details eines bestimmten Leads an.

    Args:
        lead_id (int): ID des Leads

    Returns:
        Template: Detailansicht des Leads
    """
    lead = Lead.query.get_or_404(lead_id)
    return render_template('lead_detail.html', lead=lead)

@app.route('/leads/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lead(lead_id):
    """
    Route zum Bearbeiten eines Leads.
    GET: Zeigt das Bearbeitungsformular an.
    POST: Verarbeitet das Formular und aktualisiert den Lead mit validierter Adresse.

    Args:
        lead_id (int): ID des zu bearbeitenden Leads

    Returns:
        Template: Bearbeitungsformular oder Redirect zur Lead-Detailansicht
    """
    lead = Lead.query.get_or_404(lead_id)
    validator = AdressValidator()

    if request.method == 'POST':
        # Formulardaten abrufen
        lead.name = request.form.get('name')
        lead.email = request.form.get('email')
        lead.company = request.form.get('company')
        lead.value = request.form.get('value')
        lead.source = request.form.get('source')
        lead.customer_id = request.form.get('customer_id')
        street = request.form.get('street')
        postal_code = request.form.get('postal_code')
        city = request.form.get('city')
        country = request.form.get('country')

        # Adressvalidierung
        validation_result = validator.validate_adress(street, postal_code, city, country)

        # Adressdaten aktualisieren
        lead.street = street
        lead.postal_code = postal_code
        lead.city = city
        lead.country = country

        if validation_result:
            lead.lat = validation_result['lat']
            lead.lng = validation_result['lng']

        db.session.commit()
        flash('Lead erfolgreich aktualisiert!', 'success')
        return redirect(url_for('lead_detail', lead_id=lead.id))

    # Bearbeitungsformular anzeigen
    customers = Customer.query.all()
    return render_template('edit_lead.html', lead=lead, customers=customers)

@app.route('/leads/<int:lead_id>/delete', methods=['POST'])
@login_required
def delete_lead(lead_id):
    """
    Route zum Löschen eines Leads.

    Args:
        lead_id (int): ID des zu löschenden Leads

    Returns:
        Redirect: Zur Lead-Liste mit Erfolgsmeldung
    """
    lead = Lead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()

    flash('Lead erfolgreich gelöscht!', 'success')
    return redirect(url_for('leads'))

# --- Login-Routen ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login-Seite.
    GET: Zeigt das Login-Formular an.
    POST: Verarbeitet das Login-Formular und authentifiziert den Benutzer.

    Returns:
        Template: Login-Formular oder Redirect zur Startseite bei Erfolg
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Erfolgreich eingeloggt!', 'success')
            return redirect(url_for('index'))
        flash('Ungültiger Benutzername oder Passwort.', 'error')
    return render_template('login.html')

# --- Register-Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registrierungsseite.
    GET: Zeigt das Registrierungsformular an.
    POST: Verarbeitet das Registrierungsformular und erstellt einen neuen Benutzer.

    Returns:
        Template: Registrierungsformular oder Redirect zur Login-Seite bei Erfolg
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        # Passwortbestätigung prüfen
        if password != password_confirm:
            flash('Passwörter stimmen nicht überein!', 'error')
            return redirect(url_for('register'))

        # Benutzernamen auf Eindeutigkeit prüfen
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben!', 'error')
            return redirect(url_for('register'))

        # Neuen Benutzer erstellen
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registrierung erfolgreich! Bitte logge dich ein.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# --- Logout-Route ---
@app.route('/logout')
@login_required
def logout():
    """
    Logout-Seite. Beendet die Benutzersitzung.

    Returns:
        Redirect: Zur Startseite mit Erfolgsmeldung
    """
    logout_user()
    flash('Erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('index'))

# --- API-Endpoint für Adressvalidierung ---
@app.route('/api/validate_address', methods=['POST'])
def validate_address():
    """
    API-Endpoint zur Validierung einer Adresse.

    Erwartet ein JSON-Objekt mit den Adressdaten (street, postal_code, city, country).
    Validiert die Adresse mit dem AdressValidator und gibt die Koordinaten zurück.

    Returns:
        JSON: Erfolgstatus, Koordinaten und Nachricht
    """
    data = request.get_json()
    street = data.get('street')
    postal_code = data.get('postal_code')
    city = data.get('city')
    country = data.get('country')

    # Überprüfen, ob alle Adressfelder vorhanden sind
    if not all([street, postal_code, city, country]):
        return jsonify({
            'success': False,
            'message': 'Alle Adressfelder sind erforderlich.'
        }), 400

    # Adresse validieren
    validator = AdressValidator()
    validation_result = validator.validate_adress(street, postal_code, city, country)

    if validation_result:
        # Erfolgreiche Validierung
        return jsonify({
            'success': True,
            'lat': validation_result['lat'],
            'lng': validation_result['lng'],
            'message': 'Adresse erfolgreich validiert.'
        })
    else:
        # Validierung fehlgeschlagen
        return jsonify({
            'success': False,
            'message': 'Adresse konnte nicht validiert werden.'
        }), 400

# --- Euro Währung ---
@app.template_filter('euro')
def euro_format(value):
    """
    Formatiert einen numerischen Wert im europäischen Format mit Euro-Symbol.
    Beispiel: 1234.56 wird zu "1.234,56 €"
    """
    if value is None:
        return ""
    try:
        value = float(value)
        return " {:,.2f} €".format(value).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value
    
# --- Anwendung starten ---
if __name__ == '__main__':
    """
    Startet die Flask-Anwendung.
    Initialisiert die Datenbank und fügt Testdaten hinzu, falls erforderlich.
    """
    try:
        with app.app_context():
            db.create_all()  # Erstellt alle Datenbanktabellen
            init_sample_data()  # Fügt Beispieldaten hinzu
            init_user_data()  # Erstellt einen Testbenutzer
        app.run(debug=True, host='127.0.0.1', port=5000)  # Startet den Entwicklungsserver
    except Exception as e:
        logger.error(f"Fehler beim Starten der Anwendung: {e}")