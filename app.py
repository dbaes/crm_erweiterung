from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Customer, Lead
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Customer, Lead, User

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# SQLAlchemy-Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialisiere Flask-Migrate
migrate = Migrate(app, db)

#Flask-Login initialisieren
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_sample_data():
    with app.app_context():
        # Überprüfe, ob bereits Daten existieren
        if not Customer.query.first():
            customer1 = Customer.add_customer('John Doe', 'john@example.com', 'Acme Corp', '555-0001', 'active')
            customer2 = Customer.add_customer('Jane Smith', 'jane@example.com', 'Tech Solutions', '555-0002', 'prospect')
            customer3 = Customer.add_customer('Bob Wilson', 'bob@example.com', 'Global Industries', '555-0003', 'inactive')

            Lead.add_lead('Alice Brown', 'alice@example.com', 'StartUp Inc', 50000, 'Website', customer1.id)
            Lead.add_lead('Charlie Davis', 'charlie@example.com', 'Enterprise Ltd', 100000, 'Referral', customer2.id)

def init_user_data():
    with app.app_context():
        if not User.query.first():	#Prüfen ob schon ein User existiert
            admin = User(username='test')
            admin.set_password('test')
            db.session.add(admin)
            db.session.commit()
            print("Test-User 'test' mit Passwort 'test' angelegt!")

# nicht mehr nötig wegen Flask-Migrate
#with app.app_context():
#    db.create_all()

init_sample_data()
init_user_data() 	#Test User anlegen

@app.route('/')
def index():
    if current_user.is_authenticated:
        total_customers = len(Customer.get_all_customers())
        total_leads = len(Lead.get_all_leads())
        return render_template('index.html', total_customers=total_customers, total_leads=total_leads)
    else:
        return render_template('index.html')

@app.route('/customers')
@login_required
def customers():
    return render_template('customers.html', customers=Customer.get_all_customers())

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        company = request.form.get('company')
        phone = request.form.get('phone')
        status = request.form.get('status', 'prospect')

        if not all([name, email, company, phone]):
            flash('All fields are required!', 'error')
            return redirect(url_for('add_customer'))

        Customer.add_customer(name, email, company, phone, status)
        flash(f'Customer {name} added successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('add_customer.html')

@app.route('/customers/<int:customer_id>')
@login_required
def customer_detail(customer_id):
    customer = Customer.get_customer_by_id(customer_id)
    if not customer:
        flash('Customer not found!', 'error')
        return redirect(url_for('customers'))
    return render_template('customer_detail.html', customer=customer)

@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = Customer.get_customer_by_id(customer_id)
    if not customer:
        flash('Customer not found!', 'error')
        return redirect(url_for('customers'))

    if request.method == 'POST':
        Customer.update_customer(
            customer_id,
            request.form.get('name'),
            request.form.get('email'),
            request.form.get('company'),
            request.form.get('phone'),
            request.form.get('status')
        )
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customer_detail', customer_id=customer_id))

    return render_template('edit_customer.html', customer=customer)

@app.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
def delete_customer(customer_id):
    Customer.delete_customer(customer_id)
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers'))

@app.route('/leads')
@login_required
def leads():
    return render_template('leads.html', leads=Lead.get_all_leads())

@app.route('/leads/add', methods=['GET', 'POST'])
@login_required
def add_lead():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        company = request.form.get('company')
        value = request.form.get('value')
        source = request.form.get('source')
        customer_id = request.form.get('customer_id', type=int)

        if not all([name, email, company, value, source, customer_id]):
            flash('All fields are required!', 'error')
            return redirect(url_for('add_lead'))

        try:
            Lead.add_lead(name, email, company, float(value), source, customer_id)
            flash(f'Lead {name} added successfully!', 'success')
        except ValueError:
            flash('Deal value must be a number!', 'error')

        return redirect(url_for('leads'))

    # Für das Formular: Alle Kunden abrufen, um sie im Dropdown anzuzeigen
    customers = Customer.get_all_customers()
    return render_template('add_lead.html', customers=customers)

@app.route('/leads/<int:lead_id>')
@login_required
def lead_detail(lead_id):
    lead = Lead.get_lead_by_id(lead_id)
    if not lead:
        flash('Lead not found!', 'error')
        return redirect(url_for('leads'))
    return render_template('lead_detail.html', lead=lead)

@app.route('/leads/<int:lead_id>/delete', methods=['POST'])
@login_required
def delete_lead(lead_id):
    Lead.delete_lead(lead_id)
    flash('Lead deleted successfully!', 'success')
    return redirect(url_for('leads'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash ('Erfolgreich eingeloggt!', 'success')
            return redirect(url_for('index'))
        flash('Ungültiger Benutzername oder Passwort.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
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

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
