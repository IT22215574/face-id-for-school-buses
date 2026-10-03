from __future__ import annotations

from decimal import Decimal

from app.models.payroll import Driver, PayPeriod, PayrollRecord


def generate_payslip_pdf(record: PayrollRecord, driver: Driver | None, pay_period: PayPeriod | None) -> bytes:
    driver_name = driver.name if driver else "Driver"
    period_text = f"{pay_period.month}/{pay_period.year}" if pay_period else "N/A"
    lines = [
        "School Bus Payroll Payslip",
        f"Driver: {driver_name}",
        f"Period: {period_text}",
        f"Gross: {record.gross}",
        f"Net: {record.net}",
        f"Status: {record.status}",
        f"Base: {record.base_amount}",
        f"Trip Earnings: {record.trip_earnings}",
        f"Distance Earnings: {record.distance_earnings}",
        f"Overtime: {record.overtime_amount}",
        f"Bonus: {record.bonus}",
        f"Allowances: {record.allowances}",
        f"Advance Deduction: {record.advance_deduction}",
        f"Penalty Deduction: {record.penalty_deduction}",
        f"Other Deduction: {record.other_deduction}",
    ]
    text = "\n".join(lines)
    pdf_lines = [
        "%PDF-1.4",
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj",
        "4 0 obj << /Length 0 >> stream\nendstream\nendobj",
        "5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        "xref",
        "0 6",
        "0000000000 65535 f ",
        "0000000010 00000 n ",
        "0000000064 00000 n ",
        "0000000123 00000 n ",
        "0000000244 00000 n ",
        "0000000365 00000 n ",
        "trailer",
        "<< /Root 1 0 R /Size 6 >>",
        "startxref",
        "0",
        "%%EOF",
    ]
    return ("\n".join(pdf_lines) + "\n" + text).encode("utf-8")
