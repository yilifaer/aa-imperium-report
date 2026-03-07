from django.urls import path
from . import views

app_name = "aa_imperium_report"

urlpatterns = [
    path("",                                        views.index,                name="index"),
    path("report/<int:year>/<int:month>/",          views.report_detail,        name="report_detail"),
    path("upload/imp-attendance/",                  views.upload_imp_attendance, name="upload_imp_attendance"),
    path("upload/imp-esi/",                         views.upload_imp_esi,       name="upload_imp_esi"),
    path("report/<int:year>/<int:month>/finalize/", views.finalize_report,      name="finalize_report"),
    path("report/<int:year>/<int:month>/rebuild/",  views.rebuild_report,       name="rebuild_report"),
    path("snapshot/trigger/",                       views.trigger_snapshot,     name="trigger_snapshot"),  # v0.2
    path("api/report/<int:year>/<int:month>.json",  views.api_report_json,      name="api_report_json"),
]
