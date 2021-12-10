from django.urls import re_path
from django.contrib import admin

from .views import IndexView


urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"", IndexView.as_view(), name="index"),
]
