# -*- coding: utf-8 -*-
"""
Informations dynamiques — météo (perspective V3, §25.3 du cahier des charges).

"""
import json
import urllib.request
import urllib.error
from datetime import datetime

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&current=temperature_2m,weather_code,wind_speed_10m"
    "&timezone=auto"
)

WEATHER_CODE_INFO = {
    0: ("Ciel dégagé", "fa-sun"),
    1: ("Principalement dégagé", "fa-cloud-sun"),
    2: ("Partiellement nuageux", "fa-cloud-sun"),
    3: ("Couvert", "fa-cloud"),
    45: ("Brouillard", "fa-smog"),
    48: ("Brouillard givrant", "fa-smog"),
    51: ("Bruine légère", "fa-cloud-rain"),
    53: ("Bruine modérée", "fa-cloud-rain"),
    55: ("Bruine dense", "fa-cloud-rain"),
    61: ("Pluie légère", "fa-cloud-rain"),
    63: ("Pluie modérée", "fa-cloud-showers-heavy"),
    65: ("Pluie forte", "fa-cloud-showers-heavy"),
    80: ("Averses légères", "fa-cloud-showers-heavy"),
    81: ("Averses modérées", "fa-cloud-showers-heavy"),
    82: ("Averses violentes", "fa-cloud-showers-heavy"),
    95: ("Orage", "fa-cloud-bolt"),
}
DEFAULT_WEATHER_LABEL = "Conditions variables"
DEFAULT_WEATHER_ICON = "fa-cloud"

FRENCH_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def _format_observed_at(raw_time):
    """Transforme l'horodatage brut d'Open-Meteo (ex. "2026-09-17T08:00",
    déjà exprimé en heure locale du lieu grâce à `timezone=auto`) en une
    chaîne lisible en français : "17 septembre 2026 à 08h00".

    Si le format change côté Open-Meteo ou en cas de valeur inattendue, on
    renvoie simplement la valeur brute plutôt que de faire planter la page
    — la donnée réelle reste visible, seule sa présentation se dégrade.
    """
    if not raw_time:
        return raw_time
    try:
        dt = datetime.fromisoformat(raw_time)
    except ValueError:
        return raw_time
    return "{day} {month} {year} à {hour:02d}h{minute:02d}".format(
        day=dt.day,
        month=FRENCH_MONTHS[dt.month - 1],
        year=dt.year,
        hour=dt.hour,
        minute=dt.minute,
    )


def get_current_weather(latitude, longitude, timeout=4):
    """Retourne un dict {temperature, wind_speed, label, icon, observed_at}
 seule leur mise en forme (date lisible,
    icône) est ajoutée côté CamWay."""
    if latitude is None or longitude is None:
        return None
    url = OPEN_METEO_URL.format(lat=latitude, lon=longitude)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode())
        current = data.get("current")
        if not current:
            return None
        code = current.get("weather_code")
        label, icon = WEATHER_CODE_INFO.get(code, (DEFAULT_WEATHER_LABEL, DEFAULT_WEATHER_ICON))
        raw_time = current.get("time")
        return {
            "temperature": current.get("temperature_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "label": label,
            "icon": icon,
            "observed_at": _format_observed_at(raw_time),
            "observed_at_raw": raw_time,
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return None
