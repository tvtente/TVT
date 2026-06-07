from pathlib import Path

from django.contrib.staticfiles import finders
from html import escape
from io import BytesIO

from django.utils.formats import date_format
from django.utils.translation import gettext


def _clean(value):
    return (value or "").strip()


def _translated(obj, field_name, default=""):
    if obj is None:
        return default
    if hasattr(obj, "safe_translation_getter"):
        value = obj.safe_translation_getter(field_name, any_language=True)
        return value if value not in (None, "") else default
    return getattr(obj, field_name, default) or default


def _html_text(value):
    if not value:
        return ""
    return escape(str(value)).replace("\n", "<br/>")


def _date_range(start_date, end_date, is_current=False, start_year=None, end_year=None):
    start_value = ""
    end_value = ""

    if start_date:
        start_value = date_format(start_date, "M Y")
    elif start_year:
        start_value = str(start_year)

    if is_current:
        end_value = gettext("Present")
    elif end_date:
        end_value = date_format(end_date, "M Y")
    elif end_year:
        end_value = str(end_year)

    if start_value and end_value:
        return f"{start_value} — {end_value}"
    return start_value or end_value


def _profile_avatar_path(profile):
    if not profile:
        return None

    try:
        if not profile.use_default_avatar and getattr(profile, "avatar", None):
            avatar_name = (profile.avatar.name or "").strip()
            if avatar_name:
                try:
                    avatar_path = profile.avatar.path
                except Exception:
                    avatar_path = None
                if avatar_path and Path(avatar_path).exists():
                    return avatar_path
    except Exception:
        pass

    static_avatar = profile.default_avatar_choice or profile.AvatarChoice.PRIVATE
    found = finders.find(static_avatar)
    return found if found and Path(found).exists() else None


def build_public_profile_pdf_bytes(context):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    profile = context["profile"]
    full_name = context.get("full_name") or profile.get_display_name()
    profile_identity_label = context.get("profile_identity_label") or ""
    city_country_display = context.get("city_country_display") or ""
    show_location_line = context.get("show_location_line")
    total_publications_count = context.get("total_publications_count") or 0
    total_experience_years = context.get("total_experience_years")
    total_education_years = context.get("total_education_years")
    total_certification_hours = context.get("total_certification_hours") or 0
    certification_items = context.get("certification_items") or []
    experience_items = context.get("experience_items") or []
    education_items = context.get("education_items") or []
    language_items = context.get("language_items") or []
    link_items = context.get("link_items") or []
    technical_skill_groups = context.get("technical_skill_groups") or []
    competency_items = context.get("competency_items") or []
    internal_publications = context.get("internal_publications") or []
    external_publication_items = context.get("external_publication_items") or []
    skill_items = context.get("skill_items") or []

    accent = colors.HexColor("#ffc107")
    border = colors.HexColor("#d9dee3")
    muted = colors.HexColor("#5f6b77")
    surface = colors.HexColor("#f8f9fa")
    surface_soft = colors.HexColor("#fff9e8")
    text = colors.HexColor("#212529")

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "CVBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=text,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    muted_body = ParagraphStyle(
        "CVMuted",
        parent=body,
        fontSize=9,
        leading=12,
        textColor=muted,
    )
    hero_name = ParagraphStyle(
        "CVHeroName",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=25,
        textColor=text,
        spaceAfter=4,
    )
    hero_identity = ParagraphStyle(
        "CVHeroIdentity",
        parent=body,
        fontSize=12,
        leading=15,
        textColor=muted,
        spaceAfter=4,
    )
    hero_title = ParagraphStyle(
        "CVHeroTitle",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14,
        textColor=text,
        spaceAfter=2,
    )
    section_title = ParagraphStyle(
        "CVSectionTitle",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=text,
        spaceAfter=3,
    )
    section_subtitle = ParagraphStyle(
        "CVSectionSubtitle",
        parent=muted_body,
        fontSize=8.5,
        leading=11,
        spaceAfter=0,
    )
    label_style = ParagraphStyle(
        "CVLabel",
        parent=muted_body,
        fontName="Helvetica-Bold",
        fontSize=8.3,
        leading=10,
        textTransform="uppercase",
    )
    entry_title = ParagraphStyle(
        "CVEntryTitle",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        spaceAfter=2,
    )
    badge_style = ParagraphStyle(
        "CVBadge",
        parent=body,
        backColor=accent,
        borderColor=accent,
        borderPadding=(2, 6, 2),
        borderRadius=9,
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=9,
        textColor=text,
    )
    pill_style = ParagraphStyle(
        "CVPill",
        parent=body,
        backColor=surface_soft,
        borderColor=colors.HexColor("#f0d677"),
        borderWidth=0.6,
        borderPadding=(3, 7, 3),
        borderRadius=9,
        fontSize=8.8,
        leading=10,
        textColor=text,
    )
    stat_label = ParagraphStyle(
        "CVStatLabel",
        parent=label_style,
        fontSize=8.1,
        leading=10,
    )
    stat_value = ParagraphStyle(
        "CVStatValue",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=text,
    )

    def spacer(height=4):
        return Spacer(1, height)

    def section_header(title, subtitle=None):
        rows = [[Paragraph(_html_text(title), section_title)]]
        if subtitle:
            rows.append([Paragraph(_html_text(subtitle), section_subtitle)])
        table = Table(rows, colWidths=[186 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BACKGROUND", (0, 0), (-1, 0), surface_soft),
            ("LINEBELOW", (0, -1), (-1, -1), 0.6, border),
            ("BOX", (0, 0), (-1, -1), 0.8, border),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        return table

    def boxed_story(flowables):
        table = Table([[flowables]], colWidths=[186 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, border),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        return table

    def entry_block(flowables):
        return [
            HRFlowable(width="100%", thickness=0.7, color=border, spaceBefore=2, spaceAfter=8),
            *flowables,
            Spacer(1, 10),
        ]

    def badge(text_value):
        return Paragraph(_html_text(text_value), badge_style)

    def pill(text_value):
        return Paragraph(_html_text(text_value), pill_style)

    story = []

    hero_parts = [
        Paragraph(_html_text(full_name), hero_name),
        Paragraph(_html_text(profile_identity_label), hero_identity),
        Paragraph(
            _html_text(
                f"{profile.followers_count} {gettext('followers')}"
                + (
                    f" | {total_publications_count} {gettext('Publications')}"
                    if total_publications_count else ""
                )
            ),
            muted_body,
        ),
    ]

    if profile.professional_title:
        hero_parts.append(Paragraph(_html_text(profile.professional_title), hero_title))
    if profile.headline:
        hero_parts.append(Paragraph(_html_text(profile.headline), body))
    if profile.is_researcher or profile.is_contributor:
        badges = []
        if profile.is_researcher:
            badges.append(gettext("Researcher"))
        if profile.is_contributor:
            badges.append(gettext("Contributor"))
        hero_parts.append(Paragraph(" &nbsp; ".join(_html_text(item) for item in badges), badge_style))

    for value in (
        profile.institution,
        city_country_display,
        profile.location if show_location_line else "",
        f"ORCID: {profile.orcid}" if profile.orcid else "",
        profile.website_url,
        profile.public_email,
    ):
        if value:
            hero_parts.append(Paragraph(_html_text(value), muted_body))
    avatar_path = _profile_avatar_path(profile)
    avatar_flowable = ""
    if avatar_path:
        avatar_flowable = Image(avatar_path, width=30 * mm, height=30 * mm)
    hero = Table([[avatar_flowable, hero_parts]], colWidths=[34 * mm, 152 * mm])
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7f8")),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("RIGHTPADDING", (0, 0), (0, 0), 10),
    ]))
    story.extend([hero, spacer(10)])

    if profile.bio or profile.areas_of_interest:
        bio_parts = []
        if profile.bio:
            bio_parts.extend([
                Paragraph(_html_text(gettext("About Me")), label_style),
                Paragraph(_html_text(profile.bio), body),
            ])
        if profile.areas_of_interest:
            if bio_parts:
                bio_parts.append(spacer(8))
            bio_parts.extend([
                Paragraph(_html_text(gettext("Areas of Interest")), label_style),
                Paragraph(_html_text(profile.areas_of_interest), body),
            ])
        story.extend([boxed_story(bio_parts), spacer(10)])

    if any([total_experience_years, total_education_years, certification_items, skill_items, competency_items]):
        story.append(PageBreak())
        story.append(section_header(
            gettext("Research and Professional Profile"),
            gettext("This overview highlights the lines of work, methodological resources, and public references that structure the profile."),
        ))

        stat_rows = [[
            Paragraph(_html_text(gettext("Years of Experience")), stat_label),
            Paragraph(_html_text(gettext("Years of Education")), stat_label),
            Paragraph(_html_text(gettext("N. Certifications")), stat_label),
        ], [
            Paragraph(_html_text(total_experience_years or "0"), stat_value),
            Paragraph(_html_text(total_education_years or "0"), stat_value),
            Paragraph(
                _html_text(
                    f"{len(certification_items)}"
                    + (
                        f" - {total_certification_hours} {gettext('hrs.')}"
                        if total_certification_hours else ""
                    )
                ),
                stat_value,
            ),
        ]]
        stat_table = Table(stat_rows, colWidths=[62 * mm, 62 * mm, 62 * mm])
        stat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BACKGROUND", (0, 0), (-1, -1), surface_soft),
            ("BOX", (0, 0), (-1, -1), 0.8, border),
            ("INNERGRID", (0, 0), (-1, -1), 0.8, border),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.extend([stat_table, spacer(10)])

        if skill_items:
            story.append(Paragraph(_html_text(gettext("Highlighted methods and tools")), label_style))
            skill_pills = [pill(
                f"{item.skill_type.translated_name}{f' · {item.level}' if item.level else ''}"
            ) for item in skill_items[:8] if item.skill_type]
            if skill_pills:
                story.extend(skill_pills + [spacer(8)])

        if competency_items:
            story.append(Paragraph(_html_text(gettext("Working style")), label_style))
            competency_pills = [pill(item.competency_type.translated_name) for item in competency_items[:6] if item.competency_type]
            if competency_pills:
                story.extend(competency_pills + [spacer(8)])

    if experience_items:
        story.append(PageBreak())
        story.append(section_header(gettext("Experience")))
        for item in experience_items:
            parts = [
                Paragraph(_html_text(item.position), entry_title),
                Paragraph(
                    _html_text(item.organization),
                    body,
                ),
            ]
            if item.experience_type:
                parts.extend([spacer(2), badge(item.experience_type)])
            if item.location:
                parts.append(Paragraph(_html_text(item.location), muted_body))
            date_label = _date_range(item.start_date, item.end_date, item.is_current)
            if date_label:
                parts.append(Paragraph(_html_text(date_label), muted_body))
            description = _translated(item, "description")
            main_responsibilities = _translated(item, "main_responsibilities")
            key_achievements = _translated(item, "key_achievements")
            if description:
                parts.extend([spacer(4), Paragraph(_html_text(gettext("Company description")), label_style), Paragraph(_html_text(description), body)])
            if main_responsibilities:
                parts.extend([spacer(4), Paragraph(_html_text(gettext("Main responsibilities")), label_style), Paragraph(_html_text(main_responsibilities), body)])
            if key_achievements:
                parts.extend([spacer(4), Paragraph(_html_text(gettext("Key achievements or projects")), label_style), Paragraph(_html_text(key_achievements), body)])
            story.extend(entry_block(parts))

    if education_items:
        story.append(PageBreak())
        story.append(section_header(gettext("Education")))
        for item in education_items:
            title = item.degree or item.institution
            parts = [Paragraph(_html_text(title), entry_title), Paragraph(_html_text(item.institution), body)]
            if item.field_of_study:
                parts.append(Paragraph(_html_text(item.field_of_study), muted_body))
            if item.education_type:
                parts.extend([spacer(2), badge(item.education_type)])
            if item.credit_hours:
                parts.append(Paragraph(_html_text(gettext("%(credits)s credit hours") % {"credits": item.credit_hours}), muted_body))
            date_label = _date_range(item.start_date, item.end_date, item.is_current, item.start_year, item.end_year)
            if date_label:
                parts.append(Paragraph(_html_text(date_label), muted_body))
            description = _translated(item, "description")
            if description:
                parts.extend([spacer(4), Paragraph(_html_text(description), body)])
            story.extend(entry_block(parts))

    if certification_items:
        story.append(PageBreak())
        story.append(section_header(gettext("Certifications")))
        for item in certification_items:
            parts = [Paragraph(_html_text(item.name), entry_title)]
            if item.issuer:
                parts.append(Paragraph(_html_text(item.issuer), body))
            if item.certification_type:
                parts.extend([spacer(2), badge(item.certification_type)])
            if item.credit_hours:
                parts.append(Paragraph(_html_text(gettext("%(hours)s hours") % {"hours": item.credit_hours}), muted_body))
            date_label = ""
            if item.issue_date:
                date_label = date_format(item.issue_date, "M Y")
            if item.no_expiration:
                date_label = f"{date_label} — {gettext('Sin caducar')}".strip()
            elif item.expiration_date:
                date_label = f"{date_label} — {date_format(item.expiration_date, 'M Y')}".strip()
            if date_label:
                parts.append(Paragraph(_html_text(date_label), muted_body))
            if item.credential_id:
                parts.append(Paragraph(_html_text(f"{gettext('Credential ID')}: {item.credential_id}"), muted_body))
            if item.credential_url:
                parts.append(Paragraph(_html_text(f"{gettext('View credential')}: {item.credential_url}"), muted_body))
            description = _translated(item, "description")
            if description:
                parts.extend([spacer(4), Paragraph(_html_text(description), body)])
            story.extend(entry_block(parts))

    if language_items or link_items:
        story.append(PageBreak())
        story.append(section_header(gettext("Languages")))
        if language_items:
            lang_parts = [pill(f"{_translated(item, 'language')}{f' · {item.level}' if item.level else ''}") for item in language_items]
            story.extend(lang_parts + [spacer(8)])
        if link_items:
            story.append(Paragraph(_html_text(gettext("Academic and Professional Links")), label_style))
            for item in link_items:
                story.extend([
                    Paragraph(_html_text(item.get_display_label()), entry_title),
                    Paragraph(_html_text(item.url), muted_body),
                    spacer(5),
                ])

    if technical_skill_groups:
        story.append(PageBreak())
        story.append(section_header(gettext("Technical and Methodological Knowledge")))
        for group in technical_skill_groups:
            parts = [Paragraph(_html_text(group["category_name"]), label_style)]
            parts.extend([
                pill(f"{item.skill_type.translated_name}{f' · {item.level}' if item.level else ''}")
                for item in group["items"] if item.skill_type
            ])
            story.extend(entry_block(parts))

    if competency_items:
        story.append(PageBreak())
        story.append(section_header(gettext("Transversal Competencies")))
        for item in competency_items:
            parts = [Paragraph(_html_text(item.competency_type.translated_name), entry_title)]
            description = _translated(item, "description") or item.competency_type.translated_description
            if description:
                parts.append(Paragraph(_html_text(description), body))
            story.extend(entry_block(parts))

    if internal_publications:
        story.append(PageBreak())
        story.append(section_header(gettext("TVTente Scientific Publications")))
        for publication in internal_publications:
            parts = [Paragraph(_html_text(publication.title), entry_title)]
            if publication.get_categories_display():
                parts.append(Paragraph(_html_text(publication.get_categories_display()), muted_body))
            if publication.publication_date:
                parts.append(Paragraph(_html_text(date_format(publication.publication_date, "Y")), muted_body))
            if publication.doi:
                parts.append(Paragraph(_html_text(f"DOI: {publication.doi}"), muted_body))
            if publication.abstract:
                parts.append(Paragraph(_html_text(publication.abstract), body))
            story.extend(entry_block(parts))

    if external_publication_items:
        story.append(PageBreak())
        story.append(section_header(gettext("External Publications")))
        for item in external_publication_items:
            parts = [Paragraph(_html_text(_translated(item, "title")), entry_title)]
            publisher = _translated(item, "publisher")
            if publisher:
                parts.append(Paragraph(_html_text(publisher), body))
            if item.publication_type:
                parts.extend([spacer(2), badge(item.publication_type)])
            if item.publication_date:
                parts.append(Paragraph(_html_text(date_format(item.publication_date, "DATE_FORMAT")), muted_body))
            if item.doi:
                parts.append(Paragraph(_html_text(f"DOI: {item.doi}"), muted_body))
            description = _translated(item, "description")
            if description:
                parts.append(Paragraph(_html_text(description), body))
            if item.url:
                parts.append(Paragraph(_html_text(item.url), muted_body))
            story.extend(entry_block(parts))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=12 * mm,
        title=f"{full_name} CV",
        author=full_name,
    )
    doc.build(story)
    return buffer.getvalue()
