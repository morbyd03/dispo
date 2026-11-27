from ..models import JournalAction


def journaliser(*, auteur, action, objet, details=None):
    return JournalAction.objects.create(
        auteur=auteur,
        action=action,
        type_objet=objet._meta.label_lower,
        objet_id=objet.pk,
        details=details if details is not None else {},
    )
