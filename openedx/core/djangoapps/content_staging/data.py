"""
Public python data types for content staging
"""
from attrs import field, frozen, validators
from datetime import datetime

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from opaque_keys.edx.keys import UsageKey


class StagedContentStatus(TextChoices):
    """ The status of this staged content. """
    # LOADING: We are actively (asynchronously) writing the OLX and related data into the staging area.
    # It is not ready to be read.
    LOADING = "loading", _("Loading")
    # READY: The content is staged and ready to be read.
    READY = "ready", _("Ready")
    # The content has expired and this row can be deleted, along with any associated data.
    EXPIRED = "expired", _("Expired")
    # ERROR: The content could not be staged.
    ERROR = "error", _("Error")


# Value of the "purpose" field on StagedContent objects used for clipboards.
CLIPBOARD_PURPOSE = "clipboard"
# There may be other valid values of "purpose" which aren't defined within this app.


@frozen
class StagedContentData:
    """
    Read-only data model representing StagedContent

    (OLX content that isn't part of any course at the moment)
    """
    id: int = field(validator=validators.instance_of(int))
    user_id: int = field(validator=validators.instance_of(int))
    created: datetime = field(validator=validators.instance_of(datetime))
    purpose: str = field(validator=validators.instance_of(str))
    status: StagedContentStatus = field(validator=validators.in_(StagedContentStatus), converter=StagedContentStatus)
    block_type: str = field(validator=validators.instance_of(str))
    display_name: str = field(validator=validators.instance_of(str))


@frozen
class UserClipboardData:
    """ Read-only data model for User Clipboard data (copied OLX) """
    content: StagedContentData = field(validator=validators.instance_of(StagedContentData))
    source_usage_key: UsageKey = field(validator=validators.instance_of(UsageKey))
