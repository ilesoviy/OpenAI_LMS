"""
Django Admin pages for CourseDurationLimitConfig.
"""


from django.contrib import admin

from openedx.core.djangoapps.config_model_utils.admin import StackedConfigModelAdmin

from .models import CourseDurationLimitConfig

admin.site.register(CourseDurationLimitConfig, StackedConfigModelAdmin)
