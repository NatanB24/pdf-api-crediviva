from flask import Flask, request, send_file, jsonify
import requests, os, re
from PIL import Image
from io import BytesIO
import fitz  # PyMuPDF

app = Flask(__name__)

@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    try:
        pdf_url = request.json.get("pdf_url")
        qr_url = request.json.get("qr_url")

        if not pdf_url or not qr_url:
            return jsonify({"error": "Missing pdf_url or qr_url"}), 400

        output_dir = "/tmp"
        qr_filename = os.path.basename(qr_url.split('?')[0])
        clean_name = re.sub(r'(?i)^qr[-_ ]*', '', qr_filename).replace('.png', '')

        pdf_path = os.path.join(output_dir, "template.pdf")
        qr_path = os.path.join(output_dir, "qr.png")
        output_pdf_path = os.path.join(output_dir, f"Kit de Bienvenida - {clean_name}.pdf")

        headers = {'User-Agent': 'Mozilla/5.0'}

        # Download PDF
        r = requests.get(pdf_url, headers=headers)
        with open(pdf_path, 'wb') as f:
            f.write(r.content)

        # Download QR
        r = requests.get(qr_url, headers=headers)
        image = Image.open(BytesIO(r.content))
        qr_temp_path = os.path.join(output_dir, "qr_temp.png")
        image.save(qr_temp_path)

        # Modify PDF
        doc = fitz.open(pdf_path)
        inserted = False

        for page in doc:
            text_instances = page.search_for("{{ QR_CODE }}")
            for inst in text_instances:
                # Center of the detected placeholder text
                center_x = (inst.x0 + inst.x1) / 2
                center_y = (inst.y0 + inst.y1) / 2

                # Define a square region around the center
                size = max(inst.width, inst.height) * 2.0  # adjust multiplier if needed
                square_rect = fitz.Rect(
                    center_x - size / 2,
                    center_y - size / 2,
                    center_x + size / 2,
                    center_y + size / 2
                )

                page.insert_image(square_rect, filename=qr_temp_path)
                inserted = True

        if not inserted:
            return jsonify({"error": "QR_CODE placeholder not found in PDF"}), 400

        doc.save(output_pdf_path)
        doc.close()

        return send_file(output_pdf_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "✅ Crediviva PDF QR API is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
