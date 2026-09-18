from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .models import (
    TouristSite, Region, Category, Conversation, Message,
    Itinerary, ItineraryItem, Provider, BookingRequest, Payment,
)
from .forms import (
    ExploreFilterForm, RecommendationForm, ChatForm, ItinerarySetupForm,
    RegisterForm, BookingRequestForm, MonumentImageForm,
)
from . import nlp_engine
from . import payments as payments_module
from . import weather as weather_module
from . import vision as vision_module
from .itinerary_utils import merge_session_itinerary


def _published():
    return TouristSite.objects.filter(status=TouristSite.Status.PUBLISHED).select_related("region", "category")


def _ensure_session(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


# ---------------------------------------------------------------------------
# Accueil
# ---------------------------------------------------------------------------

def home(request):
    highlighted = _published().order_by("-updated_at")[:6]
    regions = Region.objects.all()
    categories = Category.objects.all()
    stats = {
        "sites": _published().count(),
        "regions": regions.count(),
        "verified": _published().filter(
            confidence_level__in=[TouristSite.Confidence.HIGH, TouristSite.Confidence.MEDIUM]
        ).count(),
    }
    return render(request, "tourism/home.html", {
        "highlighted": highlighted,
        "regions": regions,
        "categories": categories,
        "stats": stats,
    })


# ---------------------------------------------------------------------------
# F1 — Explorer les destinations
# ---------------------------------------------------------------------------

def explore(request):
    form = ExploreFilterForm(request.GET or None)
    sites = _published()

    if form.is_valid():
        q = form.cleaned_data.get("q")
        region = form.cleaned_data.get("region")
        category = form.cleaned_data.get("category")
        if q:
            sites = sites.filter(
                Q(name__icontains=q) | Q(commune__icontains=q) | Q(description__icontains=q)
                | Q(activities__icontains=q)
            )
        if region:
            sites = sites.filter(region=region)
        if category:
            sites = sites.filter(category=category)

    return render(request, "tourism/explore.html", {
        "form": form,
        "sites": sites,
    })


def site_detail(request, slug):
    site = get_object_or_404(
        TouristSite.objects.select_related("region", "category").prefetch_related(
            "sources", "verification_records"
        ),
        slug=slug,
    )
    related = _published().filter(region=site.region).exclude(pk=site.pk)[:3]
    in_itinerary = False
    session_key = request.session.session_key
    if session_key:
        in_itinerary = ItineraryItem.objects.filter(
            itinerary__session_key=session_key, site=site
        ).exists()

    # Points de référence à afficher sur la carte (autres sites de la même
    # région disposant de coordonnées) : sert de repères géographiques
    # complémentaires sur la vue satellite.
    reference_points = [
        {
            "name": r.name,
            "lat": float(r.latitude),
            "lng": float(r.longitude),
            "url": reverse("tourism:site_detail", args=[r.slug]),
        }
        for r in related
        if r.latitude and r.longitude
    ]

    weather = weather_module.get_current_weather(site.latitude, site.longitude)

    providers = Provider.objects.filter(
        Q(sites=site) | Q(region=site.region), status=TouristSite.Status.PUBLISHED
    ).distinct()[:4]

    return render(request, "tourism/site_detail.html", {
        "site": site,
        "related": related,
        "reference_points": reference_points,
        "in_itinerary": in_itinerary,
        "weather": weather,
        "providers": providers,
    })


# ---------------------------------------------------------------------------
# F2 — Dialogue avec CamWay
# ---------------------------------------------------------------------------

def chat(request):
    session_key = _ensure_session(request)
    conversation = Conversation.objects.filter(session_key=session_key).order_by("-created_at").first()
    if conversation is None:
        conversation = Conversation.objects.create(session_key=session_key)

    if request.method == "POST":
        form = ChatForm(request.POST)
        if form.is_valid():
            user_message = form.cleaned_data["message"]

            history = [
                (m.role, m.content)
                for m in conversation.messages.order_by("created_at")
            ]

            Message.objects.create(conversation=conversation, role=Message.Role.USER, content=user_message)

            answer, sites, intent_data = nlp_engine.answer_message(user_message, history=history)

            assistant_msg = Message.objects.create(
                conversation=conversation, role=Message.Role.ASSISTANT, content=answer
            )
            if sites:
                assistant_msg.referenced_sites.set(sites)
            return redirect("tourism:chat")
    else:
        form = ChatForm()

    chat_messages = conversation.messages.prefetch_related("referenced_sites").order_by("created_at")
    return render(request, "tourism/chat.html", {
        "form": form,
        "chat_messages": chat_messages,
    })


@require_POST
def chat_reset(request):
    session_key = _ensure_session(request)
    Conversation.objects.filter(session_key=session_key).delete()
    return redirect("tourism:chat")


# ---------------------------------------------------------------------------
# F3 — Recommandation personnalisée
# ---------------------------------------------------------------------------

DURATION_HOURS = {"half_day": 4, "1": 8, "2": 24, "5": 72, "10": 168}


def recommend(request):
    form = RecommendationForm(request.GET or None)
    results = []
    searched = False

    if request.GET and form.is_valid():
        searched = True
        qs = _published()

        region = form.cleaned_data.get("region")
        budget = form.cleaned_data.get("budget")
        interests = form.cleaned_data.get("interests")
        duration = form.cleaned_data.get("duration")

        if region:
            qs = qs.filter(region=region)
        if budget:
            qs = qs.filter(Q(estimated_budget_fcfa__lte=budget) | Q(estimated_budget_fcfa__isnull=True))
        if interests:
            interest_q = Q()
            for interest in interests:
                interest_q |= (
                    Q(category__slug__icontains=interest)
                    | Q(description__icontains=interest)
                    | Q(activities__icontains=interest)
                )
            qs = qs.filter(interest_q)
        if duration:
            max_hours = DURATION_HOURS.get(duration)
            if max_hours:
                qs = qs.filter(
                    Q(recommended_duration_hours__lte=max_hours) | Q(recommended_duration_hours__isnull=True)
                )

        results = qs.distinct()[:12]

    ai_summary = None
    if searched and results:
        ai_summary = nlp_engine.generate_ai_answer(
            "Résume en 3 phrases pourquoi ces destinations correspondent à la demande, "
            "en texte brut sans Markdown (pas d'astérisques ni de tirets de liste), "
            "sans en inventer d'autres.",
            list(results),
        )

    return render(request, "tourism/recommend.html", {
        "form": form,
        "results": results,
        "searched": searched,
        "ai_summary": ai_summary,
    })


# ---------------------------------------------------------------------------
# F4 — Construction d'itinéraire
# ---------------------------------------------------------------------------

def _get_or_scope_itinerary_qs(request):
    """Hors MVP (§6.2) : si le visiteur est connecté, l'itinéraire est lié à
    son compte (persistant sur tous ses appareils) ; sinon, à sa session."""
    session_key = _ensure_session(request)
    if request.user.is_authenticated:
        return Itinerary.objects.filter(user=request.user), {"user": request.user}
    return Itinerary.objects.filter(session_key=session_key, user__isnull=True), {"session_key": session_key}


def itinerary_view(request):
    qs, owner_kwargs = _get_or_scope_itinerary_qs(request)
    itinerary = qs.order_by("-updated_at").first()

    if request.method == "POST":
        setup_form = ItinerarySetupForm(request.POST)
        if setup_form.is_valid():
            if itinerary is None:
                session_key = _ensure_session(request)
                user = request.user if request.user.is_authenticated else None
                itinerary = Itinerary.objects.create(session_key=session_key, user=user)
            itinerary.title = setup_form.cleaned_data["title"]
            itinerary.duration_days = setup_form.cleaned_data["duration_days"]
            itinerary.save()
            messages.success(request, "Itinéraire mis à jour.")
            return redirect("tourism:itinerary")
    else:
        initial = {}
        if itinerary:
            initial = {"title": itinerary.title, "duration_days": itinerary.duration_days}
        setup_form = ItinerarySetupForm(initial=initial)

    items = []
    days_range = range(1, (itinerary.duration_days if itinerary else 1) + 1)
    if itinerary:
        items = itinerary.items.select_related("site", "site__region", "site__category")

    return render(request, "tourism/itinerary.html", {
        "itinerary": itinerary,
        "items": items,
        "days_range": days_range,
        "setup_form": setup_form,
    })


@require_POST
def itinerary_add(request, slug):
    session_key = _ensure_session(request)
    site = get_object_or_404(TouristSite, slug=slug, status=TouristSite.Status.PUBLISHED)
    qs, _ = _get_or_scope_itinerary_qs(request)
    itinerary = qs.order_by("-updated_at").first()
    if itinerary is None:
        user = request.user if request.user.is_authenticated else None
        itinerary = Itinerary.objects.create(
            session_key=session_key, user=user, title="Mon itinéraire CamWay"
        )
    day_number = int(request.POST.get("day_number", 1))
    next_order = itinerary.items.filter(day_number=day_number).count()
    ItineraryItem.objects.get_or_create(
        itinerary=itinerary, site=site, day_number=day_number,
        defaults={"order": next_order},
    )
    if day_number > itinerary.duration_days:
        itinerary.duration_days = day_number
        itinerary.save()
    messages.success(request, f"« {site.name} » a été ajouté à votre itinéraire.")
    next_url = request.POST.get("next") or "tourism:itinerary"
    return redirect(next_url)


@require_POST
def itinerary_remove(request, item_id):
    qs, _ = _get_or_scope_itinerary_qs(request)
    item = get_object_or_404(ItineraryItem, pk=item_id, itinerary__in=qs)
    item.delete()
    messages.info(request, "Étape retirée de l'itinéraire.")
    return redirect("tourism:itinerary")


# ---------------------------------------------------------------------------
# F5 — Découverte contextuelle du patrimoine
# ---------------------------------------------------------------------------

def heritage(request, slug):
    site = get_object_or_404(TouristSite, slug=slug, status=TouristSite.Status.PUBLISHED)
    return render(request, "tourism/heritage.html", {"site": site})


# ---------------------------------------------------------------------------
# HORS MVP — Compte visiteur (§6.2, §25)
# ---------------------------------------------------------------------------

def register(request):
    if request.user.is_authenticated:
        return redirect("tourism:account")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            session_key = _ensure_session(request)
            merge_session_itinerary(session_key, user)
            auth_login(request, user)
            messages.success(request, f"Bienvenue sur CamWay, {user.username} !")
            return redirect("tourism:account")
    else:
        form = RegisterForm()
    return render(request, "tourism/register.html", {"form": form})


class CamWayLoginView(auth_views.LoginView):
    """Connexion à un compte EXISTANT."""
    template_name = "tourism/login.html"

    def form_valid(self, form):
        session_key = _ensure_session(self.request)
        response = super().form_valid(form)  # authentifie + renouvelle la session
        merge_session_itinerary(session_key, form.get_user())
        return response


@login_required
def account(request):
    itineraries = Itinerary.objects.filter(user=request.user).order_by("-updated_at")
    bookings = BookingRequest.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "tourism/account.html", {
        "itineraries": itineraries,
        "bookings": bookings,
    })


# ---------------------------------------------------------------------------
# HORS MVP — Réseau touristique vérifié (§25.1)
# ---------------------------------------------------------------------------

def providers_list(request):
    providers = Provider.objects.filter(status=TouristSite.Status.PUBLISHED).select_related("region")
    provider_type = request.GET.get("type")
    if provider_type:
        providers = providers.filter(provider_type=provider_type)
    return render(request, "tourism/providers_list.html", {
        "providers": providers,
        "provider_types": Provider.ProviderType.choices,
        "selected_type": provider_type,
    })


def provider_detail(request, slug):
    provider = get_object_or_404(
        Provider.objects.select_related("region").prefetch_related("sources", "sites"),
        slug=slug,
    )
    return render(request, "tourism/provider_detail.html", {"provider": provider})


# ---------------------------------------------------------------------------
# HORS MVP — Réservation et paiement (§7.2 : explicitement exclus du MVP)
# ---------------------------------------------------------------------------

def booking_request(request, provider_slug=None, site_slug=None):
    provider = get_object_or_404(Provider, slug=provider_slug) if provider_slug else None
    site = get_object_or_404(TouristSite, slug=site_slug) if site_slug else None

    initial = {}
    if request.user.is_authenticated:
        initial = {"full_name": request.user.get_full_name() or request.user.username, "email": request.user.email}

    if request.method == "POST":
        form = BookingRequestForm(request.POST, initial=initial)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.provider = provider
            booking.site = site
            if request.user.is_authenticated:
                booking.user = request.user
            booking.save()

            # Hors MVP — paiement : voir tourism/payments.py. Ne simule jamais
            # un débit réel ; informe honnêtement l'utilisateur du statut.
            estimated_amount = site.estimated_budget_fcfa if site else None
            payment_message = None
            if estimated_amount:
                provider_impl = payments_module.get_active_provider()
                result = provider_impl.initiate_payment(booking, estimated_amount)
                Payment.objects.create(
                    booking_request=booking,
                    amount_fcfa=estimated_amount,
                    provider=provider_impl.provider_code,
                    status=result.status,
                    reference=result.reference,
                )
                payment_message = result.message

            return render(request, "tourism/booking_confirmation.html", {
                "booking": booking,
                "payment_message": payment_message,
            })
    else:
        form = BookingRequestForm(initial=initial)

    return render(request, "tourism/booking_request_form.html", {
        "form": form, "provider": provider, "site": site,
    })


# ---------------------------------------------------------------------------
# HORS MVP — Assistant multimodal : identification d'image (§25.2)
# ---------------------------------------------------------------------------

def identify(request):
    result = None
    if request.method == "POST":
        form = MonumentImageForm(request.POST, request.FILES)
        if form.is_valid():
            image_file = form.cleaned_data["image"]
            result = vision_module.identify_monument(
                image_file.read(), mime_type=image_file.content_type or "image/jpeg"
            )
    else:
        form = MonumentImageForm()
    return render(request, "tourism/identify.html", {"form": form, "result": result})



def mentions_legales(request):
    return render(request, "tourism/legal/mentions_legales.html")


def confidentialite(request):
    return render(request, "tourism/legal/confidentialite.html")


def cgu(request):
    return render(request, "tourism/legal/cgu.html")
