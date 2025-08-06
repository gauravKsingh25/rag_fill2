#!/usr/bin/env python3
"""
Create a test PDF for testing enhanced PDF processing
"""
import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_test_pdf():
    """Create a test PDF with medical device content"""
    
    backend_dir = Path(__file__).parent
    uploads_dir = backend_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    
    pdf_path = uploads_dir / "test_medical_device.pdf"
    
    # Create PDF
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    
    # Add content
    y_position = height - 50
    
    content_lines = [
        "DEVICE MASTER FILE",
        "",
        "Section 1: Device Information",
        "",
        "Generic name: Pulse Oximeter",
        "Model No.: PO-2024-PRO",
        "Document No.: PLL/DMF/001/2024",
        "Manufacturer: ACME Medical Devices Inc.",
        "",
        "Date: 15/03/2024",
        "Authorized by: Dr. John Smith",
        "",
        "Description:",
        "The Pulse Oximeter PO-2024-PRO is a non-invasive medical device",
        "designed for continuous monitoring of oxygen saturation levels",
        "in patients. The device uses advanced LED technology to provide",
        "accurate readings in various clinical environments.",
        "",
        "Technical Specifications:",
        "- Measurement Range: 70-100% SpO2",
        "- Accuracy: ±2% (70-100% range)",
        "- Resolution: 1%",
        "- Operating Temperature: 5°C to 40°C",
        "- Storage Temperature: -40°C to 70°C",
        "- Power Supply: 3V DC (2 x AA batteries)",
        "",
        "Regulatory Information:",
        "FDA 510(k): K241234",
        "CE Mark: 0123",
        "ISO 13485: Compliant",
        "ISO 14155: Compliant",
        "",
        "[MISSING] Clinical evaluation data",
        "[TO BE FILLED] Risk management file reference",
        "[TBD] Post-market surveillance plan",
        "",
        "Quality Management:",
        "The device is manufactured under ISO 13485 quality management",
        "system. All manufacturing processes are validated and controlled",
        "according to FDA QSR requirements.",
        "",
        "Signature: _________________",
        "Date: __/__/____"
    ]
    
    for line in content_lines:
        c.drawString(50, y_position, line)
        y_position -= 15
        
        if y_position < 50:  # Start new page
            c.showPage()
            y_position = height - 50
    
    c.save()
    print(f"✅ Created test PDF: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    try:
        create_test_pdf()
    except ImportError:
        print("❌ reportlab not installed. Installing...")
        os.system("pip install reportlab")
        create_test_pdf()
