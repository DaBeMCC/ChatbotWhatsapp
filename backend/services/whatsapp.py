import requests
from config import Config


def _headers() -> dict:
    return {
        'Content-Type': 'application/json',
        'x-api-key': Config.INTERNAL_API_KEY,
    }


def enviar_mensaje_whatsapp(telefono: str, mensaje: str) -> dict:
    url = f"{Config.WHATSAPP_SERVICE_URL}/enviar"
    payload = {'telefono': telefono, 'mensaje': mensaje}
    response = requests.post(url, json=payload, headers=_headers(), timeout=10)
    response.raise_for_status()
    return response.json()


def enviar_campana_whatsapp(destinatarios: list) -> dict:
    url = f"{Config.WHATSAPP_SERVICE_URL}/enviar-campana"
    payload = {'destinatarios': destinatarios}
    response = requests.post(url, json=payload, headers=_headers(), timeout=10)
    response.raise_for_status()
    return response.json()
