from django import forms
from .models import Disponibilite


class DisponibiliteForm(forms.ModelForm):
    debut = forms.SplitDateTimeField(
        label="Début de disponibilité",
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time"},
            date_format="%Y-%m-%d",
            time_format="%H:%M",
        ),
    )

    fin = forms.SplitDateTimeField(
        label="Fin de disponibilité",
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time"},
            date_format="%Y-%m-%d",
            time_format="%H:%M",
        ),
    )

    class Meta:
        model = Disponibilite
        fields = ["debut", "fin"]

    def clean(self):
        cleaned_data = super().clean()

        debut = cleaned_data.get("debut")
        fin = cleaned_data.get("fin")

        if debut and fin and fin <= debut:
            self.add_error(
                "fin",
                "La fin doit être postérieure au début.",
            )

        return cleaned_data

from datetime import date

class CopieJourneeForm(forms.Form):
    date_source = forms.DateField(
        label="Date source",
        widget=forms.DateInput(
            attrs={"type": "date"},
            format="%Y-%m-%d",
        ),
        input_formats=["%Y-%m-%d"],
    )

    dates_destination = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
    )

    def clean_dates_destination(self):
        valeur = self.cleaned_data["dates_destination"]

        dates = []

        for element in valeur.split(","):
            element = element.strip()

            try:
                dates.append(date.fromisoformat(element))
            except ValueError:
                raise forms.ValidationError(
                    "Une date de destination est invalide."
                )

        dates = sorted(set(dates))

        if not dates:
            raise forms.ValidationError(
                "Sélectionnez au moins une date."
            )

        if len(dates) > 100:
            raise forms.ValidationError(
                "Vous pouvez sélectionner au maximum 100 dates."
            )

        return dates

    def clean(self):
        donnees = super().clean()

        source = donnees.get("date_source")
        destinations = donnees.get("dates_destination")

        if source and destinations:
            destinations = [
                jour for jour in destinations
                if jour != source
            ]

            if not destinations:
                self.add_error(
                    "dates_destination",
                    "Choisissez au moins une date différente "
                    "de la date source.",
                )

            donnees["dates_destination"] = destinations

        return donnees
