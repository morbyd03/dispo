from django.db import migrations


GRADES = [
    ("SAP2", "Sapeur de 2e classe", 10),
    ("SAP1", "Sapeur de 1re classe", 20),
    ("CPL", "Caporal", 30),
    ("CCH", "Caporal-chef", 40),
    ("SGT", "Sergent", 50),
    ("SCH", "Sergent-chef", 60),
    ("ADJ", "Adjudant", 70),
    ("ADC", "Adjudant-chef", 80),
    ("LTN", "Lieutenant", 90),
    ("CNE", "Capitaine", 100),
    ("CDT", "Commandant", 110),
    ("LCL", "Lieutenant-colonel", 120),
    ("COL", "Colonel", 130),
]


def initialiser_grades(apps, schema_editor):
    Grade = apps.get_model("planning", "Grade")

    for code, nom, ordre in GRADES:
        Grade.objects.using(
            schema_editor.connection.alias
        ).get_or_create(
            code=code,
            defaults={
                "nom": nom,
                "ordre": ordre,
                "active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("planning", "0008_profils_agents"),
    ]

    operations = [
        migrations.RunPython(
            initialiser_grades,
            migrations.RunPython.noop,
        ),
    ]
