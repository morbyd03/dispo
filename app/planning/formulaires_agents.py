from django import forms
from django.contrib.auth import get_user_model


class AgentForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = [
            "last_name",
            "first_name",
            "username",
            "email",
            "is_active",
        ]
        labels = {
            "last_name": "Nom",
            "first_name": "Prénom",
            "username": "Identifiant",
            "email": "Adresse e-mail",
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if not email:
            raise forms.ValidationError(
                "L'adresse e-mail est obligatoire."
            )

        return email


from .models import Competence


class AgentModificationForm(AgentForm):

    competences = forms.ModelMultipleChoiceField(
        queryset=Competence.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Compétences",
    )

    administrateur_dispo = forms.BooleanField(
        required=False,
        label="Administrateur Dispo",
    )

    def __init__(self, *args, utilisateur_connecte, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["competences"].queryset = (
            Competence.objects.filter(active=True)
            .order_by("categorie", "nom")
        )

        self.fields["competences"].initial = (
            self.instance.competences_agent
            .values_list("competence_id", flat=True)
        )

        if utilisateur_connecte.is_superuser:
            self.fields["administrateur_dispo"].initial = (
                self.instance.groups.filter(
                    name="Administrateurs Dispo"
                ).exists()
            )
        else:
            self.fields.pop("administrateur_dispo")


        attributions = {
            attribution.competence_id: attribution
            for attribution in self.instance.competences_agent.all()
        }

        for competence in self.fields["competences"].queryset:
            attribution = attributions.get(competence.pk)

            for nom, label in (
                ("date_validation", "Début de validité"),
                ("date_expiration", "Fin de validité"),
            ):
                self.fields[f"{nom}_{competence.pk}"] = forms.DateField(
                    label=label,
                    required=False,
                    initial=getattr(attribution, nom, None),
                    input_formats=["%Y-%m-%d"],
                    widget=forms.DateInput(
                        format="%Y-%m-%d",
                        attrs={"type": "date"},
                    ),
                )

    def lignes_competences(self):
        lignes = []

        for competence, choix in zip(
            self.fields["competences"].queryset,
            self["competences"],
        ):
            lignes.append({
                "choix": choix,
                "debut": self[f"date_validation_{competence.pk}"],
                "fin": self[f"date_expiration_{competence.pk}"],
            })

        return lignes

    def clean(self):
        donnees = super().clean()

        for competence in donnees.get("competences", []):
            champ_debut = f"date_validation_{competence.pk}"
            champ_fin = f"date_expiration_{competence.pk}"

            debut = donnees.get(champ_debut)
            fin = donnees.get(champ_fin)

            if debut and fin and fin < debut:
                self.add_error(
                    champ_fin,
                    "La fin de validité ne peut pas être "
                    "antérieure au début.",
                )

        return donnees
