"""
Internal signals
"""
from django.dispatch import Signal


# providing_args = ["instance"]
pre_anonymise = Signal()
post_anonymise = Signal()
