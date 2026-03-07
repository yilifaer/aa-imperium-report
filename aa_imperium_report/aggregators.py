"""
Data aggregation helpers — v0.2
字段名与数据库保持一致：
  igc_fleet_alliance_job, igc_esi_synced, igc_esi_failed
"""
import csv
import io
import logging
from datetime import date

from .models import (
    MonthlyReport, CorpMonthlyStats, MemberMonthlyStats,
    ImpAttendanceUpload, ImpEsiReport,
)

logger = logging.getLogger(__name__)

IGC_STR_KW = ["strategic (cta)", "strategic"]
IGC_PCT_KW = ["peacetime", "mining"]
IGC_JOB_KW = ["alliance job"]

IMP_STR_COLS = ["STRATEGIC", "SIG/SQUAD Strategic"]
IMP_PCT_COLS = ["PEACETIME", "SIG/SQUAD", "Beehive"]


def _igc_fleet_category(fleet_type: str) -> str:
    ft = (fleet_type or "").lower().strip()
    for kw in IGC_STR_KW:
        if kw in ft:
            return "str"
    for kw in IGC_PCT_KW:
        if kw in ft:
            return "pct"
    for kw in IGC_JOB_KW:
        if kw in ft:
            return "job"
    return "other"


def _get_corp_name_for_char(char_name: str):
    try:
        from allianceauth.eveonline.models import EveCharacter
        char = EveCharacter.objects.filter(character_name=char_name).first()
        if char and char.corporation_name:
            return char.corporation_name
    except Exception:
        pass
    return None


def get_or_create_corp_stat(report, corp_name):
    stat, _ = CorpMonthlyStats.objects.get_or_create(
        report=report, corp_name=corp_name, defaults={}
    )
    return stat


def aggregate_afat(report: MonthlyReport):
    try:
        from afat.models import Fat
        from allianceauth.eveonline.models import EveCorporationInfo

        month_start = date(report.year, report.month, 1)
        month_end   = date(report.year + 1, 1, 1) if report.month == 12 else date(report.year, report.month + 1, 1)

        fats = Fat.objects.filter(
            fatlink__created__gte=month_start,
            fatlink__created__lt=month_end,
        ).select_related("fatlink", "character")

        corp_c = {}
        mem_c  = {}

        for fat in fats:
            char_name = fat.character.character_name if fat.character else "Unknown"
            corp_name = "Unknown"
            try:
                co = EveCorporationInfo.objects.filter(corporation_id=fat.corporation_eve_id).first()
                if co:
                    corp_name = co.corporation_name
            except Exception:
                pass

            ft = fat.fatlink.fleet_type or (fat.fatlink.link_type.name if fat.fatlink.link_type else "")
            cat = _igc_fleet_category(ft)

            c = corp_c.setdefault(corp_name, {"str": 0, "pct": 0, "job": 0, "other": 0})
            c[cat] += 1
            m = mem_c.setdefault(char_name, {"corp": corp_name, "str": 0, "pct": 0, "job": 0, "other": 0})
            m[cat] += 1

        for corp_name, c in corp_c.items():
            stat = get_or_create_corp_stat(report, corp_name)
            stat.igc_fleet_str          = c["str"]
            stat.igc_fleet_pct          = c["pct"]
            stat.igc_fleet_alliance_job = c["job"]
            stat.igc_fleet_other        = c["other"]
            stat.save()

        for char_name, d in mem_c.items():
            MemberMonthlyStats.objects.update_or_create(
                report=report, character_name=char_name,
                defaults={
                    "corp_name":             d["corp"],
                    "igc_fleet_str":         d["str"],
                    "igc_fleet_pct":         d["pct"],
                    "igc_fleet_alliance_job":d["job"],
                    "igc_fleet_other":       d["other"],
                }
            )
        logger.info("AFAT: %d corps for %s", len(corp_c), report.label)
    except Exception as e:
        logger.warning("AFAT skipped: %s", e)


def aggregate_imp_attendance(report: MonthlyReport):
    try:
        upload = report.imp_attendance
    except ImpAttendanceUpload.DoesNotExist:
        return

    try:
        reader = csv.DictReader(io.StringIO(upload.raw_csv))
        rows   = list(reader)

        corp_str = {}
        corp_pct = {}

        for row in rows:
            char_name = row.get("Account", "").strip()
            if not char_name:
                continue

            imp_str = sum(int(row.get(col, 0) or 0) for col in IMP_STR_COLS)
            imp_pct = sum(int(row.get(col, 0) or 0) for col in IMP_PCT_COLS)

            if imp_str == 0 and imp_pct == 0:
                continue

            ms, _ = MemberMonthlyStats.objects.get_or_create(
                report=report, character_name=char_name,
                defaults={"corp_name": "Unknown"}
            )
            ms.imp_fleet_str = (ms.imp_fleet_str or 0) + imp_str
            ms.imp_fleet_pct = (ms.imp_fleet_pct or 0) + imp_pct

            corp_name = _get_corp_name_for_char(char_name) or ms.corp_name or "Unknown"
            ms.corp_name = corp_name
            ms.save()

            corp_str[corp_name] = corp_str.get(corp_name, 0) + imp_str
            corp_pct[corp_name] = corp_pct.get(corp_name, 0) + imp_pct

        for corp_name in set(list(corp_str) + list(corp_pct)):
            stat = get_or_create_corp_stat(report, corp_name)
            stat.imp_fleet_str = (stat.imp_fleet_str or 0) + corp_str.get(corp_name, 0)
            stat.imp_fleet_pct = (stat.imp_fleet_pct or 0) + corp_pct.get(corp_name, 0)
            stat.save()

        logger.info("IMP Attendance: %d rows for %s", len(rows), report.label)
    except Exception as e:
        logger.warning("IMP Attendance failed: %s", e)


def aggregate_imp_esi(report: MonthlyReport):
    try:
        esi_upload = report.imp_esi
    except ImpEsiReport.DoesNotExist:
        return

    try:
        for corp_data in esi_upload.parsed_json:
            corp_name = corp_data["corp"]
            stat = get_or_create_corp_stat(report, corp_name)
            stat.imp_esi_status       = corp_data["status"]
            stat.imp_esi_unregistered = len(corp_data.get("unregistered", []))
            stat.save()
        logger.info("IMP ESI: applied for %s", report.label)
    except Exception as e:
        logger.warning("IMP ESI failed: %s", e)


def aggregate_mining(report: MonthlyReport):
    try:
        from miningtaxes.models import Character as MtChar
        for char in MtChar.objects.all().select_related("eve_character"):
            try:
                monthly     = char.get_monthly_mining()
                monthly_tax = char.get_monthly_taxes()
                isk   = sum(v for k, v in monthly.items()     if k.year == report.year and k.month == report.month)
                taxes = sum(v for k, v in monthly_tax.items() if k.year == report.year and k.month == report.month)
                if isk == 0 and taxes == 0:
                    continue
                corp_name = char.eve_character.corporation_name
                char_name = char.eve_character.character_name
                stat = get_or_create_corp_stat(report, corp_name)
                stat.mining_isk     += int(isk)
                stat.mining_tax_isk += int(taxes)
                stat.save()
                ms, _ = MemberMonthlyStats.objects.get_or_create(
                    report=report, character_name=char_name, defaults={"corp_name": corp_name}
                )
                ms.mining_isk += int(isk)
                ms.save()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Mining skipped: %s", e)


def aggregate_pve(report: MonthlyReport):
    try:
        from corptools.models import CorporationWalletJournalEntry
        month_start = date(report.year, report.month, 1)
        month_end   = date(report.year + 1, 1, 1) if report.month == 12 else date(report.year, report.month + 1, 1)
        entries = CorporationWalletJournalEntry.objects.filter(
            ref_type="bounty_prizes", date__gte=month_start, date__lt=month_end,
        ).select_related("division__corporation__corporation")
        corp_totals = {}
        for entry in entries:
            try:
                corp_name = entry.division.corporation.corporation.corporation_name
            except Exception:
                corp_name = "Unknown"
            corp_totals[corp_name] = corp_totals.get(corp_name, 0) + float(entry.amount or 0)
        for corp_name, total in corp_totals.items():
            stat = get_or_create_corp_stat(report, corp_name)
            stat.pve_bounty_isk = int(total)
            stat.save()
    except Exception as e:
        logger.warning("PVE skipped: %s", e)


def aggregate_member_counts(report: MonthlyReport):
    try:
        from corpstats.models import CorpStat
        for cs in CorpStat.objects.all().select_related("corp"):
            try:
                corp_name = cs.corp.corporation_name
                total     = cs.members.count()
                try:
                    _, _, _, _, _, _, total_members, _, _, _, tracking, _ = cs.get_stats()
                    esi_ok = tracking.count() if tracking else 0
                except Exception:
                    total_members = total
                    esi_ok        = 0
                stat = get_or_create_corp_stat(report, corp_name)
                stat.member_total  = total_members
                stat.member_authed = total_members
                stat.igc_esi_synced = esi_ok
                stat.igc_esi_failed = max(0, total_members - esi_ok)
                stat.save()
            except Exception:
                pass
    except Exception as e:
        logger.warning("Member counts skipped: %s", e)


def build_report(report: MonthlyReport):
    report.corp_stats.all().delete()
    report.member_stats.all().delete()

    aggregate_afat(report)
    aggregate_mining(report)
    aggregate_pve(report)
    aggregate_member_counts(report)
    aggregate_imp_attendance(report)
    aggregate_imp_esi(report)

    from django.utils import timezone
    report.updated_at = timezone.now()
    report.save(update_fields=["updated_at"])
    logger.info("Report build complete: %s", report.label)
