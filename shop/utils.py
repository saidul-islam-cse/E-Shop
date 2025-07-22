import json
import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage


def send_verification_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    current_site = get_current_site(request)
    verification_link = f"http://{current_site.domain}/verify/{uid}/{token}"

    email_subject = "Verify Your Email Address"
    email_body = render_to_string(
        "shop/verification_email.html",
        {"user": user, "verification_link": verification_link},
    )

    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    
    email.content_subtype = "html"
    email.send()
def generate_sslcommerz_payment(order, request):
    """Generate SSLCommerz payment URL"""
    post_data = {
        'store_id': settings.SSLCOMMERZ_STORE_ID,
        'store_passwd': settings.SSLCOMMERZ_STORE_PASSWORD,
        'total_amount': float(order.get_total_cost()),
        'currency': 'BDT',
        'tran_id': str(order.id),
        'success_url': request.build_absolute_uri(f'/payment/success/{order.id}/'),
        'fail_url': request.build_absolute_uri(f'/payment/fail/{order.id}/'),
        'cancel_url': request.build_absolute_uri(f'/payment/cancel/{order.id}/'),
        'cus_name': f"{order.first_name} {order.last_name}",
        'cus_email': order.email,
        'cus_add1': order.address,
        'cus_city': order.city,
        'cus_postcode': order.postal_code,
        'cus_country': 'Bangladesh',
        'shipping_method': 'NO',
        'product_name': 'Products from our store',
        'product_category': 'General',
        'product_profile': 'general',
    }
    
    response = requests.post(settings.SSLCOMMERZ_PAYMENT_URL, data=post_data)
    return json.loads(response.text)

def send_order_confirmation_email(order):
    subject = f"Order Confirmation - Order #{order.id}"
    message = render_to_string('shop/email/order_confirmation.html', {'order' : order})
    to = order.email
    send_email = EmailMultiAlternatives(subject, '', to=[to])
    send_email.attach_alternative(message, "text/html")
    send_email.send()