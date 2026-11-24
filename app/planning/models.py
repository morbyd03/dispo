from django.conf import settings
from django.db import models


class ProfilAgent(models.Model):
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profil_agent",
        verbose_name="Utilisateur",
    )

    def __str__(self):
        return self.utilisateur.get_full_name() or self.utilisateur.username

    class Meta:
        verbose_name = "Profil agent"
        verbose_name_plural = "Profils agents"


class Disponibilite(models.Model):
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="disponibilites",
        verbose_name="Agent",
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
            f"{self.agent} : "
            f"{self.debut:%d/%m/%Y %H:%M} - "
            f"{self.fin:%d/%m/%Y %H:%M}"
        )

    class Meta:
        verbose_name = "Disponibilité"
        verbose_name_plural = "Disponibilités"
        ordering = ["debut"]


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
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="competences_agent",
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
                fields=["agent", "competence"],
                name="unique_competence_par_agent",
            ),
        ]

    def __str__(self):
        return f"{self.agent} - {self.competence}"
