# 🇨🇲 CamWay — Assistant touristique intelligent du Cameroun

---

## Fonctionnalités

| # | Fonction | Où dans le code |
|---|----------|------------------|
| F1 | Explorer les destinations (recherche, filtres région/catégorie) | `tourism/views.py::explore` |
| F2 | Dialogue en langage naturel avec CamWay | `tourism/nlp_engine.py`, `views.py::chat` |
| F3 | Recommandation personnalisée (durée, budget, intérêts) | `views.py::recommend` |
| F4 | Construction d'itinéraire jour par jour | `views.py::itinerary_*` |
| F5 | Découverte contextuelle du patrimoine | `views.py::heritage` |

Chaque fiche touristique (`TouristSite`) porte ses **sources**, sa
**date de vérification** et son **niveau de confiance**. Le
moteur conversationnel (`nlp_engine.py`) ne **recherche que dans la base
de données** — il ne peut donc pas halluciner une destination qui n'existe
pas (politique de réponse prudente, §10.4).

L'espace d'administration Django (`/admin/`) sert d'espace administratif
pour créer/modifier des fiches, gérer les sources et
enregistrer les vérifications, sans être exposé au public.

Au-delà du MVP, cette livraison inclut aussi des comptes visiteurs, une
carte interactive, une météo en temps réel, un réseau de prestataires
vérifiés et des demandes de réservation — voir la section
« Limites du MVP et évolutions » plus bas pour le détail exact de ce qui
est réellement fonctionnel et de ce qui reste un point d'intégration.

---

## Stack technique

Le cahier des charges cible Next.js + Supabase (§12.1). Cette implémentation
respecte l'esprit fonctionnel et l'architecture de recherche augmentée avec
une stack **Django** (au choix, en fonction des compétences de l'équipe) :

- **Backend / Frontend** : Django 5 (rendu serveur, templates)
- **Base de données** : SQLite en développement (facilement remplaçable par
  PostgreSQL en production — `DATABASES` dans `camway/settings.py`)
- **IA / NLP** : moteur de règles maison (`nlp_engine.py`), remplaçable par
  un appel à un service LLM externe sans changer l'interface `answer_message()`
- **Frontend** : CSS responsive « mobile first » sans framework (`tourism/static/tourism/css/style.css`)

---

## ⚙️ Configuration (fichier .env)

Un fichier `.env` est déjà présent à la racine du projet : renseignez-y vos
propres clés (optionnelles — sans elles, CamWay fonctionne normalement en
mode "base de données seule").

| Variable | Rôle |
|---|---|
| `GEMINI_API_KEY` | Active le dialogue, la recommandation et l'identification d'image générés par Google Gemini (RAG : le modèle ne reçoit que les fiches déjà trouvées dans la base, jamais de connaissance libre) |
| `GEMINI_MODEL` | Modèle Gemini à utiliser (par défaut `gemini-2.0-flash`) |
| `GOOGLE_MAPS_API_KEY` | Optionnelle : active Google Maps sur chaque fiche site. Sans elle (ou en cas d'échec), la carte utilise automatiquement OpenStreetMap/Leaflet, gratuit et sans clé |
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` | Configuration Django standard |

Sans `GEMINI_API_KEY`, le dialogue et la recommandation basculent automatiquement
sur un moteur de règles fondé uniquement sur la base de données (jamais d'invention).
La carte interactive, elle, s'affiche toujours : avec Google Maps si une clé est
configurée et valide, sinon avec OpenStreetMap/Leaflet — jamais d'élément cassé
ni de carte manquante. Sans clé du tout, l'application reste entièrement fonctionnelle.

---

## 🚀 Installation locale

```bash
# 1. Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Appliquer les migrations
python manage.py migrate

# 4. Peupler la base avec des destinations réelles et sourcées
python manage.py seed_data

# 5. Créer un compte administrateur
python manage.py createsuperuser

# 6. Lancer le serveur de développement
python manage.py runserver
```

Rendez-vous sur **http://127.0.0.1:8000/** pour l'application, et
**http://127.0.0.1:8000/admin/** pour l'espace d'administration.

### Compte administrateur
Aucun compte administrateur n'est créé automatiquement par `seed_data` : créez le vôtre
avec `python manage.py createsuperuser` (étape 5 ci-dessus) et choisissez un mot de passe
fort. Ne partagez jamais d'identifiants par défaut dans un dépôt ou une documentation.

---

---

## 🏛️ Mise en production pour un usage institutionnel/gouvernemental

Le site est fonctionnel en développement dès l'installation locale ci-dessus. Pour un
déploiement réel (ministère, organisme public ou tout usage au-delà d'une démo), suivez
cette checklist — plusieurs points sont désormais **appliqués automatiquement** par
`camway/settings.py` (le serveur refuse de démarrer en production tant qu'ils ne sont pas
configurés), d'autres restent à votre charge.

### ✅ Déjà en place, à activer via `.env`

| Élément | Comment l'activer |
|---|---|
| `DEBUG=False` obligatoire en prod | `DJANGO_DEBUG=0` |
| Clé secrète dédiée (le serveur refuse de démarrer sans, hors dev) | `DJANGO_SECRET_KEY=...` (générez avec `python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| Domaines autorisés restreints (pas de `*`) | `DJANGO_ALLOWED_HOSTS=camway.mintoul.gov.cm` |
| HTTPS forcé, cookies sécurisés, HSTS, `X-Frame-Options: DENY`, anti-sniffing | Automatique dès `DJANGO_DEBUG=0` |
| Fichiers statiques servis sans serveur externe (WhiteNoise, compressés) | Automatique — pensez à lancer `python manage.py collectstatic` au déploiement |
| Base de données PostgreSQL (recommandée en production, SQLite gère mal les écritures concurrentes) | `DATABASE_URL=postgres://...` |
| Pages d'erreur 404/500 personnalisées, sans stack trace exposée | Automatique dès `DJANGO_DEBUG=0` |
| Serveur de production (remplace `runserver`) | `Procfile` fourni : `gunicorn camway.wsgi:application` |
| Mentions légales, politique de confidentialité, CGU | Pages créées (`/mentions-legales/`, `/confidentialite/`, `/cgu/`) — **à compléter avec les informations réelles de l'organisme et faire valider par le service juridique** avant publication (voir l'encart dans chaque page) |

Validez la configuration avec l'audit officiel de Django avant chaque mise en ligne :
```bash
python manage.py check --deploy
```

### ⚠️ Reste à votre charge (hors périmètre de ce livrable)

- **Compte administrateur** : créez-en un dédié (`createsuperuser`) avec un mot de passe
  fort ; aucun compte n'est préconfiguré.
- **Nom de domaine et certificat HTTPS** réels (ex. via le prestataire d'hébergement de
  l'État ou l'ANTIC).
- **Sauvegardes régulières** de la base de données et des fichiers médias (vidéos/images
  uploadées) — non automatisées ici.
- **Stockage des fichiers médias en production** : par défaut, les vidéos/images uploadées
  sont stockées sur le disque du serveur (`MEDIA_ROOT`). Pour un hébergement avec disque
  éphémère (ex. certains PaaS), prévoyez un stockage persistant (volume monté ou stockage
  objet type S3 — nécessite une configuration `django-storages` non incluse ici).
- **Protection contre les tentatives de connexion abusives** (brute-force) sur `/admin/` et
  la connexion visiteur : non implémentée (envisager `django-axes` ou une limitation au
  niveau du reverse proxy).
- **Bilinguisme français/anglais** : le site est actuellement en français uniquement, alors
  que le Cameroun est officiellement bilingue. L'infrastructure Django i18n (`USE_I18N`)
  est active, mais la traduction effective des templates reste à faire.
- **Validation juridique** des trois pages légales par un juriste de l'organisme porteur
  (les champs entre crochets doivent être complétés).
- **Journalisation et supervision** en production (actuellement, seule la console est
  configurée dans `LOGGING` — prévoyez un envoi vers un fichier ou un service de
  supervision).

---

## 🗂️ Données incluses

La commande `seed_data` crée :
- les **10 régions** du Cameroun ;
- **4 catégories** (nature & faune, culture & patrimoine, plages & littoral, aventure & randonnée) ;
- des **sources réelles** : MINTOUL (ministère du Tourisme), UNESCO, Ape Action Africa, Wikipédia (secondaire) ;
- **10 fiches touristiques réelles** avec description, activités, budget indicatif,
  coordonnées GPS, image et traçabilité des sources : Kribi (plage & chutes
  de la Lobé), parc national de Waza, pic de Rhumsiki, palais royal des
  Bamoun (Foumban), jardin botanique de Limbe, Down Beach (Limbe), sanctuaire
  de primates de la Méfou, réserve de faune du Dja (patrimoine mondial
  UNESCO), chutes de la Vina (Ngaoundéré), mont Cameroun (Buea) — chacune
  avec, lorsque l'information est documentée, le peuple autochtone de la
  zone et la ou les langues locales parlées (ex. Bakweri/Mokpe à Limbe,
  Bamoun/Shüpamem à Foumban, Baka au Dja), en plus du français et de
  l'anglais, langues officielles.

Les images sont chargées depuis Wikimedia Commons (licence libre). Pour un
usage en production, prévoyez vos propres visuels ou un accord avec le
MINTOUL / les offices de tourisme locaux (§9.3).

---

## 🔐 Principe de confiance et anti-hallucination (§4.3, §10.4)

- Une fiche sans source **ne peut pas** afficher le badge « ✓ Vérifié ».
- Le chatbot ne répond qu'à partir des fiches **publiées** de la base ; en
  l'absence de résultat, il l'indique explicitement plutôt que d'inventer
  une réponse.
- Le workflow d'administration (`Status` : brouillon → à vérifier → publié)
  reproduit le principe *Collecte → Vérification → Validation → Publication* (§17.3).

---

## 🗺️ Structure du projet

```
camway/
├── camway/                # Configuration du projet (settings, urls)
├── tourism/
│   ├── models.py          # Région, Catégorie, Source, TouristSite (+ vidéo), Itinéraire, Conversation,
│   │                       #   + hors MVP : Provider, BookingRequest, Payment
│   ├── nlp_engine.py       # Analyse d'intention + recherche augmentée (§10)
│   ├── payments.py         # Hors MVP : architecture de paiement, sans simulation trompeuse
│   ├── weather.py          # Hors MVP : météo réelle (Open-Meteo, sans clé)
│   ├── vision.py           # Identification d'image via Gemini (RAG), nécessite GEMINI_API_KEY
│   ├── gemini_client.py    # Client Gemini partagé (dialogue, recommandation, image)
│   ├── itinerary_utils.py  # Rattachement de l'itinéraire de session au compte (connexion/inscription)
│   ├── views.py            # F1 à F5 + vues hors MVP (compte, prestataires, réservation, identification, pages légales)
│   ├── forms.py
│   ├── admin.py             # Espace d'administration (§17)
│   ├── management/commands/seed_data.py
│   ├── templates/
│   │   ├── 404.html, 500.html  # Pages d'erreur personnalisées
│   │   └── tourism/            # Gabarits HTML responsives (+ tourism/legal/ pour les pages légales)
│   └── static/tourism/     # CSS / JS
├── requirements.txt
├── Procfile                # Déploiement production (gunicorn)
└── manage.py
```

---

## 🔭 Limites du MVP (§24) et évolutions (§25)

Ce livrable respecte strictement le périmètre du MVP dans son cœur
fonctionnel (F1–F5). Une seconde itération a toutefois implémenté, **à la
demande explicite du commanditaire et de façon volontairement honnête**,
certaines fonctionnalités hors MVP listées au et aux perspectives
V2/V3 du §25. Le principe suivi partout : ne jamais simuler qu'une
fonctionnalité marche réellement quand ce n'est pas le cas.

### ✅ Hors MVP — réellement fonctionnel

| Fonctionnalité | Référence cahier des charges | Détail |
|---|---|---|
| Comptes visiteurs (inscription/connexion) | Itinéraires persistants liés au compte plutôt qu'à la seule session |
| Carte interactive | — | Google Maps si `GOOGLE_MAPS_API_KEY` est configurée ; sinon (ou en cas d'échec) bascule automatique sur OpenStreetMap/Leaflet, gratuit et sans clé — la carte s'affiche donc toujours |
| Météo en temps réel | §25.3 « Informations dynamiques » | API publique Open-Meteo (gratuite, sans clé). Si l'appel échoue, **aucune valeur n'est inventée** : message d'indisponibilité affiché |
| Réseau de prestataires vérifiés | §25.1 | Modèle `Provider` avec la même traçabilité (sources, niveau de confiance) que les fiches touristiques |
| Demandes de réservation | §7.2 (exclu du MVP) | Formulaire réel, enregistré en base, visible dans l'admin — présenté comme une *demande non garantie*, jamais comme une réservation confirmée |

###  Hors MVP — architecture prête

| Fonctionnalité | Référence | Pourquoi ce n'est pas simulé |
|---|---|---|
| **Paiement en ligne** | `tourism/payments.py` fournit une interface (`PaymentProvider`) prête à brancher sur MTN MoMo, Orange Money ou Stripe, mais **aucun identifiant marchand réel n'est disponible ici**. Le visiteur voit toujours « paiement non connecté à un prestataire réel » — CamWay ne simule jamais de paiement confirmé. |
| **Identification d'un lieu par photo** | Assistant multimodal | `tourism/vision.py` appelle l'API Gemini (vision) **si** `GEMINI_API_KEY` est configurée, puis recoupe l'hypothèse avec la base de données (RAG) avant de l'afficher. Sans clé, CamWay répond honnêtement « identification non disponible » plutôt que de deviner un site. |

### Comment activer ces options (facultatif)

```bash
# Dialogue, recommandation et identification d'image par IA (clé Google Gemini)
# -> renseignez GEMINI_API_KEY dans le fichier .env

# Carte interactive
# -> renseignez GOOGLE_MAPS_API_KEY dans le fichier .env
```

### Ce qui reste volontairement absent

- Couverture exhaustive du territoire, disponibilité garantie des
  services, identification automatique fiable sans intervention humaine :
  toujours hors périmètre, quelle que soit la version (§24).
- Aucune coordonnée commerciale (téléphone, e-mail d'agences/hôtels) n'a
  été inventée : le prestataire de démonstration préchargé
  (Ape Action Africa) est le seul dont l'activité est publiquement
  vérifiable via sa propre source. Ajoutez vos propres prestataires réels
  depuis `/admin/`.

---

*Chef de projet : Biroua Wandeya Boniface · Collaborateur : Babgai Ouyak Venant — Version 1.0, 2026.*
