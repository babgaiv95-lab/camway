# -*- coding: utf-8 -*-
"""
Moteur de compréhension du langage naturel et de recherche augmentée
(architecture décrite au §10 du cahier des charges).

Principe (§10.3 — Recherche augmentée par les données) :
    Utilisateur -> Analyse de la demande -> Recherche dans les données
                -> Sélection des informations -> Génération de la réponse

Ce moteur est volontairement fondé sur des règles (mots-clés, filtres
structurés) plutôt que sur un modèle génératif externe : il ne peut donc
pas « halluciner » une destination absente de la base (§10.4 — politique
de réponse prudente). Il peut être remplacé plus tard par un appel à un
service LLM tout en conservant la même interface, sans jamais court-
circuiter l'étape de recherche dans les données.
"""
import re
import unicodedata
from django.db.models import Q

from .models import TouristSite, Region, Category
from . import gemini_client

DURATION_PATTERNS = [
    (re.compile(r"(\d+)\s*(?:jour|jours|j)\b"), "days"),
    (re.compile(r"(\d+)\s*(?:heure|heures|h)\b"), "hours"),
]

BUDGET_PATTERN = re.compile(r"(\d[\d\s.]{2,})\s*(?:fcfa|f\.?cfa|francs?)?", re.IGNORECASE)

INTEREST_KEYWORDS = {
    "nature": ["nature", "naturel", "naturelle", "forêt", "foret", "parc", "faune", "animaux",
               "randonnée", "randonnee", "montagne", "cascade", "chute", "reserve", "réserve"],
    "culture": ["culture", "culturel", "culturelle", "histoire", "historique", "patrimoine",
                "palais", "royaume", "tradition", "musée", "musee", "artisanat"],
    "plage": ["plage", "mer", "océan", "ocean", "balnéaire", "balneaire", "côte", "cote", "sable"],
    "aventure": ["aventure", "trek", "escalade", "sport", "randonnée", "randonnee"],
}


SYSTEM_INSTRUCTION = (
    "Tu es CamWay, un assistant touristique conversationnel pour le Cameroun. "
    "Tu dialogues avec le même visiteur sur plusieurs tours de discussion : "
    "sers-toi de l'historique de la conversation fourni pour comprendre le "
    "contexte, les relances courtes (« et pour 2 jours ? », « moins cher ? », "
    "« et à Kribi ? ») et pour éviter de répéter ce que tu as déjà dit. Tu dois "
    "répondre UNIQUEMENT à partir des fiches touristiques fournies dans le "
    "message courant, jamais à partir de connaissances générales. Si les "
    "fiches fournies ne permettent pas de répondre précisément, dis-le "
    "clairement plutôt que d'inventer une information, un prix, un horaire ou "
    "une distance. Réponds dans la même langue que le visiteur (français par "
    "défaut, anglais s'il écrit en anglais), de façon naturelle, concise et "
    "chaleureuse, comme dans une vraie conversation, et cite les noms des "
    "sites utilisés. Si une fiche est marquée comme non vérifiée, mentionne-le. "
    "IMPORTANT : réponds en texte brut uniquement, sans aucune syntaxe "
    "Markdown (pas d'astérisques **, pas de tirets de liste, pas de dièses #, "
    "pas de titres) : l'interface n'interprète pas le Markdown et l'afficherait "
    "tel quel. Pour une liste, utilise simplement des phrases séparées par des "
    "retours à la ligne."
)


def _serialize_sites_for_prompt(sites):
    lines = []
    for site in sites:
        lines.append(
            f"- {site.name} (région : {site.region.name}, catégorie : {site.category.name})\n"
            f"  Description : {site.description}\n"
            f"  Activités : {', '.join(site.activities_list) or 'non renseignées'}\n"
            f"  Budget indicatif : {site.estimated_budget_fcfa or 'non renseigné'} FCFA\n"
            f"  Durée conseillée : {site.recommended_duration_hours or 'non renseignée'} h\n"
            f"  Niveau de confiance des données : {site.get_confidence_level_display()}"
        )
    return "\n".join(lines) if lines else "(aucune fiche correspondante trouvée dans la base)"


HISTORY_TURNS = 8  # nombre de messages précédents (visiteur + CamWay confondus) transmis à Gemini


def generate_ai_answer(user_message: str, sites: list, history: list | None = None):
    """Étape de génération du RAG : Gemini reçoit les fiches déjà trouvées
    par recherche dans la base (voir search_sites) pour le tour courant,
    ainsi que l'historique du dialogue (si fourni) afin de répondre de façon
    réellement interactive et de garder le contexte d'un message à l'autre.
    Retourne None si Gemini n'est pas configuré ou indisponible — l'appelant
    doit alors utiliser build_answer()."""
    context = _serialize_sites_for_prompt(sites)
    prompt = (
        f"Question du visiteur : {user_message}\n\n"
        f"Fiches touristiques disponibles pour cette question (seules sources autorisées) :\n{context}"
    )
    if history:
        return gemini_client.generate_conversation(
            SYSTEM_INSTRUCTION, history[-HISTORY_TURNS:], prompt, max_output_tokens=700
        )
    return gemini_client.generate(SYSTEM_INSTRUCTION, prompt, max_output_tokens=700)


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return text


def analyze_intent(message: str) -> dict:
    """Analyse la demande de l'utilisateur : intention, destination, durée,
    budget, centres d'intérêt, contraintes (§10.2)."""
    norm = _normalize(message)

    intent = "explore"
    if any(w in norm for w in ["itineraire", "programme", "organiser", "jours a", "jours pour"]):
        intent = "itinerary"
    elif any(w in norm for w in ["recommand", "conseill", "suggere", "que puis-je", "que puis je"]):
        intent = "recommendation"
    elif any(w in norm for w in ["histoire", "origine", "importance", "en savoir plus", "culturel"]):
        intent = "heritage"

    # Destination : on cherche une région ou une commune connue dans le message
    destination_region = None
    for region in Region.objects.all():
        if _normalize(region.name) in norm:
            destination_region = region
            break

    destination_site = None
    for site in TouristSite.objects.filter(status=TouristSite.Status.PUBLISHED):
        if _normalize(site.commune) and _normalize(site.commune) in norm:
            destination_site = site
            break
        if _normalize(site.name) in norm:
            destination_site = site
            break

    # Durée
    duration_days, duration_hours = None, None
    for pattern, unit in DURATION_PATTERNS:
        match = pattern.search(norm)
        if match:
            if unit == "days":
                duration_days = int(match.group(1))
            else:
                duration_hours = int(match.group(1))

    # Budget
    budget = None
    if "budget" in norm or "fcfa" in norm or "franc" in norm:
        match = BUDGET_PATTERN.search(norm)
        if match:
            digits = re.sub(r"[^\d]", "", match.group(1))
            if digits:
                budget = int(digits)

    # Centres d'intérêt
    interests = []
    for interest, keywords in INTEREST_KEYWORDS.items():
        if any(kw in norm for kw in keywords):
            interests.append(interest)

    # Catégorie explicitement citée
    category = None
    for cat in Category.objects.all():
        if _normalize(cat.name) in norm:
            category = cat
            break

    return {
        "intent": intent,
        "region": destination_region,
        "site": destination_site,
        "category": category,
        "duration_days": duration_days,
        "duration_hours": duration_hours,
        "budget": budget,
        "interests": interests,
        "raw_message": message,
    }


def search_sites(intent_data: dict, limit: int = 6):
    """Recherche dans les données (§10.3) : ne renvoie que des fiches
    publiées, potentiellement filtrées par région / catégorie / budget.

    Si un site précis a été identifié dans la demande (ex. « Kribi »,
    « le parc de Waza »), il est toujours renvoyé en premier — sinon la
    réponse (règles ou Gemini) risque de porter sur des sites sans rapport
    avec la question posée."""
    site = intent_data.get("site")
    if site:
        related = list(
            TouristSite.objects.filter(status=TouristSite.Status.PUBLISHED, region=site.region)
            .exclude(pk=site.pk)
            .select_related("region", "category")[: max(limit - 1, 0)]
        )
        return [site] + related

    qs = TouristSite.objects.filter(status=TouristSite.Status.PUBLISHED)

    if intent_data.get("region"):
        qs = qs.filter(region=intent_data["region"])

    if intent_data.get("category"):
        qs = qs.filter(category=intent_data["category"])

    if intent_data.get("interests"):
        interest_q = Q()
        for interest in intent_data["interests"]:
            interest_q |= Q(category__slug__icontains=interest) | Q(description__icontains=interest) \
                | Q(activities__icontains=interest) | Q(category__name__icontains=interest)
        qs = qs.filter(interest_q)

    if intent_data.get("budget"):
        qs = qs.filter(
            Q(estimated_budget_fcfa__lte=intent_data["budget"]) | Q(estimated_budget_fcfa__isnull=True)
        )

    return list(qs.distinct()[:limit])


def build_answer(intent_data: dict, sites: list) -> str:
    """Formule une réponse naturelle strictement fondée sur les données
    trouvées (§10.1, point 4). Politique de prudence : si rien n'est
    trouvé, CamWay l'indique explicitement plutôt que d'inventer (§10.4)."""

    if intent_data.get("site") and not sites:
        sites = [intent_data["site"]]

    if not sites:
        base = "Je n'ai pas trouvé, dans les données actuellement vérifiées de CamWay, " \
               "de site correspondant précisément à votre demande."
        if intent_data.get("region"):
            base += f" Aucune fiche publiée n'est encore disponible pour la région {intent_data['region'].name}."
        base += " Vous pouvez reformuler votre recherche, explorer les destinations, " \
                "ou revenir plus tard : la base est enrichie progressivement (§9)."
        return base

    intent = intent_data["intent"]
    lines = []

    if intent == "itinerary":
        lines.append(
            "Voici des sites qui pourraient s'intégrer à votre programme de visite :"
        )
    elif intent == "recommendation":
        lines.append("D'après les données disponibles, voici ce que je peux vous recommander :")
    elif intent == "heritage":
        lines.append("Voici les informations disponibles, limitées aux sources exploitées par CamWay :")
    else:
        lines.append("Voici ce que j'ai trouvé dans la base touristique de CamWay :")

    for site in sites:
        confidence_note = ""
        if not site.is_data_sufficient:
            confidence_note = " (information à vérifier — source insuffisante)"
        duration = f" · visite conseillée : {site.recommended_duration_hours} h" if site.recommended_duration_hours else ""
        budget = f" · budget indicatif : {site.estimated_budget_fcfa:,} FCFA".replace(",", " ") \
            if site.estimated_budget_fcfa else ""
        lines.append(f"— {site.name} ({site.region.name}){duration}{budget}{confidence_note}")

    lines.append(
        "Ces informations proviennent de fiches sourcées ; consultez chaque fiche pour "
        "le détail des sources et la date de vérification."
    )
    return "\n".join(lines)


def answer_message(message: str, history: list | None = None):
    """Point d'entrée principal du moteur conversationnel (F2).

    Architecture RAG : 1) recherche dans la base (search_sites) ;
    2) génération par Gemini à partir des fiches trouvées pour ce tour ET de
    l'historique du dialogue (`history`), si configuré, pour un échange
    réellement interactif ; 3) repli automatique sur une réponse fondée
    uniquement sur les données si Gemini est indisponible — jamais de
    réponse inventée."""
    intent_data = analyze_intent(message)
    sites = search_sites(intent_data)

    ai_answer = (
        generate_ai_answer(message, sites, history=history)
        if sites or gemini_client.is_configured() else None
    )
    answer = ai_answer or build_answer(intent_data, sites)
    return answer, sites, intent_data
