# -*- coding: utf-8 -*-
import datetime
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from tourism.models import (
    Region, Category, Source, TouristSite, VerificationRecord, Provider,
)

WIKIMEDIA_FILEPATH = "https://commons.wikimedia.org/wiki/Special:FilePath/{}"

REGIONS = [
    "Adamaoua", "Centre", "Est", "Extrême-Nord", "Littoral",
    "Nord", "Nord-Ouest", "Ouest", "Sud", "Sud-Ouest",
]

CATEGORIES = [
    ("Nature et faune", "fa-solid fa-leaf"),
    ("Culture et patrimoine", "fa-solid fa-landmark"),
    ("Plages et littoral", "fa-solid fa-umbrella-beach"),
    ("Aventure et randonnée", "fa-solid fa-person-hiking"),
]


def img(filename):
    return WIKIMEDIA_FILEPATH.format(filename.replace(" ", "_"))


class Command(BaseCommand):
    help = "Peuple la base CamWay avec des régions, catégories, sources et fiches touristiques réelles."

    def handle(self, *args, **options):
        self.stdout.write("Création des régions...")
        regions = {}
        for name in REGIONS:
            regions[name], _ = Region.objects.get_or_create(name=name)

        self.stdout.write("Création des catégories...")
        categories = {}
        for name, icon in CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=name, defaults={"icon": icon})
            categories[name] = cat

        self.stdout.write("Création des sources...")
        mintoul, _ = Source.objects.get_or_create(
            name="MINTOUL — Sites touristiques",
            defaults={
                "organisation": "Ministère du Tourisme et des Loisirs du Cameroun",
                "url": "https://mintoul.gov.cm/cameroun-en-decouverte/sites-touristiques/",
                "source_type": Source.SourceType.OFFICIELLE,
            },
        )
        mintoul_portail, _ = Source.objects.get_or_create(
            name="MINTOUL — Portail officiel",
            defaults={
                "organisation": "Ministère du Tourisme et des Loisirs du Cameroun",
                "url": "https://mintoul.gov.cm/",
                "source_type": Source.SourceType.OFFICIELLE,
            },
        )
        unesco, _ = Source.objects.get_or_create(
            name="UNESCO — Centre du patrimoine mondial",
            defaults={
                "organisation": "UNESCO",
                "url": "https://whc.unesco.org/en/list/407/",
                "source_type": Source.SourceType.OFFICIELLE,
            },
        )
        wikipedia_fr, _ = Source.objects.get_or_create(
            name="Wikipédia (secondaire, à recouper)",
            defaults={
                "organisation": "Fondation Wikimédia",
                "url": "https://fr.wikipedia.org/",
                "source_type": Source.SourceType.SECONDAIRE,
            },
        )
        ape_action, _ = Source.objects.get_or_create(
            name="Ape Action Africa",
            defaults={
                "organisation": "Ape Action Africa (gestionnaire du sanctuaire de la Mefou)",
                "url": "https://www.apeactionafrica.org/mefou-primate-sanctuary",
                "source_type": Source.SourceType.SECONDAIRE,
            },
        )

        today = datetime.date.today()

        sites_data = [
            dict(
                name="Plage et chutes de la Lobé, Kribi",
                region="Sud", department="Océan", commune="Kribi",
                category="Plages et littoral",
                description=(
                    "Kribi est une station balnéaire du littoral sud camerounais, réputée pour "
                    "ses plages de sable et la proximité des chutes de la Lobé, l'une des rares "
                    "chutes d'eau au monde à se jeter directement dans l'océan. La ville est un "
                    "port de pêche traditionnel et un point de départ pour découvrir la forêt "
                    "littorale et les communautés pygmées de l'arrière-pays."
                ),
                activities="Baignade\nDétente sur la plage\nExcursion aux chutes de la Lobé\nDégustation de poisson braisé\nPirogue traditionnelle",
                accessibility="Accessible par route bitumée depuis Douala (environ 150 km, 2h30).",
                nearby_services="Hôtels et résidences en bord de mer, restaurants de fruits de mer, marché aux poissons.",
                indigenous_people="Batanga, Mabéa et Yassa (peuples côtiers de tradition bantoue et de pêche)",
                local_language="Batanga ; français (langue officielle) largement parlé",
                image=img("Lobé beach kribi Cameroon.jpg"),
                latitude=2.9350, longitude=9.9100,
                estimated_budget_fcfa=15000, recommended_duration_hours=6,
                confidence=TouristSite.Confidence.MEDIUM,
                sources=[mintoul, wikipedia_fr],
            ),
            dict(
                name="Parc national de Waza",
                region="Extrême-Nord", department="Logone-et-Chari", commune="Waza",
                category="Nature et faune",
                description=(
                    "Le parc national de Waza, créé en 1934 et devenu réserve de biosphère UNESCO "
                    "en 1979, protège une savane semi-aride abritant éléphants, girafes, lions et "
                    "une grande diversité d'antilopes. C'est l'un des principaux sites de safari "
                    "d'Afrique centrale, particulièrement riche en observations pendant la saison sèche."
                ),
                activities="Safari en véhicule 4x4\nObservation de la faune\nObservation ornithologique",
                accessibility="Guide obligatoire pour la visite du parc. Accès depuis Maroua.",
                nearby_services="Campements et hébergements à proximité de l'entrée du parc.",
                indigenous_people="Kotoko, Mousgoum et communautés peules (Mbororo) de la plaine du Logone",
                local_language="Fulfulde (peul) comme langue véhiculaire ; kotoko et mousgoum localement",
                image=img("Elephants around tree in Waza, Cameroon.jpg"),
                latitude=11.3330, longitude=14.7330,
                estimated_budget_fcfa=25000, recommended_duration_hours=8,
                confidence=TouristSite.Confidence.HIGH,
                sources=[mintoul, wikipedia_fr],
            ),
            dict(
                name="Pic de Rhumsiki (monts Mandara)",
                region="Extrême-Nord", department="Mayo-Tsanaga", commune="Rhumsiki",
                category="Nature et faune",
                description=(
                    "Rhumsiki est un village des monts Mandara célèbre pour son paysage volcanique "
                    "de pitons rocheux, dont le célèbre pic de Rhumsiki (pic de Kapsiki). La région "
                    "est habitée par le peuple Kapsiki, connu pour son artisanat et son architecture "
                    "traditionnelle en pierre."
                ),
                activities="Randonnée\nPhotographie de paysage\nDécouverte de l'artisanat Kapsiki\nVisite de villages traditionnels",
                accessibility="À environ 55 km de Mokolo, piste praticable en saison sèche.",
                nearby_services="Petits campements et guides locaux.",
                indigenous_people="Kapsiki (Kirdi des monts Mandara)",
                local_language="Kapsiki (aussi appelé psikye)",
                image=img("Rhumsiki Peak.jpg"),
                latitude=10.4830, longitude=13.6000,
                estimated_budget_fcfa=10000, recommended_duration_hours=5,
                confidence=TouristSite.Confidence.MEDIUM,
                sources=[wikipedia_fr],
            ),
            dict(
                name="Palais royal des Bamoun, Foumban",
                region="Ouest", department="Noun", commune="Foumban",
                category="Culture et patrimoine",
                description=(
                    "Construit en 1917 par le roi Ibrahim Njoya, le palais royal de Foumban est le "
                    "siège du royaume Bamoun et abrite aujourd'hui le Musée du palais, consacré à "
                    "l'histoire de la dynastie depuis 1394. Njoya y créa notamment l'écriture bamoun "
                    "à la fin du XIXe siècle. Foumban est aussi un centre artisanal majeur du Cameroun."
                ),
                activities="Visite du musée du palais\nDécouverte de l'artisanat (bronze, perles, bois)\nVisite du marché des arts",
                accessibility="Ville accessible par route depuis Bafoussam (environ 80 km).",
                nearby_services="Ateliers d'artisans, hôtels, marché artisanal.",
                indigenous_people="Bamoun (royaume Bamoun)",
                local_language="Shüpamem (langue bamoun, dotée de sa propre écriture créée par le roi Njoya)",
                image=img("Bamun sultan palace.jpg"),
                latitude=5.7170, longitude=10.9170,
                estimated_budget_fcfa=5000, recommended_duration_hours=3,
                confidence=TouristSite.Confidence.HIGH,
                sources=[mintoul, wikipedia_fr],
            ),
            dict(
                name="Jardin botanique de Limbe",
                region="Sud-Ouest", department="Fako", commune="Limbe",
                category="Nature et faune",
                description=(
                    "Créé en 1892 durant la période coloniale allemande, le jardin botanique de "
                    "Limbe est le principal jardin botanique du Cameroun. Situé entre l'océan et "
                    "le mont Cameroun, il conserve une riche collection de plantes tropicales et "
                    "constitue l'une des principales attractions touristiques du Sud-Ouest."
                ),
                activities="Promenade botanique\nObservation de la flore tropicale\nVisite guidée",
                accessibility="Situé dans la ville de Limbe, facilement accessible à pied ou en taxi local.",
                nearby_services="Restaurants, hôtels, plages de sable noir à proximité.",
                indigenous_people="Bakweri, peuple autochtone du pied du mont Cameroun",
                local_language="Mokpe (langue bakweri) ; anglais très répandu (zone anglophone)",
                image=img("Limbe Botanic Garden.jpg"),
                latitude=4.0134, longitude=9.2120,
                estimated_budget_fcfa=3000, recommended_duration_hours=3,
                confidence=TouristSite.Confidence.HIGH,
                sources=[mintoul, wikipedia_fr],
            ),
            dict(
                name="Plage de Down Beach, Limbe",
                region="Sud-Ouest", department="Fako", commune="Limbe",
                category="Plages et littoral",
                description=(
                    "Down Beach est une plage de sable volcanique noir au cœur de Limbe, au pied "
                    "du mont Cameroun. C'est un lieu de vie locale animé : pêcheurs, vendeurs de "
                    "poisson braisé et de fruits de mer, avec une vue sur l'océan et le volcan."
                ),
                activities="Baignade\nDégustation de fruits de mer grillés\nPromenade en bord de mer",
                accessibility="Accès direct depuis le centre-ville de Limbe.",
                nearby_services="Restaurants de bord de plage, marché au poisson.",
                indigenous_people="Bakweri, peuple autochtone du pied du mont Cameroun",
                local_language="Mokpe (langue bakweri) ; anglais très répandu (zone anglophone)",
                image=img("DOWN BEACH LIMBE CAMEROON.jpg"),
                latitude=4.0140, longitude=9.2060,
                estimated_budget_fcfa=5000, recommended_duration_hours=3,
                confidence=TouristSite.Confidence.MEDIUM,
                sources=[wikipedia_fr],
            ),
            dict(
                name="Sanctuaire de primates de la Méfou",
                region="Centre", department="Méfou-et-Afamba", commune="Mfou",
                category="Nature et faune",
                description=(
                    "Situé à environ 45 km au sud de Yaoundé, le parc de la Méfou est un sanctuaire "
                    "géré par l'ONG Ape Action Africa. Il accueille des gorilles, chimpanzés et "
                    "singes rescapés du commerce illégal de viande de brousse et d'animaux de "
                    "compagnie, dans un cadre de forêt protégée."
                ),
                activities="Visite guidée du sanctuaire\nObservation des primates\nSensibilisation à la conservation",
                accessibility="Réservation recommandée. Route praticable depuis Yaoundé, un véhicule 4x4 est conseillé en saison des pluies.",
                nearby_services="Petite restauration sur place, aire de pique-nique.",
                indigenous_people="Peuples Beti (dont Éton), majoritaires dans la région du Centre",
                local_language="Ewondo (groupe beti-pahuin) ; français largement parlé",
                image=img("Chimpanzé in Primate Reserve sanctuary Mefou.jpg"),
                latitude=3.9600, longitude=11.9300,
                estimated_budget_fcfa=12000, recommended_duration_hours=4,
                confidence=TouristSite.Confidence.HIGH,
                sources=[ape_action, wikipedia_fr],
            ),
            dict(
                name="Réserve de faune du Dja",
                region="Est", department="Dja-et-Lobo", commune="Somalomo / Lomié",
                category="Nature et faune",
                description=(
                    "Inscrite au patrimoine mondial de l'UNESCO en 1987, la réserve de faune du "
                    "Dja est l'une des plus grandes et des mieux préservées forêts tropicales "
                    "d'Afrique, avec environ 90 % de sa surface encore intacte. Elle abrite "
                    "gorilles des plaines de l'Ouest, chimpanzés et éléphants de forêt, et est "
                    "presque entièrement entourée par la rivière Dja."
                ),
                activities="Randonnée en forêt primaire\nObservation de la faune et de la flore\nRencontre avec les communautés Baka",
                accessibility="Accès difficile, nécessite un guide et une préparation logistique depuis Yaoundé (via Somalomo).",
                nearby_services="Hébergement limité ; organisation via des opérateurs spécialisés recommandée.",
                indigenous_people="Baka (peuple autochtone semi-nomade de la forêt) et communautés bantoues voisines (Nzimé, Badjoué)",
                local_language="Baka, aux côtés du français",
                image=img("Dja Faunal Reserve-109438.jpg"),
                latitude=3.0000, longitude=13.0000,
                estimated_budget_fcfa=None, recommended_duration_hours=None,
                confidence=TouristSite.Confidence.HIGH,
                sources=[unesco, mintoul],
            ),
            dict(
                name="Chutes de la Vina, Ngaoundéré",
                region="Adamaoua", department="Vina", commune="Ngaoundéré",
                category="Nature et faune",
                description=(
                    "Situées à proximité de Ngaoundéré, capitale traditionnelle peule de "
                    "l'Adamaoua, les chutes de la Vina offrent un cadre naturel sur le plateau "
                    "de l'Adamaoua, région d'altitude connue pour son climat frais et ses "
                    "paysages de savane et d'élevage."
                ),
                activities="Randonnée\nPique-nique\nPhotographie de paysage",
                accessibility="À proximité de la ville de Ngaoundéré, accessible par piste.",
                nearby_services="Hébergements disponibles à Ngaoundéré (terminus du chemin de fer Transcamerounais).",
                indigenous_people="Peuls (Foulbé/Mbororo), dominants depuis le XIXe siècle, aux côtés des Mboum, peuple autochtone antérieur à leur arrivée",
                local_language="Fulfulde (peul) ; mboum localement",
                image=img("Les chutes d'eau de la Vina à Ngaoundéré.jpg"),
                latitude=7.3200, longitude=13.5800,
                estimated_budget_fcfa=8000, recommended_duration_hours=4,
                confidence=TouristSite.Confidence.LOW,
                sources=[wikipedia_fr],
            ),
            dict(
                name="Mont Cameroun, Buea",
                region="Sud-Ouest", department="Fako", commune="Buea",
                category="Aventure et randonnée",
                description=(
                    "Le mont Cameroun est un volcan actif culminant à 4 040 mètres, point culminant "
                    "d'Afrique de l'Ouest et centrale. Son ascension, au départ de Buea, est l'une "
                    "des randonnées les plus emblématiques du pays et donne lieu chaque année à une "
                    "célèbre course de montagne."
                ),
                activities="Ascension guidée (2 à 3 jours)\nRandonnée\nObservation de la biodiversité volcanique",
                accessibility="Guide et porteur obligatoires, départ depuis Buea ; bonne condition physique requise.",
                nearby_services="Refuges d'altitude sommaires, agences de guides à Buea.",
                indigenous_people="Bakweri, peuple autochtone du pied du mont Cameroun",
                local_language="Mokpe (langue bakweri) ; anglais très répandu (zone anglophone)",
                image=img("Buea from Fako.jpg"),
                latitude=4.2170, longitude=9.1730,
                estimated_budget_fcfa=40000, recommended_duration_hours=48,
                confidence=TouristSite.Confidence.MEDIUM,
                sources=[mintoul, wikipedia_fr],
            ),
        ]

        self.stdout.write("Création des fiches touristiques...")
        for data in sites_data:
            slug = slugify(data["name"])
            site, created = TouristSite.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    name=data["name"],
                    description=data["description"],
                    region=regions[data["region"]],
                    department=data["department"],
                    commune=data["commune"],
                    category=categories[data["category"]],
                    activities=data["activities"],
                    accessibility=data["accessibility"],
                    nearby_services=data["nearby_services"],
                    indigenous_people=data.get("indigenous_people", ""),
                    local_language=data.get("local_language", ""),
                    image_url=data["image"],
                    latitude=data["latitude"],
                    longitude=data["longitude"],
                    estimated_budget_fcfa=data["estimated_budget_fcfa"],
                    recommended_duration_hours=data["recommended_duration_hours"],
                    status=TouristSite.Status.PUBLISHED,
                    confidence_level=data["confidence"],
                    verification_date=today,
                ),
            )
            if created:
                site.sources.set(data["sources"])
                VerificationRecord.objects.create(
                    site=site,
                    verified_by="Équipe CamWay (import initial)",
                    verification_date=today,
                    confidence_level=data["confidence"],
                    notes="Vérification initiale lors du peuplement de la base de démonstration.",
                )
                self.stdout.write(self.style.SUCCESS(f"  + {site.name}"))
            else:
                self.stdout.write(f"  = {site.name} (déjà présent)")

        # ---------------------------------------------------------------
        # HORS MVP (§25.1) : un seul prestataire, dont l'existence et
        # l'activité sont réellement documentées par sa propre source
        # (apeactionafrica.org). Nous n'inventons volontairement aucune
        # coordonnée commerciale (téléphone, e-mail) que nous ne pourrions
        # pas vérifier : ces champs restent vides plutôt qu'imaginés.
        # ---------------------------------------------------------------
        mefou_site = TouristSite.objects.filter(slug="sanctuaire-de-primates-de-la-mefou").first()
        provider, p_created = Provider.objects.get_or_create(
            slug="ape-action-africa",
            defaults=dict(
                name="Ape Action Africa",
                provider_type=Provider.ProviderType.ACTIVITY,
                region=regions["Centre"],
                description=(
                    "ONG de conservation gestionnaire du sanctuaire de primates de la Méfou, "
                    "près de Yaoundé. Organise l'accueil des visiteurs et la sensibilisation à "
                    "la protection des grands singes du Cameroun."
                ),
                website="https://www.apeactionafrica.org/mefou-primate-sanctuary",
                status=TouristSite.Status.PUBLISHED,
                confidence_level=TouristSite.Confidence.MEDIUM,
                verification_date=today,
            ),
        )
        if p_created:
            provider.sources.set([ape_action])
            if mefou_site:
                provider.sites.set([mefou_site])
            self.stdout.write(self.style.SUCCESS(f"  + Prestataire : {provider.name}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé : {Region.objects.count()} régions, {Category.objects.count()} catégories, "
            f"{Source.objects.count()} sources, {TouristSite.objects.count()} fiches touristiques, "
            f"{Provider.objects.count()} prestataire(s) vérifié(s)."
        ))
        self.stdout.write(
            "Astuce : créez un compte administrateur avec `python manage.py createsuperuser` "
            "pour gérer les données depuis /admin/."
        )
