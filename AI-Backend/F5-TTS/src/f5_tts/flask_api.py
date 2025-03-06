from flask import Flask, request, send_file, jsonify
from flask_cors import CORS  # Add this import
import os
from werkzeug.utils import secure_filename
from f5_tts.api import F5TTS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['UPLOAD_FOLDER'] = 'AI-Backend/F5-TTS/tests/output'
app.config['OUTPUT_FOLDER'] = 'AI-Backend/F5-TTS/tests/upload'

# Ensure the folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

f5tts = F5TTS()

@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "F5-TTS Flask API"})

@app.route('/generate', methods=['POST'])
def generate():
    if 'ref_file' not in request.files:
        return jsonify({"error": "No ref_file part"}), 400

    ref_file = request.files['ref_file']
    ref_text = request.form.get('ref_text')
    gen_text = request.form.get('gen_text')

    if ref_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if ref_file and ref_text and gen_text:
        filename = secure_filename(ref_file.filename)
        ref_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        ref_file.save(ref_file_path)

        output_wave_path = os.path.join(app.config['OUTPUT_FOLDER'], 'output.wav')
        output_spect_path = os.path.join(app.config['OUTPUT_FOLDER'], 'output.png')

        wav, sr, spect = f5tts.infer(
            ref_file=ref_file_path,
            ref_text=ref_text,
            gen_text=gen_text,
            file_wave=output_wave_path,
            file_spect=output_spect_path,
            seed=-1,  # random seed = -1
        )

        return send_file(output_wave_path, as_attachment=True)

    return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    app.run(debug=True)