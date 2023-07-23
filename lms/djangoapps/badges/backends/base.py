"""
Base class for badge backends.
"""


from abc import ABCMeta, abstractmethod


class BadgeBackend(metaclass=ABCMeta):
    """
    Defines the interface for badging backends.
    """

    @abstractmethod
    def award(self, badge_class, user, evidence_url=None):
        """
        Create a badge assertion for the user using this backend.
        """
