from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from api.external.adress_validator import AdressValidator
from models import db, Customer, Lead, User

# Blueprint für API-Routen
api_bp = Blueprint("api", __name__)
adress_validator = AdressValidator()

# =============================================
# HILFSFUNKTION: Rollenprüfung
# =============================================
def admin_required(f):
    """
    Dekorator, um sicherzustellen, dass nur Admins auf die Route zugreifen können.
    """
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            return jsonify({"error": "Zugriff verweigert: Admin-Rechte erforderlich"}), 403
        return f(*args, **kwargs)
    return wrapper

# =============================================
# ADRESSVALIDIERUNG (bereits vorhanden)
# =============================================
@api_bp.route("/validate_adress", methods=["POST"])
def validate_adress():
    """
    Validiert eine Adresse (strukturiert mit vier Feldern)
    ---
    tags:
      - Adressvalidierung
    requestBody:
      description: Adressdaten als JSON mit street, postal_code, city, country.
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - street
              - postal_code
              - city
              - country
            properties:
              street:
                type: string
                description: Straße und Hausnummer
                example: "Mariahilfer Straße 30"
              postal_code:
                type: string
                description: Postleitzahl
                example: "1070"
              city:
                type: string
                description: Stadt/Ort
                example: "Wien"
              country:
                type: string
                description: Land
                example: "Österreich"
    responses:
      200:
        description: Erfolg! Koordinaten und formatierte Adresse.
      400:
        description: Ungültige Anfrage (fehlende Felder).
      404:
        description: Adresse nicht gefunden.
      500:
        description: Serverfehler.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Ungültige Anfrage: JSON fehlt"}), 400

    required_fields = ["street", "postal_code", "city", "country"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Fehlende Felder: {', '.join(missing_fields)}"}), 400

    try:
        result = adress_validator.validate_adress(
            data["street"],
            data["postal_code"],
            data["city"],
            data["country"]
        )
        if not result:
            return jsonify({"error": "Adresse nicht gefunden"}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Serverfehler: {str(e)}"}), 500

# =============================================
# KUNDEN-ENDPOINTS (CRUD)
# =============================================
@api_bp.route("/customers", methods=["GET"])
@login_required  # Nur angemeldete Benutzer
def get_customers():
    """
    Gibt alle Kunden zurück.
    ---
    tags:
      - Kunden
    responses:
      200:
        description: Liste aller Kunden.
      500:
        description: Serverfehler.
    """
    try:
        customers = Customer.query.all()
        return jsonify([
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "company": c.company,
                "street": c.street,
                "postal_code": c.postal_code,
                "city": c.city,
                "country": c.country,
                "lat": str(c.lat) if c.lat else None,
                "lng": str(c.lng) if c.lng else None
            }
            for c in customers
        ])
    except Exception as e:
        return jsonify({"error": f"Fehler: {str(e)}"}), 500

@api_bp.route("/customers", methods=["POST"], endpoint="api_create_customer")  # Eindeutiger Endpoint-Name
@admin_required  # Nur Admins dürfen Kunden erstellen
def create_customer():
    """
    Erstellt einen neuen Kunden.
    ---
    tags:
      - Kunden
    requestBody:
      description: Kundendaten (inkl. Adresse für Validierung).
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - name
              - email
              - street
              - postal_code
              - city
              - country
            properties:
              name:
                type: string
                description: Name
                example: "Max Mustermann"
              email:
                type: string
                description: E-Mail
                example: "max@example.com"
              company:
                type: string
                description: Firma (optional)
                example: "Muster GmbH"
              street:
                type: string
                description: Straße
                example: "Musterstraße 1"
              postal_code:
                type: string
                description: PLZ
                example: "1010"
              city:
                type: string
                description: Stadt
                example: "Wien"
              country:
                type: string
                description: Land
                example: "Österreich"
    responses:
      201:
        description: Kunde erfolgreich erstellt.
      400:
        description: Ungültige Daten.
      403:
        description: Zugriff verweigert.
      500:
        description: Serverfehler.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Ungültige Anfrage"}), 400

    # Adresse validieren
    validation_result = adress_validator.validate_adress(
        data["street"],
        data["postal_code"],
        data["city"],
        data["country"]
    )
    if not validation_result:
        return jsonify({"error": "Adresse nicht gültig"}), 400

    try:
        customer = Customer(
            name=data["name"],
            email=data["email"],
            company=data.get("company", ""),
            street=data["street"],
            postal_code=data["postal_code"],
            city=data["city"],
            country=data["country"],
            lat=validation_result["lat"],
            lng=validation_result["lng"]
        )
        db.session.add(customer)
        db.session.commit()
        return jsonify({
            "id": customer.id,
            "message": "Kunde erfolgreich erstellt!"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Fehler: {str(e)}"}), 500

@api_bp.route("/customers/<int:customer_id>", methods=["GET"])
@login_required
def get_customer(customer_id):
    """
    Gibt einen bestimmten Kunden zurück.
    ---
    tags:
      - Kunden
    parameters:
      - name: customer_id
        in: path
        required: true
        description: ID des Kunden
        schema:
          type: integer
    responses:
      200:
        description: Kundendetails.
      403:
        description: Zugriff verweigert.
      404:
        description: Kunde nicht gefunden.
    """
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Kunde nicht gefunden"}), 404
    return jsonify({
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "company": customer.company,
        "street": customer.street,
        "postal_code": customer.postal_code,
        "city": customer.city,
        "country": customer.country,
        "lat": str(customer.lat),
        "lng": str(customer.lng)
    })

@api_bp.route("/customers/<int:customer_id>", methods=["PUT"], endpoint="api_update_customer")  # Eindeutiger Endpoint-Name
@admin_required
def update_customer(customer_id):
    """
    Aktualisiert einen Kunden.
    ---
    tags:
      - Kunden
    parameters:
      - name: customer_id
        in: path
        required: true
        description: ID des Kunden
        schema:
          type: integer
    requestBody:
      description: Aktualisierte Kundendaten.
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
                description: Name
              email:
                type: string
                description: E-Mail
              company:
                type: string
                description: Firma
              street:
                type: string
                description: Straße
              postal_code:
                type: string
                description: PLZ
              city:
                type: string
                description: Stadt
              country:
                type: string
                description: Land
    responses:
      200:
        description: Kunde erfolgreich aktualisiert.
      400:
        description: Ungültige Daten.
      403:
        description: Zugriff verweigert.
      404:
        description: Kunde nicht gefunden.
    """
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Kunde nicht gefunden"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Ungültige Anfrage"}), 400

    # Adresse validieren (falls geändert)
    if all(field in data for field in ["street", "postal_code", "city", "country"]):
        validation_result = adress_validator.validate_adress(
            data["street"],
            data["postal_code"],
            data["city"],
            data["country"]
        )
        if not validation_result:
            return jsonify({"error": "Adresse nicht gültig"}), 400
        customer.lat = validation_result["lat"]
        customer.lng = validation_result["lng"]

    # Felder aktualisieren
    customer.name = data.get("name", customer.name)
    customer.email = data.get("email", customer.email)
    customer.company = data.get("company", customer.company)
    customer.street = data.get("street", customer.street)
    customer.postal_code = data.get("postal_code", customer.postal_code)
    customer.city = data.get("city", customer.city)
    customer.country = data.get("country", customer.country)

    db.session.commit()
    return jsonify({"message": "Kunde erfolgreich aktualisiert!"})

@api_bp.route("/customers/<int:customer_id>", methods=["DELETE"], endpoint="api_delete_customer")  # Eindeutiger Endpoint-Name
@admin_required
def delete_customer(customer_id):
    """
    Löscht einen Kunden.
    ---
    tags:
      - Kunden
    parameters:
      - name: customer_id
        in: path
        required: true
        description: ID des Kunden
        schema:
          type: integer
    responses:
      200:
        description: Kunde erfolgreich gelöscht.
      403:
        description: Zugriff verweigert.
      404:
        description: Kunde nicht gefunden.
    """
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Kunde nicht gefunden"}), 404

    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": "Kunde erfolgreich gelöscht!"})

# =============================================
# LEAD-ENDPOINTS (CRUD)
# =============================================
@api_bp.route("/leads", methods=["GET"])
@login_required
def get_leads():
    """
    Gibt alle Leads zurück.
    ---
    tags:
      - Leads
    responses:
      200:
        description: Liste aller Leads.
      403:
        description: Zugriff verweigert.
    """
    try:
        leads = Lead.query.all()
        return jsonify([
            {
                "id": lead.id,
                "name": lead.name,
                "email": lead.email,
                "company": lead.company,
                "value": float(lead.value) if lead.value else None,
                "street": lead.street,
                "postal_code": lead.postal_code,
                "city": lead.city,
                "country": lead.country,
                "lat": str(lead.lat) if lead.lat else None,
                "lng": str(lead.lng) if lead.lng else None
            }
            for lead in leads
        ])
    except Exception as e:
        return jsonify({"error": f"Fehler: {str(e)}"}), 500

@api_bp.route("/leads", methods=["POST"], endpoint="api_create_lead")  # Eindeutiger Endpoint-Name
@admin_required
def create_lead():
    """
    Erstellt einen neuen Lead.
    ---
    tags:
      - Leads
    requestBody:
      description: Leaddaten (inkl. Adresse für Validierung).
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - name
              - email
              - street
              - postal_code
              - city
              - country
            properties:
              name:
                type: string
                description: Name
              email:
                type: string
                description: E-Mail
              company:
                type: string
                description: Firma (optional)
              value:
                type: number
                description: Wert des Leads (optional)
              street:
                type: string
                description: Straße
              postal_code:
                type: string
                description: PLZ
              city:
                type: string
                description: Stadt
              country:
                type: string
                description: Land
    responses:
      201:
        description: Lead erfolgreich erstellt.
      400:
        description: Ungültige Daten.
      403:
        description: Zugriff verweigert.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Ungültige Anfrage"}), 400

    # Adresse validieren
    validation_result = adress_validator.validate_adress(
        data["street"],
        data["postal_code"],
        data["city"],
        data["country"]
    )
    if not validation_result:
        return jsonify({"error": "Adresse nicht gültig"}), 400

    try:
        lead = Lead(
            name=data["name"],
            email=data["email"],
            company=data.get("company", ""),
            value=data.get("value", 0),
            street=data["street"],
            postal_code=data["postal_code"],
            city=data["city"],
            country=data["country"],
            lat=validation_result["lat"],
            lng=validation_result["lng"]
        )
        db.session.add(lead)
        db.session.commit()
        return jsonify({
            "id": lead.id,
            "message": "Lead erfolgreich erstellt!"
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Fehler: {str(e)}"}), 500

@api_bp.route("/leads/<int:lead_id>", methods=["GET"])
@login_required
def get_lead(lead_id):
    """
    Gibt einen bestimmten Lead zurück.
    ---
    tags:
      - Leads
    parameters:
      - name: lead_id
        in: path
        required: true
        description: ID des Leads
        schema:
          type: integer
    responses:
      200:
        description: Leaddetails.
      403:
        description: Zugriff verweigert.
      404:
        description: Lead nicht gefunden.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({"error": "Lead nicht gefunden"}), 404
    return jsonify({
        "id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "company": lead.company,
        "value": float(lead.value) if lead.value else None,
        "street": lead.street,
        "postal_code": lead.postal_code,
        "city": lead.city,
        "country": lead.country,
        "lat": str(lead.lat),
        "lng": str(lead.lng)
    })

@api_bp.route("/leads/<int:lead_id>", methods=["PUT"], endpoint="api_update_lead")  # Eindeutiger Endpoint-Name
@admin_required
def update_lead(lead_id):
    """
    Aktualisiert einen Lead.
    ---
    tags:
      - Leads
    parameters:
      - name: lead_id
        in: path
        required: true
        description: ID des Leads
        schema:
          type: integer
    requestBody:
      description: Aktualisierte Leaddaten.
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
                description: Name
              email:
                type: string
                description: E-Mail
              company:
                type: string
                description: Firma
              value:
                type: number
                description: Wert
              street:
                type: string
                description: Straße
              postal_code:
                type: string
                description: PLZ
              city:
                type: string
                description: Stadt
              country:
                type: string
                description: Land
    responses:
      200:
        description: Lead erfolgreich aktualisiert.
      400:
        description: Ungültige Daten.
      403:
        description: Zugriff verweigert.
      404:
        description: Lead nicht gefunden.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({"error": "Lead nicht gefunden"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Ungültige Anfrage"}), 400

    # Adresse validieren (falls geändert)
    if all(field in data for field in ["street", "postal_code", "city", "country"]):
        validation_result = adress_validator.validate_adress(
            data["street"],
            data["postal_code"],
            data["city"],
            data["country"]
        )
        if not validation_result:
            return jsonify({"error": "Adresse nicht gültig"}), 400
        lead.lat = validation_result["lat"]
        lead.lng = validation_result["lng"]

    # Felder aktualisieren
    lead.name = data.get("name", lead.name)
    lead.email = data.get("email", lead.email)
    lead.company = data.get("company", lead.company)
    lead.value = data.get("value", lead.value)
    lead.street = data.get("street", lead.street)
    lead.postal_code = data.get("postal_code", lead.postal_code)
    lead.city = data.get("city", lead.city)
    lead.country = data.get("country", lead.country)

    db.session.commit()
    return jsonify({"message": "Lead erfolgreich aktualisiert!"})

@api_bp.route("/leads/<int:lead_id>", methods=["DELETE"], endpoint="api_delete_lead")  # Eindeutiger Endpoint-Name
@admin_required
def delete_lead(lead_id):
    """
    Löscht einen Lead.
    ---
    tags:
      - Leads
    parameters:
      - name: lead_id
        in: path
        required: true
        description: ID des Leads
        schema:
          type: integer
    responses:
      200:
        description: Lead erfolgreich gelöscht.
      403:
        description: Zugriff verweigert.
      404:
        description: Lead nicht gefunden.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({"error": "Lead nicht gefunden"}), 404

    db.session.delete(lead)
    db.session.commit()
    return jsonify({"message": "Lead erfolgreich gelöscht!"})

# =============================================
# BENUTZER-ENDPOINTS (Rollenverwaltung)
# =============================================
@api_bp.route("/users", methods=["GET"], endpoint="api_get_users")  # Eindeutiger Endpoint-Name
@admin_required
def get_users():
    """
    Gibt alle Benutzer zurück (nur für Admins).
    ---
    tags:
      - Benutzer
    responses:
      200:
        description: Liste aller Benutzer.
      403:
        description: Zugriff verweigert.
    """
    users = User.query.all()
    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "created_at": user.created_at.isoformat()
        }
        for user in users
    ])

@api_bp.route("/users/<int:user_id>/role", methods=["PUT"], endpoint="api_update_user_role")  # Eindeutiger Endpoint-Name
@admin_required
def update_user_role(user_id):
    """
    Aktualisiert die Rolle eines Benutzers (nur für Admins).
    ---
    tags:
      - Benutzer
    parameters:
      - name: user_id
        in: path
        required: true
        description: ID des Benutzers
        schema:
          type: integer
    requestBody:
      description: Neue Rolle des Benutzers.
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - role
            properties:
              role:
                type: string
                description: Rolle ("admin" oder "user")
                example: "admin"
    responses:
      200:
        description: Rolle erfolgreich aktualisiert.
      400:
        description: Ungültige Rolle.
      403:
        description: Zugriff verweigert.
      404:
        description: Benutzer nicht gefunden.
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Benutzer nicht gefunden"}), 404

    data = request.get_json()
    if not data or "role" not in data:
        return jsonify({"error": "Rolle muss angegeben werden"}), 400

    if data["role"] not in ["admin", "user"]:
        return jsonify({"error": "Ungültige Rolle (nur 'admin' oder 'user' erlaubt)"}), 400

    user.role = data["role"]
    db.session.commit()
    return jsonify({"message": f"Rolle von {user.username} zu {user.role} geändert!"})