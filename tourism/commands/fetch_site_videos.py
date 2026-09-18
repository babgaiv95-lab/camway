# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from tourism import youtube_client
from tourism.models import SiteVideo, TouristSite


class Command(BaseCommand):
    help = (
        "Récupère, via l'API YouTube Data v3, une vidéo de preuve pour chaque fiche "
        "touristique qui n'en a pas encore. La clé YOUTUBE_API_KEY doit être renseignée "
        "dans .env, sinon la commande s'arrête sans rien inventer. Les vidéos ajoutées "
        "restent marquées « non vérifiées » tant qu'un administrateur ne les a pas "
        "confirmées dans /admin/ (principe de prudence du projet, §4.3, §10.4)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true",
            help="Traiter aussi les fiches ayant déjà une vidéo (les complète, sans les supprimer).",
        )
        parser.add_argument(
            "--status", default=TouristSite.Status.PUBLISHED,
            help="Ne traiter que les fiches ayant ce statut (par défaut : published). Utiliser 'all' pour tout traiter.",
        )

    def handle(self, *args, **options):
        if not youtube_client.is_configured():
            self.stderr.write(self.style.ERROR(
                "YOUTUBE_API_KEY n'est pas configurée dans .env : aucune vidéo ne peut être "
                "recherchée. Ajoutez votre clé (voir .env.example) puis relancez cette commande."
            ))
            return

        sites = TouristSite.objects.all()
        if options["status"] != "all":
            sites = sites.filter(status=options["status"])
        if not options["all"]:
            sites = sites.filter(videos__isnull=True)
        sites = sites.distinct()

        total = sites.count()
        if total == 0:
            self.stdout.write("Aucune fiche à traiter : toutes les fiches concernées ont déjà une vidéo.")
            return

        self.stdout.write(f"Recherche d'une vidéo YouTube pour {total} fiche(s)...")
        found, missing = 0, 0

        for site in sites:
            result = youtube_client.search_video_for_site(site)
            if result is None:
                missing += 1
                self.stdout.write(self.style.WARNING(f"  — Aucune vidéo trouvée pour « {site.name} »."))
                continue

            SiteVideo.objects.update_or_create(
                site=site, youtube_video_id=result["video_id"],
                defaults={
                    "title": result["title"],
                    "channel_title": result["channel_title"],
                    "thumbnail_url": result["thumbnail_url"],
                    "search_query": result["search_query"],
                    "added_automatically": True,
                },
            )
            found += 1
            self.stdout.write(self.style.SUCCESS(f"  ✓ Vidéo ajoutée pour « {site.name} » : {result['title']}"))

        self.stdout.write(
            f"\nTerminé : {found} vidéo(s) ajoutée(s), {missing} fiche(s) sans résultat. "
            "Pensez à valider les nouvelles vidéos dans /admin/ avant de les considérer comme fiables."
        )
