from django import forms
from django.db.models import Q

from .models import Grade, FonctionAgent
from .identites import (
    normaliser_matricule,
    normaliser_email,
    normaliser_nom,
    normaliser_prenom,
)


class ProfilAgentForm(forms.Form):

    nom = forms.CharField(
        label="Nom",
        max_length=150,
    )

    prenom = forms.CharField(
        label="Prénom",
        max_length=150,
    )

    grade = forms.ModelChoiceField(
        label="Grade",
        queryset=Grade.objects.none(),
        empty_label="Sélectionner un grade",
    )

    telephone = forms.CharField(
        label="Téléphone",
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={"type": "tel"}
        ),
    )

    fonctions = forms.ModelMultipleChoiceField(
        label="Fonctions",
        queryset=FonctionAgent.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    actif = forms.BooleanField(
        label="Compte autorisé",
        required=False,
        initial=True,
    )

    def __init__(self, *args, profil=None, **kwargs):
        self.profil = profil

        super().__init__(*args, **kwargs)

        grades = Q(active=True)
        fonctions = Q(active=True)

        if profil is not None:
            grades |= Q(pk=profil.grade_id)

            fonctions |= Q(
                pk__in=profil.fonctions.values_list(
                    "pk", flat=True
                )
            )

        self.fields["grade"].queryset = (
            Grade.objects.filter(grades)
            .order_by("-ordre", "nom")
        )

        self.fields["fonctions"].queryset = (
            FonctionAgent.objects.filter(fonctions)
            .order_by("nom")
        )

    def clean_nom(self):
        return normaliser_nom(
            self.cleaned_data["nom"]
        )

    def clean_prenom(self):
        return normaliser_prenom(
            self.cleaned_data["prenom"]
        )

    def donnees_profil(self):
        return {
            "nom": self.cleaned_data["nom"],
            "prenom": self.cleaned_data["prenom"],
            "grade_id": self.cleaned_data["grade"].pk,
            "telephone": self.cleaned_data["telephone"],
            "fonctions_ids": list(
                self.cleaned_data["fonctions"]
                .values_list("pk", flat=True)
            ),
        }


class AgentForm(ProfilAgentForm):

    matricule = forms.CharField(
        label="Matricule",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
            }
        ),
    )

    email = forms.EmailField(
        label="Adresse e-mail",
        max_length=254,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.order_fields([
            "matricule",
            "nom",
            "prenom",
            "email",
            "grade",
            "telephone",
            "fonctions",
            "actif",
        ])

    def clean_matricule(self):
        return normaliser_matricule(
            self.cleaned_data["matricule"]
        )

    def clean_email(self):
        return normaliser_email(
            self.cleaned_data["email"]
        )

    def donnees_creation(self):
        return {
            **self.donnees_profil(),
            "matricule": self.cleaned_data["matricule"],
            "email": self.cleaned_data["email"],
            "actif": self.cleaned_data["actif"],
        }


class AgentModificationForm(ProfilAgentForm):

    matricule = forms.CharField(
        label="Matricule",
        disabled=True,
        required=False,
    )

    email = forms.EmailField(
        label="Adresse e-mail",
        disabled=True,
        required=False,
    )

    def __init__(self, *args, profil, **kwargs):
        utilisateur = profil.utilisateur

        initial = {
            "matricule": utilisateur.username,
            "nom": utilisateur.last_name,
            "prenom": utilisateur.first_name,
            "email": utilisateur.email,
            "grade": profil.grade_id,
            "telephone": profil.telephone,
            "fonctions": list(
                profil.fonctions.values_list(
                    "pk", flat=True
                )
            ),
            "actif": utilisateur.is_active,
        }

        kwargs["initial"] = initial

        super().__init__(
            *args,
            profil=profil,
            **kwargs,
        )

        self.order_fields([
            "matricule",
            "nom",
            "prenom",
            "email",
            "grade",
            "telephone",
            "fonctions",
            "actif",
        ])


class QualificationsAgentForm(forms.Form):

    def __init__(self, *args, profil, validateur, **kwargs):
        from .models import Competence

        super().__init__(*args, **kwargs)

        self.profil = profil

        self.attributions = {
            attribution.competence_id: attribution
            for attribution in profil.attributions_competences.all()
        }

        self.competences = list(
            Competence.objects.filter(active=True)
            .order_by("categorie", "nom")
        )

        peut_attribuer = validateur.has_perm(
            "planning.add_competenceagent"
        )

        peut_modifier = validateur.has_perm(
            "planning.change_competenceagent"
        )

        peut_retirer = validateur.has_perm(
            "planning.delete_competenceagent"
        )

        for competence in self.competences:
            pk = competence.pk
            attribution = self.attributions.get(pk)

            self.fields[f"competence_{pk}"] = forms.BooleanField(
                label=competence.nom,
                required=False,
                initial=attribution is not None,
                disabled=(
                    not peut_retirer
                    if attribution
                    else not peut_attribuer
                ),
            )

            for champ, label in (
                ("date_validation", "Début de validité"),
                ("date_expiration", "Fin de validité"),
            ):
                self.fields[f"{champ}_{pk}"] = forms.DateField(
                    label=label,
                    required=False,
                    initial=getattr(attribution, champ, None),
                    disabled=(
                        not peut_modifier
                        if attribution
                        else not peut_attribuer
                    ),
                    input_formats=["%Y-%m-%d"],
                    widget=forms.DateInput(
                        format="%Y-%m-%d",
                        attrs={"type": "date"},
                    ),
                )

    def lignes_competences(self):
        return [
            {
                "competence": competence,
                "choix": self[f"competence_{competence.pk}"],
                "debut": self[f"date_validation_{competence.pk}"],
                "fin": self[f"date_expiration_{competence.pk}"],
            }
            for competence in self.competences
        ]

    def clean(self):
        donnees = super().clean()

        for competence in self.competences:
            pk = competence.pk

            if not donnees.get(f"competence_{pk}"):
                continue

            debut = donnees.get(f"date_validation_{pk}")
            fin = donnees.get(f"date_expiration_{pk}")

            if debut and fin and fin < debut:
                self.add_error(
                    f"date_expiration_{pk}",
                    "La fin de validité ne peut pas "
                    "précéder le début.",
                )

        return donnees

    def operations(self):
        if not self.is_valid():
            raise ValueError("Formulaire invalide.")

        operations = []

        for competence in self.competences:
            pk = competence.pk
            attribution = self.attributions.get(pk)

            selectionnee = self.cleaned_data[
                f"competence_{pk}"
            ]

            debut = self.cleaned_data[
                f"date_validation_{pk}"
            ]

            fin = self.cleaned_data[
                f"date_expiration_{pk}"
            ]

            if selectionnee and attribution is None:
                operations.append({
                    "action": "attribuer",
                    "profil_id": self.profil.pk,
                    "competence_id": pk,
                    "date_validation": debut,
                    "date_expiration": fin,
                })

            elif not selectionnee and attribution:
                operations.append({
                    "action": "retirer",
                    "attribution_id": attribution.pk,
                })

            elif selectionnee and attribution:
                if (
                    attribution.date_validation != debut
                    or attribution.date_expiration != fin
                ):
                    operations.append({
                        "action": "modifier",
                        "attribution_id": attribution.pk,
                        "date_validation": debut,
                        "date_expiration": fin,
                    })

        return operations


class DroitsAgentForm(forms.Form):

    administrateur_dispo = forms.BooleanField(
        label="Administrateur Dispo",
        required=False,
        help_text=(
            "Autorise la gestion des agents et des qualifications, "
            "sans accès à l'administration technique Django."
        ),
    )

    delegations = forms.MultipleChoiceField(
        label="Délégations individuelles",
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=(
            (
                "planning.add_competenceagent",
                "Attribuer des qualifications",
            ),
            (
                "planning.change_competenceagent",
                "Modifier les dates de validité",
            ),
            (
                "planning.delete_competenceagent",
                "Retirer des qualifications",
            ),
        ),
        help_text=(
            "Ces autorisations restent indépendantes "
            "du rôle d'administrateur Dispo."
        ),
    )

    def __init__(self, *args, profil, **kwargs):
        from .services.droits import etat_droits_agent
        from .autorisations import (
            PERMISSIONS_DELEGATION_QUALIFICATIONS,
        )

        kwargs["initial"] = etat_droits_agent(
            profil.utilisateur
        )

        super().__init__(*args, **kwargs)

        self.fields["delegations"].choices = [
            (permission, libelle)
            for permission, libelle in
            self.fields["delegations"].choices
            if permission in PERMISSIONS_DELEGATION_QUALIFICATIONS
        ]

    def donnees_droits(self):
        if not self.is_valid():
            raise ValueError("Formulaire invalide.")

        return {
            "administrateur_dispo": (
                self.cleaned_data["administrateur_dispo"]
            ),
            "delegations": self.cleaned_data["delegations"],
        }
