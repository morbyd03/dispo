from django.db import migrations


def initialiser_catalogue(apps, schema_editor):
    Competence = apps.get_model("planning", "Competence")
    alias = schema_editor.connection.alias

    catalogue = [
        ("chef_ssuap", "Chef d'agrès SSUAP", "SSUAP"),
        ("equipier_ssuap", "Équipier SSUAP", "SSUAP"),
        ("chef_inc", "Chef d'agrès incendie", "Incendie"),
        ("equipier_inc", "Équipier incendie", "Incendie"),
        ("permis_pl", "Permis poids lourd", "Conduite"),
        ("cod1", "COD1", "Conduite"),
        ("fdf1", "FDF1", "Feux de forêt"),
        ("fdf2", "FDF2", "Feux de forêt"),
    ]

    for code, nom, categorie in catalogue:
        Competence.objects.using(alias).get_or_create(
            code=code,
            defaults={
                "nom": nom,
                "categorie": categorie,
                "active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("planning", "0006_alter_competence_code"),
    ]

    operations = [
        migrations.RunPython(
            initialiser_catalogue,
            migrations.RunPython.noop,
        ),
    ]
