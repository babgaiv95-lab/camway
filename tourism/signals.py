# -*- coding: utf-8 -*-
"""
Rattachement de l'itinéraire au compte visiteur lors de la connexion
(§6.2, §25). `register()` (tourism/views.py) le fait déjà à l'inscription ;
ce signal applique la même règle à chaque connexion, pour que les
étapes ajoutées à l'itinéraire avant de se connecter (session anonyme)
ne soient jamais perdues une fois le visiteur identifié.
"""
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def attach_session_itinerary_to_user(sender, request, user, **kwargs):

    old_session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    if not old_session_key:
        return
    from .models import Itinerary

    # On ne rattache que les itinéraires de session qui n'appartiennent
    # encore à aucun compte, pour ne jamais réassigner l'itinéraire d'un
    # autre visiteur (§10.4 — jamais de mélange de données entre comptes).
    Itinerary.objects.filter(session_key=old_session_key, user__isnull=True).update(user=user)
