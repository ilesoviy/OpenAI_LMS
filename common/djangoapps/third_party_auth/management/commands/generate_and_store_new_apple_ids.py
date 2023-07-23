"""
Management command to exchange apple transfer identifiers with Apple ID of the
user for new migrated team.
"""


import logging
import requests
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
import jwt
from social_django.utils import load_strategy

from common.djangoapps.third_party_auth.models import AppleMigrationUserIdInfo
from common.djangoapps.third_party_auth.appleid import AppleIdAuth

log = logging.getLogger(__name__)


class AccessTokenExpiredException(Exception):
    """
    Raised when access token has been expired.
    """


class Command(BaseCommand):
    """
    Management command to exchange transfer identifiers for new team-scoped identifier for
    the user in new migrated team.

    Usage:
        manage.py generate_and_store_apple_transfer_ids
    """

    def _generate_client_secret(self):
        """
        Generate client secret for use in Apple API's
        """
        now = int(time.time())
        expiry = 60 * 60 * 3  # 3 hours

        backend = load_strategy().get_backend(AppleIdAuth.name)
        team_id = backend.setting('TEAM')
        key_id = backend.setting('KEY')
        private_key = backend.get_private_key()
        audience = backend.TOKEN_AUDIENCE

        headers = {
            "alg": "ES256",
            'kid': key_id
        }
        payload = {
            'iss': team_id,
            'iat': now,
            'exp': now + expiry,
            'aud': audience,
            'sub': "org.edx.mobile",
        }

        return jwt.encode(payload, key=private_key, algorithm='ES256',
                          headers=headers)

    def _generate_access_token(self, client_secret):
        """
        Generate access token for use in Apple API's
        """
        access_token_url = 'https://appleid.apple.com/auth/token'
        app_id = "org.edx.mobile"
        payload = {
            "grant_type": "client_credentials",
            "scope": "user.migration",
            "client_id": app_id,
            "client_secret": client_secret
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "appleid.apple.com"
        }
        response = requests.post(access_token_url, data=payload, headers=headers)
        access_token = response.json().get('access_token')
        return access_token

    def _get_token_and_secret(self):
        """
        Get access_token and client_secret
        """
        client_secret = self._generate_client_secret()
        access_token = self._generate_access_token(client_secret)
        return access_token, client_secret

    def _update_token_and_secret(self):
        self.access_token, self.client_secret = self._get_token_and_secret()  # pylint: disable=W0201

    def _fetch_new_apple_id(self, transfer_id):
        """
        Fetch Apple ID for a given transfer ID from Apple API.
        """
        migration_url = "https://appleid.apple.com/auth/usermigrationinfo"
        app_id = "org.edx.mobile"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "appleid.apple.com",
            "Authorization": "Bearer " + self.access_token
        }
        payload = {
            "client_id": app_id,
            "client_secret": self.client_secret,
            "transfer_sub": transfer_id
        }
        response = requests.post(migration_url, data=payload, headers=headers)
        if response.status_code == 400:
            raise AccessTokenExpiredException

        return response.json().get('sub')

    def _exchange_transfer_id_for_new_apple_id(self, transfer_id):
        """
        For a Transfer ID obtained from the transferring team,
        return the correlating Apple ID belonging to the recipient team.
        """
        try:
            new_apple_id = self._fetch_new_apple_id(transfer_id)
        except AccessTokenExpiredException:
            log.info('Access token expired. Re-creating access token.')
            self._update_token_and_secret()
            new_apple_id = self._fetch_new_apple_id(transfer_id)

        return new_apple_id

    @transaction.atomic
    def handle(self, *args, **options):
        self._update_token_and_secret()
        if not self.access_token:
            raise CommandError('Failed to create access token.')

        apple_user_ids_info = AppleMigrationUserIdInfo.objects.filter(Q(new_apple_id__isnull=True) | Q(new_apple_id=""),
                                                                      ~Q(transfer_id=""), transfer_id__isnull=False)
        for apple_user_id_info in apple_user_ids_info:
            new_apple_id = self._exchange_transfer_id_for_new_apple_id(apple_user_id_info.transfer_id)
            if new_apple_id:
                apple_user_id_info.new_apple_id = new_apple_id
                apple_user_id_info.save()
                log.info('Updated new Apple ID for uid %s',
                         apple_user_id_info.old_apple_id)
            else:
                log.info('Unable to fetch new Apple ID for uid %s',
                         apple_user_id_info.old_apple_id)
