from django.apps import AppConfig


class AaImperiumReportConfig(AppConfig):
    name = "aa_imperium_report"
    label = "aa_imperium_report"
    verbose_name = "Imperium Report"

    def ready(self):
        pass
