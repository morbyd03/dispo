from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def envoyer_activation_agent(request, agent):
    if not agent.is_active or not agent.email:
        raise ValueError("Le compte doit être actif et posséder un e-mail.")

    uid = urlsafe_base64_encode(force_bytes(agent.pk))
    token = default_token_generator.make_token(agent)

    chemin = reverse(
        "password_reset_confirm",
        kwargs={"uidb64": uid, "token": token},
    )

    lien = request.build_absolute_uri(chemin)

    message = (
        f"Bonjour {agent.first_name or agent.username},\n\n"
        f"Votre compte {settings.DISPO_NAME} a été créé.\n\n"
        "Pour définir votre mot de passe, cliquez sur ce lien :\n"
        f"{lien}\n\n"
        "Si vous n'attendiez pas cet e-mail, ignorez-le.\n"
    )

    return send_mail(
        subject=f"{settings.DISPO_NAME} - Activation de votre compte",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[agent.email],
        fail_silently=False,
    )


def envoyer_reinitialisation_agent(request, agent):
    if not agent.is_active or not agent.email:
        raise ValueError(
            "Le compte doit être actif et posséder un e-mail."
        )

    uid = urlsafe_base64_encode(force_bytes(agent.pk))
    token = default_token_generator.make_token(agent)

    chemin = reverse(
        "password_reset_confirm",
        kwargs={"uidb64": uid, "token": token},
    )

    lien = request.build_absolute_uri(chemin)

    message = (
        f"Bonjour {agent.first_name or agent.username},\n\n"
        f"Votre administrateur {settings.DISPO_NAME} vous invite à définir "
        "un nouveau mot de passe.\n\n"
        "Cliquez sur le lien suivant :\n"
        f"{lien}\n\n"
        "Si vous n'attendiez pas cet e-mail, ignorez-le.\n"
        "Votre mot de passe actuel restera inchangé.\n\n"
        f"L'équipe {settings.DISPO_NAME}"
    )

    return send_mail(
        subject=f"{settings.DISPO_NAME} - Réinitialisation de votre mot de passe",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[agent.email],
        fail_silently=False,
    )
