"""
Example models for GDPR-assist
"""
import random

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from gdpr_assist import register
from gdpr_assist.deletion import ANONYMISE
from gdpr_assist.signals import pre_anonymise


class UserPrivacyMeta:
    fields = ["username", "email"]


register(User, UserPrivacyMeta, default_manager_name="objects_anonymised")


class Person(models.Model):
    """
    A model with PII
    """

    name = models.CharField(max_length=255)
    email = models.EmailField()

    class Meta:
        verbose_name_plural = "People"

    class PrivacyMeta:
        fields = ["name", "email"]
        search_fields = ["email"]

    def __str__(self):
        return self.name


class HealthRecord(models.Model):
    """
    A model with PII, with an FK to another model with PII
    """

    person = models.ForeignKey("Person", on_delete=models.CASCADE)
    notes = models.CharField(max_length=255)

    class PrivacyMeta:
        fields = ["notes"]

    def __str__(self):
        return self.person.name


class PersonProfile(models.Model):
    """
    A model with an ANONYMISE FK to a third party model
    """

    person = models.ForeignKey(
        "Person", on_delete=ANONYMISE(models.SET_NULL), blank=True, null=True
    )
    age = models.IntegerField(blank=True, null=True)
    address = models.TextField(blank=True)
    has_children = models.BooleanField(null=True)

    class PrivacyMeta(object):
        fields = ["age", "address"]

        def anonymise_age(self, instance):
            """
            Anonymise the age by shifting it by a random amount
            """
            instance.age = instance.age + random.randrange(-5, 5)

    def __str__(self):
        if self.person:
            return self.person.name
        else:
            return "Anonymised {}".format(self.pk)


class MailingListLog(models.Model):
    """
    A model which relates to another PII model but with no direct DB reference
    """

    email = models.EmailField()
    sent_at = models.DateTimeField()

    class PrivacyMeta:
        fields = ["email"]
        search_fields = ["email"]

    def __str__(self):
        return self.email


@receiver(pre_delete, sender=Person)
@receiver(pre_anonymise, sender=Person)
def anonymise_mailing_list_log(sender, instance, **kwargs):
    """
    Automatic anonymiser will not detect this, as it's not a true database
    relationship
    """
    MailingListLog.objects.filter(email=instance.email).anonymise()
