"""
Views for IGC-CN Toolbox — Monthly Reports.
v0.2: Added manual snapshot trigger for testing.

Permission tiers:
  alliance_access  → see all corps (Alliance Leader / Co-Leader)
  corp_access      → see own corp  (CEO / Co-CEO)
  basic_access     → see own data  (IGC member)
"""
import logging
from datetime import date

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import MonthlyReport, CorpMonthlyStats, MemberMonthlyStats, ImpAttendanceUpload, ImpEsiReport
from .parsers import parse_imp_esi_report, summarize_results
from .aggregators import build_report

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────
def _has_alliance_access(user):
    return user.has_perm("aa_imperium_report.alliance_access")

def _has_corp_access(user):
    return user.has_perm("aa_imperium_report.corp_access") or _has_alliance_access(user)

def _has_basic_access(user):
    return user.has_perm("aa_imperium_report.basic_access") or _has_corp_access(user)

def _get_user_corp_name(user):
    try:
        return user.profile.main_character.corporation_name
    except Exception:
        return None


# ── Dashboard / report list ────────────────────────────────────────────────
@login_required
def index(request):
    if not _has_basic_access(request.user):
        return HttpResponseForbidden("You need the IGC member role to access this tool.")

    reports = MonthlyReport.objects.all().order_by("-year", "-month")
    context = {
        "reports":      reports,
        "can_upload":   request.user.has_perm("aa_imperium_report.upload_imp_data"),
        "has_alliance": _has_alliance_access(request.user),
        "has_corp":     _has_corp_access(request.user),
    }
    return render(request, "aa_imperium_report/index.html", context)


# ── Report detail ──────────────────────────────────────────────────────────
@login_required
def report_detail(request, year, month):
    if not _has_basic_access(request.user):
        return HttpResponseForbidden()

    report = get_object_or_404(MonthlyReport, year=year, month=month)

    user_corp   = _get_user_corp_name(request.user)
    is_alliance = _has_alliance_access(request.user)
    is_corp_mgr = _has_corp_access(request.user)

    if is_alliance:
        corp_stats = report.corp_stats.all().order_by("-imp_fleet_str")
    elif is_corp_mgr:
        corp_stats = report.corp_stats.filter(corp_name=user_corp)
    else:
        corp_stats = CorpMonthlyStats.objects.none()

    if is_alliance:
        member_stats = report.member_stats.all()
    elif is_corp_mgr:
        member_stats = report.member_stats.filter(corp_name=user_corp)
    else:
        char_name = None
        try:
            char_name = request.user.profile.main_character.character_name
        except Exception:
            pass
        member_stats = report.member_stats.filter(
            character_name=char_name
        ) if char_name else MemberMonthlyStats.objects.none()

    # IMP ESI summary: alliance sees all, corp_mgr sees own corp only
    imp_esi = None
    imp_esi_own_corp = None   # corp CEO: own corp ESI stat row
    try:
        imp_esi_obj = report.imp_esi
        if is_alliance:
            imp_esi = imp_esi_obj
        elif is_corp_mgr and user_corp:
            # Find own corp in parsed ESI data
            for entry in imp_esi_obj.parsed_json:
                if entry.get("corp") == user_corp:
                    imp_esi_own_corp = entry
                    break
    except ImpEsiReport.DoesNotExist:
        pass

    # Corp ESI stat for corp_mgr
    own_corp_stat = None
    if is_corp_mgr and not is_alliance and user_corp:
        own_corp_stat = corp_stats.first()

    context = {
        "report":          report,
        "corp_stats":      corp_stats,
        "member_stats":    member_stats,
        "imp_esi":         imp_esi,           # alliance only: full summary
        "imp_esi_own_corp":imp_esi_own_corp,  # corp_mgr only: own corp ESI entry
        "own_corp_stat":   own_corp_stat,
        "is_alliance":     is_alliance,
        "is_corp_mgr":     is_corp_mgr,
        "can_upload":      request.user.has_perm("aa_imperium_report.upload_imp_data"),
        "can_finalize":    is_alliance,
        "user_corp":       user_corp,
    }
    return render(request, "aa_imperium_report/report_detail.html", context)


# ── Upload IMP Attendance CSV ──────────────────────────────────────────────
@login_required
@permission_required("aa_imperium_report.upload_imp_data", raise_exception=True)
def upload_imp_attendance(request):
    if request.method == "POST":
        year     = int(request.POST.get("year",  date.today().year))
        month    = int(request.POST.get("month", date.today().month))
        csv_file = request.FILES.get("csv_file")

        if not csv_file:
            messages.error(request, "No file selected.")
            return redirect("aa_imperium_report:index")

        raw_csv = csv_file.read().decode("utf-8-sig")
        report, _ = MonthlyReport.objects.get_or_create(year=year, month=month)

        ImpAttendanceUpload.objects.update_or_create(
            report=report,
            defaults={"raw_csv": raw_csv, "uploaded_by": str(request.user)}
        )
        report.imp_attendance_uploaded = True
        report.save(update_fields=["imp_attendance_uploaded"])
        build_report(report)
        messages.success(request, f"IMP Attendance for {report.label} uploaded and report rebuilt.")
        return redirect("aa_imperium_report:report_detail", year=year, month=month)

    return render(request, "aa_imperium_report/upload_imp_attendance.html", {"today": date.today()})


# ── Upload IMP ESI Report ──────────────────────────────────────────────────
@login_required
@permission_required("aa_imperium_report.upload_imp_data", raise_exception=True)
def upload_imp_esi(request):
    if request.method == "POST":
        year     = int(request.POST.get("year",  date.today().year))
        month    = int(request.POST.get("month", date.today().month))
        raw_text = request.POST.get("raw_text", "").strip()

        if not raw_text:
            messages.error(request, "Report text is empty.")
            return redirect("aa_imperium_report:index")

        parsed  = parse_imp_esi_report(raw_text)
        summary = summarize_results(parsed)
        report, _ = MonthlyReport.objects.get_or_create(year=year, month=month)

        ImpEsiReport.objects.update_or_create(
            report=report,
            defaults={
                "raw_text":           raw_text,
                "parsed_json":        parsed,
                "uploaded_by":        str(request.user),
                "total_corps":        summary["total"],
                "pass_count":         summary["pass"],
                "fail_count":         summary["fail"],
                "no_token_count":     summary["no_token"],
                "unregistered_total": summary["unregistered"],
            }
        )
        report.imp_esi_uploaded = True
        report.save(update_fields=["imp_esi_uploaded"])
        build_report(report)
        messages.success(
            request,
            f"IMP ESI Report for {report.label} parsed: "
            f"{summary['pass']} PASS / {summary['fail']} FAIL / "
            f"{summary['no_token']} NO TOKEN — {summary['unregistered']} unregistered pilots."
        )
        return redirect("aa_imperium_report:report_detail", year=year, month=month)

    return render(request, "aa_imperium_report/upload_imp_esi.html", {"today": date.today()})


# ── Finalize report ────────────────────────────────────────────────────────
@login_required
@permission_required("aa_imperium_report.alliance_access", raise_exception=True)
@require_POST
def finalize_report(request, year, month):
    report  = get_object_or_404(MonthlyReport, year=year, month=month)
    missing = []
    if not report.imp_attendance_uploaded:
        missing.append("IMP Attendance CSV")
    if not report.imp_esi_uploaded:
        missing.append("IMP ESI Report")

    if missing and not request.POST.get("force"):
        return JsonResponse({
            "ok": False, "missing": missing,
            "message": f"Missing: {', '.join(missing)}. POST force=1 to override.",
        })

    build_report(report)
    report.is_final     = True
    report.finalized_at = timezone.now()
    report.save(update_fields=["is_final", "finalized_at"])
    messages.success(request, f"Report {report.label} finalized.")
    return redirect("aa_imperium_report:report_detail", year=year, month=month)


# ── Rebuild report (alliance only) ────────────────────────────────────────
@login_required
@permission_required("aa_imperium_report.alliance_access", raise_exception=True)
@require_POST
def rebuild_report(request, year, month):
    report = get_object_or_404(MonthlyReport, year=year, month=month)
    if report.is_final:
        messages.warning(request, "Report is already finalized. Unfinalize first.")
        return redirect("aa_imperium_report:report_detail", year=year, month=month)
    build_report(report)
    messages.success(request, f"Report {report.label} rebuilt.")
    return redirect("aa_imperium_report:report_detail", year=year, month=month)


# ── v0.2: Manual snapshot trigger (alliance only, for testing) ────────────
@login_required
@permission_required("aa_imperium_report.alliance_access", raise_exception=True)
@require_POST
def trigger_snapshot(request):
    """
    Manually trigger a daily snapshot without waiting for DT.
    Deletes today's existing snapshot first so it can always re-run.
    """
    from .tasks import daily_snapshot
    from .models import DailySnapshot

    today = date.today()
    deleted, _ = DailySnapshot.objects.filter(date=today).delete()
    if deleted:
        logger.info("Deleted existing snapshot for %s to allow re-run", today)

    try:
        daily_snapshot()
        messages.success(request, f"✅ 快照触发成功 / Snapshot triggered for {today}.")
    except Exception as e:
        logger.exception("Manual snapshot failed")
        messages.error(request, f"❌ 快照失败 / Snapshot failed: {e}")

    return redirect("aa_imperium_report:index")


# ── API: Corp stats JSON ───────────────────────────────────────────────────
@login_required
def api_report_json(request, year, month):
    if not _has_alliance_access(request.user):
        return HttpResponseForbidden()
    report = get_object_or_404(MonthlyReport, year=year, month=month)
    data   = list(report.corp_stats.values())
    return JsonResponse({"report": report.label, "corps": data})
