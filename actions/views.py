from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import UserNotification

import json

@method_decorator(csrf_exempt, name='dispatch')
class MarkNotificationsAsReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            # Parse the notification IDs from the request body
            data = json.loads(request.body)
            notification_ids = data.get('notification_ids', [])

            # Bulk update the notifications to mark them as read
            UserNotification.objects.filter(id__in=notification_ids, user=request.user).update(
                is_read=True,
                read_at=timezone.now()
            )

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)