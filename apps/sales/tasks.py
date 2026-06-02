"""apps/sales/tasks.py — Sales background tasks."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_order_confirmation(self, order_id: str) -> str:
    """
    Send order confirmation email.
    High priority queue — retries with exponential backoff.
    """
    from django.conf import settings
    from django.core.mail import send_mail

    from apps.sales.models import Order

    try:
        logger.info("Sending order confirmation for order %s", order_id)

        # Lấy thông tin Order và Customer từ Database
        order = Order.objects.select_related("customer").get(pk=order_id)
        customer_email = order.customer.email
        customer_name = order.customer.full_name

        subject = f"BikeStore - Xác nhận Đơn hàng #{str(order.id)[:8]}"
        message = (
            f"Xin chào {customer_name},\n\n"
            f"Cảm ơn bạn đã mua sắm tại BikeStore! Đơn hàng của bạn đã được ghi nhận thành công.\n"
            f"Trạng thái: {order.status.upper()}\n"
            f"Ngày đặt hàng: {order.order_date}\n\n"
            f"Trân trọng,\nĐội ngũ BikeStore."
        )

        # Gọi hàm gửi Mail thực sự của Django
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer_email],
            fail_silently=False,
        )

        return f"Confirmation sent for {order_id}"
    except Exception as exc:
        logger.error("Failed to send confirmation for %s: %s", order_id, exc)
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@shared_task
def cleanup_expired_orders() -> int:
    """
    Cancel PENDING orders older than 7 days.
    Runs periodically (e.g. daily via celery-beat).

    Uses selectors to get the queryset and bulk-updates status to REJECTED.
    """
    from .models import OrderStatus
    from .selectors import get_pending_orders_older_than

    expired_qs = get_pending_orders_older_than(days=7)
    count = expired_qs.update(status=OrderStatus.REJECTED)

    logger.info("Cleaned up %d expired PENDING orders", count)
    return count
