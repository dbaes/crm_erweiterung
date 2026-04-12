from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, send_from_directory
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from werkzeug.security import check_password_hash
from models import db, Customer, Lead, User
from api.routes import api_bp
from api.external.adress_validator import AdressValidator
from flask_swagger_ui import get_swaggerui_blueprint
import logging
import sys
from functools import wraps

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

# --- Swagger-UI-Konfiguration ---
SWAGGER_URL = '/api/docs'  # URL, unter der die Swagger-UI erreichbar ist
API_URL = '/api/swagger'   # URL, unter der die OpenAPI-Spezifikation bereitgestellt wird
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "CRM API"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# --- Endpoint für die OpenAPI-Spezifikation ---
@app.route('/api/swagger')
def swagger_spec():
    """
    Stellt die OpenAPI-Spezifikation als JSON bereit.
    """
    return send_from_directory('api/swagger', 'swagger_template.yaml')

@app.route('/api/docs')
def swagger_ui():
    """
    Zeigt die Swagger-UI für die API-Dokumentation an.
    """
    return redirect('/api/docs/')  # Weiterleitung zur Swagger-UI

# --- Rest deiner bestehenden app.py ---
# (Alle bestehenden Funktionen, Routen und Konfigurationen bleiben unverändert!)
# ...
# --- Anwendung starten ---
if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
            init_sample_data()
            init_user_data()
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception as e:
        logger.error(f"Fehler beim Starten der Anwendung: {e}")
        import traceback
        traceback.print_exc()

# --- Dekorator für Admin-Berechtigung ---
def admin_required(f):
    """
    Dekorator, um sicherzustellen, dass nur Admins auf die Route zugreifen können.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != "admin":
            logger.warning(f"Zugriff verweigert: Benutzer {current_user.username} (Rolle: {current_user.role}) versuchte auf Admin-Route {request.path} zuzugreifen.")
            abort(403)  # HTTP 403 Forbidden
        return f(*args, **kwargs)
    return decorated_function

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
    Erstellt drei Beispielkunden und drei Beispiel-Leads aus Österreich, Deutschland und der Schweiz.
    """
    try:
        print("Starte init_sample_data()...")
        with app.app_context():
            validator = AdressValidator()
            if not Customer.query.first():
                print("Keine Kunden gefunden. Erstelle Beispieldaten...")

                # Beispielkunden aus Österreich, Deutschland und der Schweiz
                customers_data = [
					{
						'name': 'Max Mustermann',
						'email': 'max@example.com',
						'company': 'Alpen GmbH',
						'phone': '555-1001',
						'street': 'Mariahilfer Straße 81',
						'postal_code': '1060',
						'city': 'Wien',
						'country': 'Österreich',
						'default_lat': 48.2010,
						'default_lng': 16.3550
					},
					{
						'name': 'Anna Schmidt',
						'email': 'anna@example.com',
						'company': 'Rhein AG',
						'phone': '555-1002',
						'street': 'Königsallee 60',
						'postal_code': '40212',
						'city': 'Düsseldorf',
						'country': 'Deutschland',
						'default_lat': 51.2254,
						'default_lng': 6.7763
					},
					{
						'name': 'Marc Weber',
						'email': 'marc@example.com',
						'company': 'Alpenblick Ltd.',
						'phone': '555-1003',
						'street': 'Rämistrasse 7',
						'postal_code': '8001',
						'city': 'Zürich',
						'country': 'Schweiz',
						'default_lat': 47.3760,
						'default_lng': 8.5480
					}
				]

                customers = []
                for data in customers_data:
                    print(f"Validiere Adresse für {data['name']}...")
                    validation_result = validator.validate_adress(
                        data['street'],
                        data['postal_code'],
                        data['city'],
                        data['country']
                    )
                    if not validation_result:
                        print(f"Adressvalidierung für {data['name']} fehlgeschlagen! Verwende Standardkoordinaten.")
                        validation_result = {'lat': data['default_lat'], 'lng': data['default_lng']}

                    print(f"Erstelle Beispielkunde {data['name']}...")
                    customer = Customer(
                        name=data['name'],
                        email=data['email'],
                        company=data['company'],
                        phone=data['phone'],
                        status='active',
                        street=data['street'],
                        postal_code=data['postal_code'],
                        city=data['city'],
                        country=data['country'],
                        lat=validation_result['lat'],
                        lng=validation_result['lng']
                    )
                    db.session.add(customer)
                    customers.append(customer)
                    print(f"Beispielkunde {data['name']} erstellt.")

                db.session.commit()
                print("Beispielkunden erfolgreich in die Datenbank geschrieben!")

                # Beispiel-Leads für die erstellten Kunden
                leads_data = [
                    {
                        'name': 'Österreichische Firma',
                        'email': 'lead_at@example.com',
                        'company': 'Quaxi',
                        'value': 1000,
                        'source': 'Website',
                        'street': 'Mariahilfer Straße 30',
                        'postal_code': '1070',
                        'city': 'Wien',
                        'country': 'Österreich',
                        'default_lat': 48.2018,
                        'default_lng': 16.3656,
                        'customer_index': 0
                    },
                    {
                        'name': 'Deutsche Firma',
                        'email': 'lead_de@example.com',
                        'company': 'Linden',
                        'value': 1500,
                        'source': 'Empfehlung',
                        'street': 'Unter den Linden 1',
                        'postal_code': '10117',
                        'city': 'Berlin',
                        'country': 'Deutschland',
                        'default_lat': 52.5173,
                        'default_lng': 13.3899,
                        'customer_index': 1
                    },
                    {
                        'name': 'Schweizer Firma',
                        'email': 'lead_ch@example.com',
                        'company': 'Ricola',
                        'value': 2000,
                        'source': 'Messe',
                        'street': 'Limmatquai 1',
                        'postal_code': '8001',
                        'city': 'Zürich',
                        'country': 'Schweiz',
                        'default_lat': 47.3789,
                        'default_lng': 8.5382,
                        'customer_index': 2
                    }
                ]

                for data in leads_data:
                    print(f"Validiere Adresse für Lead {data['name']}...")
                    validation_result = validator.validate_adress(
                        data['street'],
                        data['postal_code'],
                        data['city'],
                        data['country']
                    )
                    if not validation_result:
                        print(f"Adressvalidierung für Lead {data['name']} fehlgeschlagen! Verwende Standardkoordinaten.")
                        validation_result = {'lat': data['default_lat'], 'lng': data['default_lng']}

                    print(f"Erstelle Beispiel-Lead {data['name']}...")
                    lead = Lead(
                        name=data['name'],
                        email=data['email'],
                        company=data['company'],
                        value=data['value'],
                        source=data['source'],
                        customer_id=customers[data['customer_index']].id,
                        street=data['street'],
                        postal_code=data['postal_code'],
                        city=data['city'],
                        country=data['country'],
                        lat=validation_result['lat'],
                        lng=validation_result['lng']
                    )
                    db.session.add(lead)
                    print(f"Beispiel-Lead {data['name']} erstellt.")

                db.session.commit()
                print("Beispiel-Leads erfolgreich in die Datenbank geschrieben!")
            else:
                print("Kunden existieren bereits. Keine neuen Beispieldaten angelegt.")
    except Exception as e:
        print(f"Fehler beim Einfügen der Beispieldaten: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()

def init_user_data():
    """
    Erstellt einen Test-Benutzer und einen Admin-Benutzer, falls noch keine existieren.
    Benutzername: 'user', Passwort: 'user' (Rolle: user)
    Benutzername: 'admin', Passwort: 'admin' (Rolle: admin)
    """
    try:
        print("Starte init_user_data()...")
        with app.app_context():
            print("App-Kontext aktiv.")
            if not User.query.first():
                print("Keine Benutzer gefunden. Erstelle Test-Benutzer...")

                # Standardbenutzer
                user = User(username='test', role='user')
                user.set_password('test')
                db.session.add(user)
                print(f"Benutzer 'test' mit Rolle 'user' erstellt.")

                # Admin-Benutzer
                admin = User(username='admin', role='admin')
                admin.set_password('admin')
                db.session.add(admin)
                print(f"Benutzer 'admin' mit Rolle 'admin' erstellt.")

                db.session.commit()
                print("Test-Benutzer erfolgreich angelegt und in die Datenbank geschrieben!")
            else:
                print("Benutzer existieren bereits. Keine neuen Benutzer angelegt.")
    except Exception as e:
        print(f"Fehler beim Anlegen der Test-Benutzer: {e}")
        import traceback
        traceback.print_exc()
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
    """
    logger.error(f"404 Fehler: {error}")
    return jsonify({"error": "Endpoint nicht gefunden"}), 404

@api_bp.errorhandler(500)
def api_internal_error(error):
    """
    Behandelt 500-Fehler (Interner Serverfehler) für API-Routen.
    """
    logger.error(f"500 Fehler: {error}")
    return jsonify({"error": "Interner Serverfehler"}), 500

# --- Globale Fehlerhandler ---
@app.errorhandler(403)
def forbidden(error):
    """
    Behandelt 403-Fehler (Zugriff verweigert).
    """
    logger.warning(f"403 Fehler: {error}")
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(error):
    """
    Behandelt 404-Fehler (Nicht gefunden) für die gesamte Anwendung.
    """
    logger.error(f"404 Fehler: {error}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """
    Behandelt 500-Fehler (Interner Serverfehler) für die gesamte Anwendung.
    """
    logger.error(f"500 Fehler: {error}")
    return render_template('500.html'), 500

# --- Startseite ---
@app.route('/')
@login_required
def index():
    """Zeigt die Startseite mit Statistiken und den neuesten Einträgen an."""
    try:
        total_customers = len(Customer.query.all())
        total_leads = len(Lead.query.all())

        # Hole alle Kunden und Leads für die Karte
        customers = Customer.query.all()
        leads = Lead.query.all()

        # Hole die 5 neuesten Kunden und Leads, sortiert nach Erstellungsdatum
        newest_customers = Customer.query.order_by(Customer.created_at.desc()).limit(5).all()
        newest_leads = Lead.query.order_by(Lead.created_at.desc()).limit(5).all()

        return render_template(
            'index.html',
            total_customers=total_customers,
            total_leads=total_leads,
            customers=customers,
            leads=leads,
            newest_customers=newest_customers,
            newest_leads=newest_leads
        )
    except Exception as e:
        logger.error(f"Fehler in der Index-Route: {e}")
        return render_template('500.html'), 500

# --- Admin-Dashboard ---
@app.route('/admin')
@admin_required  # Nur Admins
def admin_dashboard():
    """
    Zeigt das Admin-Dashboard mit Benutzerverwaltung an.
    """
    try:
        users = User.query.all()
        return render_template('admin_dashboard.html', users=users)
    except Exception as e:
        logger.error(f"Fehler im Admin-Dashboard: {e}")
        return render_template('500.html'), 500

# --- Benutzerrolle aktualisieren ---
@app.route('/admin/users/<int:user_id>/update_role', methods=['POST'])
@admin_required  # Nur Admins
def update_user_role(user_id):
    """
    Aktualisiert die Rolle eines Benutzers (nur für Admins).
    """
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')

    if new_role not in ['admin', 'user']:
        flash('Ungültige Rolle! Nur "admin" oder "user" erlaubt.', 'error')
        return redirect(url_for('admin_dashboard'))

    user.role = new_role
    db.session.commit()
    flash(f'Rolle von {user.username} zu {user.role} geändert!', 'success')
    return redirect(url_for('admin_dashboard'))

# --- Kunden-Routen ---
@app.route('/customers')
@login_required
def customers():
    """
    Zeigt alle Kunden an. Erfordert angemeldeten Benutzer.
    """
    try:
        customers_list = Customer.query.all()
        return render_template('customers.html', customers=customers_list)
    except Exception as e:
        logger.error(f"Fehler in der Customers-Route: {e}")
        return render_template('500.html'), 500

@app.route('/customers/add', methods=['GET', 'POST'])
@admin_required  # Nur Admins dürfen Kunden hinzufügen
def add_customer():
    """
    Route zum Hinzufügen eines neuen Kunden.
    GET: Zeigt das Formular an.
    POST: Verarbeitet das Formular und speichert den Kunden mit validierter Adresse.
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

@app.route('/customers/<int:customer_id>')
@login_required
def customer_detail(customer_id):
    """
    Zeigt die Details eines bestimmten Kunden an.
    """
    customer = Customer.query.get_or_404(customer_id)
    return render_template('customer_detail.html', customer=customer)

@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@admin_required  # Nur Admins dürfen Kunden bearbeiten
def edit_customer(customer_id):
    """
    Route zum Bearbeiten eines Kunden.
    GET: Zeigt das Bearbeitungsformular an.
    POST: Verarbeitet das Formular und aktualisiert den Kunden mit validierter Adresse.
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

@app.route('/customers/<int:customer_id>/delete', methods=['POST'])
@admin_required  # Nur Admins dürfen Kunden löschen
def delete_customer(customer_id):
    """
    Löscht einen Kunden aus der Datenbank.
    """
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()

    flash('Kunde erfolgreich gelöscht!', 'success')
    return redirect(url_for('customers'))

# --- Leads-Routen ---
@app.route('/leads')
@login_required
def leads():
    """
    Zeigt alle Leads an. Erfordert angemeldeten Benutzer.
    """
    try:
        leads_list = Lead.query.all()
        return render_template('leads.html', leads=leads_list)
    except Exception as e:
        logger.error(f"Fehler in der Leads-Route: {e}")
        return render_template('500.html'), 500

@app.route('/leads/add', methods=['GET', 'POST'])
@admin_required  # Nur Admins dürfen Leads hinzufügen
def add_lead():
    """
    Route zum Hinzufügen eines neuen Leads.
    GET: Zeigt das Formular an.
    POST: Verarbeitet das Formular und speichert den Lead mit validierter Adresse.
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
    """
    lead = Lead.query.get_or_404(lead_id)
    return render_template('lead_detail.html', lead=lead)

@app.route('/leads/<int:lead_id>/edit', methods=['GET', 'POST'])
@admin_required  # Nur Admins dürfen Leads bearbeiten
def edit_lead(lead_id):
    """
    Route zum Bearbeiten eines Leads.
    GET: Zeigt das Bearbeitungsformular an.
    POST: Verarbeitet das Formular und aktualisiert den Lead mit validierter Adresse.
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
@admin_required  # Nur Admins dürfen Leads löschen
def delete_lead(lead_id):
    """
    Route zum Löschen eines Leads.
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

        # Neuen Benutzer erstellen (Standardrolle: user)
        new_user = User(username=username, role='user')
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
    """
    logout_user()
    flash('Erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('login'))

# --- Euro-Währung ---
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
            print("Starte Datenbankinitialisierung...")
            db.create_all()
            print("Datenbanktabellen erstellt.")

            print("Füge Beispieldaten hinzu...")
            init_sample_data()

            print("Erstelle Testbenutzer...")
            init_user_data()

            print("Alle Initialisierungen abgeschlossen.")
        app.run(debug=True, host='127.0.0.1', port=5000)  # Startet den Entwicklungsserver
    except Exception as e:
        logger.error(f"Fehler beim Starten der Anwendung: {e}")
        import traceback
        traceback.print_exc()