# -*- coding: utf-8 -*-
"""
Identification d'un lieu à partir d'une photo, via l'API Gemini (vision),
avec une étape de recoupement (RAG) contre la base de données de CamWay :
l'hypothèse du modèle n'est présentée comme correspondant à une fiche
connue que si une correspondance est effectivement retrouvée dans la base.
Sans clé Gemini configurée, ou en cas d'échec, aucun résultat n'est inventé.
"""
from dataclasses import dataclass

from . import gemini_client
from . import nlp_engine

SYSTEM_INSTRUCTION = (
    "Tu analyses une photo qui pourrait montrer un site touristique du "
    "Cameroun. Donne une hypothèse prudente (jamais une certitude) sur ce "
    "que représente l'image, en une ou deux phrases : type de lieu, éléments "
    "visibles, région probable si identifiable. Précise explicitement s'il "
    "s'agit d'une simple supposition à vérifier. Réponds en texte brut, sans "
    "Markdown (pas d'astérisques ni de mise en forme)."
)


@dataclass
class IdentificationResult:
    available: bool
    hypothesis: str = ""
    matched_site: object = None
    message: str = ""


def identify_monument(image_bytes: bytes, mime_type: str = "image/jpeg") -> IdentificationResult:
    if not gemini_client.is_configured():
        return IdentificationResult(
            available=False,
            message=(
                "L'identification d'image n'est pas configurée sur cette instance "
                " CamWay préfère ne "
                "proposer aucune hypothèse plutôt que de risquer une identification "
                "erronée. Décrivez le lieu dans le module « Dialoguer avec CamWay » "
                "pour une recherche fondée sur la base de données."
            ),
        )

    hypothesis = gemini_client.generate_with_image(
        SYSTEM_INSTRUCTION,
        "Que représente cette photo ?",
        image_bytes,
        mime_type=mime_type,
    )
    if not hypothesis:
        return IdentificationResult(
            available=False,
            message="L'appel au service d'identification a échoué ou n'a rien retourné.",
        )

    # Étape RAG : on tente de recouper l'hypothèse du modèle avec la base
    # de données de CamWay plutôt que de faire confiance à Gemini seul.
    intent_data = nlp_engine.analyze_intent(hypothesis)
    matches = nlp_engine.search_sites(intent_data, limit=1)
    matched_site = matches[0] if matches else None

    result = IdentificationResult(
        available=True,
        hypothesis=hypothesis,
        message=(
            "Hypothèse générée par un modèle d'IA à partir de l'image : à vérifier, "
            "ce n'est pas une certitude."
        ),
    )
    result.matched_site = matched_site
    return result
