from django.contrib import admin
from .models import (
    Region, Category, Source, TouristSite, VerificationRecord,
    Itinerary, ItineraryItem, Conversation, Message,
    Provider, BookingRequest, Payment,
)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "organisation", "source_type", "url")
    list_filter = ("source_type",)
    search_fields = ("name", "organisation")


class VerificationRecordInline(admin.TabularInline):
    model = VerificationRecord
    extra = 0
    fields = ("verified_by", "verification_date", "confidence_level", "notes")


@admin.register(TouristSite)
class TouristSiteAdmin(admin.ModelAdmin):
    list_display = (
        "name", "region", "category", "status", "confidence_level",
        "verification_date", "has_source", "has_video",
    )
    list_filter = ("status", "confidence_level", "region", "category")
    search_fields = ("name", "commune", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("sources",)
    inlines = [VerificationRecordInline]
    fieldsets = (
        ("Identification", {
            "fields": ("name", "slug", "description", "image_url")
        }),
        ("Vidéo (preuve / présentation)", {
            "fields": ("video_file", "video_url", "video_caption"),
            "description": (
                "Ajoutez une vidéo directement (fichier MP4, hébergée par CamWay"
                ") ou collez un lien externe (YouTube, Vimeo...). Si les "
                "deux sont renseignés, le fichier uploadé est utilisé en priorité."
            ),
        }),
        ("Localisation", {
            "fields": ("region", "department", "commune", "latitude", "longitude")
        }),
        ("Contenu touristique", {
            "fields": ("category", "activities", "accessibility", "nearby_services",
                       "contact", "opening_hours", "price_information")
        }),
        ("Peuplement et langues", {
            "fields": ("indigenous_people", "local_language")
        }),
        ("Recommandation", {
            "fields": ("estimated_budget_fcfa", "recommended_duration_hours")
        }),
        ("Traçabilité et validation", {
            "fields": ("sources", "status", "verification_date", "confidence_level")
        }),
    )

    @admin.display(boolean=True, description="Source ?")
    def has_source(self, obj):
        return obj.sources.exists()

    @admin.display(boolean=True, description="Vidéo ?")
    def has_video(self, obj):
        return obj.has_video


@admin.register(VerificationRecord)
class VerificationRecordAdmin(admin.ModelAdmin):
    list_display = ("site", "verified_by", "verification_date", "confidence_level")
    list_filter = ("confidence_level",)


class ItineraryItemInline(admin.TabularInline):
    model = ItineraryItem
    extra = 0


@admin.register(Itinerary)
class ItineraryAdmin(admin.ModelAdmin):
    list_display = ("title", "session_key", "duration_days", "updated_at")
    inlines = [ItineraryItemInline]


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "content", "created_at")
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "session_key", "created_at")
    inlines = [MessageInline]


# --- Hors MVP : réseau touristique vérifié, réservations, paiements ---

@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "provider_type", "region", "status", "confidence_level")
    list_filter = ("provider_type", "status", "region")
    filter_horizontal = ("sources", "sites")
    prepopulated_fields = {"slug": ("name",)}


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "site", "provider", "requested_date", "status", "created_at")
    list_filter = ("status",)
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("booking_request", "amount_fcfa", "provider", "status", "created_at")
    list_filter = ("provider", "status")


admin.site.site_header = "CamWay — Administration"
admin.site.site_title = "CamWay Admin"
admin.site.index_title = "Gestion de la base touristique"
