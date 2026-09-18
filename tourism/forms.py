from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Region, Category, BookingRequest


class ExploreFilterForm(forms.Form):
    q = forms.CharField(
        label="Rechercher", required=False,
        widget=forms.TextInput(attrs={"placeholder": "Nom du site, ville, activité..."})
    )
    region = forms.ModelChoiceField(
        label="Région", queryset=Region.objects.all(), required=False, empty_label="Toutes les régions"
    )
    category = forms.ModelChoiceField(
        label="Catégorie", queryset=Category.objects.all(), required=False, empty_label="Toutes les catégories"
    )


class RecommendationForm(forms.Form):
    DURATION_CHOICES = [
        ("", "Peu importe"),
        ("half_day", "Une demi-journée"),
        ("1", "1 jour"),
        ("2", "2-3 jours"),
        ("5", "4-7 jours"),
        ("10", "Plus d'une semaine"),
    ]
    INTEREST_CHOICES = [
        ("nature", "Nature et faune"),
        ("culture", "Culture et patrimoine"),
        ("plage", "Plages et littoral"),
        ("aventure", "Aventure et randonnée"),
    ]

    region = forms.ModelChoiceField(
        label="Région ou destination souhaitée", queryset=Region.objects.all(),
        required=False, empty_label="Peu importe"
    )
    duration = forms.ChoiceField(label="Durée disponible", choices=DURATION_CHOICES, required=False)
    budget = forms.IntegerField(
        label="Budget indicatif (FCFA / personne)", required=False, min_value=0,
        widget=forms.NumberInput(attrs={"placeholder": "Exemple : 25000"})
    )
    interests = forms.MultipleChoiceField(
        label="Centres d'intérêt", choices=INTEREST_CHOICES, required=False,
        widget=forms.CheckboxSelectMultiple
    )


class ChatForm(forms.Form):
    message = forms.CharField(
        label="", required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "Ex : « Que puis-je visiter à Kribi en 2 jours ? »",
            "autocomplete": "off",
        })
    )


class ItinerarySetupForm(forms.Form):
    title = forms.CharField(label="Titre de l'itinéraire", initial="Mon itinéraire CamWay", max_length=200)
    duration_days = forms.IntegerField(label="Nombre de jours", min_value=1, max_value=30, initial=2)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label="E-mail", required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class BookingRequestForm(forms.ModelForm):
    class Meta:
        model = BookingRequest
        fields = ["full_name", "email", "phone", "requested_date", "participants", "message"]
        widgets = {
            "requested_date": forms.DateInput(attrs={"type": "date"}),
            "message": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "full_name": "Nom complet",
            "email": "E-mail",
            "phone": "Téléphone",
            "requested_date": "Date souhaitée",
            "participants": "Nombre de participants",
            "message": "Message (précisions, disponibilités...)",
        }


class MonumentImageForm(forms.Form):
    image = forms.ImageField(
        label="Photo du lieu ou du monument",
        help_text="Fonctionnalité expérimentale (§25.2) : une hypothèse prudente, jamais une certitude.",
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/*",
            "capture": "environment",  # ouvre directement l'appareil photo sur mobile (repli si pas d'aperçu live)
            "id": "camera-file-input",
            "data-camera-file-input": "true",
            "hidden": "hidden",  # l'input natif reste utilisable au clavier/lecteur d'écran mais l'UI est pilotée par camera-capture.js
        }),
    )
