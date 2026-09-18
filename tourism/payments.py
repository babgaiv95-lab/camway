# -*- coding: utf-8 -*-
"""
Paiement en ligne.

Pourquoi ce module ne débite jamais réellement d'argent
---------------------------------------------------------
Un vrai paiement (MTN Mobile Money, Orange Money, Stripe...) nécessite des
identifiants marchands réels (clé API, compte agréé) que cet environnement
ne possède pas. Faire semblant qu'un paiement a réussi serait trompeur :
ce module ne simule donc jamais de paiement confirmé. Tant qu'aucun vrai
prestataire n'est branché, chaque demande est enregistrée normalement,
sans paiement en ligne, et traitée manuellement.

Pour brancher un vrai prestataire
-----------------------------------
1. Créer une classe qui hérite de `PaymentProvider` et implémente
   `initiate_payment()` en appelant le SDK ou l'API HTTP du prestataire
   (ex. MTN MoMo Collection API, Orange Money Web Payment, Stripe
   PaymentIntents).
2. Lire les identifiants depuis les variables d'environnement
   (ex. `MOMO_API_KEY`, `STRIPE_SECRET_KEY`) — ne jamais les coder en dur.
3. Mettre à jour `get_active_provider()` pour retourner cette classe une
   fois les identifiants configurés.
"""
from dataclasses import dataclass


@dataclass
class PaymentResult:
    success: bool
    status: str
    reference: str
    message: str


class PaymentProvider:
    """Interface à implémenter pour un vrai prestataire de paiement."""

    provider_code = "not_connected"

    def initiate_payment(self, booking_request, amount_fcfa: int) -> PaymentResult:
        raise NotImplementedError


class NotConnectedProvider(PaymentProvider):
    """Comportement par défaut et unique tant qu'aucun prestataire réel n'a
    été intégré : le paiement en ligne n'est pas encore opérationnel."""

    provider_code = "not_connected"

    def initiate_payment(self, booking_request, amount_fcfa: int) -> PaymentResult:
        return PaymentResult(
            success=False,
            status="pending",
            reference="",
            message=(
                "Le paiement en ligne n'est pas encore connecté à un prestataire "
                "réel. Votre demande a bien été enregistrée : elle sera traitée "
                "manuellement, sans paiement en ligne pour l'instant."
            ),
        )


def get_active_provider() -> PaymentProvider:
    return NotConnectedProvider()
