"""Fusion de l'itinéraire anonyme (lié à la session) vers le compte d'un
visiteur qui se connecte ou s'inscrit — pour qu'il ne perde jamais son
travail en cours de construction
"""
from .models import Itinerary


def merge_session_itinerary(session_key, user):
    if not session_key:
        return
    session_itineraries = Itinerary.objects.filter(session_key=session_key, user__isnull=True)
    if not session_itineraries.exists():
        return

    existing = Itinerary.objects.filter(user=user).order_by("-updated_at").first()
    if existing is None:
        session_itineraries.update(user=user)
        return

    for session_itinerary in session_itineraries:
        for item in session_itinerary.items.all():
            if not existing.items.filter(site=item.site, day_number=item.day_number).exists():
                existing.items.create(site=item.site, day_number=item.day_number, order=item.order)
        session_itinerary.delete()
