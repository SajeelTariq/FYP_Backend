"""
Email alert service for TrackRival.
Called at the end of daily monitoring and LinkedIn monitoring Celery tasks.
Each function is independent — queries AlertPreference records and sends
per-user emails scoped to their own competitors only.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry points — called from Celery tasks
# ---------------------------------------------------------------------------

def send_website_change_alerts():
    """
    Send significant website change emails after run_daily_monitoring.
    One email per user who has notify_website_changes=True and an email set.
    """
    from .models import AlertPreference
    from apps.monitoring.models import HTMLDifference

    since = timezone.now() - timedelta(hours=25)

    for pref in AlertPreference.objects.filter(notify_website_changes=True).select_related('user'):
        email = pref.get_alert_email()
        if not email:
            continue

        changes = (
            HTMLDifference.objects
            .filter(
                competitor__user=pref.user,
                change_category='critical',
                detected_at__gte=since,
                is_onboarding_snapshot=False,
            )
            .select_related('competitor')
            .order_by('competitor__name')
        )

        if not changes.exists():
            continue

        subject = f"[TrackRival] Website Changes Detected — {_today_str()}"
        _dispatch(subject, _website_text(pref.user, changes), _website_html(pref.user, changes), email)
        logger.info(f"[EmailAlert] website_changes → {email} ({changes.count()} changes)")


def send_new_pages_alerts():
    """
    Send new-page-discovered emails after run_daily_monitoring.
    Triggered when entirely new URLs are added to a competitor's site.
    """
    from .models import AlertPreference
    from apps.monitoring.models import HTMLDifference

    since = timezone.now() - timedelta(hours=25)

    for pref in AlertPreference.objects.filter(notify_new_pages=True).select_related('user'):
        email = pref.get_alert_email()
        if not email:
            continue

        new_pages = (
            HTMLDifference.objects
            .filter(
                competitor__user=pref.user,
                change_type='added',
                detected_at__gte=since,
                is_onboarding_snapshot=False,
            )
            .exclude(diff_summary__has_key='note')
            .select_related('competitor')
            .order_by('competitor__name')
        )

        if not new_pages.exists():
            continue

        subject = f"[TrackRival] New Pages Discovered — {_today_str()}"
        _dispatch(subject, _new_pages_text(pref.user, new_pages), _new_pages_html(pref.user, new_pages), email)
        logger.info(f"[EmailAlert] new_pages → {email} ({new_pages.count()} pages)")


def send_job_alerts():
    """
    Send new-job-posting emails after run_linkedin_monitoring.
    Uses JobPosting.is_new=True records created in the last 25 hours.
    """
    from .models import AlertPreference
    from apps.social_media.models import JobPosting

    since = timezone.now() - timedelta(hours=25)

    for pref in AlertPreference.objects.filter(notify_new_jobs=True).select_related('user'):
        email = pref.get_alert_email()
        if not email:
            continue

        jobs = (
            JobPosting.objects
            .filter(
                competitor__user=pref.user,
                is_new=True,
                first_seen_at__gte=since,
            )
            .select_related('competitor')
            .order_by('competitor__name', 'title')
        )

        if not jobs.exists():
            continue

        subject = f"[TrackRival] New Job Postings Detected — {_today_str()}"
        _dispatch(subject, _jobs_text(pref.user, jobs), _jobs_html(pref.user, jobs), email)
        logger.info(f"[EmailAlert] new_jobs → {email} ({jobs.count()} jobs)")


def send_follower_change_alerts():
    """
    Send LinkedIn follower/employee spike emails after run_linkedin_monitoring.
    Fires when today's snapshot differs >= 5% from yesterday's.
    """
    from .models import AlertPreference
    from apps.social_media.models import SocialMediaSnapshot

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    for pref in AlertPreference.objects.filter(notify_follower_change=True).select_related('user'):
        email = pref.get_alert_email()
        if not email:
            continue

        spikes = []
        for comp in pref.user.competitors.filter(is_deleted=False, linkedin_url__isnull=False):
            today_snap = (
                SocialMediaSnapshot.objects
                .filter(competitor=comp, recorded_at__date=today)
                .order_by('-recorded_at').first()
            )
            yesterday_snap = (
                SocialMediaSnapshot.objects
                .filter(competitor=comp, recorded_at__date=yesterday)
                .order_by('-recorded_at').first()
            )

            if not today_snap or not yesterday_snap:
                continue

            f_pct = _pct(yesterday_snap.follower_count, today_snap.follower_count)
            e_pct = _pct(yesterday_snap.employee_count, today_snap.employee_count)

            if abs(f_pct) >= 5 or abs(e_pct) >= 5:
                spikes.append({
                    'competitor': comp,
                    'yesterday': yesterday_snap,
                    'today': today_snap,
                    'follower_pct': f_pct,
                    'employee_pct': e_pct,
                })

        if not spikes:
            continue

        subject = f"[TrackRival] LinkedIn Activity Spike Detected — {_today_str()}"
        _dispatch(subject, _follower_text(pref.user, spikes), _follower_html(pref.user, spikes), email)
        logger.info(f"[EmailAlert] follower_change → {email} ({len(spikes)} competitors)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_str():
    return timezone.now().strftime('%b %d, %Y')


def _pct(old, new):
    if old is None or new is None or old == 0:
        return 0.0
    return round(((new - old) / old) * 100, 1)


def _group_by_competitor(queryset):
    grouped = {}
    for obj in queryset:
        grouped.setdefault(obj.competitor.name, []).append(obj)
    return grouped


def _dispatch(subject, text_body, html_body, recipient_email):
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.error(f"[EmailAlert] Failed to send '{subject}' to {recipient_email}: {exc}")


# ---------------------------------------------------------------------------
# Plain-text builders
# ---------------------------------------------------------------------------

def _website_text(user, changes):
    name = user.get_full_name() or user.username
    lines = [f"Hello {name},\n", "Significant website changes were detected:\n"]
    for comp_name, diffs in _group_by_competitor(changes).items():
        lines.append(f"\n[{comp_name}]")
        for d in diffs:
            added = d.diff_summary.get('added_lines', 0)
            removed = d.diff_summary.get('removed_lines', 0)
            lines.append(f"  Page : {d.url}")
            lines.append(f"  Type : {d.change_type} (+{added} / -{removed} lines)")
            lines.append(f"  What : {d.llm_summary}\n")
    lines.append("— TrackRival")
    return '\n'.join(lines)


def _new_pages_text(user, new_pages):
    name = user.get_full_name() or user.username
    lines = [f"Hello {name},\n", "New pages were discovered on competitor websites:\n"]
    for comp_name, pages in _group_by_competitor(new_pages).items():
        lines.append(f"\n[{comp_name}]")
        for p in pages:
            lines.append(f"  {p.url}")
    lines.append("\n— TrackRival")
    return '\n'.join(lines)


def _jobs_text(user, jobs):
    name = user.get_full_name() or user.username
    lines = [f"Hello {name},\n", "New job postings were detected:\n"]
    for comp_name, job_list in _group_by_competitor(jobs).items():
        lines.append(f"\n[{comp_name}] — {len(job_list)} new job(s)")
        for j in job_list:
            lines.append(f"  {j.title} | {j.location} | {j.seniority_level}")
            if j.job_url:
                lines.append(f"  {j.job_url}")
    lines.append("\n— TrackRival")
    return '\n'.join(lines)


def _follower_text(user, spikes):
    name = user.get_full_name() or user.username
    lines = [f"Hello {name},\n", "Significant LinkedIn activity was detected (>=5% change):\n"]
    for s in spikes:
        comp = s['competitor']
        lines.append(f"\n[{comp.name}]")
        lines.append(f"  Followers : {s['yesterday'].follower_count:,} → {s['today'].follower_count:,}  ({s['follower_pct']:+}%)")
        lines.append(f"  Employees : {s['yesterday'].employee_count:,} → {s['today'].employee_count:,}  ({s['employee_pct']:+}%)")
    lines.append("\n— TrackRival")
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def _website_html(user, changes):
    name = user.get_full_name() or user.username
    rows = ''
    for comp_name, diffs in _group_by_competitor(changes).items():
        rows += f'<h3 style="color:#c0392b;margin:16px 0 6px;">{comp_name}</h3>'
        for d in diffs:
            added = d.diff_summary.get('added_lines', 0)
            removed = d.diff_summary.get('removed_lines', 0)
            rows += f'''
            <div style="background:#fafafa;border-left:4px solid #c0392b;padding:12px 14px;margin:6px 0;border-radius:4px;">
                <p style="margin:0 0 4px;font-size:12px;color:#888;word-break:break-all;">{d.url}</p>
                <p style="margin:0 0 6px;font-size:13px;">
                    <strong>Change:</strong> {d.change_type.title()}
                    <span style="color:#666;"> (+{added} / -{removed} lines)</span>
                </p>
                <p style="margin:0;font-size:13px;color:#333;">{d.llm_summary}</p>
            </div>'''
    return _wrap_html(name, 'Website Changes Detected', rows)


def _new_pages_html(user, new_pages):
    name = user.get_full_name() or user.username
    rows = ''
    for comp_name, pages in _group_by_competitor(new_pages).items():
        rows += f'<h3 style="color:#c0392b;margin:16px 0 6px;">{comp_name}</h3>'
        for p in pages:
            rows += f'''
            <div style="background:#fafafa;border-left:4px solid #27ae60;padding:10px 14px;margin:6px 0;border-radius:4px;">
                <p style="margin:0;font-size:13px;">
                    New page: <a href="{p.url}" style="color:#c0392b;word-break:break-all;">{p.url}</a>
                </p>
            </div>'''
    return _wrap_html(name, 'New Pages Discovered', rows)


def _jobs_html(user, jobs):
    name = user.get_full_name() or user.username
    rows = ''
    for comp_name, job_list in _group_by_competitor(jobs).items():
        rows += f'<h3 style="color:#c0392b;margin:16px 0 6px;">{comp_name} — {len(job_list)} new job(s)</h3>'
        for j in job_list:
            view_link = f'<a href="{j.job_url}" style="color:#c0392b;font-size:12px;">View →</a>' if j.job_url else ''
            rows += f'''
            <div style="background:#fafafa;border-left:4px solid #3498db;padding:10px 14px;margin:6px 0;border-radius:4px;">
                <p style="margin:0 0 3px;font-weight:bold;font-size:13px;">{j.title} {view_link}</p>
                <p style="margin:0;font-size:12px;color:#666;">
                    {j.location or "—"} &nbsp;·&nbsp; {j.seniority_level or "—"} &nbsp;·&nbsp; {j.employment_type or "—"}
                </p>
            </div>'''
    return _wrap_html(name, 'New Job Postings Detected', rows)


def _follower_html(user, spikes):
    name = user.get_full_name() or user.username
    rows = ''
    for s in spikes:
        comp = s['competitor']
        f_pct = s['follower_pct']
        e_pct = s['employee_pct']

        def _badge(pct):
            color = '#27ae60' if pct >= 0 else '#e74c3c'
            arrow = '↑' if pct >= 0 else '↓'
            return f'<span style="color:{color};font-weight:bold;">{arrow} {abs(pct)}%</span>'

        rows += f'''
        <div style="background:#fafafa;border-left:4px solid #9b59b6;padding:12px 14px;margin:8px 0;border-radius:4px;">
            <h3 style="margin:0 0 8px;color:#c0392b;">{comp.name}</h3>
            <p style="margin:0 0 4px;font-size:13px;">
                Followers: <strong>{s["yesterday"].follower_count:,}</strong> → <strong>{s["today"].follower_count:,}</strong>
                &nbsp; {_badge(f_pct)}
            </p>
            <p style="margin:0;font-size:13px;">
                Employees: <strong>{s["yesterday"].employee_count:,}</strong> → <strong>{s["today"].employee_count:,}</strong>
                &nbsp; {_badge(e_pct)}
            </p>
        </div>'''
    return _wrap_html(name, 'LinkedIn Activity Spike Detected', rows)


def _wrap_html(user_name, title, content):
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:30px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
  <tr>
    <td style="background:#c0392b;padding:20px 24px;">
      <h1 style="margin:0;color:#fff;font-size:20px;letter-spacing:0.5px;">TrackRival</h1>
      <p style="margin:4px 0 0;color:rgba(255,255,255,0.75);font-size:12px;">AI-Powered Competitive Intelligence</p>
    </td>
  </tr>
  <tr>
    <td style="padding:24px;">
      <p style="margin:0 0 4px;">Hello <strong>{user_name}</strong>,</p>
      <h2 style="color:#c0392b;margin:12px 0 16px;font-size:18px;">{title}</h2>
      {content}
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0 16px;">
      <p style="font-size:11px;color:#aaa;margin:0;">
        You received this because you enabled email alerts in TrackRival.<br>
        Visit the <strong>Alerts</strong> page to manage your preferences.
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""
