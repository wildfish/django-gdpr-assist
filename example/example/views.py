"""
Example views for gdpr-assist
"""
import random

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import TemplateView

from autofixture import AutoFixture, generators

from .models import Person, HealthRecord, PersonProfile, MailingListLog


class IndexView(TemplateView):
    template_name = 'index.html'
    error_msg = ''

    def post(self, request, *args, **kwargs):
        person_pk = request.POST.get('person_pk')
        person = None
        if person_pk:
            try:
                person = Person.objects.get(pk=person_pk)
            except Person.DoesNotExist:
                messages.error(request, 'Person {} not found'.format(person_pk))

        action = request.POST['action']
        if action == 'Populate data':
            self.populate_data()
        elif action == 'Delete':
            if not person:
                messages.error(request, 'Person not found')
            else:
                person.delete()
                messages.success(request, 'Person {} deleted'.format(person_pk))
        else:
            messages.error(request, 'Unrecognised action')

        return redirect('index')

    def get_context_data(self, **context):
        context.update(dict(
            people=Person.objects.all(),
            health_records=HealthRecord.objects.all(),
            person_profiles=PersonProfile.objects.all(),
            mailing_list_logs=MailingListLog.objects.all(),
        ))
        return context

    def populate_data(self):
        people = AutoFixture(
            Person,
            field_values={
                'anonymised': False,
                'name': generators.FirstNameGenerator(),
            },
        ).create(5)

        for person in people:
            AutoFixture(
                HealthRecord,
                field_values={
                    'anonymised': False,
                    'person': person,
                },
            ).create(random.randint(1, 3))

            AutoFixture(
                PersonProfile,
                field_values={
                    'anonymised': False,
                    'person': person,
                    'age': generators.IntegerGenerator(5, 55),
                    'address': generators.LoremGenerator(max_length=100),
                },
            ).create(random.randint(1, 3))

            AutoFixture(
                MailingListLog,
                field_values={
                    'anonymised': False,
                    'email': person.email,
                    'sent_at': generators.DateTimeGenerator(),
                },
            ).create(random.randint(1, 3))
