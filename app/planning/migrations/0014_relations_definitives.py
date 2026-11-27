import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def verifier_relations(apps, schema_editor):
    alias = schema_editor.connection.alias

    for nom in ("CompetenceAgent", "Disponibilite"):
        Modele = apps.get_model("planning", nom)
        objets = Modele.objects.using(alias)

        if objets.filter(profil_id__isnull=True).exists():
            raise RuntimeError(f"{nom} : profil manquant.")

        if objets.exclude(
            agent_id=F("profil__utilisateur_id")
        ).exists():
            raise RuntimeError(f"{nom} : relation incoherente.")


class Migration(migrations.Migration):

    atomic = True

    dependencies = [
        ("planning", "0013_verifier_relations_profils"),
    ]

    operations = [
        migrations.RunPython(verifier_relations),
        migrations.RemoveConstraint(
            model_name="competenceagent",
            name="unique_competence_par_agent",
        ),
        migrations.AlterField(
            model_name="competenceagent",
            name="profil",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="attributions_competences",
                to="planning.profilagent",
                verbose_name="Profil agent",
            ),
        ),
        migrations.AlterField(
            model_name="disponibilite",
            name="profil",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="disponibilites_operationnelles",
                to="planning.profilagent",
                verbose_name="Profil agent",
            ),
        ),
        migrations.RemoveField(
            model_name="competenceagent",
            name="agent",
        ),
        migrations.RemoveField(
            model_name="disponibilite",
            name="agent",
        ),
    ]
