from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flasgger import Swagger
from flask_cors import CORS  # Für CORS-Unterstützung
from models import db, Customer, Lead, User
from api.routes import api_bp
from api.external.adress_validator import AdressValidator

# --- App erstellen und Grundkonfiguration ---
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Geheimschlüssel für Sessions
CORS(app)  # CORS für alle Routen aktivieren

# --- Datenbankkonfiguration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# --- Swagger-Konfiguration ---
app.config['SWAGGER'] = {
    'title': 'CRM API',
    'uiversion': 3,
    'specs_route': '/api/docs/',
    'config': {
        'app_name': 'CRM API',
        'headers': [],
        'specs': [
            {
                'endpoint': 'apispec_1',
                'route': '/apispec_1.json',
                'rule_filter': lambda rule: True,
                'model_filter': lambda tag: True,
            }
        ],
        'static_url_path': '/flasgger_static',
        'swagger_ui': True,
        'specs_route': '/api/docs/'
    }
}
Swagger(app)

# --- Flask-Erweiterungen initialisieren ---
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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
            # Deine Beispieldaten (wie in deinem Code)
            customer1 = Customer.add_customer(...)
            # ...
            db.session.commit()
            print("Beispieldaten wurden eingefügt.")

def init_user_data():
    """Erstellt einen Test-Benutzer, falls keiner existiert."""
    with app.app_context():
        if not User.query.first():
            admin = User(username='test')
            admin.set_password('test')
            db.session.add(admin)
            db.session.commit()
            print("Test-Benutzer 'test' mit Passwort 'test' angelegt!")

# --- API-Routen registrieren ---
app.register_blueprint(api_bp, url_prefix="/api")

# --- API-spezifische Fehlerhandler ---
@api_bp.errorhandler(404)
def api_not_found(error):
    """API-spezifischer 404-Fehler."""
    return jsonify({"error": "Endpoint nicht gefunden"}), 404

@api_bp.errorhandler(500)
def api_internal_error(error):
    """API-spezifischer 500-Fehler."""
    return jsonify({"error": "Interner Serverfehler"}), 500

# --- Startseite ---
@app.route('/')
def index():
    """Zeigt die Startseite mit Statistiken an."""
    total_customers = len(Customer.get_all_customers())
    total_leads = len(Lead.get_all_leads())
    return render_template('index.html', total_customers=total_customers, total_leads=total_leads)

# --- Web-Routen (wie in deinem Code) ---
@app.route('/customers')
@login_required
def customers():
    """Zeigt alle Kunden an."""
    return render_template('customers.html', customers=Customer.get_all_customers())

# --- Weitere Web-Routen (wie in deinem Code) ---
# ...

# --- Anwendung starten ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Customer.query.first():
            init_sample_data()
        if not User.query.first():
            init_user_data()
    app.run(debug=True, host='127.0.0.1', port=5000)
