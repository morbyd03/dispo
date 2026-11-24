from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def mon_profil(request):
    agent = request.user

    if agent.is_superuser:
        role = "Superutilisateur"
    elif agent.groups.filter(name="Administrateurs Dispo").exists():
        role = "Administrateur Dispo"
    else:
        role = "Agent"

    competences = (
        agent.competences_agent
        .select_related("competence")
        .order_by("competence__nom")
    )

    return render(
        request,
        "planning/mon_profil.html",
        {
            "agent": agent,
            "role": role,
            "competences": competences,
        },
    )


from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.contrib import messages


class ChangerMotDePasse(PasswordChangeView):
    template_name = "planning/changer_mot_de_passe.html"
    success_url = reverse_lazy("mon_profil")

    def form_valid(self, form):
        reponse = super().form_valid(form)
        messages.success(
            self.request,
            "Votre mot de passe a été modifié avec succès."
        )
        return reponse
