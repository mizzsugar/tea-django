from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from tea.models import Tea


def published_tea_list(request):
    now = timezone.now()
    teas = Tea.objects.filter(published_at__isnull=False, published_at__lt=now)
    return render(request, 'tea/published_tea_list.html', {'teas': teas})


def published_tea_detail(request, tea_id: int):
    now = timezone.now()
    tea = get_object_or_404(Tea, id=tea_id, published_at__isnull=False, published_at__lt=now)
    return render(request, 'tea/published_tea_detail.html', {'tea': tea})
