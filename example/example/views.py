"""
Example views for gdpr-assist
"""
import random

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import TemplateView

from model_bakery import baker
from model_bakery.recipe import seq

from .models import HealthRecord, MailingListLog, Person, PersonProfile


class IndexView(TemplateView):
    template_name = "index.html"
    error_msg = ""

    def post(self, request, *args, **kwargs):
        person_pk = request.POST.get("person_pk")
        person = None
        if person_pk:
            try:
                person = Person.objects.get(pk=person_pk)
            except Person.DoesNotExist:
                messages.error(request, "Person {} not found".format(person_pk))

        action = request.POST["action"]
        if action == "Populate data":
            self.populate_data()
        elif action == "Delete":
            if not person:
                messages.error(request, "Person not found")
            else:
                person.delete()
                messages.success(request, "Person {} deleted".format(person_pk))
        else:
            messages.error(request, "Unrecognised action")

        return redirect("index")

    def get_context_data(self, **context):
        context.update(
            dict(
                people=Person.objects.all(),
                health_records=HealthRecord.objects.all(),
                person_profiles=PersonProfile.objects.all(),
                mailing_list_logs=MailingListLog.objects.all(),
            )
        )
        return context

    def populate_data(self):
        people = baker.make(Person, name=seq('Name'), _quantity=5)

        for person in people:
            baker.make(HealthRecord, person=person, _quantity=random.randint(1, 3))
            baker.make(PersonProfile, person=person, age=random.randint(5, 555))
            baker.make(MailingListLog, email=person.email, _quantity=random.randint(1, 3))
