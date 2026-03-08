from flask import Flask, render_template, request, redirect, url_for, flash
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Customer, Lead, User  
from api.routes import api_bp
from api.external.adress_validator import AdressValidator

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Geheimschlüssel für Sessions

# --- Datenbankkonfiguration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Deaktiviert Modifikations-Tracking (Performance)
db.init_app(app)

# --- Flask-Erweiterungen initialisieren ---
migrate = Migrate(app, db)  # Für Datenbankmigrationen
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Login-Route für @login_required

# --- Login-Manager Konfiguration ---
@login_manager.user_loader
def load_user(user_id):
    """Lädt einen Benutzer für Flask-Login."""
    return User.query.get(int(user_id))

# --- Testdaten initialisieren ---
def init_sample_data():
    """Fügt Beispieldaten hinzu, falls die Datenbank leer ist."""
    with app.app_context():
        if not Customer.query.first():
            # Österreich (Wiener Staatsoper)
            customer1 = Customer.add_customer(
                name='John Doe',
                email='john@example.com',
                company='Acme Corp',
                phone='555-0001',
                status='active',
                street='Opernring 1',
                postal_code='1010',
                city='Wien',
                country='Österreich',
                lat=48.2039,  # Vorvalidierte Koordinaten
                lng=16.3683
            )
            # Deutschland (Brandenburger Tor)
            customer2 = Customer.add_customer(
                name='Jane Smith',
                email='jane@example.com',
                company='Tech Solutions',
                phone='555-0002',
                status='prospect',
                street='Brandenburger Tor',
                postal_code='10117',
                city='Berlin',
                country='Deutschland',
                lat=52.5163,
                lng=13.3777
            )
            # Schweiz (Zürich Hauptbahnhof)
            customer3 = Customer.add_customer(
                name='Bob Wilson',
                email='bob@example.com',
                company='Global Industries',
                phone='555-0003',
                status='inactive',
                street='Bahnhofplatz 7',
                postal_code='8001',
                city='Zürich',
                country='Schweiz',
                lat=47.3778,
                lng=8.5402
            )
            # Frankreich (Louvre, Paris)
            customer4 = Customer.add_customer(
                name='Marie Dupont',
                email='marie@example.com',
                company='Paris Fashion',
                phone='555-0004',
                status='active',
                street='35 Rue du Louvre',
                postal_code='75001',
                city='Paris',
                country='Frankreich',
                lat=48.8617,
                lng=2.3378
            )

            # Leads mit Adressdaten und Koordinaten
            Lead.add_lead(
                name='Alice Brown',
                email='alice@example.com',
                company='StartUp Inc',
                value=50000,
                source='Website',
                customer_id=customer1.id,
                street='Mariahilfer Straße 30',
                postal_code='1070',
                city='Wien',
                country='Österreich',
                lat=48.2018,
                lng=16.3656
            )
            Lead.add_lead(
                name='Charlie Davis',
                email='charlie@example.com',
                company='Enterprise Ltd',
                value=100000,
                source='Referral',
                customer_id=customer2.id,
                street='Unter den Linden 14',
                postal_code='10117',
                city='Berlin',
                country='Deutschland',
                lat=52.5173,
                lng=13.3897
            )

def init_user_data():
    """Erstellt einen Test-Benutzer, falls keiner existiert."""
    with app.app_context():
        if not User.query.first():
            admin = User(username='test')
            admin.set_password('test')
            db.session.add(admin)
            db.session.commit()
            print("Test-User 'test' mit Passwort 'test' angelegt!")

# --- API-Routen registrieren ---
app.register_blueprint(api_bp, url_prefix="/api")

# --- Startseite ---
@app.route('/')
def index():
    """Zeigt die Startseite mit Statistiken an."""
    total_customers = len(Customer.get_all_customers())
    total_leads = len(Lead.get_all_leads())
    return render_template('index.html', total_customers=total_customers, total_leads=total_leads)

# --- Kunden-Routen ---
@app.route('/customers')
def customers():
    """Zeigt alle Kunden an."""
    return render_template('customers.html', customers=Customer.get_all_customers())

@app.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        form_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'company': request.form.get('company'),
            'phone': request.form.get('phone'),
            'status': request.form.get('status', 'prospect'),
            'street': request.form.get('street'),
            'postal_code': request.form.get('postal_code'),
            'city': request.form.get('city'),
            'country': request.form.get('country')
        }

        if not all(form_data.values()):
            flash('Alle Felder sind erforderlich!', 'error')
            return render_template('add_customer.html', **form_data)  # Daten zurückgeben

        validator = AdressValidator()
        validation_result = validator.validate_adress(
            form_data['street'],
            form_data['postal_code'],
            form_data['city'],
            form_data['country']
        )

        if validation_result and 'lat' in validation_result:
            Customer.add_customer(
                name=form_data['name'], email=form_data['email'], company=form_data['company'],
                phone=form_data['phone'], status=form_data['status'],
                street=form_data['street'], postal_code=form_data['postal_code'],
                city=form_data['city'], country=form_data['country'],
                lat=validation_result['lat'], lng=validation_result['lng']
            )
            flash(f'Kunde {form_data["name"]} erfolgreich hinzugefügt!', 'success')
            return redirect(url_for('customers'))
        else:
            flash('Adresse konnte nicht validiert werden. Bitte überprüfe die Angaben.', 'error')
            return render_template('add_customer.html', **form_data)  # Daten zurückgeben

    return render_template('add_customer.html')

@app.route('/customers/<int:customer_id>')
def customer_detail(customer_id):
    """Zeigt Details zu einem Kunden an."""
    customer = Customer.get_customer_by_id(customer_id)
    if not customer:
        flash('Kunde nicht gefunden!', 'error')
        return redirect(url_for('customers'))
    return render_template('customer_detail.html', customer=customer)

@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
def edit_customer(customer_id):
    """Bearbeitet einen bestehenden Kunden (mit Adressvalidierung)."""
    customer = Customer.get_customer_by_id(customer_id)
    if not customer:
        flash('Kunde nicht gefunden!', 'error')
        return redirect(url_for('customers'))

    if request.method == 'POST':
        # Adressvalidierung beim Bearbeiten
        validator = AdressValidator()
        validation_result = validator.validate_adress(
            request.form.get('street'),
            request.form.get('postal_code'),
            request.form.get('city'),
            request.form.get('country')
        )

        if validation_result and 'lat' in validation_result:
            Customer.update_customer(
                customer_id=customer_id,
                name=request.form.get('name'),
                email=request.form.get('email'),
                company=request.form.get('company'),
                phone=request.form.get('phone'),
                status=request.form.get('status', 'prospect'),
                street=request.form.get('street'),
                postal_code=request.form.get('postal_code'),
                city=request.form.get('city'),
                country=request.form.get('country'),
                lat=validation_result['lat'],
                lng=validation_result['lng']
            )
            flash('Kunde erfolgreich aktualisiert!', 'success')
        else:
            flash('Adresse konnte nicht validiert werden.', 'error')
            return redirect(url_for('edit_customer', customer_id=customer_id))

        return redirect(url_for('customer_detail', customer_id=customer_id))

    return render_template('edit_customer.html', customer=customer)

@app.route('/customers/<int:customer_id>/delete', methods=['POST'])
def delete_customer(customer_id):
    """Löscht einen Kunden."""
    Customer.delete_customer(customer_id)
    flash('Kunde erfolgreich gelöscht!', 'success')
    return redirect(url_for('customers'))

# --- Lead-Routen ---
@app.route('/leads')
def leads():
    """Zeigt alle Leads an."""
    return render_template('leads.html', leads=Lead.get_all_leads())

@app.route('/leads/add', methods=['GET', 'POST'])
def add_lead():
    if request.method == 'POST':
        form_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'company': request.form.get('company'),
            'value': request.form.get('value'),
            'source': request.form.get('source'),
            'customer_id': request.form.get('customer_id', type=int),
            'street': request.form.get('street'),
            'postal_code': request.form.get('postal_code'),
            'city': request.form.get('city'),
            'country': request.form.get('country')
        }

        if not all([form_data['name'], form_data['email'], form_data['company'], form_data['value'],
                   form_data['source'], form_data['customer_id'], form_data['street'],
                   form_data['postal_code'], form_data['city'], form_data['country']]):
            flash('Alle Felder sind erforderlich!', 'error')
            customers = Customer.get_all_customers()
            return render_template('add_lead.html', customers=customers, **form_data)

        validator = AdressValidator()
        validation_result = validator.validate_adress(
            form_data['street'],
            form_data['postal_code'],
            form_data['city'],
            form_data['country']
        )

        if validation_result and 'lat' in validation_result:
            Lead.add_lead(
                name=form_data['name'], email=form_data['email'], company=form_data['company'],
                value=float(form_data['value']), source=form_data['source'],
                customer_id=form_data['customer_id'],
                street=form_data['street'], postal_code=form_data['postal_code'],
                city=form_data['city'], country=form_data['country'],
                lat=validation_result['lat'], lng=validation_result['lng']
            )
            flash(f'Lead {form_data["name"]} erfolgreich hinzugefügt!', 'success')
            return redirect(url_for('leads'))
        else:
            flash('Adresse konnte nicht validiert werden.', 'error')
            customers = Customer.get_all_customers()
            return render_template('add_lead.html', customers=customers, **form_data)

    customers = Customer.get_all_customers()
    return render_template('add_lead.html', customers=customers)

@app.route('/leads/<int:lead_id>')
def lead_detail(lead_id):
    """Zeigt Details zu einem Lead an."""
    lead = Lead.get_lead_by_id(lead_id)
    if not lead:
        flash('Lead nicht gefunden!', 'error')
        return redirect(url_for('leads'))
    return render_template('lead_detail.html', lead=lead)

@app.route('/leads/<int:lead_id>/edit', methods=['GET', 'POST'])
def edit_lead(lead_id):
    """Bearbeitet einen bestehenden Lead (mit Adressvalidierung)."""
    lead = Lead.get_lead_by_id(lead_id)
    if not lead:
        flash('Lead nicht gefunden!', 'error')
        return redirect(url_for('leads'))

    if request.method == 'POST':
        form_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'company': request.form.get('company'),
            'value': request.form.get('value'),
            'source': request.form.get('source'),
            'customer_id': request.form.get('customer_id', type=int),
            'street': request.form.get('street'),
            'postal_code': request.form.get('postal_code'),
            'city': request.form.get('city'),
            'country': request.form.get('country')
        }

        validator = AdressValidator()
        validation_result = validator.validate_address(
            form_data['street'],
            form_data['postal_code'],
            form_data['city'],
            form_data['country']
        )

        if validation_result and 'lat' in validation_result:
            Lead.update_lead(
                lead_id=lead_id,
                name=form_data['name'],
                email=form_data['email'],
                company=form_data['company'],
                value=float(form_data['value']),
                source=form_data['source'],
                customer_id=form_data['customer_id'],
                street=form_data['street'],
                postal_code=form_data['postal_code'],
                city=form_data['city'],
                country=form_data['country'],
                lat=validation_result['lat'],
                lng=validation_result['lng']
            )
            flash('Lead erfolgreich aktualisiert!', 'success')
            return redirect(url_for('lead_detail', lead_id=lead_id))
        else:
            flash('Adresse konnte nicht validiert werden.', 'error')
            customers = Customer.get_all_customers()
            return render_template('edit_lead.html', lead=lead, customers=customers, **form_data)

    customers = Customer.get_all_customers()
    return render_template('edit_lead.html', lead=lead, customers=customers)


@app.route('/leads/<int:lead_id>/delete', methods=['POST'])
def delete_lead(lead_id):
    """Löscht einen Lead."""
    Lead.delete_lead(lead_id)
    flash('Lead erfolgreich gelöscht!', 'success')
    return redirect(url_for('leads'))

# --- Authentifizierungs-Routen ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Benutzeranmeldung."""
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

@app.route('/logout')
@login_required
def logout():
    """Benutzerabmeldung."""
    logout_user()
    flash('Erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Benutzerregistrierung."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben!', 'error')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registrierung erfolgreich! Bitte logge dich ein.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# --- Fehlerseiten ---
@app.errorhandler(404)
def page_not_found(error):
    """404-Seite."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500-Seite (Serverfehler)."""
    return render_template('500.html'), 500

# --- Anwendung starten ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()      # Tabellen erstellen
        init_sample_data()   # Testdaten einfügen
        init_user_data()     # Test-Benutzer anlegen
    app.run(debug=True, host='127.0.0.1', port=5000)
