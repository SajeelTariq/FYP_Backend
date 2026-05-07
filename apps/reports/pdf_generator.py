"""
PDF generator for competitor intelligence reports using ReportLab.
"""
from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── Colour palette ──────────────────────────────────────────────────────────
PRIMARY   = colors.HexColor('#1a237e')   # dark navy
ACCENT    = colors.HexColor('#1565c0')   # blue
LIGHT_BG  = colors.HexColor('#e8eaf6')   # light lavender
BORDER    = colors.HexColor('#c5cae9')
TEXT_DARK = colors.HexColor('#212121')
TEXT_MID  = colors.HexColor('#424242')
TEXT_LIGHT= colors.HexColor('#757575')
WHITE     = colors.white


def _styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('title', fontName='Helvetica-Bold',
                                fontSize=22, textColor=WHITE,
                                leading=28, alignment=TA_CENTER),
        'subtitle': ParagraphStyle('subtitle', fontName='Helvetica',
                                   fontSize=11, textColor=WHITE,
                                   leading=16, alignment=TA_CENTER),
        'section': ParagraphStyle('section', fontName='Helvetica-Bold',
                                  fontSize=13, textColor=PRIMARY,
                                  leading=18, spaceBefore=14, spaceAfter=4),
        'subsection': ParagraphStyle('subsection', fontName='Helvetica-Bold',
                                     fontSize=10, textColor=ACCENT,
                                     leading=14, spaceBefore=8, spaceAfter=2),
        'body': ParagraphStyle('body', fontName='Helvetica',
                               fontSize=9, textColor=TEXT_MID,
                               leading=14, alignment=TA_JUSTIFY),
        'body_bold': ParagraphStyle('body_bold', fontName='Helvetica-Bold',
                                    fontSize=9, textColor=TEXT_DARK, leading=14),
        'bullet': ParagraphStyle('bullet', fontName='Helvetica',
                                 fontSize=9, textColor=TEXT_MID,
                                 leading=13, leftIndent=14,
                                 bulletIndent=4),
        'label': ParagraphStyle('label', fontName='Helvetica-Bold',
                                fontSize=8, textColor=TEXT_LIGHT,
                                leading=11, spaceAfter=1),
        'small': ParagraphStyle('small', fontName='Helvetica',
                                fontSize=8, textColor=TEXT_LIGHT, leading=11),
        'tag': ParagraphStyle('tag', fontName='Helvetica-Bold',
                              fontSize=8, textColor=WHITE, leading=11,
                              alignment=TA_CENTER),
    }


def _header_table(report_type: str, period_start, period_end) -> Table:
    """Dark navy header banner."""
    s = _styles()
    type_label = 'Executive Summary Report' if report_type == 'executive' else 'Analyst Intelligence Report'
    period_str = f"{period_start}  →  {period_end}"

    data = [
        [Paragraph('Competitor Intelligence', s['title'])],
        [Paragraph(type_label, s['subtitle'])],
        [Paragraph(period_str, s['small'])],
    ]
    tbl = Table(data, colWidths=[17 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, 0), 18),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 14),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor('#9fa8da')),
    ]))
    return tbl


def _competitor_badge(name: str) -> Table:
    """Coloured badge row for competitor name."""
    s = _styles()
    tbl = Table([[Paragraph(name, ParagraphStyle(
        'badge', fontName='Helvetica-Bold', fontSize=11,
        textColor=WHITE, leading=16,
    ))]], colWidths=[17 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), ACCENT),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
    ]))
    return tbl


def _info_row(label: str, value: str) -> Table:
    """Two-column label/value row for data tables."""
    s = _styles()
    tbl = Table([
        [Paragraph(label, s['label']), Paragraph(value or '—', s['body'])],
    ], colWidths=[4 * cm, 13 * cm])
    tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return tbl


def _key_signals_table(signals: list) -> Table:
    """Light-bg table listing key strategic signals."""
    s = _styles()
    rows = [[Paragraph(f'• {sig}', s['bullet'])] for sig in signals]
    tbl = Table(rows, colWidths=[17 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), LIGHT_BG),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('BOX',           (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    return tbl


def _stats_row(changes: int, posts: int, jobs: int) -> Table:
    """Three-cell statistics bar."""
    s = _styles()
    def cell(n, label):
        return [
            Paragraph(str(n), ParagraphStyle('stat_n', fontName='Helvetica-Bold',
                                              fontSize=16, textColor=ACCENT,
                                              leading=20, alignment=TA_CENTER)),
            Paragraph(label, ParagraphStyle('stat_l', fontName='Helvetica',
                                             fontSize=8, textColor=TEXT_LIGHT,
                                             leading=11, alignment=TA_CENTER)),
        ]

    data = [[
        *cell(changes, 'Website Changes'),
        *cell(posts,   'Social Posts'),
        *cell(jobs,    'Job Postings'),
    ]]
    # Flatten into 6 columns
    flat = [[
        Paragraph(str(changes), ParagraphStyle('sn', fontName='Helvetica-Bold', fontSize=16, textColor=ACCENT, leading=20, alignment=TA_CENTER)),
        Paragraph('Website\nChanges', ParagraphStyle('sl', fontName='Helvetica', fontSize=8, textColor=TEXT_LIGHT, leading=11, alignment=TA_CENTER)),
        Paragraph(str(posts), ParagraphStyle('sn', fontName='Helvetica-Bold', fontSize=16, textColor=ACCENT, leading=20, alignment=TA_CENTER)),
        Paragraph('Social\nPosts', ParagraphStyle('sl', fontName='Helvetica', fontSize=8, textColor=TEXT_LIGHT, leading=11, alignment=TA_CENTER)),
        Paragraph(str(jobs), ParagraphStyle('sn', fontName='Helvetica-Bold', fontSize=16, textColor=ACCENT, leading=20, alignment=TA_CENTER)),
        Paragraph('Job\nPostings', ParagraphStyle('sl', fontName='Helvetica', fontSize=8, textColor=TEXT_LIGHT, leading=11, alignment=TA_CENTER)),
    ]]
    tbl = Table(flat, colWidths=[2*cm, 3.67*cm, 2*cm, 3.67*cm, 2*cm, 3.66*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), LIGHT_BG),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BOX',           (0, 0), (-1, -1), 0.5, BORDER),
        ('LINEAFTER',     (1, 0), (3, 0), 0.5, BORDER),
    ]))
    return tbl


# ── Public entry point ───────────────────────────────────────────────────────

def generate_pdf(report) -> bytes:
    """
    Build a styled PDF for a completed Report instance.
    Returns raw PDF bytes.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title='Competitor Intelligence Report',
    )

    s = _styles()
    content = report.content
    report_type = content.get('report_type', report.report_type)
    period = content.get('period', {})
    period_start = period.get('start', str(report.period_start))
    period_end   = period.get('end',   str(report.period_end))
    competitors  = content.get('competitors', [])

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(_header_table(report_type, period_start, period_end))
    story.append(Spacer(1, 0.5*cm))

    # ── Executive Summary ───────────────────────────────────────────────────
    story.append(Paragraph('Executive Summary', s['section']))
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER, spaceAfter=6))
    exec_summary = content.get('executive_summary', '')
    if exec_summary:
        story.append(Paragraph(exec_summary, s['body']))
    story.append(Spacer(1, 0.4*cm))

    # ── Per-competitor sections ──────────────────────────────────────────────
    story.append(Paragraph('Competitor Breakdown', s['section']))
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER, spaceAfter=6))

    for comp in competitors:
        name        = comp.get('name', 'Unknown')
        summary     = comp.get('summary', '')
        raw_data    = comp.get('raw_data', {})
        wc_count    = raw_data.get('website_changes_count',  len(comp.get('website_changes', [])))
        sp_count    = raw_data.get('social_posts_count',     len(comp.get('social_posts',    [])))
        jp_count    = raw_data.get('new_job_postings_count', len(comp.get('job_postings',     [])))

        block = []
        block.append(_competitor_badge(name))
        block.append(Spacer(1, 0.2*cm))

        # Stats bar
        block.append(_stats_row(wc_count, sp_count, jp_count))
        block.append(Spacer(1, 0.2*cm))

        # Summary paragraph (both types)
        if summary:
            block.append(Paragraph(summary, s['body']))
            block.append(Spacer(1, 0.2*cm))

        # ── Analyst-only sections ────────────────────────────────────────
        if report_type == 'analyst':
            for field, label in [
                ('website_analysis', 'Website Activity'),
                ('social_analysis',  'Social Media'),
                ('hiring_analysis',  'Hiring Signals'),
            ]:
                text = comp.get(field, '')
                if text and text.lower() != 'no activity in this period.':
                    block.append(Paragraph(label, s['subsection']))
                    block.append(Paragraph(text, s['body']))
                    block.append(Spacer(1, 0.15*cm))

            # Key signals
            signals = comp.get('key_signals', [])
            if signals:
                block.append(Paragraph('Key Strategic Signals', s['subsection']))
                block.append(_key_signals_table(signals))
                block.append(Spacer(1, 0.15*cm))

            # Website changes detail table
            website_changes = comp.get('website_changes', [])
            if website_changes:
                block.append(Paragraph('Website Changes Detail', s['subsection']))
                for ch in website_changes:
                    block.append(_info_row('URL', ch.get('url', '')))
                    block.append(_info_row('Change', ch.get('change_type', '').title()))
                    block.append(_info_row('Summary', ch.get('llm_summary', '')))
                    block.append(_info_row('Detected', ch.get('detected_at', '')))
                    block.append(HRFlowable(width='100%', thickness=0.3,
                                            color=BORDER, spaceAfter=4))

            # Job postings detail
            job_postings = comp.get('job_postings', [])
            if job_postings:
                block.append(Paragraph('Open Positions', s['subsection']))
                rows = [['Title', 'Location', 'Level', 'Function']]
                for j in job_postings:
                    rows.append([
                        j.get('title', ''),
                        j.get('location', ''),
                        j.get('seniority_level', ''),
                        j.get('job_function', ''),
                    ])
                tbl = Table(rows, colWidths=[6*cm, 4*cm, 3.5*cm, 3.5*cm])
                tbl.setStyle(TableStyle([
                    ('BACKGROUND',    (0, 0), (-1, 0), PRIMARY),
                    ('TEXTCOLOR',     (0, 0), (-1, 0), WHITE),
                    ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE',      (0, 0), (-1, -1), 8),
                    ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
                    ('GRID',          (0, 0), (-1, -1), 0.3, BORDER),
                    ('TOPPADDING',    (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 6),
                ]))
                block.append(tbl)
                block.append(Spacer(1, 0.15*cm))

        story.append(KeepTogether(block[:4]))  # badge + stats + summary together
        story.extend(block[4:])
        story.append(Spacer(1, 0.4*cm))

    # ── Footer note ─────────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceBefore=10))
    story.append(Paragraph(
        f'Generated on {date.today()} · TrackRival',
        ParagraphStyle('footer', fontName='Helvetica', fontSize=7,
                       textColor=TEXT_LIGHT, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()
