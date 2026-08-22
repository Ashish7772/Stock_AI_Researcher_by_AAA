from __future__ import annotations

from io import BytesIO
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


def _money(value: float) -> str:
    return f"INR {float(value):,.2f}"


def _pct(value: float) -> str:
    return f"{float(value):.1f}%"


def _fmt(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.4g}"
    return str(value)


def build_pdf_report(summary: dict, full_report: dict | None = None) -> bytes:
    """Build a self-contained PDF report from the analysis result."""
    full_report = full_report or {}
    p1 = summary["probabilities_1m"]
    p2 = summary["probabilities_2m"]
    s1 = summary["scenario_1m"]
    s2 = summary["scenario_2m"]

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Stock AI Researcher by AAA - {summary['symbol']}",
        author="AAA",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=21,
        leading=25, spaceAfter=5, textColor=colors.HexColor("#202637")
    )
    subtitle = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9,
        leading=12, textColor=colors.HexColor("#667085"), spaceAfter=13
    )
    h1 = ParagraphStyle(
        "H1", parent=styles["Heading1"], fontSize=15, leading=18,
        spaceBefore=12, spaceAfter=7, textColor=colors.HexColor("#202637")
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontSize=11.5, leading=14,
        spaceBefore=7, spaceAfter=4, textColor=colors.HexColor("#344054")
    )
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontSize=8.8, leading=12,
        textColor=colors.HexColor("#344054"), spaceAfter=4
    )
    small = ParagraphStyle(
        "Small", parent=body, fontSize=7.5, leading=10, textColor=colors.HexColor("#667085")
    )
    big = ParagraphStyle(
        "Big", parent=body, fontSize=14, leading=18, alignment=TA_CENTER,
        textColor=colors.HexColor("#101828"), spaceAfter=2
    )

    story = []
    story.append(Paragraph("Stock AI Researcher by AAA", title))
    story.append(Paragraph(
        f"{escape(str(summary['company']))} - {escape(str(summary['symbol']))}", subtitle
    ))

    current = float(summary["current_price"])
    cards = [
        [Paragraph("NEXT 1 MONTH", h2), Paragraph("NEXT 2 MONTHS", h2)],
        [
            Paragraph(f"<b>{_money(summary['expected_price_1m'])}</b>", big),
            Paragraph(f"<b>{_money(summary['expected_price_2m'])}</b>", big),
        ],
        [
            Paragraph(f"Bullish chance: <b>{_pct(p1['bullish'])}</b><br/>View: <b>{escape(summary['recommendation_1m'])}</b>", body),
            Paragraph(f"Bullish chance: <b>{_pct(p2['bullish'])}</b><br/>View: <b>{escape(summary['recommendation_2m'])}</b>", body),
        ],
        [
            Paragraph(f"Expected move: <b>{(summary['expected_price_1m'] / current - 1) * 100:+.1f}%</b>", body),
            Paragraph(f"Expected move: <b>{(summary['expected_price_2m'] / current - 1) * 100:+.1f}%</b>", body),
        ],
    ]
    card_table = Table(cards, colWidths=[86 * mm, 86 * mm])
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D0D5DD")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E7EC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        f"Current price: <b>{_money(current)}</b> | Analysis time: {escape(str(summary['data_as_of']))}",
        small,
    ))
    story.append(Paragraph(
        "Expected price is a probability-weighted model estimate across bear/base/bull scenarios. It is not a guaranteed target.",
        small,
    ))

    story.append(Paragraph("Direction probabilities", h1))
    prob_data = [
        ["Horizon", "Bearish", "Sideways", "Bullish", "View"],
        ["1 Month", _pct(p1["bearish"]), _pct(p1["sideways"]), _pct(p1["bullish"]), summary["recommendation_1m"]],
        ["2 Months", _pct(p2["bearish"]), _pct(p2["sideways"]), _pct(p2["bullish"]), summary["recommendation_2m"]],
    ]
    t = Table(prob_data, colWidths=[34*mm, 31*mm, 31*mm, 31*mm, 40*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#344054")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D0D5DD")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    story.append(Paragraph("Scenario price ranges", h1))
    scen = [
        ["Horizon", "Bear", "Base", "Bull", "Scenario range"],
        ["1 Month", _money(s1["bear"]), _money(s1["base"]), _money(s1["bull"]), f"{_money(s1['bear'])} - {_money(s1['bull'])}"],
        ["2 Months", _money(s2["bear"]), _money(s2["base"]), _money(s2["bull"]), f"{_money(s2['bear'])} - {_money(s2['bull'])}"],
    ]
    t = Table(scen, colWidths=[28*mm, 29*mm, 29*mm, 29*mm, 52*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D0D5DD")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    story.append(Paragraph("Research scorecard", h1))
    scores = [
        ["Signal", "Score"],
        ["Technical", f"{summary['technical_score']:+.1f} / 100"],
        ["Fundamental", f"{summary['fundamental_score']:+.1f} / 100"],
        ["NIFTY relative strength", f"{summary['market_score']:+.1f} / 100"],
        ["Support", _money(summary["support"])],
        ["Resistance", _money(summary["resistance"])],
    ]
    t = Table(scores, colWidths=[94*mm, 73*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D0D5DD")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    def add_bullets(title_text, items):
        story.append(Paragraph(title_text, h2))
        if items:
            for item in items:
                story.append(Paragraph(f"• {escape(str(item))}", body))
        else:
            story.append(Paragraph("No specific items returned.", body))

    add_bullets("Bullish factors", summary.get("technical_reasons", []) + summary.get("fundamental_reasons", []) + summary.get("market_reasons", []))
    add_bullets("Risks / weaknesses", summary.get("technical_risks", []) + summary.get("fundamental_risks", []) + summary.get("market_risks", []))

    story.append(PageBreak())
    story.append(Paragraph("Fundamental snapshot", h1))
    fin = full_report.get("fundamentals", {})
    if fin:
        fin_rows = [["Metric", "Value"]]
        for key, value in fin.items():
            if value is not None:
                fin_rows.append([str(key), _fmt(value)])
        t = Table(fin_rows, colWidths=[84*mm, 83*mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D5DD")),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No fundamental snapshot was returned.", body))

    story.append(Paragraph("Technical indicators", h1))
    indicators = full_report.get("indicators", {})
    ind_rows = [["Indicator", "Value"]]
    for key, value in indicators.items():
        if value is not None:
            ind_rows.append([str(key), _fmt(value)])
    t = Table(ind_rows, colWidths=[84*mm, 83*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D5DD")),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    story.append(Paragraph("ML validation", h1))
    val_rows = [["Horizon", "Accuracy", "Balanced accuracy", "Precision", "Recall", "Folds"]]
    for label, key in (("1 Month", "validation_1m"), ("2 Months", "validation_2m")):
        bt = summary.get(key)
        if bt:
            val_rows.append([
                label,
                _pct(bt.get("accuracy", 0) * 100),
                _pct(bt.get("balanced_accuracy", 0) * 100),
                _pct(bt.get("precision_macro", 0) * 100),
                _pct(bt.get("recall_macro", 0) * 100),
                str(bt.get("folds", 0)),
            ])
    if len(val_rows) == 1:
        story.append(Paragraph("Validation skipped or insufficient history.", body))
    else:
        t = Table(val_rows, colWidths=[25*mm, 28*mm, 36*mm, 28*mm, 28*mm, 22*mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D5DD")),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    story.append(Paragraph("News", h1))
    news = full_report.get("news", [])
    if news:
        for item in news:
            title_text = escape(str(item.get("title", "")))
            publisher = escape(str(item.get("publisher", "")))
            link = escape(str(item.get("link", "")))
            if link:
                story.append(Paragraph(f"• <link href='{link}'>{title_text}</link> - {publisher}", body))
            else:
                story.append(Paragraph(f"• {title_text} - {publisher}", body))
    else:
        story.append(Paragraph("No news feed was returned by the free sources.", body))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Important: model probabilities are outputs of this application's heuristic + ML pipeline using available free data. They are not probabilities supplied by the market and are not a guarantee of future prices. This report is for research/education, not financial advice.",
        small,
    ))

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#98A2B3"))
        canvas.drawString(14 * mm, 8 * mm, "Stock AI Researcher by AAA")
        canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
