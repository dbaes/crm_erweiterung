import requests
import logging

# Konfiguriere das Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdressValidator:
    """Klasse zur Validierung von Adressen über die Nominatim-API."""

    def __init__(self, base_url="https://nominatim.openstreetmap.org"):
        """Initialisiert die AdressValidator-Klasse mit der Basis-URL der API."""
        self.base_url = base_url

    def validate_adress(self, street, postal_code, city, country):
        url = "https://nominatim.openstreetmap.org/search"
        params = {
			"street": street,
			"postalcode": postal_code,
			"city": city,
			"country": country,
			"format": "json",  # Wichtig: JSON-Antwort anfordern
			"limit": 1
		}

        """
        Validiert eine Adresse aus Einzelteilen (Straße, PLZ, Ort, Land) und gibt die Koordinaten zurück.

        Args:
            street (str): Straße und Hausnummer.
            postal_code (str): Postleitzahl.
            city (str): Ort/Stadt.
            country (str): Land.

        Returns:
            dict: Ein Dictionary mit den Koordinaten und der formatierten Adresse oder None, falls die Adresse nicht gefunden wurde.
        """
        try:
            # Konstruiere die vollständige Adresszeile für die API
            adress = f"{street}, {postal_code} {city}, {country}"
            url = f"{self.base_url}/search?format=json&q={adress}"
            headers = {"User-Agent": "CRM-Erweiterung/1.0"}

            # Führe die API-Anfrage aus
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Überprüfe, ob Ergebnisse vorhanden sind
            if not data:
                logger.info(f"No results for adress: {adress}")
                return None

            # Extrahiere die relevanten Daten
            result = {
                "lat": data[0]["lat"],
                "lng": data[0]["lon"],
                "formattedAdress": data[0]["display_name"]
            }
            logger.info(f"Validated adress: {result}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating adress: {e}")
            return None
