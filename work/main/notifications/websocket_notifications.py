from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def send_websocket_notification(user_id, message):
    """
    Отправка сообщения через WebSocket конкретному пользователю.
    """
    try:
        print(f"Отправка сообщения для user_{user_id}, message={message}")
        channel_layer = get_channel_layer()
        group_name = f"user_{user_id}"
        print(f"Подключен channel_layer: {channel_layer}")
        print(f"Определена группа: {group_name}")


        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",
                "message": {
                    "message": message
                },
            }
        )
        print("Сообщение успешно отправлено!")
    except Exception as e:
        print(f"Ошибка при отправке сообщения через WebSocket: {e}")
