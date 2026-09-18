import re
import uuid
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.text import slugify
from django.urls import reverse


# Référentiels


class Region(models.Model):
    """Une des 10 régions du Cameroun."""
    name = models.CharField("Nom", max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)

    class Meta:
        verbose_name = "Région"
        verbose_name_plural = "Régions"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    """Catégorie d'un site touristique (nature, culture, plage, faune...)."""
    name = models.CharField("Nom", max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    icon = models.CharField(
        "Icône (classe Font Awesome)", max_length=40, default="fa-solid fa-location-dot",
        help_text="Ex : fa-solid fa-leaf. Voir fontawesome.com/icons pour la liste complète."
    )

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Source(models.Model):
    """Une source d'information touristique ."""

    class SourceType(models.TextChoices):
        OFFICIELLE = "officielle", "Source officielle"
        SECONDAIRE = "secondaire", "Source secondaire fiable"

    name = models.CharField("Nom de la source", max_length=200)
    organisation = models.CharField(
        "Organisme", max_length=200, blank=True,
        help_text="Ex : MINTOUL, Collectivité territoriale, Office de tourisme..."
    )
    url = models.URLField("URL / référence documentaire", blank=True)
    source_type = models.CharField(
        "Type de source", max_length=20,
        choices=SourceType.choices, default=SourceType.SECONDAIRE
    )
    notes = models.TextField("Notes", blank=True)

    class Meta:
        verbose_name = "Source"
        verbose_name_plural = "Sources"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Fiche touristique
# ---------------------------------------------------------------------------

class TouristSite(models.Model):
    """Fiche touristique — cœur de la base de données de CamWay."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon (non publié)"
        TO_VERIFY = "to_verify", "À vérifier"
        PUBLISHED = "published", "Publié"
        ARCHIVED = "archived", "Archivé"

    class Confidence(models.TextChoices):
        HIGH = "eleve", "Élevé (source officielle vérifiée)"
        MEDIUM = "moyen", "Moyen (source secondaire fiable)"
        LOW = "faible", "Faible (à vérifier)"
        NONE = "non_verifie", "Non vérifié"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Nom", max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField("Description")

    region = models.ForeignKey(
        Region, verbose_name="Région", on_delete=models.PROTECT,
        related_name="sites"
    )
    department = models.CharField("Département", max_length=120, blank=True)
    commune = models.CharField("Commune / Ville", max_length=120, blank=True)
    category = models.ForeignKey(
        Category, verbose_name="Catégorie", on_delete=models.PROTECT,
        related_name="sites"
    )

    latitude = models.DecimalField(
        "Latitude", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        "Longitude", max_digits=9, decimal_places=6, null=True, blank=True
    )

    activities = models.TextField(
        "Activités", blank=True,
        help_text="Une activité par ligne."
    )
    accessibility = models.TextField("Conditions d'accès", blank=True)
    nearby_services = models.TextField("Services à proximité", blank=True)
    indigenous_people = models.CharField(
        "Peuple(s) autochtone(s) de la zone", max_length=200, blank=True,
        help_text="Ex : Bakweri, Bamoun, Baka... — information générale sur le peuplement de la zone, à recouper avec une source."
    )
    local_language = models.CharField(
        "Langue(s) locale(s) parlée(s)", max_length=200, blank=True,
        help_text="Ex : Mokpe, Shüpamem, Fulfulde... en plus du français/anglais, langues officielles."
    )
    contact = models.CharField("Contact", max_length=200, blank=True)
    opening_hours = models.CharField("Horaires", max_length=200, blank=True)
    price_information = models.CharField(
        "Information tarifaire", max_length=200, blank=True,
        help_text="Ne renseigner que si l'information est fiable (§8.4)."
    )
    image_url = models.URLField("Image (URL)", blank=True)
    video_file = models.FileField(
        "Vidéo (fichier)", upload_to="sites/videos/%Y/%m/", blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=["mp4", "webm", "ogg", "mov"])],
        help_text=(
            "Vidéo hébergée directement par CamWay (vidéo de vérification du site sur le "
            "terrain), lisible sans dépendre d'un service tiers ni d'une clé API externe. "
            "Formats conseillés : MP4 (H.264), quelques dizaines de Mo maximum."
        ),
    )
    video_url = models.URLField(
        "Vidéo (lien externe)", blank=True,
        help_text=(
            "Alternative au fichier ci-dessus : lien vers une vidéo déjà hébergée ailleurs "
            "(YouTube, Vimeo, site institutionnel...). Un simple lien public suffit — aucune "
            "clé d'API n'est nécessaire, la vidéo s'intègre ou s'ouvre automatiquement. "
            "Si les deux champs sont renseignés, le fichier ci-dessus est prioritaire."
        ),
    )
    video_caption = models.CharField(
        "Légende de la vidéo", max_length=200, blank=True,
        help_text="Ex. « Visite de vérification sur site, mars 2026 » — apparaît sous la vidéo.",
    )

    # Recommandation
    estimated_budget_fcfa = models.PositiveIntegerField(
        "Budget indicatif (FCFA / personne)", null=True, blank=True
    )
    recommended_duration_hours = models.PositiveIntegerField(
        "Durée de visite conseillée (heures)", null=True, blank=True
    )

    # Traçabilité (§9.4)
    sources = models.ManyToManyField(
        Source, verbose_name="Sources", related_name="sites", blank=True
    )
    status = models.CharField(
        "Statut", max_length=20, choices=Status.choices, default=Status.TO_VERIFY
    )
    verification_date = models.DateField("Date de vérification", null=True, blank=True)
    confidence_level = models.CharField(
        "Niveau de confiance", max_length=20,
        choices=Confidence.choices, default=Confidence.NONE
    )

    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Mis à jour le", auto_now=True)

    class Meta:
        verbose_name = "Fiche touristique"
        verbose_name_plural = "Fiches touristiques"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 1
            while TouristSite.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("tourism:site_detail", kwargs={"slug": self.slug})

    @property
    def activities_list(self):
        return [a.strip() for a in self.activities.splitlines() if a.strip()]

    @property
    def has_video(self):
        return bool(self.video_file) or bool(self.video_url)

    @property
    def video_embed_url(self):
        """Si `video_url` pointe vers YouTube ou Vimeo, renvoie l'URL
        d'intégration correspondante (simple iframe publique, sans clé
        d'API ni quota — pas la YouTube Data API). Sinon, renvoie None : le
        gabarit proposera alors un lien « Ouvrir la vidéo » classique."""
        if not self.video_url:
            return None
        url = self.video_url.strip()

        yt_match = re.search(
            r"(?:youtube\.com/watch\?v=|youtube\.com/shorts/|youtu\.be/|youtube\.com/embed/)"
            r"([A-Za-z0-9_-]{11})",
            url,
        )
        if yt_match:
            return f"https://www.youtube-nocookie.com/embed/{yt_match.group(1)}"

        vimeo_match = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
        if vimeo_match:
            return f"https://player.vimeo.com/video/{vimeo_match.group(1)}"

        return None

    @property
    def is_data_sufficient(self):
        """Le principe de confiance : une info ne doit pas être présentée
        comme certaine si elle n'a pas de source et de vérification (§4.3, §10.4)."""
        return self.sources.exists() and self.confidence_level in (
            self.Confidence.HIGH, self.Confidence.MEDIUM
        )


class VerificationRecord(models.Model):
    """Historique des vérifications d'une fiche (§17.2)."""
    site = models.ForeignKey(
        TouristSite, verbose_name="Fiche", on_delete=models.CASCADE,
        related_name="verification_records"
    )
    verified_by = models.CharField("Vérifié par", max_length=150)
    verification_date = models.DateField("Date de vérification")
    confidence_level = models.CharField(
        "Niveau de confiance", max_length=20,
        choices=TouristSite.Confidence.choices
    )
    notes = models.TextField("Notes", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Enregistrement de vérification"
        verbose_name_plural = "Enregistrements de vérification"
        ordering = ["-verification_date"]

    def __str__(self):
        return f"{self.site.name} – {self.verification_date}"


# ---------------------------------------------------------------------------
# Itinéraires
# ---------------------------------------------------------------------------

class Itinerary(models.Model):
    """Un programme de visite construit par un visiteur."""
    session_key = models.CharField(
        "Clé de session", max_length=64, db_index=True,
        help_text="Identifie le visiteur non authentifié (MVP sans compte obligatoire)."
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Compte visiteur", null=True, blank=True,
        on_delete=models.CASCADE, related_name="itineraries",
        help_text="Renseigné uniquement si le visiteur s'est connecté (fonctionnalité hors MVP, §6.2)."
    )
    title = models.CharField("Titre", max_length=200, default="Mon itinéraire CamWay")
    duration_days = models.PositiveIntegerField("Durée (jours)", default=1)
    budget_fcfa = models.PositiveIntegerField("Budget indicatif (FCFA)", null=True, blank=True)
    interests = models.CharField("Centres d'intérêt", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Itinéraire"
        verbose_name_plural = "Itinéraires"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    @property
    def total_estimated_budget(self):
        total = 0
        has_value = False
        for item in self.items.select_related("site"):
            if item.site.estimated_budget_fcfa:
                total += item.site.estimated_budget_fcfa
                has_value = True
        return total if has_value else None


class ItineraryItem(models.Model):
    """Une étape (un site) au sein d'un itinéraire."""
    itinerary = models.ForeignKey(
        Itinerary, verbose_name="Itinéraire", on_delete=models.CASCADE,
        related_name="items"
    )
    site = models.ForeignKey(
        TouristSite, verbose_name="Site", on_delete=models.CASCADE,
        related_name="itinerary_items"
    )
    day_number = models.PositiveIntegerField("Jour", default=1)
    order = models.PositiveIntegerField("Ordre", default=0)
    notes = models.CharField("Notes", max_length=300, blank=True)

    class Meta:
        verbose_name = "Étape d'itinéraire"
        verbose_name_plural = "Étapes d'itinéraire"
        ordering = ["day_number", "order"]

    def __str__(self):
        return f"J{self.day_number} – {self.site.name}"


# ---------------------------------------------------------------------------
# Dialogue conversationnel
# ---------------------------------------------------------------------------

class Conversation(models.Model):
    session_key = models.CharField("Clé de session", max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Conversation {self.pk} ({self.created_at:%d/%m/%Y})"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Visiteur"
        ASSISTANT = "assistant", "CamWay"

    conversation = models.ForeignKey(
        Conversation, verbose_name="Conversation", on_delete=models.CASCADE,
        related_name="messages"
    )
    role = models.CharField("Rôle", max_length=10, choices=Role.choices)
    content = models.TextField("Contenu")
    referenced_sites = models.ManyToManyField(
        TouristSite, verbose_name="Sites référencés", blank=True,
        related_name="messages"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"


# ---------------------------------------------------------------------------
# HORS MVP — Perspective V2
# Guides, agences, hébergements, prestataires d'activités.
# ---------------------------------------------------------------------------

class Provider(models.Model):
    """Un professionnel du tourisme (guide, agence, hébergement, prestataire).

    Cette fonctionnalité correspond à la perspective V2 du cahier des charges
    (§25.1) et était explicitement hors du périmètre du MVP (§7.2). Elle
    reprend le même principe de traçabilité que les fiches touristiques :
    un prestataire non vérifié n'est jamais présenté comme fiable.
    """

    class ProviderType(models.TextChoices):
        GUIDE = "guide", "Guide touristique"
        AGENCY = "agence", "Agence de voyage"
        LODGING = "hebergement", "Hébergement"
        ACTIVITY = "activite", "Prestataire d'activités"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Nom", max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    provider_type = models.CharField(
        "Type de prestataire", max_length=20, choices=ProviderType.choices
    )
    region = models.ForeignKey(
        Region, verbose_name="Région d'intervention", on_delete=models.PROTECT,
        related_name="providers"
    )
    sites = models.ManyToManyField(
        TouristSite, verbose_name="Sites concernés", blank=True, related_name="providers"
    )
    description = models.TextField("Description", blank=True)
    contact_phone = models.CharField("Téléphone", max_length=50, blank=True)
    contact_email = models.EmailField("E-mail", blank=True)
    website = models.URLField("Site web", blank=True)

    sources = models.ManyToManyField(
        Source, verbose_name="Sources", related_name="providers", blank=True
    )
    status = models.CharField(
        "Statut", max_length=20, choices=TouristSite.Status.choices,
        default=TouristSite.Status.TO_VERIFY
    )
    confidence_level = models.CharField(
        "Niveau de confiance", max_length=20,
        choices=TouristSite.Confidence.choices, default=TouristSite.Confidence.NONE
    )
    verification_date = models.DateField("Date de vérification", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prestataire vérifié"
        verbose_name_plural = "Prestataires vérifiés (réseau touristique V2)"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 1
            while Provider.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("tourism:provider_detail", kwargs={"slug": self.slug})

    @property
    def is_verified(self):
        return self.sources.exists() and self.confidence_level in (
            TouristSite.Confidence.HIGH, TouristSite.Confidence.MEDIUM
        )


class BookingRequest(models.Model):
    """Demande de réservation (non garantie, traitée manuellement)."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente de traitement"
        CONTACTED = "contacted", "Visiteur contacté"
        CONFIRMED = "confirmed", "Confirmée par le prestataire"
        DECLINED = "declined", "Déclinée / indisponible"

    site = models.ForeignKey(
        TouristSite, verbose_name="Site concerné", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="booking_requests"
    )
    provider = models.ForeignKey(
        Provider, verbose_name="Prestataire sollicité", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="booking_requests"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Compte visiteur", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="booking_requests"
    )
    full_name = models.CharField("Nom complet", max_length=150)
    email = models.EmailField("E-mail")
    phone = models.CharField("Téléphone", max_length=50, blank=True)
    requested_date = models.DateField("Date souhaitée", null=True, blank=True)
    participants = models.PositiveIntegerField("Nombre de participants", default=1)
    message = models.TextField("Message / précisions", blank=True)
    status = models.CharField("Statut", max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Demande de réservation"
        verbose_name_plural = "Demandes de réservation (hors MVP)"
        ordering = ["-created_at"]

    def __str__(self):
        target = self.provider.name if self.provider else (self.site.name if self.site else "—")
        return f"Demande {self.full_name} → {target} ({self.get_status_display()})"


class Payment(models.Model):
    """Architecture d'un paiement — voir tourism/payments.py.

    Aucun prestataire de paiement réel n'étant configuré, ce modèle sert de
    point d'intégration : son statut reste « not_connected » tant qu'un
    vrai prestataire (MTN MoMo, Orange Money, Stripe...) n'a pas été
    branché, avec ses propres identifiants API. Aucun paiement n'est
    jamais simulé comme confirmé.
    """

    class Provider_(models.TextChoices):
        NOT_CONNECTED = "not_connected", "Aucun prestataire réel connecté"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        FAILED = "failed", "Échec"

    booking_request = models.OneToOneField(
        BookingRequest, verbose_name="Demande associée", on_delete=models.CASCADE,
        related_name="payment"
    )
    amount_fcfa = models.PositiveIntegerField("Montant (FCFA)")
    provider = models.CharField(
        "Prestataire de paiement", max_length=20,
        choices=Provider_.choices, default=Provider_.NOT_CONNECTED
    )
    status = models.CharField("Statut", max_length=20, choices=Status.choices, default=Status.PENDING)
    reference = models.CharField("Référence", max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def __str__(self):
        return f"Paiement {self.amount_fcfa} FCFA — {self.get_status_display()}"
