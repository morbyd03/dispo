from django import template

register = template.Library()


@register.filter
def heures_minutes(minutes):
    if minutes is None:
        return "—"

    minutes = int(minutes)

    heures, minutes_restantes = divmod(minutes, 60)

    if minutes_restantes == 0:
        return f"{heures} h"

    return f"{heures} h {minutes_restantes:02d}"
