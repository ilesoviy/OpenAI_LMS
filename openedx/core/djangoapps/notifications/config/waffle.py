"""
This module contains various configuration settings via
waffle switches for the notifications app.
"""

from openedx.core.djangoapps.waffle_utils import CourseWaffleFlag

WAFFLE_NAMESPACE = 'notifications'

# .. toggle_name: notifications.enable_notifications
# .. toggle_implementation: CourseWaffleFlag
# .. toggle_default: False
# .. toggle_description: Waffle flag to enable the Notifications feature
# .. toggle_use_cases: temporary, open_edx
# .. toggle_creation_date: 2023-05-05
# .. toggle_target_removal_date: 2023-11-05
# .. toggle_warning: When the flag is ON, Notifications feature is enabled.
# .. toggle_tickets: INF-866
ENABLE_NOTIFICATIONS = CourseWaffleFlag(f'{WAFFLE_NAMESPACE}.enable_notifications', __name__)
