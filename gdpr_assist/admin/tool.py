"""
Personal data admin tool
"""
from collections import defaultdict
import csv
from io import StringIO, BytesIO
import six
import zipfile

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

try:
    from django.urls import reverse
except ImportError:
    # Django <2.0
    from django.core.urlresolvers import reverse

from .. import app_settings
from ..registry import registry

csrf_protect_m = method_decorator(csrf_protect)


class PersonalData(models.Model):
    """
    Fake model to make this project appear in the admin without intrusive hacks
    """
    class Meta:
        managed = False
        verbose_name_plural = 'Personal data'


class PersonalDataSearchForm(forms.Form):
    ACTION_EXPORT = 'export'
    ACTION_ANONYMISE = 'anonymise'

    term = forms.CharField(
        label='Search for',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'id': 'searchbar'}),  # Reuse std styles
    )
    action = forms.ChoiceField(
        label='Action',
        choices=(
            (ACTION_EXPORT, 'Export'),
            (ACTION_ANONYMISE, 'Anonymise'),
        ),
        required=False,
    )


class PersonalDataAdmin(admin.ModelAdmin):
    change_list_template = 'gdpr_assist/admin/pd_change_list.html'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request):
        return False

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        """
        The replacement view to manage PII
        """
        form = PersonalDataSearchForm(request.POST or None)
        results = None
        if form.is_valid():
            term = form.cleaned_data['term']
            action = form.cleaned_data['action']
            if action:
                # Get list of pks by object
                raw_objs = request.POST.getlist('obj_pk')
                group_pks = defaultdict(list)
                for raw_obj in raw_objs:
                    content_type_id, obj_pk = raw_obj.split('-', 1)
                    group_pks[content_type_id].append(obj_pk)

                # Get the objects
                querysets = {}
                for content_type_id, pks in group_pks.items():
                    content_type = ContentType.objects.get_for_id(
                        content_type_id,
                    )
                    model = content_type.model_class()
                    qs = model.objects.filter(pk__in=pks)
                    if qs.exists():
                        querysets[model] = qs

                if not querysets:
                    messages.error(request, "No objects selected")

                elif action == PersonalDataSearchForm.ACTION_EXPORT:
                    return self.handle_export(request, querysets)

                elif action == PersonalDataSearchForm.ACTION_ANONYMISE:
                    return self.handle_anonymise(request, querysets)

            # Search
            raw_results = registry.search(term)

            # Restructure results so it can be used in the template
            results = (
                {
                    'model': model,
                    'results': model_results,
                    'app_label': model._meta.app_label,
                    'model_name': model._meta.verbose_name,
                    'content_type': ContentType.objects.get_for_model(model),
                    'url_name': 'admin:{}_{}_change'.format(
                        model._meta.app_label,
                        model._meta.model_name,
                    ),
                }
                for model, model_results in raw_results
                if model_results
            )

        return render(request, self.change_list_template, {
            'title': 'Personal Data',
            'form': form,
            'results': results,
            'media': self.media,
        })

    def handle_export(self, request, querysets):
        """
        Handle an export request
        """
        zipfile_buffer = BytesIO()
        with zipfile.ZipFile(zipfile_buffer, 'w') as zipped_file:
            for model, queryset in querysets.items():
                # Generate CSV data in memory
                csv_buffer = StringIO()
                csv_writer = None
                for obj in queryset:
                    privacy_meta = getattr(
                        model,
                        app_settings.GDPR_PRIVACY_INSTANCE_NAME,
                    )
                    obj_export = privacy_meta.export(obj)

                    # If this is the first row, add the header row
                    if not csv_writer:
                        csv_writer = csv.DictWriter(
                            csv_buffer,
                            fieldnames=[
                                six.text_type(key)
                                for key in obj_export.keys()
                            ],
                        )
                        csv_writer.writeheader()

                    csv_writer.writerow(obj_export)

                # Add CSV file to zip
                privacy_meta = getattr(
                    model,
                    app_settings.GDPR_PRIVACY_INSTANCE_NAME,
                )
                csv_filename = privacy_meta.get_export_filename()
                zipped_file.writestr(csv_filename, csv_buffer.getvalue())

        # Return HTTP response
        zipfile_buffer.seek(0)
        response = HttpResponse(zipfile_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=export.zip'
        return response

    def handle_anonymise(self, request, querysets):
        """
        Handle an anonymisation request
        """
        count = 0
        for model, queryset in querysets.items():
            queryset.anonymise()
            count += queryset.count()

        messages.success(
            request,
            "{} records anonymised".format(count),
        )
        return HttpResponseRedirect(
            reverse(
                'admin:{}_{}_changelist'.format(
                    self.model._meta.app_label,
                    self.model._meta.model_name,
                ),
            ),
        )


admin.site.register(PersonalData, PersonalDataAdmin)
