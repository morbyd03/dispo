from django.db import migrations
from django.db.models import F


def verifier_relations(apps, schema_editor):
    alias = schema_editor.connection.alias
    anomalies = []

    for nom in ("CompetenceAgent", "Disponibilite"):
        Modele = apps.get_model("planning", nom)
        objets = Modele.objects.using(alias)

        sans_profil = objets.filter(
            profil_id__isnull=True
        ).count()

        incoherents = objets.filter(
            profil_id__isnull=False
        ).exclude(
            agent_id=F("profil__utilisateur_id")
        ).count()

        if sans_profil or incoherents:
            anomalies.append(
                f"{nom}: {sans_profil} sans profil, "
                f"{incoherents} relations incoherentes"
            )

    if anomalies:
        raise RuntimeError(
            "Migration interrompue. "
            "Regularisation necessaire : "
            + "; ".join(anomalies)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("planning", "0012_contraintes_integrite"),
    ]

    operations = [
        migrations.RunPython(
            verifier_relations,
            migrations.RunPython.noop,
        ),
    ]
