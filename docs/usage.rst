=====
Usage
=====

Configure your models
=====================

Define privacy settings in a ``PrivacyMeta`` class on your model::

    class MyModel(models.Model):
        user = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            blank=True,
            null=True,
            on_delete=gdpr_assist.ANONYMISE(models.SET_NULL),
        )
        display_name = models.CharField(max_length=255)
        private_data = models.IntegerField()
        public_data = models.TextField()

        class PrivacyMeta:
            fields = ['display_name', 'private_data']

            def anonymise_private_data(self, instance):
                return 0

            def search(self, value):
                return self.model.objects.filter(display_name__icontains=value)


Next:

* See :doc:`Privacy Meta <privacy_meta>` for the full set of ``PrivacyMeta``
  options, and for how to register a third-party model.
* See :doc:`Anonymising <anonymising>` for how anonymisation works.
* See :doc:`Admin <admin>` to register your model in the admin site, and how
  to use the admin personal data tool to search and export data.




