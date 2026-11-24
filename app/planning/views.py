from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .couverture import alertes_ssuap
from .forms import DisponibiliteForm, CopieJourneeForm
from .models import Disponibilite
from datetime import date, datetime, time, timedelta
from .incendie import alertes_inc
from django.utils import timezone
from .synthese import synthese_gardes
from django.contrib import messages
from .copie import copier_journee

@login_required
def mes_disponibilites(request):
    disponibilites = list(
        Disponibilite.objects.filter(
            agent=request.user
        ).order_by("debut")
    )

    evenements = []

    for disponibilite in disponibilites:
        debut = timezone.localtime(disponibilite.debut)
        fin = timezone.localtime(disponibilite.fin)

        evenements.append({
            "id": disponibilite.pk,
            "title": "Disponible",
            "start": debut.isoformat(),
            "end": fin.isoformat(),
        })

    return render(
        request,
        "planning/mes_disponibilites.html",
        {
            "disponibilites": disponibilites,
            "evenements": evenements,
        },
    )

@login_required
def ajouter_disponibilite(request):
    modal = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        formulaire = DisponibiliteForm(request.POST)

        if formulaire.is_valid():
            disponibilite = formulaire.save(commit=False)
            disponibilite.agent = request.user
            disponibilite.save()

            if modal:
                return JsonResponse({"success": True})

            return redirect("mes_disponibilites")
    else:
        formulaire = DisponibiliteForm()

        date_choisie = request.GET.get("date")
        heure_choisie = request.GET.get("heure", "08:00")
        fin_date_choisie = request.GET.get("fin_date")
        fin_heure_choisie = request.GET.get("fin_heure")

        if date_choisie:
            try:
                jour = date.fromisoformat(date_choisie)
                heure = time.fromisoformat(heure_choisie)

                debut = datetime.combine(jour, heure)
                fin = debut + timedelta(hours=1)

                if fin_date_choisie and fin_heure_choisie:
                    fin = datetime.combine(
                        date.fromisoformat(fin_date_choisie),
                        time.fromisoformat(fin_heure_choisie),
                    )

                formulaire = DisponibiliteForm(
                    initial={"debut": debut, "fin": fin}
                )
            except ValueError:
                pass

    template = (
        "planning/_formulaire_modal.html"
        if modal
        else "planning/formulaire_disponibilite.html"
    )

    return render(
        request,
        template,
        {"formulaire": formulaire},
        status=400 if modal and request.method == "POST" else 200,
    )

@login_required
def modifier_disponibilite(request, pk):
    disponibilite = get_object_or_404(
        Disponibilite,
        pk=pk,
        agent=request.user,
    )

    modal = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        formulaire = DisponibiliteForm(
            request.POST,
            instance=disponibilite,
        )

        if formulaire.is_valid():
            formulaire.save()

            if modal:
                return JsonResponse({"success": True})

            return redirect("mes_disponibilites")
    else:
        formulaire = DisponibiliteForm(
            instance=disponibilite,
        )

    template = (
        "planning/_formulaire_modal.html"
        if modal
        else "planning/formulaire_disponibilite.html"
    )

    return render(
        request,
        template,
        {
            "formulaire": formulaire,
            "modification": True,
        },
        status=400 if modal and request.method == "POST" else 200,
    )

@login_required
def supprimer_disponibilite(request, pk):
    disponibilite = get_object_or_404(
        Disponibilite,
        pk=pk,
        agent=request.user,
    )

    if request.method == "POST":
        disponibilite.delete()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})

        return redirect("mes_disponibilites")

    return render(
        request,
        "planning/confirmer_suppression.html",
        {"disponibilite": disponibilite},
    )

@login_required
def planning_hebdomadaire(request):
    aujourd_hui = timezone.localdate()

    date_demandee = request.GET.get("semaine")

    if date_demandee:
        try:
            jour = date.fromisoformat(date_demandee)
        except ValueError:
            jour = aujourd_hui
    else:
        jour = aujourd_hui

    lundi = jour - timedelta(days=jour.weekday())
    lundi_suivant = lundi + timedelta(days=7)

    debut_semaine = timezone.make_aware(
        datetime.combine(lundi, time.min)
    )
    fin_semaine = timezone.make_aware(
        datetime.combine(lundi_suivant, time.min)
    )

    disponibilites = (
        Disponibilite.objects
        .filter(
            debut__lt=fin_semaine,
            fin__gt=debut_semaine,
        )
        .select_related("agent")
        .order_by("debut", "agent__username")
    )

    jours = []

    for numero in range(7):
        jour_courant = lundi + timedelta(days=numero)

        debut_jour = timezone.make_aware(
            datetime.combine(jour_courant, time.min)
        )
        fin_jour = timezone.make_aware(
            datetime.combine(
                jour_courant + timedelta(days=1),
                time.min,
            )
        )

        disponibilites_jour = [
            disponibilite
            for disponibilite in disponibilites
            if (
                disponibilite.debut < fin_jour
                and disponibilite.fin > debut_jour
            )
        ]

        jours.append({
            "date": jour_courant,
            "disponibilites": disponibilites_jour,
        })

        # Calcul des alertes SSUAP sur la semaine affichée.
        # On prolonge jusqu'au lundi suivant à 6 h
        # pour inclure la fin de la garde du week-end.
    debut_analyse = timezone.make_aware(
        datetime.combine(lundi, time.min)
    )

    fin_analyse = timezone.make_aware(
        datetime.combine(
            lundi + timedelta(days=7),
            time(hour=6),
        )
    )

    alertes = alertes_ssuap(debut_analyse, fin_analyse)
    alertes_incendie = alertes_inc(debut_analyse, fin_analyse)
    gardes = synthese_gardes(debut_analyse, fin_analyse)

    return render(
        request,
        "planning/planning_hebdomadaire.html",
        {
            "jours": jours,
            "lundi": lundi,
            "dimanche": lundi + timedelta(days=6),
            "semaine_precedente": (
                lundi - timedelta(days=7)
            ).isoformat(),
            "semaine_suivante": (
                lundi + timedelta(days=7)
            ).isoformat(),
            "alertes_ssuap": alertes,
            "alertes_inc": alertes_incendie,
            "synthese_gardes": gardes,
        },
    )

@login_required
@xframe_options_sameorigin
def copier_journee_disponibilites(request):
    modal = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        formulaire = CopieJourneeForm(request.POST)

        if formulaire.is_valid():
            date_source = formulaire.cleaned_data["date_source"]
            dates_destination = formulaire.cleaned_data[
                "dates_destination"
            ]

            resultat = copier_journee(
                agent=request.user,
                date_source=date_source,
                dates_destination=dates_destination,
            )

            if resultat["creneaux_source"] == 0:
                message = (
                    "Aucune disponibilité ne commence "
                    "à la date source sélectionnée."
                )
                messages.warning(request, message)
            else:
                message = (
                    f"{resultat['creations']} disponibilité(s) "
                    f"créée(s), {resultat['doublons']} "
                    "doublon(s) ignoré(s)."
                )
                messages.success(request, message)

            if modal:
                return JsonResponse({
                    "success": True,
                    "message": message,
                    "creations": resultat["creations"],
                    "doublons": resultat["doublons"],
                })

            return redirect("mes_disponibilites")

    else:
        formulaire = CopieJourneeForm()

    template = "planning/copier_journee.html"

    return render(
        request,
        template,
        {"formulaire": formulaire},
        status=400 if modal and request.method == "POST" else 200,
    )

@login_required
def couverture_ssuap_calendrier(request):
    """État SSUAP de chaque date pour le calendrier."""
    try:
        debut_jour = date.fromisoformat(request.GET["debut"])
        fin_jour = date.fromisoformat(request.GET["fin"])
    except (KeyError, ValueError):
        return JsonResponse(
            {"erreur": "Dates invalides (format AAAA-MM-JJ)."},
            status=400,
        )

    nombre_jours = (fin_jour - debut_jour).days

    if not 1 <= nombre_jours <= 62:
        return JsonResponse(
            {"erreur": "La période doit couvrir entre 1 et 62 jours."},
            status=400,
        )

    fuseau = timezone.get_current_timezone()
    debut = timezone.make_aware(
        datetime.combine(debut_jour, time.min), fuseau
    )
    fin = timezone.make_aware(
        datetime.combine(fin_jour, time.min), fuseau
    )

    alertes = alertes_ssuap(debut, fin)

    jours_rouges = set()

    for alerte in alertes:
        jour = timezone.localtime(alerte["debut"], fuseau).date()
        dernier = timezone.localtime(
            alerte["fin"] - timedelta(microseconds=1), fuseau
        ).date()

        while jour <= dernier:
            jours_rouges.add(jour.isoformat())
            jour += timedelta(days=1)

    resultats = {}

    for index in range(nombre_jours):
        jour = debut_jour + timedelta(days=index)
        cle = jour.isoformat()
        resultats[cle] = (
            "rouge" if cle in jours_rouges else "vert"
        )

    return JsonResponse({"jours": resultats})
