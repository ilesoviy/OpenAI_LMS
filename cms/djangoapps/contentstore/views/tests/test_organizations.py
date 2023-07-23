"""Tests covering the Organizations listing on the Studio home."""


import json

from django.test import TestCase
from django.urls import reverse
from organizations.api import add_organization

from common.djangoapps.student.tests.factories import UserFactory


class TestOrganizationListing(TestCase):
    """Verify Organization listing behavior."""
    def setUp(self):
        super().setUp()
        self.staff = UserFactory(is_staff=True)
        self.client.login(username=self.staff.username, password='test')
        self.org_names_listing_url = reverse('organizations')
        self.org_short_names = ["alphaX", "betaX", "orgX"]
        for index, short_name in enumerate(self.org_short_names):
            add_organization(organization_data={
                'name': 'Test Organization %s' % index,
                'short_name': short_name,
                'description': 'Testing Organization %s Description' % index,
            })

    def test_organization_list(self):
        """Verify that the organization names list api returns list of organization short names."""
        response = self.client.get(self.org_names_listing_url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        org_names = json.loads(response.content.decode('utf-8'))
        self.assertEqual(org_names, self.org_short_names)
