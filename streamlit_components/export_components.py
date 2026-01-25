"""
Export Components
PDF, Excel, CSV, and chart image export functionality
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime
import io
import base64
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils.dataframe import dataframe_to_rows
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import kaleido
    KALEIDO_AVAILABLE = True
except ImportError:
    KALEIDO_AVAILABLE = False


def sanitize_data_for_export(data: List[Dict]) -> List[Dict]:
    """
    Sanitize data for export by flattening complex structures.

    Args:
        data: Raw data list

    Returns:
        Cleaned data suitable for DataFrame conversion
    """
    if not data:
        return []

    cleaned = []
    for item in data:
        clean_item = {}
        for key, value in item.items():
            # Skip complex nested objects
            if isinstance(value, (dict, list)):
                continue
            # Convert to string if not a basic type
            if value is None:
                clean_item[key] = ''
            elif isinstance(value, (int, float, str, bool)):
                clean_item[key] = value
            else:
                clean_item[key] = str(value)
        cleaned.append(clean_item)
    return cleaned


def export_to_csv(data: List[Dict], filename: Optional[str] = None) -> bytes:
    """
    Export to CSV format

    Args:
        data: List of data to export
        filename: Filename (optional)

    Returns:
        CSV data as bytes
    """
    if not data:
        return b""

    clean_data = sanitize_data_for_export(data)
    df = pd.DataFrame(clean_data)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    return csv_buffer.getvalue().encode('utf-8-sig')


def export_to_excel(data: List[Dict], filename: Optional[str] = None) -> bytes:
    """
    Export to Excel format

    Args:
        data: List of data to export
        filename: Filename (optional)

    Returns:
        Excel data as bytes
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is required for Excel export. Install it with: pip install openpyxl")

    if not data:
        return b""

    clean_data = sanitize_data_for_export(data)
    df = pd.DataFrame(clean_data)
    wb = Workbook()
    ws = wb.active
    ws.title = "Investment Data"

    # Header styling
    header_fill = PatternFill(start_color="1a1a2e", end_color="1a1a2e", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    thin_border = Border(
        left=Side(style='thin', color='444444'),
        right=Side(style='thin', color='444444'),
        top=Side(style='thin', color='444444'),
        bottom=Side(style='thin', color='444444')
    )

    # Write data
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.border = thin_border
            if r_idx == 1:  # Header row
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Auto-adjust column width
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Convert to bytes
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()


def export_chart_to_image(fig: go.Figure, format: str = "png", width: int = 1200, height: int = 600) -> bytes:
    """
    Export chart as image

    Args:
        fig: Plotly Figure object
        format: Image format (png, svg, jpeg, webp)
        width: Image width
        height: Image height

    Returns:
        Image data as bytes
    """
    if not KALEIDO_AVAILABLE:
        raise ImportError("kaleido is required for chart export. Install it with: pip install kaleido")

    try:
        img_bytes = fig.to_image(format=format, width=width, height=height)
        return img_bytes
    except Exception as e:
        st.error(f"Failed to export chart image: {e}")
        return b""


def export_to_pdf(
    data: List[Dict],
    title: str = "Investment Analysis Report",
    filename: Optional[str] = None
) -> bytes:
    """
    Export to PDF format

    Args:
        data: List of data to export
        title: Report title
        filename: Filename (optional)

    Returns:
        PDF data as bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is required for PDF export. Install it with: pip install reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = styles['Heading1']
    title_style.textColor = colors.HexColor('#1a1a2e')
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.2*inch))

    # Date
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    story.append(Paragraph(f"Generated: {date_str}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))

    if not data:
        story.append(Paragraph("No data available", styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    # Data table
    clean_data = sanitize_data_for_export(data)
    df = pd.DataFrame(clean_data)

    # Limit columns for PDF
    priority_cols = ['symbol', 'Symbol', 'total_score', 'Score', 'current_state', 'State',
                     'category', 'Category', 'current_price', 'Price']
    available_cols = [c for c in priority_cols if c in df.columns]
    if available_cols:
        df = df[available_cols]
    elif len(df.columns) > 6:
        df = df.iloc[:, :6]

    # Table header
    table_data = [df.columns.tolist()]

    # Table data (max 100 rows)
    max_rows = min(100, len(df))
    for idx, row in df.head(max_rows).iterrows():
        table_data.append([str(val)[:30] for val in row.values])  # Truncate long values

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))

    story.append(table)

    if len(df) > max_rows:
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"* Showing {max_rows} of {len(df)} total rows.", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def create_export_buttons(data: List[Dict], filename_prefix: str = "export"):
    """
    Create export buttons with modern styling

    Args:
        data: Data to export
        filename_prefix: Filename prefix
    """
    if not data:
        st.warning("No data available for export")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            csv_data = export_to_csv(data)
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"CSV export error: {e}")

    with col2:
        if OPENPYXL_AVAILABLE:
            try:
                excel_data = export_to_excel(data)
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_data,
                    file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Excel export error: {e}")
        else:
            st.info("Excel export requires openpyxl")

    with col3:
        if REPORTLAB_AVAILABLE:
            try:
                pdf_data = export_to_pdf(data, title="Investment Analysis Report")
                st.download_button(
                    label="📑 Download PDF",
                    data=pdf_data,
                    file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF export error: {e}")
        else:
            st.info("PDF export requires reportlab")


def export_chart_button(fig: go.Figure, chart_name: str = "chart"):
    """
    Chart image export button

    Args:
        fig: Plotly Figure object
        chart_name: Chart name
    """
    if not KALEIDO_AVAILABLE:
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        format_type = st.selectbox("Format", ["PNG", "SVG", "JPEG"], key=f"format_{chart_name}")

    with col2:
        try:
            img_data = export_chart_to_image(fig, format=format_type.lower())
            if img_data:
                st.download_button(
                    label=f"📷 Save as {format_type}",
                    data=img_data,
                    file_name=f"{chart_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type.lower()}",
                    mime=f"image/{format_type.lower()}"
                )
        except Exception as e:
            st.error(f"Image export error: {e}")
