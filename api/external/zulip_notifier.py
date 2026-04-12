import requests
from flask import current_app

def send_zulip_notification(subject, message):
    """
    Sendet eine Benachrichtigung an Zulip über die REST API.
    """
    # Sicherstellen, dass wir innerhalb eines Flask-Kontexts sind
    try:
        url = f"{current_app.config['ZULIP_SITE']}/api/v1/messages"

        payload = {
            "type": "stream",
            "to": current_app.config['ZULIP_STREAM'],
            "subject": subject,
            "content": message
        }

        # WICHTIG: Zulip erwartet oft 'data' statt 'json'
        response = requests.post(
            url,
            auth=(current_app.config['ZULIP_BOT_EMAIL'], current_app.config['ZULIP_API_KEY']),
            data=payload
        )
        
        # Prüfen, ob der Server einen Fehler (4xx oder 5xx) gemeldet hat
        if response.status_code != 200:
            current_app.logger.error(f"Zulip API Fehler: {response.status_code} - {response.text}")
            return False
            
        return True
        
    except Exception as e:
        # Hier fangen wir auch Fehler ab, falls current_app nicht verfügbar ist
        print(f"Fehler beim Senden der Zulip-Benachrichtigung: {e}")
        return False