"""
Management command to update new Apple ID from AppleMigrationUserIdInfo to UserSocialAuth.
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from social_django.models import UserSocialAuth

from common.djangoapps.third_party_auth.models import AppleMigrationUserIdInfo
from common.djangoapps.third_party_auth.appleid import AppleIdAuth

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to update new Apple ID from AppleMigrationUserIdInfo to UserSocialAuth.

    Usage:
        manage.py update_new_apple_ids_in_social_auth
    """

    @transaction.atomic
    def handle(self, *args, **options):
        apple_user_ids_info = AppleMigrationUserIdInfo.objects.filter(
            ~Q(new_apple_id=''), new_apple_id__isnull=False
        )
        if not apple_user_ids_info:
            raise CommandError('No Apple ID User info found.')
        for apple_user_id_info in apple_user_ids_info:
            user_social_auth = UserSocialAuth.objects.filter(
                uid=apple_user_id_info.old_apple_id, provider=AppleIdAuth.name
            ).first()
            if user_social_auth:
                user_social_auth.uid = apple_user_id_info.new_apple_id
                user_social_auth.save()
                log.info(
                    'Replaced Apple ID %s with %s',
                    apple_user_id_info.old_apple_id,
                    apple_user_id_info.new_apple_id
                )
