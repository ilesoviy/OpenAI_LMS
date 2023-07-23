""" Admin site bindings for commerce app. """


from config_models.admin import ConfigurationModelAdmin
from django.contrib import admin

from .models import CommerceConfiguration

admin.site.register(CommerceConfiguration, ConfigurationModelAdmin)
