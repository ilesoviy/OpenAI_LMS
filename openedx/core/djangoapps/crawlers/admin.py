"""Admin panel for configuring which user agents we consider to be Crawlers."""


from config_models.admin import ConfigurationModelAdmin
from django.contrib import admin

from .models import CrawlersConfig

admin.site.register(CrawlersConfig, ConfigurationModelAdmin)
