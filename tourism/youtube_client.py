# -*- coding: utf-8 -*-
"""
Recherche de vidéos YouTube pour servir de complément de preuve visuelle
aux fiches touristiques
"""
import json
import logging
import urllib.parse
import urllib.request
import urllib.error

from django.conf import settings

logger = logging.getLogger("camway.youtube")

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def is_configured() -> bool:
    return bool(settings.YOUTUBE_API_KEY)


def build_search_query(site) -> str:
    """Construit une requête précise pour limiter le risque de faux
    résultat (nom du site + commune/région + « Cameroun »)."""
    parts = [site.name]
    if site.commune:
        parts.append(site.commune)
    parts.append(site.region.name if site.region_id else "")
    parts.append("Cameroun")
    return " ".join(p for p in parts if p)


def search_video_for_site(site, timeout=6):
    """Retourne un dict {video_id, title, channel_title, thumbnail_url,
    search_query} pour la vidéo la plus pertinente trouvée sur YouTube, ou
    None si l'API n'est pas configurée, injoignable, ou ne renvoie aucun
    résultat. Ne lève jamais d'exception vers l'appelant."""
    if not is_configured():
        return None

    query = build_search_query(site)
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 1,
        "safeSearch": "strict",
        "relevanceLanguage": "fr",
        "key": settings.YOUTUBE_API_KEY,
    }
    url = f"{YOUTUBE_SEARCH_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError) as exc:
        logger.warning("Recherche YouTube indisponible pour %s : %s", site.name, exc)
        return None

    items = data.get("items") or []
    if not items:
        return None

    item = items[0]
    video_id = item.get("id", {}).get("videoId")
    if not video_id:
        return None
    snippet = item.get("snippet", {})
    thumbnails = snippet.get("thumbnails", {})
    thumbnail_url = (
        thumbnails.get("high", {}).get("url")
        or thumbnails.get("medium", {}).get("url")
        or thumbnails.get("default", {}).get("url")
        or ""
    )
    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "channel_title": snippet.get("channelTitle", ""),
        "thumbnail_url": thumbnail_url,
        "search_query": query,
    }
