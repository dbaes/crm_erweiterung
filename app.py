from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, send_from_directory, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from models import db, Customer, Lead, User
from api.routes import api_bp
from api.external.adress_validator import AdressValidator
from flask_swagger_ui import get_swaggerui_blueprint
import logging
import sys
from functools import wraps
from api.external.zulip_notifier import send_zulip_notification
from flask_mail import Mail, Message
from flask import render_template_string
import uuid
from itsdangerous import URLSafeTimedSerializer

# --- App Konfiguration ---
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this' 
CORS(app)

# Zulip-Konfiguration
app.config['ZULIP_BOT_EMAIL'] = 'crmhook-bot@dbf.zulipchat.com'
app.config['ZULIP_API_KEY'] = 'Iya9i0yXBMPQ7Tf9gtOMnlOQUkebopIo'
app.config['ZULIP_STREAM'] = 'crm'
app.config['ZULIP_SITE'] = 'https://dbf.zulipchat.com'

# Logging
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Datenbank
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Swagger UI ---
SWAGGER_URL = '/api/docs'
API_URL = '/api/swagger'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL, API_URL,
    config={'app_name': "CRM API", 'docExpansion': 'none', 'persistAuthorization': True}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/api/swagger')
def swagger_spec():
    return send_from_directory('api/swagger', 'swagger_template.yaml')

# --- Blueprints ---
app.register_blueprint(api_bp, url_prefix="/api")

# --- Berechtigungs-Dekorator ---
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != "admin":
            logger.warning(f"Zugriff verweigert: {current_user.username}")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    # Entferne das int()!
    return User.query.get(user_id)

# --- Haupt-Routen ---

@app.route('/api/users/<int:user_id>/role', methods=['POST'])
@login_required
def update_user_role(user_id):
    if current_user.role != 'admin':
        return {"error": "Nicht autorisiert"}, 403

    # Wir schauen uns an, was wirklich ankommt
    print(f"DEBUG: Raw Data: {request.data}")
    
    data = request.get_json(silent=True) # silent=True verhindert den automatischen 400er
    print(f"DEBUG: Parsed JSON: {data}")

    if not data or 'role' not in data:
        return {"error": f"Ungültiges JSON oder Feld 'role' fehlt. Empfangen: {data}"}, 400

    new_role = data.get('role')
    user = db.session.get(User, user_id)
    
    if user and new_role in ['admin', 'user']:
        user.role = new_role
        db.session.commit()
        return {"message": "Rolle erfolgreich geändert"}, 200
    
    return {"error": "User nicht gefunden oder Rolle ungültig"}, 404

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return {"error": "Nicht autorisiert"}, 403
    
    if current_user.id == user_id:
        return {"error": "Du kannst dich nicht selbst löschen!"}, 400
    
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return {"message": f"Benutzer {user.username} wurde gelöscht"}, 200
    
    return {"error": "Benutzer nicht gefunden"}, 404

@app.route('/')
@login_required
def index():
    customers = Customer.query.all()
    leads = Lead.query.all()
    newest_customers = Customer.query.order_by(Customer.created_at.desc()).limit(5).all()
    newest_leads = Lead.query.order_by(Lead.created_at.desc()).limit(5).all()
    return render_template('index.html', 
                           total_customers=len(customers), 
                           total_leads=len(leads),
                           customers=customers, 
                           leads=leads,
                           newest_customers=newest_customers,
                           newest_leads=newest_leads)

@app.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

# --- Kunden Verwaltung ---

@app.route('/customers')
@login_required
def customers():
    customers_list = Customer.query.all()
    return render_template('customers.html', customers=customers_list)

@app.route('/customers/add', methods=['GET', 'POST'])
@admin_required
def add_customer():
    if request.method == 'POST':
        data = request.form
        validator = AdressValidator()
        val_res = validator.validate_adress(data.get('street'), data.get('postal_code'), data.get('city'), data.get('country'))
        
        if not val_res:
            flash('Adresse konnte nicht validiert werden.', 'error')
            return render_template('add_customer.html', **data)

        new_customer = Customer(
            name=data.get('name'),
            email=data.get('email'),
            company=data.get('company'),
            phone=data.get('phone'),
            status=data.get('status', 'prospect'),
            street=data.get('street'),
            postal_code=data.get('postal_code'),
            city=data.get('city'),
            country=data.get('country'),
            lat=val_res['lat'],
            lng=val_res['lng']
        )
        db.session.add(new_customer)
        db.session.commit()
        send_zulip_notification(f"Neuer Kunde: {new_customer.name}", f"**{new_customer.name}** wurde angelegt.")
        flash('Kunde erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('customers'))
    return render_template('add_customer.html')

@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == 'POST':
        data = request.form
        customer.name = data.get('name')
        customer.email = data.get('email')
        customer.company = data.get('company')
        customer.phone = data.get('phone')
        customer.status = data.get('status')
        # ... weitere Felder falls nötig ...
        db.session.commit()
        flash('Kundendaten aktualisiert!', 'success')
        return redirect(url_for('customers'))
    
    return render_template('edit_customer.html', customer=customer)

@app.route('/customers/<int:customer_id>')
@login_required
def customer_detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    return render_template('customer_detail.html', customer=customer)


@app.route('/customers/<int:customer_id>/delete', methods=['POST'])
@admin_required
def delete_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()
    flash('Kunde gelöscht', 'success')
    return redirect(url_for('customers'))

# --- Leads Verwaltung ---

@app.route('/leads')
@login_required
def leads():
    leads_list = Lead.query.all()
    return render_template('leads.html', leads=leads_list)

@app.route('/leads/add', methods=['GET', 'POST'])
@admin_required
def add_lead():
    if request.method == 'POST':
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        
        if not lat or not lng:
            validator = AdressValidator()
            val_res = validator.validate_adress(
                request.form.get('street'), request.form.get('postal_code'), 
                request.form.get('city'), request.form.get('country')
            )
            if val_res:
                lat, lng = val_res['lat'], val_res['lng']

        new_lead = Lead(
            name=request.form.get('name'),
            email=request.form.get('email'),
            company=request.form.get('company'),
            value=request.form.get('value'),
            source=request.form.get('source'),
            customer_id=request.form.get('customer_id'),
            street=request.form.get('street'),
            postal_code=request.form.get('postal_code'),
            city=request.form.get('city'),
            country=request.form.get('country'),
            lat=lat,
            lng=lng
        )
        db.session.add(new_lead)
        db.session.commit()
        
		# Zulip Benachrichtigung senden
        try:
            send_zulip_notification(
                subject=f"Neuer Lead: {new_lead.company}",
                message=f"🚀 Ein neuer Lead wurde erstellt: **{new_lead.name}** von **{new_lead.company}**.\n"
                        f"Potenzieller Wert: {new_lead.value} €"
            )
        except Exception as e:
            logger.error(f"Zulip Fehler: {e}") # Verhindert, dass die App abstürzt, wenn Zulip offline ist

        flash('Lead erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('leads'))


    customers = Customer.query.all()
    return render_template('add_lead.html', customers=customers)

@app.route('/leads/<int:lead_id>')
@login_required
def lead_detail(lead_id):
    """Route für die Detailansicht eines Leads (Wichtig für url_for in leads.html)"""
    lead = Lead.query.get_or_404(lead_id)
    return render_template('lead_detail.html', lead=lead)

@app.route('/leads/<int:lead_id>/delete', methods=['POST'])
@admin_required
def delete_lead(lead_id):
    """Route zum Löschen eines Leads"""
    lead = Lead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()
    flash('Lead wurde gelöscht.', 'success')
    return redirect(url_for('leads'))

@app.route('/leads/<int:lead_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if request.method == 'POST':
        # Hier die Logik zum Speichern einfügen (ähnlich wie add_lead)
        lead.name = request.form.get('name')
        # ... weitere Felder ...
        db.session.commit()
        flash('Lead aktualisiert!', 'success')
        return redirect(url_for('leads'))
    
    customers = Customer.query.all()
    return render_template('edit_lead.html', lead=lead, customers=customers)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 1. Prüfen, ob User oder E-Mail schon existieren
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben.', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('E-Mail bereits registriert.', 'error')
            return redirect(url_for('register'))
        
        # 2. Neuen User anlegen
        new_user = User(
            username=username,
            email=email,
            role="user", # Standardmäßig kein Admin
            fs_uniquifier=str(uuid.uuid4()),
            active=True
        )
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registrierung erfolgreich! Bitte logge dich ein.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler bei der Registrierung: {e}', 'error')
            
    return render_template('register.html')

# --- Hilfsfunktionen & Auth ---
def init_sample_data():
    # 1. PRÜFUNG: Wenn schon Kunden da sind, brich sofort ab!
    if Customer.query.first():
        logger.info("Datenbank enthält bereits Kunden. Überspringe Initialisierung.")
        return

    logger.info("Datenbank ist leer. Erstelle Beispieldaten...")
    
    # 1. ADMIN ANLEGEN (falls nicht vorhanden)
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        logger.info("Erstelle Admin-Account...")
        admin = User(
            username="admin", email="admin@danu.at", role="admin",
            fs_uniquifier=str(uuid.uuid4()), active=True
        )
        admin.set_password("admin123")
        db.session.add(admin)
    
    # 2. STANDARD-USER ANLEGEN (falls nicht vorhanden)
    standard_user = User.query.filter_by(username="user").first()
    if not standard_user:
        logger.info("Erstelle Standard-User-Account...")
        standard_user = User(
            username="user", email="user@danu.at", role="user",
            fs_uniquifier=str(uuid.uuid4()), active=True
        )
        standard_user.set_password("user123")
        db.session.add(standard_user)

    # 2. Drei Kunden anlegen
    c1 = Customer(name="Max Mustermann", email="max@muster.at", company="Muster GmbH", 
                  status="customer", city="Wien", country="Österreich", lat=48.2082, lng=16.3738)
    c2 = Customer(name="Anna Beispiel", email="anna@test.de", company="Beispiel AG", 
                  status="prospect", city="Berlin", country="Deutschland", lat=52.5200, lng=13.4050)
    c3 = Customer(name="John Doe", email="john@doe.com", company="Doe Inc.", 
                  status="customer", city="London", country="UK", lat=51.5074, lng=-0.1278)
    
    db.session.add_all([c1, c2, c3])
    db.session.commit()

    # 3. Drei Leads anlegen (jeweils einem Kunden zugeordnet)
    l1 = Lead(
        name="Expansion Süd", email="info@moda.it", company="Moda Italia", 
        value=25000.0, source="Messe", customer_id=c1.id,
        street="Via del Corso 12", postal_code="00186", city="Rom", country="Italien",
        lat=41.9028, lng=12.4964
    )
    
    l2 = Lead(
        name="Digitalisierung Point of Sale", email="contact@boulangerie.fr", company="Boulangerie Paris", 
        value=4200.0, source="Website", customer_id=c2.id,
        street="Rue de Rivoli 4", postal_code="75001", city="Paris", country="Frankreich",
        lat=48.8566, lng=2.3522
    )
    
    l3 = Lead(
        name="Server Upgrade", email="it@stockholm.se", company="Stockholm Tech", 
        value=15700.0, source="Kaltakquise", customer_id=c3.id,
        street="Drottninggatan 10", postal_code="11151", city="Stockholm", country="Schweden",
        lat=59.3293, lng=18.0686
    )

    db.session.add_all([l1, l2, l3])

    try:
        db.session.commit()
        logger.info("Setup erfolgreich: 3 Kunden und 3 Leads erstellt.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Fehler beim Befüllen: {e}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash('Ungültige Logindaten', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.template_filter('euro')
def euro_format(value):
    if value is None: return "0,00 €"
    try:
        return "{:,.2f} €".format(float(value)).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00 €"
    
# SMTP-Konfiguration (für Postausgang)
app.config['MAIL_SERVER'] = 'smtp.world4you.com'  
app.config['MAIL_PORT'] = 587                      # Port für STARTTLS
app.config['MAIL_USE_TLS'] = True                 # STARTTLS aktivieren
app.config['MAIL_USERNAME'] = 'crm@danu.at'  
app.config['MAIL_PASSWORD'] = 'CRM26Schule'
app.config['MAIL_DEFAULT_SENDER'] = 'crm@danu.at'  # Absenderadresse

# Initialisiere Flask-Mail
mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Route für Passwort-Reset
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = s.dumps(email, salt='password-reset-salt')
            link = url_for('reset_password', token=token, _external=True)
            
            msg = Message('Passwort zurücksetzen - CRM',
                          recipients=[email])
            msg.body = f'Klicke auf den folgenden Link, um dein Passwort zu ändern: {link}'
            mail.send(msg)
            flash('Ein Link zum Zurücksetzen wurde an deine E-Mail gesendet.', 'info')
        else:
            flash('Diese E-Mail ist uns nicht bekannt.', 'warning')
            
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html')

# Platzhalter für die Reset-Route
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Link ist 30 Minuten (1800 Sek) gültig
        email = s.loads(token, salt='password-reset-salt', max_age=1800)
    except:
        flash('Der Link ist ungültig oder abgelaufen.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        user = User.query.filter_by(email=email).first()
        new_password = request.form.get('password')
        
        user.set_password(new_password)
        db.session.commit()
        
        flash('Dein Passwort wurde erfolgreich aktualisiert!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_sample_data()  
    app.run(debug=True, port=5000)