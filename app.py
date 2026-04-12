from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, send_from_directory
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
    return User.query.get(int(user_id))

# --- Haupt-Routen ---

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

# --- Hilfsfunktionen & Auth ---

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)