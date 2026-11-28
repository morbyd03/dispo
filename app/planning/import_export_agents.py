import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import OperationalError, transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .services.import_agents import (
    verifier_autorisation_import,
)
from .services.export_agents import exporter_agents_csv


logger = logging.getLogger(__name__)


@login_required
@require_GET
@never_cache
def export_agents(request):
    verifier_autorisation_import(request.user.pk)

    return render(
        request,
        "planning/export_agents.html",
    )


@login_required
@require_GET
@never_cache
def telecharger_export_agents(request):
    verifier_autorisation_import(request.user.pk)

    mode = request.GET.get("mode", "consultation")

    if mode not in ("consultation", "reimport"):
        return HttpResponse(
            "Mode d'export invalide.",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    try:
        with transaction.atomic():
            contenu = exporter_agents_csv(
                utilisateur_id=request.user.pk,
                mode=mode,
            )

    except ValidationError as erreur:
        for message in erreur.messages:
            messages.error(request, message)

        return redirect("export_agents")

    except OperationalError:
        logger.exception("Echec transactionnel de l'export CSV")

        reponse = HttpResponse(
            "Export temporairement indisponible.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

        reponse["Retry-After"] = "5"

        return reponse

    reponse = HttpResponse(
        contenu,
        content_type="text/csv; charset=utf-8",
    )

    reponse["Content-Disposition"] = (
        f'attachment; filename="agents-dispo-{mode}.csv"'
    )

    reponse["X-Content-Type-Options"] = "nosniff"

    return reponse


from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from .formulaires_import_export import (
    ImportAgentsForm,
    ConfirmationImportAgentsForm,
    AnnulationImportAgentsForm,
)

from .services.imports_temporaires import (
    preparer_import_temporaire,
)

from .services.presentation_import import (
    presenter_import_agents,
)


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
@csrf_protect
@sensitive_post_parameters()
def import_agents(request):
    verifier_autorisation_import(request.user.pk)

    if request.method == "GET":
        return render(
            request,
            "planning/import_agents.html",
            {"formulaire": ImportAgentsForm()},
        )

    formulaire = ImportAgentsForm(
        request.POST,
        request.FILES,
    )

    if not formulaire.is_valid():
        return render(
            request,
            "planning/import_agents.html",
            {"formulaire": formulaire},
            status=400,
        )

    try:
        fichier = formulaire.cleaned_data["fichier"]

        with transaction.atomic():
            preparation = preparer_import_temporaire(
                contenu=fichier.read(),
                utilisateur_id=request.user.pk,
            )

            lignes_presentees = presenter_import_agents(
                preparation["previsualisation"]
            )

    except ValidationError as erreur:
        for message in erreur.messages:
            formulaire.add_error("fichier", message)

        return render(
            request,
            "planning/import_agents.html",
            {"formulaire": formulaire},
            status=400,
        )

    except OperationalError:
        logger.exception(
            "Echec transactionnel de la preparation d'import"
        )

        reponse = HttpResponse(
            "Import temporairement indisponible.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

        reponse["Retry-After"] = "5"

        return reponse

    previsualisation = preparation["previsualisation"]

    bilan = {
        "creations": 0,
        "rattachements": 0,
        "modifications": 0,
        "qualifications_seules": 0,
        "inchanges": 0,
        "qualifications_attribuees": 0,
        "qualifications_retirees": 0,
    }

    for ligne in previsualisation["lignes"]:
        if ligne["action"] == "creer":
            bilan["creations"] += 1

        elif ligne["action"] == "rattacher":
            bilan["rattachements"] += 1

        elif ligne["changements"]:
            bilan["modifications"] += 1

        elif ligne["operations_qualifications"]:
            bilan["qualifications_seules"] += 1

        else:
            bilan["inchanges"] += 1

        for operation in ligne["operations_qualifications"]:
            if operation["action"] == "attribuer":
                bilan["qualifications_attribuees"] += 1

            elif operation["action"] == "retirer":
                bilan["qualifications_retirees"] += 1

    contexte = {
        "previsualisation": previsualisation,
        "lignes_presentees": lignes_presentees,
        "bilan": bilan,
        "confirmable": preparation["confirmable"],
        "changements_email": preparation["changements_email"],
        "retraits_necessaires": (
            bilan["qualifications_retirees"] > 0
        ),
    }

    if preparation["confirmable"]:
        initial = {
            "identifiant": preparation["identifiant"],
        }

        contexte["formulaire_confirmation"] = (
            ConfirmationImportAgentsForm(initial=initial)
        )

        contexte["formulaire_annulation"] = (
            AnnulationImportAgentsForm(initial=initial)
        )

    return render(
        request,
        "planning/previsualisation_import_agents.html",
        contexte,
    )


from django.views.decorators.http import require_POST

from .services.imports_temporaires import (
    confirmer_import_temporaire,
    annuler_import_temporaire,
)


def erreur_transaction_import():
    reponse = HttpResponse(
        "Import temporairement indisponible. "
        "Veuillez reessayer.",
        status=503,
        content_type="text/plain; charset=utf-8",
    )

    reponse["Retry-After"] = "5"

    return reponse


@login_required
@require_POST
@never_cache
@csrf_protect
@sensitive_post_parameters()
def confirmer_import_agents(request):
    verifier_autorisation_import(request.user.pk)

    formulaire = ConfirmationImportAgentsForm(
        request.POST
    )

    if not formulaire.is_valid():
        messages.error(
            request,
            "Confirmation invalide ou incomplete. "
            "Veuillez analyser a nouveau le fichier.",
        )

        return redirect("import_agents")

    try:
        bilan = confirmer_import_temporaire(
            utilisateur_id=request.user.pk,
            identifiant=formulaire.cleaned_data["identifiant"],
            confirmer_retraits=(
                formulaire.cleaned_data["confirmer_retraits"]
            ),
        )

    except ValidationError as erreur:
        for message in erreur.messages:
            messages.error(request, message)

        return redirect("import_agents")

    except OperationalError:
        logger.exception(
            "Echec transactionnel de la confirmation d'import"
        )

        return erreur_transaction_import()

    messages.success(
        request,
        "Import termine avec succes."
    )

    messages.info(
        request,
        f"Creations : {bilan['creations']} ; "
        f"rattachements : {bilan['rattachements']} ; "
        f"modifications de profil : {bilan['modifications']} ; "
        f"qualifications uniquement : {bilan['qualifications_seules']} ; "
        f"agents inchanges : {bilan['inchanges']} ; "
        f"qualifications attribuees : "
        f"{bilan['qualifications_attribuees']} ; "
        f"qualifications retirees : "
        f"{bilan['qualifications_retirees']}."
    )

    return redirect("import_agents")


@login_required
@require_POST
@never_cache
@csrf_protect
@sensitive_post_parameters()
def annuler_import_agents(request):
    verifier_autorisation_import(request.user.pk)

    formulaire = AnnulationImportAgentsForm(
        request.POST
    )

    if not formulaire.is_valid():
        messages.error(
            request,
            "Demande d'annulation invalide."
        )

        return redirect("import_agents")

    try:
        annule = annuler_import_temporaire(
            utilisateur_id=request.user.pk,
            identifiant=formulaire.cleaned_data["identifiant"],
        )

    except ValidationError as erreur:
        for message in erreur.messages:
            messages.error(request, message)

        return redirect("import_agents")

    except OperationalError:
        logger.exception(
            "Echec transactionnel de l'annulation d'import"
        )

        return erreur_transaction_import()

    if annule:
        messages.success(
            request,
            "Import annule. Aucune modification "
            "des agents n'a ete effectuee."
        )

    else:
        messages.warning(
            request,
            "Cette previsualisation n'est plus disponible."
        )

    return redirect("import_agents")
