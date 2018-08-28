"""
Internal signals
"""
from django.dispatch import Signal


pre_anonymise = Signal(providing_args=['instance'])
post_anonymise = Signal(providing_args=['instance'])
