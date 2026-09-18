from django.urls import path
from . import views

app_name = "tourism"

urlpatterns = [
    path("", views.home, name="home"),
    path("explorer/", views.explore, name="explore"),
    path("site/<slug:slug>/", views.site_detail, name="site_detail"),
    path("site/<slug:slug>/patrimoine/", views.heritage, name="heritage"),
    path("chat/", views.chat, name="chat"),
    path("chat/reset/", views.chat_reset, name="chat_reset"),
    path("recommandation/", views.recommend, name="recommend"),
    path("itineraire/", views.itinerary_view, name="itinerary"),
    path("itineraire/ajouter/<slug:slug>/", views.itinerary_add, name="itinerary_add"),
    path("itineraire/retirer/<int:item_id>/", views.itinerary_remove, name="itinerary_remove"),

    # --- Hors MVP : compte visiteur (§6.2, §25) ---
    path("compte/inscription/", views.register, name="register"),
    path("compte/", views.account, name="account"),

    # --- Hors MVP : réseau touristique vérifié (§25.1) ---
    path("prestataires/", views.providers_list, name="providers_list"),
    path("prestataires/<slug:slug>/", views.provider_detail, name="provider_detail"),

    # --- Hors MVP : réservation et paiement (§7.2) ---
    path("reserver/prestataire/<slug:provider_slug>/", views.booking_request, name="booking_request_provider"),
    path("reserver/site/<slug:site_slug>/", views.booking_request, name="booking_request_site"),

    # --- Hors MVP : identification d'image (§25.2) ---
    path("identifier/", views.identify, name="identify"),

    # --- Pages institutionnelles / légales ---
    path("mentions-legales/", views.mentions_legales, name="mentions_legales"),
    path("confidentialite/", views.confidentialite, name="confidentialite"),
    path("cgu/", views.cgu, name="cgu"),
]
