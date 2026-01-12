from django.shortcuts import render
from .models import Milestone

def timeline_view(request):
    milestones = Milestone.objects.all()
    return render(request, 'timeline.html', {'milestones': milestones})