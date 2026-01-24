"""
エクスポート機能コンポーネント
PDF、Excel、CSV、チャート画像のエクスポート
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import io
import base64
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
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


def export_to_csv(data: List[Dict], filename: Optional[str] = None) -> bytes:
    """
    CSV形式でエクスポート
    
    Args:
        data: エクスポートするデータのリスト
        filename: ファイル名（オプション）
    
    Returns:
        CSVデータのバイト列
    """
    if not data:
        return b""
    
    df = pd.DataFrame(data)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    return csv_buffer.getvalue().encode('utf-8-sig')


def export_to_excel(data: List[Dict], filename: Optional[str] = None) -> bytes:
    """
    Excel形式でエクスポート
    
    Args:
        data: エクスポートするデータのリスト
        filename: ファイル名（オプション）
    
    Returns:
        Excelデータのバイト列
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is required for Excel export. Install it with: pip install openpyxl")
    
    if not data:
        return b""
    
    df = pd.DataFrame(data)
    wb = Workbook()
    ws = wb.active
    ws.title = "データ"
    
    # ヘッダーのスタイル
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    # データを書き込み
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            if r_idx == 1:  # ヘッダー行
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # 列幅の自動調整
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
    
    # バイト列に変換
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()


def export_chart_to_image(fig: go.Figure, format: str = "png", width: int = 1200, height: int = 600) -> bytes:
    """
    チャートを画像としてエクスポート
    
    Args:
        fig: Plotly Figureオブジェクト
        format: 画像形式（png, svg, jpeg, webp）
        width: 画像の幅
        height: 画像の高さ
    
    Returns:
        画像データのバイト列
    """
    if not KALEIDO_AVAILABLE:
        raise ImportError("kaleido is required for chart export. Install it with: pip install kaleido")
    
    try:
        img_bytes = fig.to_image(format=format, width=width, height=height)
        return img_bytes
    except Exception as e:
        st.error(f"チャート画像のエクスポートに失敗しました: {e}")
        return b""


def export_to_pdf(
    data: List[Dict],
    title: str = "投資分析レポート",
    filename: Optional[str] = None
) -> bytes:
    """
    PDF形式でエクスポート
    
    Args:
        data: エクスポートするデータのリスト
        title: レポートタイトル
        filename: ファイル名（オプション）
    
    Returns:
        PDFデータのバイト列
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is required for PDF export. Install it with: pip install reportlab")
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # タイトル
    title_style = styles['Heading1']
    title_style.textColor = colors.HexColor('#2c3e50')
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # 日付
    date_str = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    story.append(Paragraph(f"生成日時: {date_str}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    if not data:
        story.append(Paragraph("データがありません", styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    # データテーブル
    df = pd.DataFrame(data)
    
    # テーブルヘッダー
    table_data = [df.columns.tolist()]
    
    # テーブルデータ（最大100行）
    max_rows = min(100, len(df))
    for idx, row in df.head(max_rows).iterrows():
        table_data.append([str(val) for val in row.values])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    
    story.append(table)
    
    if len(df) > max_rows:
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"※ 表示は最大{max_rows}行までです。全{len(df)}行のデータがあります。", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def create_export_buttons(data: List[Dict], filename_prefix: str = "export"):
    """
    エクスポートボタンを作成
    
    Args:
        data: エクスポートするデータ
        filename_prefix: ファイル名のプレフィックス
    """
    if not data:
        st.warning("エクスポートするデータがありません")
        return
    
    st.subheader("📥 データエクスポート")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        csv_data = export_to_csv(data)
        st.download_button(
            label="📄 CSV",
            data=csv_data,
            file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        if OPENPYXL_AVAILABLE:
            try:
                excel_data = export_to_excel(data)
                st.download_button(
                    label="📊 Excel",
                    data=excel_data,
                    file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Excelエクスポートエラー: {e}")
        else:
            st.info("Excelエクスポートにはopenpyxlが必要です")
    
    with col3:
        if REPORTLAB_AVAILABLE:
            try:
                pdf_data = export_to_pdf(data, title="投資分析レポート")
                st.download_button(
                    label="📑 PDF",
                    data=pdf_data,
                    file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"PDFエクスポートエラー: {e}")
        else:
            st.info("PDFエクスポートにはreportlabが必要です")
    
    with col4:
        if KALEIDO_AVAILABLE:
            st.info("チャート画像のエクスポートは各チャートのメニューから利用できます")
        else:
            st.info("チャート画像エクスポートにはkaleidoが必要です")


def export_chart_button(fig: go.Figure, chart_name: str = "chart"):
    """
    チャート画像エクスポートボタン
    
    Args:
        fig: Plotly Figureオブジェクト
        chart_name: チャート名
    """
    if not KALEIDO_AVAILABLE:
        return
    
    col1, col2 = st.columns([1, 3])
    with col1:
        format_type = st.selectbox("形式", ["PNG", "SVG", "JPEG"], key=f"format_{chart_name}")
    
    with col2:
        try:
            img_data = export_chart_to_image(fig, format=format_type.lower())
            if img_data:
                st.download_button(
                    label=f"📷 {format_type}として保存",
                    data=img_data,
                    file_name=f"{chart_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type.lower()}",
                    mime=f"image/{format_type.lower()}"
                )
        except Exception as e:
            st.error(f"画像エクスポートエラー: {e}")
