from django import forms

from .services.import_agents import TAILLE_MAXIMALE


class ImportAgentsForm(forms.Form):

    fichier = forms.FileField(
        label="Fichier CSV",
        help_text=(
            "Fichier CSV UTF-8, de 2 Mio maximum "
            "et contenant au maximum 1000 agents."
        ),
        widget=forms.ClearableFileInput(
            attrs={"accept": ".csv,text/csv"}
        ),
    )

    def clean_fichier(self):
        fichier = self.cleaned_data["fichier"]

        if fichier.size > TAILLE_MAXIMALE:
            raise forms.ValidationError(
                "Le fichier dépasse la taille maximale de 2 Mio."
            )

        if not fichier.name.lower().endswith(".csv"):
            raise forms.ValidationError(
                "Veuillez sélectionner un fichier CSV."
            )

        return fichier


class ConfirmationImportAgentsForm(forms.Form):

    identifiant = forms.RegexField(
        regex=r"\A[0-9a-f]{32}\Z",
        min_length=32,
        max_length=32,
        widget=forms.HiddenInput(),
        error_messages={
            "invalid": "Identifiant de prévisualisation invalide.",
        },
    )

    confirmer_import = forms.BooleanField(
        label="Je confirme les opérations présentées.",
        required=True,
    )

    confirmer_retraits = forms.BooleanField(
        label="Je confirme les retraits de qualifications.",
        required=False,
    )


class AnnulationImportAgentsForm(forms.Form):

    identifiant = forms.RegexField(
        regex=r"\A[0-9a-f]{32}\Z",
        min_length=32,
        max_length=32,
        widget=forms.HiddenInput(),
    )
