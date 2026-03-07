"""
tasks.py — Celery periodic tasks for aa-imperium-report.

Register in your celerybeat schedule (local.py / settings):

  CELERYBEAT_SCHEDULE["aa_imperium_report.daily_snapshot"] = {
      "task":     "aa_imperium_report.tasks.daily_snapshot",
      "schedule": crontab(hour=11, minute=5),   # ~10 min after DT
  }
"""
import logging
from datetime import date

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def daily_snapshot():
    """
    Capture a lightweight daily snapshot:
    - Fleet counts from AFAT (today's fats)
    - ESI sync status from corpstats
    - Member join/leave delta (not yet implemented — placeholder)
    """
    from .models import DailySnapshot

    today = date.today()
    snap, created = DailySnapshot.objects.get_or_create(date=today)

    # ── Fleet counts (AFAT) ─────────────────────────────────────────────
    try:
        from afat.models import Fat
        from .aggregators import _igc_fleet_category

        fats_today = Fat.objects.filter(fatlink__created__date=today)
        str_count   = sum(1 for f in fats_today if _igc_fleet_category(
            f.fatlink.fleet_type or "") == "str")
        pct_count   = sum(1 for f in fats_today if _igc_fleet_category(
            f.fatlink.fleet_type or "") == "pct")
        other_count = fats_today.count() - str_count - pct_count

        snap.fleet_count_str   = str_count
        snap.fleet_count_pct   = pct_count
        snap.fleet_count_other = other_count
    except Exception as e:
        logger.warning("Snapshot: AFAT skipped — %s", e)

    # ── ESI sync status (corpstats) ─────────────────────────────────────
    try:
        from corpstats.models import CorpStat
        ok = bad = 0
        for cs in CorpStat.objects.all():
            try:
                _, _, _, _, _, _, total, _, _, _, tracking, _ = cs.get_stats()
                ok  += tracking.count() if tracking else 0
                bad += max(0, (total or 0) - (tracking.count() if tracking else 0))
            except Exception:
                pass
        snap.esi_sync_ok  = ok
        snap.esi_sync_bad = bad
    except Exception as e:
        logger.warning("Snapshot: corpstats skipped — %s", e)

    snap.save()
    logger.info("Daily snapshot saved for %s (new=%s)", today, created)
    return f"Snapshot {today} saved"
