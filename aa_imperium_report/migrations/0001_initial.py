from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("eveonline", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="General",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
            ],
            options={
                "managed": False,
                "default_permissions": (),
                "permissions": [
                    ("basic_access",    "Can access Imperium Report (member view)"),
                    ("corp_access",     "Can view own corporation report"),
                    ("alliance_access", "Can view all corporation reports"),
                    ("upload_imp_data", "Can upload IMP attendance / ESI reports"),
                ],
            },
        ),
        migrations.CreateModel(
            name="MonthlyReport",
            fields=[
                ("id",                      models.AutoField(primary_key=True, serialize=False)),
                ("year",                    models.PositiveSmallIntegerField()),
                ("month",                   models.PositiveSmallIntegerField()),
                ("imp_attendance_uploaded", models.BooleanField(default=False)),
                ("imp_esi_uploaded",        models.BooleanField(default=False)),
                ("is_final",                models.BooleanField(default=False)),
                ("finalized_at",            models.DateTimeField(blank=True, null=True)),
                ("fleet_json",              models.JSONField(default=dict)),
                ("mining_json",             models.JSONField(default=dict)),
                ("pve_json",                models.JSONField(default=dict)),
                ("pvp_json",                models.JSONField(default=dict)),
                ("esi_json",                models.JSONField(default=dict)),
                ("member_json",             models.JSONField(default=dict)),
                ("created_at",              models.DateTimeField(auto_now_add=True)),
                ("updated_at",              models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("-year", "-month"),
            },
        ),
        migrations.AlterUniqueTogether(
            name="monthlyreport",
            unique_together={("year", "month")},
        ),
        migrations.CreateModel(
            name="ImpAttendanceUpload",
            fields=[
                ("id",          models.AutoField(primary_key=True, serialize=False)),
                ("raw_csv",     models.TextField()),
                ("uploaded_at", models.DateTimeField(auto_now=True)),
                ("uploaded_by", models.CharField(max_length=255)),
                ("report",      models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="imp_attendance",
                    to="aa_imperium_report.monthlyreport",
                )),
            ],
        ),
        migrations.CreateModel(
            name="ImpEsiReport",
            fields=[
                ("id",                 models.AutoField(primary_key=True, serialize=False)),
                ("raw_text",           models.TextField()),
                ("parsed_json",        models.JSONField(default=list)),
                ("uploaded_at",        models.DateTimeField(auto_now=True)),
                ("uploaded_by",        models.CharField(max_length=255)),
                ("total_corps",        models.PositiveIntegerField(default=0)),
                ("pass_count",         models.PositiveIntegerField(default=0)),
                ("fail_count",         models.PositiveIntegerField(default=0)),
                ("no_token_count",     models.PositiveIntegerField(default=0)),
                ("unregistered_total", models.PositiveIntegerField(default=0)),
                ("report",             models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="imp_esi",
                    to="aa_imperium_report.monthlyreport",
                )),
            ],
        ),
        migrations.CreateModel(
            name="DailySnapshot",
            fields=[
                ("id",                models.AutoField(primary_key=True, serialize=False)),
                ("date",              models.DateField(unique=True)),
                ("fleet_count_str",   models.PositiveIntegerField(default=0)),
                ("fleet_count_pct",   models.PositiveIntegerField(default=0)),
                ("fleet_count_other", models.PositiveIntegerField(default=0)),
                ("new_members",       models.JSONField(default=list)),
                ("left_members",      models.JSONField(default=list)),
                ("esi_sync_ok",       models.PositiveIntegerField(default=0)),
                ("esi_sync_bad",      models.PositiveIntegerField(default=0)),
                ("mining_isk",        models.BigIntegerField(default=0)),
                ("created_at",        models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("-date",),
            },
        ),
        migrations.CreateModel(
            name="CorpMonthlyStats",
            fields=[
                ("id",                     models.AutoField(primary_key=True, serialize=False)),
                ("corp_name",              models.CharField(max_length=255)),
                ("member_total",           models.PositiveIntegerField(default=0)),
                ("member_authed",          models.PositiveIntegerField(default=0)),
                ("igc_fleet_str",          models.PositiveIntegerField(default=0)),
                ("igc_fleet_pct",          models.PositiveIntegerField(default=0)),
                ("igc_fleet_alliance_job", models.PositiveIntegerField(default=0)),
                ("igc_fleet_other",        models.PositiveIntegerField(default=0)),
                ("imp_fleet_str",          models.PositiveIntegerField(default=0)),
                ("imp_fleet_pct",          models.PositiveIntegerField(default=0)),
                ("igc_esi_synced",         models.PositiveIntegerField(default=0)),
                ("igc_esi_failed",         models.PositiveIntegerField(default=0)),
                ("imp_esi_status",         models.CharField(
                    choices=[("PASS","PASS"),("FAIL","FAIL"),("NO_TOKEN","NO_TOKEN"),("UNKNOWN","UNKNOWN")],
                    default="UNKNOWN",
                    max_length=16,
                )),
                ("imp_esi_unregistered",   models.PositiveIntegerField(default=0)),
                ("mining_isk",             models.BigIntegerField(default=0)),
                ("pve_bounty_isk",         models.BigIntegerField(default=0)),
                ("mining_tax_isk",         models.BigIntegerField(default=0)),
                ("kills",                  models.PositiveIntegerField(default=0)),
                ("kill_isk",               models.BigIntegerField(default=0)),
                ("losses",                 models.PositiveIntegerField(default=0)),
                ("loss_isk",               models.BigIntegerField(default=0)),
                ("report",      models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="corp_stats",
                    to="aa_imperium_report.monthlyreport",
                )),
                ("corporation", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to="eveonline.evecorporationinfo",
                )),
            ],
            options={
                "ordering": ("-imp_fleet_str",),
            },
        ),
        migrations.AlterUniqueTogether(
            name="corpmonthlystat",
            unique_together={("report", "corp_name")},
        ),
        migrations.CreateModel(
            name="MemberMonthlyStats",
            fields=[
                ("id",                     models.AutoField(primary_key=True, serialize=False)),
                ("character_name",         models.CharField(max_length=255)),
                ("corp_name",              models.CharField(max_length=255)),
                ("igc_fleet_str",          models.PositiveIntegerField(default=0)),
                ("igc_fleet_pct",          models.PositiveIntegerField(default=0)),
                ("igc_fleet_alliance_job", models.PositiveIntegerField(default=0)),
                ("igc_fleet_other",        models.PositiveIntegerField(default=0)),
                ("imp_fleet_str",          models.PositiveIntegerField(default=0)),
                ("imp_fleet_pct",          models.PositiveIntegerField(default=0)),
                ("mining_isk",             models.BigIntegerField(default=0)),
                ("kills",                  models.PositiveIntegerField(default=0)),
                ("esi_ok",                 models.BooleanField(default=False)),
                ("report",      models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="member_stats",
                    to="aa_imperium_report.monthlyreport",
                )),
            ],
            options={
                "ordering": ("-igc_fleet_str",),
            },
        ),
        migrations.AlterUniqueTogether(
            name="membermonthlystat",
            unique_together={("report", "character_name")},
        ),
    ]
