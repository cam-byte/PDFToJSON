# main.py
import json
import os
import sys
import glob
from config import ANTHROPIC_API_KEY, MODEL_NAME
from form_analyzer import FormAnalyzer
from form_inputs import prompt_for_form_inputs

# Paths
INPUT_DIR = "./input"
OUTPUT_DIR = "./output"
JSON_TO_PDF_PATH = "/Users/camerondyas/Documents/scripts/pythonScripts/JSONToPDF"


def find_pdf_in_input():
    """Find a PDF file in the input directory."""
    pdfs = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    if not pdfs:
        print(f"❌ No PDF files found in {INPUT_DIR}/")
        print(f"   Drop a PDF file in the input folder and run again.")
        sys.exit(1)
    if len(pdfs) > 1:
        print(f"⚠️  Multiple PDFs found in {INPUT_DIR}/:")
        for i, pdf in enumerate(pdfs, 1):
            print(f"   {i}. {os.path.basename(pdf)}")
        print(f"\n   Using: {os.path.basename(pdfs[0])}")
    return pdfs[0]


def generate_pdf(json_path: str, output_pdf_path: str):
    """Generate PDF using the JSONToPDF project."""
    sys.path.insert(0, JSON_TO_PDF_PATH)
    from jsonToPDF import generate_form_pdf
    generate_form_pdf(json_path, output_pdf_path)


def main():
    print("\n" + "=" * 50)
    print("  PDF to Fillable Form Converter")
    print("=" * 50)

    # Ensure directories exist
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Find PDF in input folder
    pdf_path = find_pdf_in_input()
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"\n📄 Found: {os.path.basename(pdf_path)}")

    # Get form details interactively
    print("\n📝 Enter form details:\n")
    try:
        inputs = prompt_for_form_inputs()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled")
        sys.exit(1)

    # Analyze with Claude
    print("\n🔍 Analyzing PDF with Claude AI...")
    analyzer = FormAnalyzer(ANTHROPIC_API_KEY, MODEL_NAME, inputs)
    form_data = analyzer.analyze_pdf(pdf_path)

    if not form_data:
        print("\n❌ Failed to extract form data")
        sys.exit(1)

    # Save JSON
    json_output = os.path.join(OUTPUT_DIR, f"{pdf_name}.json")
    with open(json_output, 'w') as f:
        json.dump(form_data, indent=2, fp=f)
    print(f"\n💾 Saved: {json_output}")

    # Generate PDF
    print("\n🖨️  Generating fillable PDF...")
    pdf_output = os.path.join(OUTPUT_DIR, f"{pdf_name}_fillable.pdf")
    try:
        generate_pdf(json_output, pdf_output)
        print(f"💾 Saved: {pdf_output}")
    except Exception as e:
        print(f"⚠️  PDF generation failed: {e}")
        print(f"   JSON was saved - you can manually generate the PDF")

    print("\n" + "=" * 50)
    print("✅ Complete!")
    print("=" * 50)
    print(f"\nOutput files in {OUTPUT_DIR}/:")
    print(f"  • {pdf_name}.json")
    if os.path.exists(pdf_output):
        print(f"  • {pdf_name}_fillable.pdf")


if __name__ == "__main__":
    main()
