from django.shortcuts import render
from django.utils import timezone
from tea.models import Tea


def published_tea_list(request):
    now = timezone.now()
    teas = Tea.objects.filter(published_at__isnull=False, published_at__lt=now)
    return render(request, 'tea/published_tea_list.html', {'teas': teas})
