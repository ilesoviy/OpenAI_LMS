"""
Signal handling functions for use with external commerce service.
"""


import logging

from crum import get_current_request
from django.contrib.auth.models import AnonymousUser
from django.dispatch import receiver

from common.djangoapps.student.signals import REFUND_ORDER
from openedx.core.djangoapps.commerce.utils import is_commerce_service_configured

from .utils import refund_seat

log = logging.getLogger(__name__)


# pylint: disable=unused-argument
@receiver(REFUND_ORDER)
def handle_refund_order(sender, course_enrollment=None, **kwargs):
    """
    Signal receiver for unenrollments, used to automatically initiate refunds
    when applicable.
    """
    if not is_commerce_service_configured():
        return

    if course_enrollment and course_enrollment.refundable():
        try:
            request_user = get_request_user() or course_enrollment.user
            if isinstance(request_user, AnonymousUser):
                # Assume the request was initiated via server-to-server
                # API call (presumably Otto).  In this case we cannot
                # construct a client to call Otto back anyway, because
                # the client does not work anonymously, and furthermore,
                # there's certainly no need to inform Otto about this request.
                return
            refund_seat(course_enrollment, change_mode=True)
        except Exception:  # pylint: disable=broad-except
            # don't assume the signal was fired with `send_robust`.
            # avoid blowing up other signal handlers by gracefully
            # trapping the Exception and logging an error.
            log.exception(
                "Unexpected exception while attempting to initiate refund for user [%s], course [%s]",
                course_enrollment.user.id,
                course_enrollment.course_id,
            )


def get_request_user():
    """
    Helper to get the authenticated user from the current HTTP request (if
    applicable).

    If the requester of an unenrollment is not the same person as the student
    being unenrolled, we authenticate to the commerce service as the requester.
    """
    request = get_current_request()
    return getattr(request, 'user', None)
