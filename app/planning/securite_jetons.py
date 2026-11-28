from django.contrib.auth.tokens import PasswordResetTokenGenerator

from .services.securite import version_securite_compte


class JetonCompteDispo(PasswordResetTokenGenerator):

    def _make_hash_value(self, user, timestamp):
        valeur = super()._make_hash_value(
            user, timestamp
        )

        version = version_securite_compte(user.pk)

        return (
            f"{valeur}|dispo-v1|"
            f"{version}|{int(user.is_active)}"
        )

    def check_token(self, user, token):
        if user is None or not user.is_active:
            return False

        return super().check_token(user, token)


generateur_jetons_compte = JetonCompteDispo()
