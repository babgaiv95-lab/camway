from django.conf import settings


def site_config(request):
    """Rend disponible dans tous les templates la configuration publique
    (jamais de clé secrète : la clé Google Maps JS est conçue pour être
    visible côté navigateur, à condition de la restreindre par domaine
    dans la console Google Cloud)."""
    return {
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "ai_enabled": bool(settings.GEMINI_API_KEY),
    }
