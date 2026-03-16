from django.urls import path
from apps.widget.views import widget_config, widget_summary, widget_summary_read

urlpatterns = [
    path("config/<str:widget_key>/", widget_config, name="widget-config"),
    path("summary/<str:token>/", widget_summary, name="widget-summary"),
    path("summary/<str:token>/read/", widget_summary_read, name="widget-summary-read"),
]
