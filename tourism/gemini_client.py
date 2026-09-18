# -*- coding: utf-8 -*-
"""
Client Gemini partagé par le dialogue (F2), la recommandation (F3) et
l'identification d'image. Utilisé uniquement en complément de la
recherche dans la base de données (RAG) : le modèle ne reçoit jamais la
consigne de répondre librement, seulement de reformuler ou d'expliquer
les résultats déjà trouvés dans la base. S'il n'est pas configuré ou que
l'appel échoue, l'appelant doit toujours pouvoir retomber sur une réponse
fondée uniquement sur les données, sans jamais rien inventer.
"""
import logging
import re

from django.conf import settings

logger = logging.getLogger("camway.gemini")


def is_configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _client():
    if not is_configured():
        return None
    from google import genai
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _strip_markdown(text: str) -> str:
    """L'interface de CamWay affiche le texte de Gemini tel quel, sans
    moteur de rendu Markdown : on retire donc systématiquement la syntaxe
    Markdown (gras, listes à puces, titres) pour ne jamais laisser
    apparaître des ** ou des * bruts à l'écran."""
    if not text:
        return text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # **gras**
    text = re.sub(r"__(.+?)__", r"\1", text)       # __gras__
    text = re.sub(r"(?m)^[ \t]*[*\-]\s+", "• ", text)  # * item / - item -> • item
    text = re.sub(r"(?m)^#{1,6}\s*", "", text)     # # Titre
    text = text.replace("*", "").replace("_", "")  # tout marqueur résiduel
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def generate_conversation(system_instruction: str, history: list, prompt: str,
                           max_output_tokens: int = 700):
    """Comme generate(), mais transmet l'historique du dialogue à Gemini pour un
    vrai échange interactif (le modèle voit les tours précédents et peut donc
    répondre à des relances du type « et pour 2 jours ? », « et moins cher ? »,
    sans que le visiteur ait à tout répéter). `history` est une liste de tuples
    (role, texte) avec role parmi 'user' / 'assistant', du plus ancien au plus
    récent. Retourne None si Gemini n'est pas configuré ou en cas d'échec —
    l'appelant doit alors toujours pouvoir retomber sur une réponse fondée
    uniquement sur les données (jamais de texte inventé)."""
    client = _client()
    if client is None:
        return None
    try:
        from google.genai import types
        contents = []
        for role, text in history:
            if not text:
                continue
            contents.append(types.Content(
                role="model" if role == "assistant" else "user",
                parts=[types.Part.from_text(text=text)],
            ))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
                max_output_tokens=max_output_tokens,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            logger.warning("Gemini (conversation) a répondu sans texte exploitable.")
            return None
        return _strip_markdown(text) or None
    except Exception as exc:
        logger.warning("Échec de l'appel Gemini conversationnel (modèle=%s) : %s", settings.GEMINI_MODEL, exc)
        return None


def generate(system_instruction: str, prompt: str, max_output_tokens: int = 500):
    """Retourne le texte généré, ou None en cas d'échec/absence de clé —
    jamais un texte inventé côté appelant. En cas d'échec, l'erreur est
    tracée dans les logs serveur (pas affichée au visiteur) pour permettre
    de diagnostiquer une clé invalide, un quota dépassé, etc."""
    client = _client()
    if client is None:
        return None
    try:
        from google.genai import types
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
                max_output_tokens=max_output_tokens,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            logger.warning("Gemini a répondu sans texte exploitable (contenu peut-être filtré).")
            return None
        return _strip_markdown(text) or None
    except Exception as exc:
        logger.warning("Échec de l'appel Gemini (modèle=%s) : %s", settings.GEMINI_MODEL, exc)
        return None


def generate_with_image(system_instruction: str, prompt: str, image_bytes: bytes,
                         mime_type: str = "image/jpeg", max_output_tokens: int = 400):
    client = _client()
    if client is None:
        return None
    try:
        from google.genai import types
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[prompt, part],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                max_output_tokens=max_output_tokens,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            logger.warning("Gemini (image) a répondu sans texte exploitable.")
            return None
        return _strip_markdown(text) or None
    except Exception as exc:
        logger.warning("Échec de l'appel Gemini vision (modèle=%s) : %s", settings.GEMINI_MODEL, exc)
        return None
