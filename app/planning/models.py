from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator


class Grade(models.Model):
    code = models.CharField(
        max_length=12,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9]+\Z",
                message="Utilisez uniquement des lettres majuscules et des chiffres.",
            ),
        ],
        verbose_name="Code du grade",
    )
    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Appellation",
    )
    ordre = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Ordre hiérarchique",
    )
    galon = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Fichier du galon",
    )
    active = models.BooleanField(
        default=True,
        verbose_name="Actif",
    )

    class Meta:
        ordering = ["-ordre", "nom"]
        verbose_name = "Grade"
        verbose_name_plural = "Grades"

    def __str__(self):
        return f"{self.code} - {self.nom}"


class FonctionAgent(models.Model):
    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Fonction",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
    )
    active = models.BooleanField(
        default=True,
        verbose_name="Active",
    )

    class Meta:
        ordering = ["nom"]
        verbose_name = "Fonction"
        verbose_name_plural = "Fonctions"

    def __str__(self):
        return self.nom


class ProfilAgent(models.Model):
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profil_agent",
        verbose_name="Utilisateur",
    )

    grade = models.ForeignKey(
        Grade,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="agents",
        verbose_name="Grade",
    )
    telephone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Téléphone",
    )
    fonctions = models.ManyToManyField(
        FonctionAgent,
        blank=True,
        related_name="agents",
        verbose_name="Fonctions dans le centre",
    )

    def __str__(self):
        return self.utilisateur.get_full_name() or self.utilisateur.username

    class Meta:
        verbose_name = "Profil agent"
        verbose_name_plural = "Profils agents"


class Disponibilite(models.Model):
    profil = models.ForeignKey(
        ProfilAgent,
        on_delete=models.PROTECT,
        related_name="disponibilites_operationnelles",
        verbose_name="Profil agent",
    )


    debut = models.DateTimeField(
        verbose_name="Début de disponibilité",
    )

    fin = models.DateTimeField(
        verbose_name="Fin de disponibilité",
    )

    cree_le = models.DateTimeField(
        auto_now_add=True,
    )

    modifie_le = models.DateTimeField(
        auto_now=True,
    )

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()

        if self.debut and self.fin and self.fin <= self.debut:
            raise ValidationError({
                "fin": "La fin doit être postérieure au début."
            })

    def __str__(self):
        return (
            f"{self.profil} : "
            f"{self.debut:%d/%m/%Y %H:%M} - "
            f"{self.fin:%d/%m/%Y %H:%M}"
        )

    class Meta:
        verbose_name = "Disponibilité"
        verbose_name_plural = "Disponibilités"
        ordering = ["debut"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fin__gt=models.F("debut")),
                name="disponibilite_fin_apres_debut",
            ),
        ]


class Competence(models.Model):
    code = models.SlugField(max_length=100, unique=True)
    nom = models.CharField(max_length=150, unique=True)
    categorie = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["categorie", "nom"]
        verbose_name = "Compétence"
        verbose_name_plural = "Compétences"

    def __str__(self):
        return self.nom


class CompetenceAgent(models.Model):
    profil = models.ForeignKey(
        ProfilAgent,
        on_delete=models.PROTECT,
        related_name="attributions_competences",
        verbose_name="Profil agent",
    )

    competence = models.ForeignKey(
        Competence,
        on_delete=models.PROTECT,
        related_name="attributions",
    )
    date_validation = models.DateField(
        null=True,
        blank=True,
    )
    date_expiration = models.DateField(
        null=True,
        blank=True,
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="competences_validees",
    )

    class Meta:
        ordering = ["competence__nom"]
        verbose_name = "Compétence d'un agent"
        verbose_name_plural = "Compétences des agents"
        constraints = [
            models.UniqueConstraint(
                fields=["profil", "competence"],
                name="unique_competence_par_profil",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(date_validation__isnull=True)
                    | models.Q(date_expiration__isnull=True)
                    | models.Q(
                        date_expiration__gte=models.F("date_validation")
                    )
                ),
                name="competence_dates_coherentes",
            ),
        ]

    def __str__(self):
        return f"{self.profil} - {self.competence}"


class JournalAction(models.Model):

    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actions_journalisees",
    )

    action = models.CharField(max_length=100)

    type_objet = models.CharField(max_length=100)

    objet_id = models.PositiveBigIntegerField()

    details = models.JSONField(default=dict, blank=True)

    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_action", "-pk"]
        verbose_name = "Action journalisée"
        verbose_name_plural = "Actions journalisées"

        indexes = [
            models.Index(
                fields=["type_objet", "objet_id"],
                name="journal_objet_idx",
            ),
        ]

    def __str__(self):
        return f"{self.action} - {self.type_objet} #{self.objet_id}"


class ConfirmationImport(models.Model):

    empreinte = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )

    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="imports_confirmes",
    )

    date_confirmation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_confirmation"]
        verbose_name = "Confirmation d'import"
        verbose_name_plural = "Confirmations d'import"

    def __str__(self):
        return f"Import #{self.pk}"
