from django.db import migrations


def verifier_emails(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT LOWER(TRIM(email))
                FROM auth_user
                WHERE TRIM(email) <> ''
                GROUP BY LOWER(TRIM(email))
                HAVING COUNT(*) > 1
            ) AS doublons
        """)

        nombre = cursor.fetchone()[0]

    if nombre:
        raise RuntimeError(
            f"Migration interrompue : {nombre} groupe(s) "
            "d'adresses email en doublon."
        )


class Migration(migrations.Migration):

    dependencies = [
        ("planning", "0014_relations_definitives"),
    ]

    operations = [
        migrations.RunPython(
            verifier_emails,
            migrations.RunPython.noop,
        ),
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX dispo_unique_email
                ON auth_user (LOWER(TRIM(email)))
                WHERE TRIM(email) <> '';
            """,
            reverse_sql="""
                DROP INDEX dispo_unique_email;
            """,
        ),
    ]
