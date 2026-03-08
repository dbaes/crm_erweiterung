from flask import Blueprint, request, jsonify
from api.external.adress_validator import AdressValidator 

# Erstelle einen Blueprint für die API-Routen
api_bp = Blueprint("api", __name__)
adress_validator = AdressValidator()

@api_bp.route("/validate_adress", methods=["POST"])
def validate_adress():
    """
    Endpunkt zur Validierung von Adressen.

    Erwartet:
        JSON-Daten mit dem Schlüssel "adress".

    Gibt zurück:
        JSON-Daten mit den Koordinaten und der formatierten Adresse oder eine Fehlermeldung.
    """
    data = request.get_json()
    adress = data.get("adress")

    # Überprüfe, ob die Adresse im Request enthalten ist
    if not adress:
        return jsonify({"error": "Adress is required"}), 400

    # Validiere die Adresse
    result = adress_validator.validate_adress(adress)
    if not result:
        return jsonify({"error": "Adresse nicht gefunden"}), 404

    return jsonify(result)
