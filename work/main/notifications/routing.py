from django.urls import re_path
from main.notifications.consumers import NotificationsConsumer

websocket_urlpatterns = [
    re_path(r'ws/api/v1/ws/notifications/(?P<user_id>\d+)/$', NotificationsConsumer.as_asgi()),
]