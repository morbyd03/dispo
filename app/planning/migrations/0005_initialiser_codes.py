from django.db import migrations
from django.db.models import Q
from django.utils.text import slugify


def initialiser_codes(apps, schema_editor):
    Competence = apps.get_model("planning", "Competence")

    for competence in Competence.objects.filter(Q(code__isnull=True) | Q(code="")):
        base = slugify(competence.nom) or "competence"
        code = base[:100]
        numero = 2

        while Competence.objects.filter(code=code).exclude(
            pk=competence.pk
        ).exists():
            suffixe = f"-{numero}"
            code = f"{base[:100 - len(suffixe)]}{suffixe}"
            numero += 1

        competence.code = code
        competence.save(update_fields=["code"])


class Migration(migrations.Migration):
    dependencies = [
        ("planning", "0004_remove_profilagent_chef_inc_and_more"),
    ]

    operations = [
        migrations.RunPython(
            initialiser_codes,
            migrations.RunPython.noop,
        ),
    ]
