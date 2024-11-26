from django.core.mail import send_mail

def send_email_notification(subject, message, recipient_list):
    send_mail(
        subject,
        message,
        'artemsuskoa@yandex.ru',
        recipient_list,
        fail_silently=False,
    )
