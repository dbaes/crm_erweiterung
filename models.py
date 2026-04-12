from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_security import UserMixin as SecurityUserMixin  # Flask-Security UserMixin

# Initialisiere SQLAlchemy
db = SQLAlchemy()

class Customer(db.Model):
    """Kundenmodell für CRM-System"""
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    company = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default="prospect")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    street = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(50))
    country = db.Column(db.String(50))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    leads = db.relationship('Lead', backref='customer', lazy=True)

    @classmethod
    def add_customer(cls, name, email, company, phone, status="prospect",
                    street=None, postal_code=None, city=None, country=None, lat=None, lng=None):
        """Fügt einen neuen Kunden zur Datenbank hinzu"""
        customer = cls(
            name=name,
            email=email,
            company=company,
            phone=phone,
            status=status,
            street=street,
            postal_code=postal_code,
            city=city,
            country=country,
            lat=lat,
            lng=lng
        )
        db.session.add(customer)
        db.session.commit()
        return customer

    @classmethod
    def get_all_customers(cls):
        """Gibt alle Kunden zurück"""
        return cls.query.all()

    @classmethod
    def get_customer_by_id(cls, customer_id):
        """Gibt einen Kunden basierend auf der ID zurück"""
        return cls.query.get(customer_id)

    @classmethod
    def update_customer(cls, customer_id, name, email, company, phone, status="prospect",
                        street=None, postal_code=None, city=None, country=None, lat=None, lng=None):
        """Aktualisiert einen bestehenden Kunden"""
        customer = cls.get_customer_by_id(customer_id)
        if customer:
            customer.name = name
            customer.email = email
            customer.company = company
            customer.phone = phone
            customer.status = status
            customer.street = street
            customer.postal_code = postal_code
            customer.city = city
            customer.country = country
            customer.lat = lat
            customer.lng = lng
            db.session.commit()
        return customer

    @classmethod
    def delete_customer(cls, customer_id):
        """Löscht einen Kunden"""
        customer = cls.get_customer_by_id(customer_id)
        if customer:
            db.session.delete(customer)
            db.session.commit()

class Lead(db.Model):
    """Lead-Modell für CRM-System"""
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(100))
    value = db.Column(db.Numeric(10, 2))
    source = db.Column(db.String(50))
    status = db.Column(db.String(20), default="new")
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    street = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(50))
    country = db.Column(db.String(50))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

    @classmethod
    def add_lead(cls, name, email, company, value, source, customer_id,
                 street=None, postal_code=None, city=None, country=None, lat=None, lng=None):
        """Fügt einen neuen Lead zur Datenbank hinzu"""
        lead = cls(
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
            lat=lat,
            lng=lng
        )
        db.session.add(lead)
        db.session.commit()
        return lead

    @classmethod
    def get_all_leads(cls):
        """Gibt alle Leads zurück"""
        return cls.query.all()

    @classmethod
    def get_lead_by_id(cls, lead_id):
        """Gibt einen Lead basierend auf der ID zurück"""
        return cls.query.get(lead_id)

    @classmethod
    def update_lead(cls, lead_id, name, email, company, value, source, customer_id,
                    street=None, postal_code=None, city=None, country=None, lat=None, lng=None):
        """Aktualisiert einen bestehenden Lead"""
        lead = cls.get_lead_by_id(lead_id)
        if lead:
            lead.name = name
            lead.email = email
            lead.company = company
            lead.value = value
            lead.source = source
            lead.customer_id = customer_id
            lead.street = street
            lead.postal_code = postal_code
            lead.city = city
            lead.country = country
            lead.lat = lat
            lead.lng = lng
            db.session.commit()
        return lead

    @classmethod
    def delete_lead(cls, lead_id):
        """Löscht einen Lead"""
        lead = cls.get_lead_by_id(lead_id)
        if lead:
            db.session.delete(lead)
            db.session.commit()

class User(db.Model, UserMixin):
    """Benutzermodell mit Flask-Security-Unterstützung für Passwort-Reset"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)  # Wichtig für Passwort-Reset
    password_hash = db.Column(db.String(128), nullable=False)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)  # Wird von Flask-Security benötigt
    active = db.Column(db.Boolean(), default=True)  # Wird von Flask-Security benötigt
    role = db.Column(db.String(20), nullable=False, default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Setzt das Passwort (gehasht)"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Überprüft das Passwort"""
        return check_password_hash(self.password_hash, password)

    @classmethod
    def add_user(cls, username, email, password, role="user"):
        """Fügt einen neuen Benutzer hinzu"""
        user = cls(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def get_user_by_id(cls, user_id):
        """Gibt einen Benutzer basierend auf der ID zurück"""
        return cls.query.get(user_id)

    @classmethod
    def get_user_by_username(cls, username):
        """Gibt einen Benutzer basierend auf dem Benutzernamen zurück"""
        return cls.query.filter_by(username=username).first()

    @classmethod
    def get_user_by_email(cls, email):
        """Gibt einen Benutzer basierend auf der E-Mail zurück (für Passwort-Reset)"""
        return cls.query.filter_by(email=email).first()

    @classmethod
    def update_user_role(cls, user_id, new_role):
        """Aktualisiert die Rolle eines Benutzers"""
        user = cls.get_user_by_id(user_id)
        if user:
            user.role = new_role
            db.session.commit()
        return user