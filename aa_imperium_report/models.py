from django.db import models
from allianceauth.eveonline.models import EveCorporationInfo


class General(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access",    "Can access IGC-CN Toolbox (member view)"),
            ("corp_access",     "Can view own corporation report"),
            ("alliance_access", "Can view all corporation reports"),
            ("upload_imp_data", "Can upload IMP attendance / ESI reports"),
        )


class MonthlyReport(models.Model):
    year  = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    imp_attendance_uploaded = models.BooleanField(default=False)
    imp_esi_uploaded        = models.BooleanField(default=False)
    is_final                = models.BooleanField(default=False)
    finalized_at            = models.DateTimeField(null=True, blank=True)
    fleet_json  = models.JSONField(default=dict)
    mining_json = models.JSONField(default=dict)
    pve_json    = models.JSONField(default=dict)
    pvp_json    = models.JSONField(default=dict)
    esi_json    = models.JSONField(default=dict)
    member_json = models.JSONField(default=dict)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("year", "month")
        ordering = ("-year", "-month")

    def __str__(self):
        return f"{self.year}-{self.month:02d} Report"

    @property
    def label(self):
        return f"{self.year}-{self.month:02d}"


class ImpAttendanceUpload(models.Model):
    report      = models.OneToOneField(MonthlyReport, on_delete=models.CASCADE, related_name="imp_attendance")
    raw_csv     = models.TextField()
    uploaded_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.CharField(max_length=255)


class ImpEsiReport(models.Model):
    report      = models.OneToOneField(MonthlyReport, on_delete=models.CASCADE, related_name="imp_esi")
    raw_text    = models.TextField()
    parsed_json = models.JSONField(default=list)
    uploaded_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.CharField(max_length=255)
    total_corps        = models.PositiveIntegerField(default=0)
    pass_count         = models.PositiveIntegerField(default=0)
    fail_count         = models.PositiveIntegerField(default=0)
    no_token_count     = models.PositiveIntegerField(default=0)
    unregistered_total = models.PositiveIntegerField(default=0)


class DailySnapshot(models.Model):
    date              = models.DateField(unique=True)
    fleet_count_str   = models.PositiveIntegerField(default=0)
    fleet_count_pct   = models.PositiveIntegerField(default=0)
    fleet_count_other = models.PositiveIntegerField(default=0)
    new_members       = models.JSONField(default=list)
    left_members      = models.JSONField(default=list)
    esi_sync_ok       = models.PositiveIntegerField(default=0)
    esi_sync_bad      = models.PositiveIntegerField(default=0)
    mining_isk        = models.BigIntegerField(default=0)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-date",)


class CorpMonthlyStats(models.Model):
    report      = models.ForeignKey(MonthlyReport, on_delete=models.CASCADE, related_name="corp_stats")
    corporation = models.ForeignKey(EveCorporationInfo, on_delete=models.SET_NULL, null=True, blank=True)
    corp_name   = models.CharField(max_length=255)

    # Members
    member_total  = models.PositiveIntegerField(default=0)   # 总角色数
    member_authed = models.PositiveIntegerField(default=0)   # 主角色/注册成员数

    # IGC Fleet (AFAT) — 字段名与0002 migration一致
    igc_fleet_str         = models.PositiveIntegerField(default=0)
    igc_fleet_pct         = models.PositiveIntegerField(default=0)
    igc_fleet_alliance_job= models.PositiveIntegerField(default=0)   # db列名 igc_fleet_alliance_job
    igc_fleet_other       = models.PositiveIntegerField(default=0)

    # IMP Fleet (CSV)
    imp_fleet_str = models.PositiveIntegerField(default=0)
    imp_fleet_pct = models.PositiveIntegerField(default=0)

    # IGC ESI — 字段名与0002 migration一致
    igc_esi_synced = models.PositiveIntegerField(default=0)   # ESI正常
    igc_esi_failed = models.PositiveIntegerField(default=0)   # ESI失败

    # IMP ESI
    imp_esi_status = models.CharField(
        max_length=16,
        choices=[("PASS","PASS"),("FAIL","FAIL"),("NO_TOKEN","NO_TOKEN"),("UNKNOWN","UNKNOWN")],
        default="UNKNOWN"
    )
    imp_esi_unregistered = models.PositiveIntegerField(default=0)

    # Economy
    mining_isk     = models.BigIntegerField(default=0)
    pve_bounty_isk = models.BigIntegerField(default=0)
    mining_tax_isk = models.BigIntegerField(default=0)

    # PVP
    kills    = models.PositiveIntegerField(default=0)
    kill_isk = models.BigIntegerField(default=0)
    losses   = models.PositiveIntegerField(default=0)
    loss_isk = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ("report", "corp_name")
        ordering = ("-imp_fleet_str",)

    def __str__(self):
        return f"{self.corp_name} @ {self.report.label}"

    @property
    def igc_fleet_total(self):
        return self.igc_fleet_str + self.igc_fleet_pct + self.igc_fleet_alliance_job + self.igc_fleet_other

    @property
    def imp_fleet_total(self):
        return self.imp_fleet_str + self.imp_fleet_pct

    @property
    def fleet_grand_total(self):
        return self.igc_fleet_total + self.imp_fleet_total

    @property
    def fleet_per_capita(self):
        if self.member_authed == 0:
            return 0
        return round(self.fleet_grand_total / self.member_authed, 2)

    @property
    def igc_esi_total(self):
        return self.igc_esi_synced + self.igc_esi_failed

    @property
    def igc_esi_pct(self):
        t = self.igc_esi_total
        if t == 0:
            return None
        return round(self.igc_esi_synced / t * 100, 1)

    @property
    def imp_esi_pct(self):
        """(total - unregistered) / total * 100，用军团总角色数"""
        if self.imp_esi_status == "UNKNOWN":
            return None
        if self.imp_esi_status == "NO_TOKEN":
            return 0.0
        if self.member_total > 0:
            registered = max(0, self.member_total - self.imp_esi_unregistered)
            return round(registered / self.member_total * 100, 1)
        if self.imp_esi_status == "PASS":
            return 100.0
        return None


class MemberMonthlyStats(models.Model):
    report         = models.ForeignKey(MonthlyReport, on_delete=models.CASCADE, related_name="member_stats")
    character_name = models.CharField(max_length=255)
    corp_name      = models.CharField(max_length=255)

    igc_fleet_str          = models.PositiveIntegerField(default=0)
    igc_fleet_pct          = models.PositiveIntegerField(default=0)
    igc_fleet_alliance_job = models.PositiveIntegerField(default=0)
    igc_fleet_other        = models.PositiveIntegerField(default=0)

    imp_fleet_str = models.PositiveIntegerField(default=0)
    imp_fleet_pct = models.PositiveIntegerField(default=0)

    mining_isk = models.BigIntegerField(default=0)
    kills      = models.PositiveIntegerField(default=0)
    esi_ok     = models.BooleanField(default=False)

    class Meta:
        unique_together = ("report", "character_name")
        ordering = ("-igc_fleet_str",)

    @property
    def igc_fleet_total(self):
        return self.igc_fleet_str + self.igc_fleet_pct + self.igc_fleet_alliance_job + self.igc_fleet_other

    @property
    def imp_fleet_total(self):
        return self.imp_fleet_str + self.imp_fleet_pct

    @property
    def fleet_total(self):
        return self.igc_fleet_total + self.imp_fleet_total
