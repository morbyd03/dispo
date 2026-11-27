from django.db import migrations


def transferer_relations(apps, schema_editor):
    alias = schema_editor.connection.alias

    ProfilAgent = apps.get_model("planning", "ProfilAgent")

    for nom_modele in ("CompetenceAgent", "Disponibilite"):
        Modele = apps.get_model("planning", nom_modele)

        for profil in ProfilAgent.objects.using(alias).all():
            Modele.objects.using(alias).filter(
                agent_id=profil.utilisateur_id,
                profil_id__isnull=True,
            ).update(profil_id=profil.pk)


def annuler_transfert(apps, schema_editor):
    alias = schema_editor.connection.alias

    for nom_modele in ("CompetenceAgent", "Disponibilite"):
        Modele = apps.get_model("planning", nom_modele)
        Modele.objects.using(alias).update(profil_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("planning", "0010_relations_profils"),
    ]

    operations = [
        migrations.RunPython(
            transferer_relations,
            annuler_transfert,
        ),
    ]
