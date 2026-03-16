from django.urls import path

from apps.telehealth.views import check_compliance, get_state_rule, list_state_rules

urlpatterns = [
    path("compliance/check/", check_compliance, name="telehealth-compliance-check"),
    path("states/", list_state_rules, name="telehealth-state-rules"),
    path("states/<str:state_code>/", get_state_rule, name="telehealth-state-rule"),
]
