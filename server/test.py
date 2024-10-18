import pikepdf
import logging
import os

logging.basicConfig(level=logging.DEBUG)

def extract_and_compress_pdf_page(input_pdf_path, page_number, output_pdf_path):
    logging.info(f"Processing PDF: {input_pdf_path}")
    logging.info(f"Extracting page: {page_number}")

    try:
        with pikepdf.Pdf.open(input_pdf_path) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                logging.error(f"Invalid page number. PDF has {len(pdf.pages)} pages.")
                return

            # Create a new PDF with only the specified page
            new_pdf = pikepdf.Pdf.new()
            new_pdf.pages.append(pdf.pages[page_number - 1])

            # Save with compression
            new_pdf.save(output_pdf_path, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)

        logging.info(f"Compressed PDF saved: {output_pdf_path}")
        logging.info(f"Compressed PDF size: {os.path.getsize(output_pdf_path)} bytes")

    except Exception as e:
        logging.error(f"Error processing PDF: {str(e)}")

# Usage
input_pdf = r"C:\Users\Manvir\Downloads\Calculus_Volume_1_-_WEB_68M1Z5W.pdf"
page_to_extract = 7
output_pdf = r"C:\Users\Manvir\Downloads\output_compressed.pdf"

extract_and_compress_pdf_page(input_pdf, page_to_extract, output_pdf)