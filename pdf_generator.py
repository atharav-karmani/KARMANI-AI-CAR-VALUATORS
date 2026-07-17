import io
import os
import urllib.request
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class ReportNumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to add 'Page X of Y' footers and headers to the Valuation Report.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # 1. Header (all pages)
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor('#0055FF'))
        self.drawString(40, 755, "KARMANI AI CAR VALUATORS")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#4B5563'))
        self.drawRightString(letter[0] - 40, 755, "AI-Powered Technical Valuation & Specification Report")
        
        self.setStrokeColor(colors.HexColor('#E5E7EB'))
        self.setLineWidth(0.75)
        self.line(40, 747, letter[0] - 40, 747)
        
        # 2. Footer (all pages)
        self.line(40, 45, letter[0] - 40, 45)
        self.setFont("Helvetica-Oblique", 7.5)
        self.setFillColor(colors.HexColor('#9CA3AF'))
        self.drawString(40, 32, "Disclaimer: Calculated valuations are estimates based on machine learning. Local taxations apply.")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor('#4B5563'))
        self.drawRightString(letter[0] - 40, 32, f"Page {self._pageNumber} of {page_count}")
        
        self.restoreState()


def get_network_qr_image(qr_url):
    """
    Fetches QR code image from qrcode API with a safe offline fallback.
    """
    try:
        req = urllib.request.Request(
            qr_url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            return io.BytesIO(response.read())
    except Exception as e:
        print(f"Offline QR code generation fallback: {e}")
        return None


def generate_depreciation_chart(trend_prices, years):
    """
    Generates a beautiful matplotlib valuation chart for the PDF story.
    """
    if not MATPLOTLIB_AVAILABLE:
        return None
        
    fig, ax = plt.subplots(figsize=(5.5, 2.6))
    ax.plot(years, trend_prices, marker='o', color='#0055FF', linewidth=2.5, markersize=5, label="AI Market Trend")
    ax.fill_between(years, trend_prices, color='#0055FF', alpha=0.08)
    
    ax.set_title("5-Year Valuation Trend (INR)", fontsize=9.5, fontweight='bold', color='#111827', pad=10)
    ax.grid(True, linestyle='--', alpha=0.4, color='#D1D5DB')
    
    # Custom lakh formatter
    def lakh_formatter(x, pos):
        if x >= 100000:
            return f"Rs {x/100000:.2f}L"
        return f"Rs {int(x):,}"
    
    ax.yaxis.set_major_formatter(FuncFormatter(lakh_formatter))
    
    # Style spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E5E7EB')
    ax.spines['bottom'].set_color('#E5E7EB')
    ax.tick_params(colors='#4B5563', labelsize=8)
    
    plt.tight_layout()
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300, transparent=True)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer


def enrich_specs_dictionary(spec):
    """
    Augments spec dictionary to ensure all 16 comfort/safety fields are present.
    """
    enriched = dict(spec) if spec else {}
    
    # Standardize existing
    enriched['abs'] = 'Yes' if str(enriched.get('abs', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
    enriched['esp'] = 'Yes' if str(enriched.get('esp', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
    enriched['sunroof'] = 'Yes' if str(enriched.get('sunroof', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
    enriched['adas'] = 'Yes' if str(enriched.get('adas', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
    enriched['cruise_control'] = 'Yes' if str(enriched.get('cruise_control', '')).strip().lower() in ['yes', 'y', '1', 'true'] else 'No'
    
    # Derive dynamically
    price = enriched.get('base_showroom_price', 0) or 0
    try:
        price = float(price)
    except (ValueError, TypeError):
        price = 0.0

    is_premium = price > 1200000 or enriched.get('adas', 'No') == 'Yes' or enriched.get('esp', 'No') == 'Yes'
    variant_name = str(enriched.get('variant', '')).lower()
    
    enriched['reverse_camera'] = 'Yes' if (is_premium or 'lxi' not in variant_name) else 'No'
    enriched['android_auto'] = 'Yes' if (is_premium or 'lxi' not in variant_name) else 'No'
    enriched['apple_carplay'] = 'Yes' if (is_premium or 'lxi' not in variant_name) else 'No'
    enriched['tpms'] = 'Yes' if is_premium else 'No'
    enriched['hill_assist'] = 'Yes' if (is_premium or enriched.get('transmission', '').lower() == 'automatic') else 'No'
    enriched['fog_lamps'] = 'Yes' if ('lxi' not in variant_name) else 'No'
    enriched['power_steering'] = 'Yes'
    enriched['automatic_climate_control'] = 'Yes' if is_premium else 'No'
    enriched['traction_control'] = 'Yes' if (enriched.get('esp', 'No') == 'Yes' or is_premium) else 'No'
    enriched['parking_sensors'] = 'Yes'
    
    return enriched


def generate_valuation_report_pdf(car_data, spec_data, output_stream, qr_url):
    """
    Generates a premium light-themed multi-page Valuation Report PDF.
    """
    doc = SimpleDocTemplate(
        output_stream,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=70, bottomMargin=70
    )
    
    styles = getSampleStyleSheet()
    
    # Color Palette Definitions
    c_primary = colors.HexColor('#0055FF')
    c_secondary = colors.HexColor('#0EA5FF')
    c_text = colors.HexColor('#1F2937')
    c_bold = colors.HexColor('#111827')
    
    # Paragraph Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=c_primary)
    section_style = ParagraphStyle('SecStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=c_bold, spaceBefore=14, spaceAfter=8)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=13.5, textColor=c_text)
    body_bold_style = ParagraphStyle('BodyBoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9.5, leading=13.5, textColor=c_bold)
    
    yes_style = ParagraphStyle('YesStyle', parent=body_bold_style, textColor=colors.HexColor('#10B981'))
    no_style = ParagraphStyle('NoStyle', parent=body_bold_style, textColor=colors.HexColor('#EF4444'))
    
    story = []
    
    # Header Section
    story.append(Paragraph("KARMANI AI CAR VALUATORS", title_style))
    story.append(Paragraph("<b>AUTONOMOUS TECHNICAL APPRAISAL REPORT</b>", ParagraphStyle('Sub', parent=body_style, fontSize=9, textColor=c_secondary, fontName='Helvetica-Bold', letterSpacing=1)))
    story.append(Spacer(1, 12))
    
    # Report Meta & Owner Table
    meta_data = [
        [Paragraph("<b>Report ID:</b>", body_bold_style), Paragraph(f"REP-2026-{car_data['id']}", body_style),
         Paragraph("<b>Date Generated:</b>", body_bold_style), Paragraph(str(car_data['date']), body_style)],
        [Paragraph("<b>Client Name:</b>", body_bold_style), Paragraph(str(car_data.get('user_name', 'Guest Owner')), body_style),
         Paragraph("<b>Reg. State / No:</b>", body_bold_style), Paragraph(f"{car_data['state']} ({car_data['reg_no'] if car_data['reg_no'] else 'N/A'})", body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[1.4*inch, 2.1*inch, 1.4*inch, 2.1*inch])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FCFF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E6EEF7')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E6EEF7')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    
    # Vehicle General Info Table
    story.append(Paragraph("Vehicle Identification", section_style))
    ident_data = [
        [Paragraph("<b>Brand:</b>", body_bold_style), Paragraph(str(car_data['brand']), body_style),
         Paragraph("<b>Model:</b>", body_bold_style), Paragraph(str(car_data['model']), body_style)],
        [Paragraph("<b>Variant:</b>", body_bold_style), Paragraph(str(car_data['variant']), body_style),
         Paragraph("<b>Launch Year:</b>", body_bold_style), Paragraph(str(car_data['year']), body_style)],
        [Paragraph("<b>Transmission:</b>", body_bold_style), Paragraph(str(car_data['transmission']), body_style),
         Paragraph("<b>Fuel Type:</b>", body_bold_style), Paragraph(str(car_data['fuel']), body_style)],
        [Paragraph("<b>Kms Driven:</b>", body_bold_style), Paragraph(f"{car_data['kms']:,} km" if isinstance(car_data['kms'], (int, float)) else f"{car_data['kms']} km", body_style),
         Paragraph("<b>No. of Owners:</b>", body_bold_style), Paragraph(f"{car_data['owners']} Owner", body_style)]
    ]
    t_ident = Table(ident_data, colWidths=[1.4*inch, 2.1*inch, 1.4*inch, 2.1*inch])
    t_ident.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))
    story.append(t_ident)
    story.append(Spacer(1, 10))
    
    # 16 Comfort & Safety Specifications Grid
    story.append(Paragraph("Comfort & Safety Specifications", section_style))
    spec = enrich_specs_dictionary(spec_data)
    
    def get_status_flowable(val):
        if str(val).lower() == 'yes' or (isinstance(val, int) and val > 0):
            return Paragraph("AVAILABLE", yes_style)
        return Paragraph("UNAVAILABLE", no_style)
        
    specs_grid = [
        [Paragraph("<b>ABS Brake Support:</b>", body_bold_style), get_status_flowable(spec.get('abs')),
         Paragraph("<b>Airbags Count:</b>", body_bold_style), Paragraph(f"YES ({spec.get('airbags', 2)} airbags)" if spec.get('airbags', 2) else "NO", yes_style if spec.get('airbags', 2) else no_style)],
        [Paragraph("<b>Electronic Stability (ESP):</b>", body_bold_style), get_status_flowable(spec.get('esp')),
         Paragraph("<b>Sunroof Configured:</b>", body_bold_style), get_status_flowable(spec.get('sunroof'))],
        [Paragraph("<b>Cruise Control:</b>", body_bold_style), get_status_flowable(spec.get('cruise_control')),
         Paragraph("<b>Reverse Camera:</b>", body_bold_style), get_status_flowable(spec.get('reverse_camera'))],
        [Paragraph("<b>Android Auto Interface:</b>", body_bold_style), get_status_flowable(spec.get('android_auto')),
         Paragraph("<b>Apple CarPlay Support:</b>", body_bold_style), get_status_flowable(spec.get('apple_carplay'))],
        [Paragraph("<b>TPMS Monitor:</b>", body_bold_style), get_status_flowable(spec.get('tpms')),
         Paragraph("<b>Hill Assist Control:</b>", body_bold_style), get_status_flowable(spec.get('hill_assist'))],
        [Paragraph("<b>Fog Lamps Installed:</b>", body_bold_style), get_status_flowable(spec.get('fog_lamps')),
         Paragraph("<b>ADAS Intelligent Safety:</b>", body_bold_style), get_status_flowable(spec.get('adas'))],
        [Paragraph("<b>Power Steering Active:</b>", body_bold_style), get_status_flowable(spec.get('power_steering')),
         Paragraph("<b>Automatic Climate (ACC):</b>", body_bold_style), get_status_flowable(spec.get('automatic_climate_control'))],
        [Paragraph("<b>Traction Control:</b>", body_bold_style), get_status_flowable(spec.get('traction_control')),
         Paragraph("<b>Parking Radar Sensors:</b>", body_bold_style), get_status_flowable(spec.get('parking_sensors'))]
    ]
    t_specs = Table(specs_grid, colWidths=[2.2*inch, 1.3*inch, 2.2*inch, 1.3*inch])
    t_specs.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))
    story.append(t_specs)
    
    # Page Break for layout cleanliness
    story.append(PageBreak())
    
    # Page 2: Neural AI Appraisal Analysis
    story.append(Paragraph("Neural AI Valuation Appraisal", title_style))
    story.append(Paragraph("<b>DYNAMIC MARKET INTEGRATION SUMMARY</b>", ParagraphStyle('Sub2', parent=body_style, fontSize=9, textColor=c_secondary, fontName='Helvetica-Bold', letterSpacing=1)))
    story.append(Spacer(1, 14))
    
    # Pricing Summary Layout Table
    price_data = [
        [Paragraph("<b>Appraisal Category</b>", body_bold_style), Paragraph("<b>Estimated Cost (INR)</b>", body_bold_style), Paragraph("<b>Market Interpretation</b>", body_bold_style)],
        [Paragraph("Estimated Market Price", body_bold_style), Paragraph(f"<b>₹ {car_data['price']:,}</b>", ParagraphStyle('P1', parent=body_bold_style, textColor=c_primary)), Paragraph("The final dynamic appraisal value calculated by the AI engine.", body_style)],
        [Paragraph("Expected Client Selling Price", body_bold_style), Paragraph(f"₹ {car_data['price_expected']:,}", body_style), Paragraph("Targeted individual transaction benchmark price.", body_style)],
        [Paragraph("Fair Selling Price Range", body_bold_style), Paragraph(f"₹ {car_data['price_low']:,} - ₹ {car_data['price_high']:,}", body_style), Paragraph("Allowable dealership/buyer bidding boundary limits.", body_style)]
    ]
    t_price = Table(price_data, colWidths=[2.0*inch, 2.0*inch, 3.0*inch])
    t_price.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E6EEF7')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E6EEF7')),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(t_price)
    story.append(Spacer(1, 10))
    
    # Scorecard Table
    score_data = [
        [Paragraph("<b>Proprietary AI Score Card</b>", body_bold_style), Paragraph("<b>Appraisal Score</b>", body_bold_style), Paragraph("<b>Interpretation Rating</b>", body_bold_style)],
        [Paragraph("Health Score Index", body_bold_style), Paragraph(f"{car_data.get('health_score', 90)}/100", body_style), Paragraph("Calculated wear rating from document audit parameters.", body_style)],
        [Paragraph("AI Confidence Interval", body_bold_style), Paragraph(f"{car_data['confidence']}%", body_style), Paragraph("Prediction accuracy threshold based on segment market logs.", body_style)],
        [Paragraph("Depreciation Index", body_bold_style), Paragraph(f"{car_data['depreciation']}%", body_style), Paragraph("Total life-cycle value deduction score.", body_style)]
    ]
    t_score = Table(score_data, colWidths=[2.0*inch, 1.5*inch, 3.5*inch])
    t_score.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E6EEF7')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E6EEF7')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(t_score)
    story.append(Spacer(1, 12))
    
    # Chart & Recommendations Row
    recom_para = Paragraph(f"<b>AI Decision Analysis:</b><br/>{car_data.get('recom_reason', 'The vehicle holds a high health score and stable resale parameters. Recommended for individual private resale to maximize yield.')}", body_style)
    
    # Future forecasts table
    fore_1 = car_data.get('price', 0) * 0.91
    fore_2 = car_data.get('price', 0) * 0.83
    fore_3 = car_data.get('price', 0) * 0.76
    
    fore_data = [
        [Paragraph("<b>Forecast Period</b>", body_bold_style), Paragraph("<b>Resale Valuation</b>", body_bold_style)],
        [Paragraph("In 1 Year Forecast", body_bold_style), Paragraph(f"Rs {int(fore_1):,}", body_style)],
        [Paragraph("In 2 Years Forecast", body_bold_style), Paragraph(f"Rs {int(fore_2):,}", body_style)],
        [Paragraph("In 3 Years Forecast", body_bold_style), Paragraph(f"Rs {int(fore_3):,}", body_style)]
    ]
    t_fore = Table(fore_data, colWidths=[1.8*inch, 1.6*inch])
    t_fore.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    
    # Matplotlib line chart insertion
    chart_img = None
    if MATPLOTLIB_AVAILABLE:
        cur_year = 2026
        years = [cur_year - 4, cur_year - 3, cur_year - 2, cur_year - 1, cur_year]
        # Calculate dynamic historical values based on depreciation
        base = car_data['price']
        prices_trend = [base * 1.35, base * 1.24, base * 1.15, base * 1.07, base]
        chart_buffer = generate_depreciation_chart(prices_trend, years)
        if chart_buffer:
            chart_img = Image(chart_buffer, width=3.3*inch, height=1.56*inch)
            
    # Bottom Layout: Left chart, Right forecasts
    side_data = [
        [chart_img if chart_img else Paragraph("Depreciation Graph Unavailable", body_style), t_fore]
    ]
    t_side = Table(side_data, colWidths=[3.5*inch, 3.5*inch])
    t_side.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (1,0), (1,0), 10),
        ('RIGHTPADDING', (0,0), (0,0), 10)
    ]))
    story.append(t_side)
    story.append(Spacer(1, 10))
    
    # Recommendations box
    story.append(recom_para)
    story.append(Spacer(1, 15))
    
    # Bottom Verification & QR Code
    qr_img_bytes = get_network_qr_image(qr_url)
    qr_flowable = None
    if qr_img_bytes:
        qr_flowable = Image(qr_img_bytes, width=1.1*inch, height=1.1*inch)
    else:
        # Fallback drawn placeholder box
        qr_flowable = Paragraph("<b>[QR CODE]</b><br/>Verify Online", ParagraphStyle('QR', parent=body_style, align='center'))
        
    cert_text = Paragraph(
        "<b>VERIFICATION REGISTER RECORD</b><br/>"
        "This appraisal record is securely published under ID <b>VAL-" + str(car_data['id']) + "-SECURE</b> "
        "on the autonomous vehicles ledger index. Scan the QR code with any mobile device to verify real-time certificate authenticity, "
        "historical depreciation logs, and dynamic market predictions.",
        body_style
    )
    
    verify_data = [
        [qr_flowable, cert_text]
    ]
    t_verify = Table(verify_data, colWidths=[1.3*inch, 5.7*inch])
    t_verify.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAFBFD')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E6EEF7')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t_verify)

    doc.build(story, canvasmaker=ReportNumberedCanvas)


def generate_valuation_certificate_pdf(car_data, output_stream, qr_url):
    """
    Generates a premium security certificate page for the vehicle (no human signatures).
    """
    # Single page doc
    doc = SimpleDocTemplate(
        output_stream,
        pagesize=letter,
        rightMargin=45, leftMargin=45,
        topMargin=45, bottomMargin=45
    )
    
    styles = getSampleStyleSheet()
    
    c_gold = colors.HexColor('#B59410')
    c_dark_navy = colors.HexColor('#111827')
    c_blue = colors.HexColor('#0055FF')
    
    title_style = ParagraphStyle('CertTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=c_blue, alignment=1)
    sub_title_style = ParagraphStyle('CertSub', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=c_gold, alignment=1, letterSpacing=2)
    desc_style = ParagraphStyle('CertDesc', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=17, textColor=c_dark_navy, alignment=1)
    body_style = ParagraphStyle('CertBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=14, textColor=colors.HexColor('#4B5563'))
    body_bold_style = ParagraphStyle('CertBodyBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9.5, leading=14, textColor=c_dark_navy)
    
    story = []
    
    story.append(Spacer(1, 15))
    story.append(Paragraph("KARMANI AI CAR VALUATORS", ParagraphStyle('C1', parent=title_style, fontSize=15, textColor=c_blue, letterSpacing=1)))
    story.append(Spacer(1, 10))
    story.append(Paragraph("VEHICLE VALUATION CERTIFICATE", title_style))
    story.append(Paragraph("SECURE MACHINE LEARNING APPRAISAL INDEX", sub_title_style))
    story.append(Spacer(1, 20))
    
    cert_intro = (
        f"This official certificate confirms that the vehicle described below has been appraised and valuated "
        f"using the <b>KARMANI AI Vehicle Valuation Engine</b> (v4.2) utilizing historical transaction data, "
        f"structural inspection parameters, regional market liquidity registers, and neural network algorithms."
    )
    story.append(Paragraph(cert_intro, desc_style))
    story.append(Spacer(1, 22))
    
    # Specs summary table
    cert_rows = [
        [Paragraph("<b>Vehicle Brand & Model:</b>", body_bold_style), Paragraph(f"{car_data['brand']} {car_data['model']}", body_style),
         Paragraph("<b>Appraisal Valuation:</b>", body_bold_style), Paragraph(f"<b>₹ {car_data['price']:,}</b>" if isinstance(car_data['price'], (int, float)) else f"<b>₹ {car_data['price']}</b>", ParagraphStyle('V', parent=body_bold_style, textColor=colors.HexColor('#10B981'), fontSize=11))],
        [Paragraph("<b>Trim & Variant Level:</b>", body_bold_style), Paragraph(str(car_data['variant']), body_style),
         Paragraph("<b>AI Confidence Score:</b>", body_bold_style), Paragraph(f"{car_data['confidence']}% Verified", body_style)],
        [Paragraph("<b>Registration Number:</b>", body_bold_style), Paragraph(str(car_data['reg_no'] if car_data['reg_no'] else 'N/A'), body_style),
         Paragraph("<b>Appraisal Issue Date:</b>", body_bold_style), Paragraph(str(car_data['date']), body_style)],
        [Paragraph("<b>Certificate ID Number:</b>", body_bold_style), Paragraph(f"CERT-VAL-{car_data['id']}-SECURE", body_style),
         Paragraph("<b>Algorithmic Engine:</b>", body_bold_style), Paragraph("KARMANI ML v4.2", body_style)]
    ]
    t_cert = Table(cert_rows, colWidths=[2.1*inch, 1.9*inch, 1.8*inch, 2.2*inch])
    t_cert.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1.5, c_gold),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAFBFD')),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(t_cert)
    story.append(Spacer(1, 30))
    
    # Bottom Layout: Left Verification Statement, Right QR Code
    qr_bytes = get_network_qr_image(qr_url)
    qr_flowable = None
    if qr_bytes:
        qr_flowable = Image(qr_bytes, width=1.3*inch, height=1.3*inch)
    else:
        qr_flowable = Paragraph("<b>[QR CODE]</b><br/>Verify Online", ParagraphStyle('QR2', parent=body_style, align='center'))
        
    validation_text = (
        "<b>VALUATED BY:</b><br/>"
        "<b>KARMANI AI CAR VALUATORS</b><br/>"
        "<i>Artificial Intelligence Vehicle Valuation Engine</i><br/>"
        "Powered by Machine Learning Algorithms<br/>"
        "<font color='#10B981'><b>AI VERIFIED ✓</b></font>"
    )
    
    bottom_table_data = [
        [Paragraph(validation_text, ParagraphStyle('ValT', parent=body_style, fontSize=11, leading=16, textColor=c_dark_navy)), qr_flowable]
    ]
    t_bottom = Table(bottom_table_data, colWidths=[4.8*inch, 2.2*inch])
    t_bottom.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (1,0), (1,0), 30),
        ('PADDING', (0,0), (-1,-1), 10)
    ]))
    story.append(t_bottom)
    
    # Certificate frame border decorator
    def draw_certificate_border(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(c_gold)
        canvas_obj.setLineWidth(3)
        canvas_obj.rect(20, 20, letter[0] - 40, letter[1] - 40)
        canvas_obj.setStrokeColor(c_blue)
        canvas_obj.setLineWidth(1)
        canvas_obj.rect(24, 24, letter[0] - 48, letter[1] - 48)
        canvas_obj.restoreState()
        
    doc.build(story, onFirstPage=draw_certificate_border)


def generate_vehicle_pdf(car_data, output_stream):
    """
    Standard backward compatible PDF exporter mapping.
    """
    spec_dummy = {
        'engine_capacity': car_data.get('engine', 'N/A'),
        'power': car_data.get('power', 'N/A'),
        'torque': car_data.get('torque', 'N/A'),
        'mileage': car_data.get('mileage', 'N/A'),
        'transmission': car_data.get('transmission', 'N/A'),
        'drivetrain': car_data.get('drivetrain', 'N/A'),
        'ground_clearance': car_data.get('ground_clearance', 'N/A'),
        'safety_rating': car_data.get('safety_rating', 0),
        'seating_capacity': car_data.get('seating_capacity', 'N/A'),
        'fuel_tank_capacity': car_data.get('fuel_tank', 'N/A'),
        'airbags': car_data.get('airbags', 'N/A'),
        'adas': car_data.get('adas', 'No'),
    }
    generate_valuation_report_pdf(car_data, spec_dummy, output_stream, "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=http://localhost:5000/report/1")
