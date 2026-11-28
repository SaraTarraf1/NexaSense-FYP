from io import BytesIO
from xml.sax.saxutils import escape

from app.services.report_service import describe_report


def render_report_pdf(report):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=53, bottomMargin=54,
        title=f"NexaSense inspection report {report.id}", author="NexaSense",
    )
    styles = getSampleStyleSheet()
    ink = colors.HexColor("#193738")
    teal = colors.HexColor("#155e5b")
    styles["Title"].textColor = ink
    styles["Heading2"].textColor = teal
    styles["Heading3"].textColor = ink
    cell_style = ParagraphStyle("TableCell", parent=styles["BodyText"], fontSize=8, leading=11)
    story = []
    snapshot = report.snapshot
    equipment = snapshot["equipment"]
    inspection = snapshot["inspection"]

    def paragraph(value, style="BodyText"):
        value = "Unavailable" if value is None or value == "" else str(value)
        return Paragraph(escape(value).replace("\n", "<br/>"), styles[style])

    def heading(title):
        story.append(paragraph(title, "Heading2"))

    def fields(data, names):
        for key, label in names:
            story.append(paragraph(f"{label}: {data.get(key) if data.get(key) is not None else 'Unavailable'}"))

    def table(headers, rows, fractions, empty):
        rows = list(rows)
        if not rows:
            story.append(paragraph(empty))
            return
        cells = [
            [Paragraph(escape(str(value) if value is not None else "—"), cell_style) for value in row]
            for row in [headers, *rows]
        ]
        grid = LongTable(cells, colWidths=[document.width * fraction for fraction in fractions], repeatRows=1, splitInRow=1)
        grid.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcecea")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f7f6")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, teal),
        ]))
        story.extend([grid, Spacer(1, 8)])

    def reading_text(reading):
        value = reading["value"]
        measurement = f"{value} {reading['unit']}" if value is not None else "Unavailable"
        return f"#{reading['id']} {reading['sensor_type']}: {measurement} at {reading['timestamp']}"

    story.append(paragraph("Inspection and Maintenance Report", "Title"))
    generated_at = describe_report(report)["generated_at"]
    story.append(paragraph(f"Report #{report.id} · Generated {generated_at.isoformat()}"))
    heading("Equipment")
    fields(equipment, [
        ("name", "Name"), ("identifier", "Identifier"), ("equipment_type", "Type"),
        ("location", "Location"), ("manufacturer", "Manufacturer"), ("model", "Model"),
        ("serial_number", "Serial number"), ("installation_date", "Installed"),
        ("status", "Status"), ("description", "Notes"),
    ])
    heading("Inspection execution")
    fields(inspection, [
        ("id", "Inspection"), ("status", "Status"), ("scheduled_at", "Scheduled"),
        ("started_at", "Actual start"), ("ended_at", "Actual end"), ("notes", "Inspection notes"),
    ])
    fields(snapshot, [("duration_seconds", "Duration (seconds)")])
    heading("Sensor measurement summary")
    story.append(paragraph(f"{len(snapshot['readings'])} stored measurements · {sum(group['count'] for group in snapshot['statistics'])} valid finite values"))
    table(
        ["Sensor", "Unit", "Min", "Max", "Average", "Count"],
        ([group[key] for key in ["sensor_type", "unit", "minimum", "maximum", "average", "count"]]
         for group in snapshot["statistics"]),
        [.26, .13, .14, .14, .17, .16], "No applicable sensor statistics.",
    )
    heading("Detected anomalies")
    if not snapshot["anomalies"]:
        story.append(paragraph("No anomalies recorded."))
    for item in snapshot["anomalies"]:
        story.append(paragraph(f"{reading_text(item)} · {item['anomaly_type']} · {item['detection_message'] or ''}"))
    heading("Classified faults and evidence")
    if not snapshot["faults"]:
        story.append(paragraph("No fault classifications recorded."))
    for item in snapshot["faults"]:
        story.append(paragraph(f"{item['status'].replace('_', ' ').title()} · {item['classified_at']}", "Heading3"))
        story.append(paragraph(f"{item['message']} · Source {reading_text(item['source_reading'])}"))
        if item["missing_sensor_types"]:
            story.append(paragraph("Missing sensors: " + ", ".join(item["missing_sensor_types"])))
        for match in item["matches"]:
            story.append(paragraph(f"{match['rule_id']} · {match['fault_type'].replace('_', ' ')}"))
            for reading in match["evidence"]:
                story.append(paragraph(reading_text(reading)))
    heading("Equipment health")
    status = snapshot["health_status"]
    indicators = {"normal": "#187347", "warning": "#925000", "critical": "#a32430"}
    status_style = ParagraphStyle("HealthStatus", parent=styles["Heading3"], textColor=colors.HexColor(indicators.get(status, "#465560")))
    story.append(Paragraph(escape(status.replace("_", " ").title()), status_style))
    for item in snapshot["health"]:
        story.append(paragraph(f"{item['assessed_at']} · {item['status'].replace('_', ' ')} · {item['message']}"))
        if item["missing_sensor_types"]:
            story.append(paragraph("Missing sensors: " + ", ".join(item["missing_sensor_types"])))
        if item["fault_rule_ids"] or item["evidence_reading_ids"]:
            story.append(paragraph(
                f"Rules: {', '.join(item['fault_rule_ids']) or 'None'} · Evidence readings: "
                f"{', '.join(map(str, item['evidence_reading_ids'])) or 'None'}"
            ))
    if snapshot.get("alerts"):
        heading("Recorded alert severity")
        for alert in snapshot["alerts"]:
            severity = alert["severity"].title()
            color = indicators.get(alert["severity"], "#465560")
            description = escape(f"{alert['status'].title()} · {alert['created_at']} · {alert['description']}")
            story.append(Paragraph(f'<font color="{color}"><b>{severity}</b></font> · {description}', styles["BodyText"]))
    heading("Suggested maintenance actions")
    for action in snapshot["recommendations"]:
        story.append(paragraph(f"• {action}"))
    if snapshot["limitations"]:
        heading("Analysis limitations")
        for limitation in snapshot["limitations"]:
            story.append(paragraph(f"• {limitation}"))
    heading("Stored sensor measurements")
    table(
        ["ID", "Timestamp", "Sensor", "Value", "Unit", "Validation"],
        ([item["id"], item["timestamp"], item["sensor_type"], item["value"], item["unit"],
          " · ".join(filter(None, [item["validation_status"], item["validation_message"]]))]
         for item in snapshot["readings"]),
        [.08, .25, .16, .12, .1, .29], "No measurements recorded.",
    )

    def page_header(canvas, doc):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(teal)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(42, height - 32, "NexaSense")
        canvas.setFillColor(ink)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(42, 33, f"Inspection #{report.inspection_id} · Report #{report.id}")
        canvas.drawRightString(width - 42, 33, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=page_header, onLaterPages=page_header)
    return buffer.getvalue()
