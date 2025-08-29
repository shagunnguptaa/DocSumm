import io
import os
import re
from typing import List, Tuple

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from PIL import Image
import pytesseract
import PyPDF2

# Configure Tesseract executable on Windows if needed. You can change this path in README instructions.
# Example (uncomment and set if tesseract is not on PATH):
# pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "bmp", "tiff"}

app = Flask(__name__, static_folder="static", static_url_path="/static")


# ---------------------------
# Utility: file type handling
# ---------------------------

def allowed_file(filename: str) -> bool:
	return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def load_image(file_stream: io.BytesIO) -> Image.Image:
	image = Image.open(file_stream)
	# Convert to RGB for consistent OCR results
	if image.mode != "RGB":
		image = image.convert("RGB")
	return image


# ---------------------------------
# Text Extraction: PDF and Images
# ---------------------------------

def extract_text_from_pdf(file_stream: io.BytesIO) -> Tuple[str, List[Image.Image]]:
	"""Extract text from PDF using PyPDF2. If text is scarce, try to extract images for OCR.

	Returns (text, images_for_ocr)
	"""
	reader = PyPDF2.PdfReader(file_stream)
	text_parts: List[str] = []
	for page in reader.pages:
		try:
			page_text = page.extract_text() or ""
			if page_text.strip():
				text_parts.append(page_text)
		except Exception:
			# Skip problematic pages but continue
			continue

	combined_text = "\n".join(text_parts).strip()

	# Attempt to extract images embedded in the PDF (basic/common cases only)
	images: List[Image.Image] = []
	try:
		for page_index, page in enumerate(reader.pages):
			resources = page.get("/Resources") or {}
			xobject = None
			if "/XObject" in resources:
				xobject = resources["/XObject"]
			elif resources and hasattr(resources, "get"):
				xobject = resources.get("/XObject")
			if not xobject:
				continue

			xobject = xobject.get_object()
			for obj_name in xobject:
				obj = xobject[obj_name]
				subtype = obj.get("/Subtype")
				if subtype and subtype == "/Image":
					width = obj.get("/Width")
					height = obj.get("/Height")
					color_space = obj.get("/ColorSpace")
					filter_ = obj.get("/Filter")
					data = obj.get_data()

					try:
						if filter_ == "/DCTDecode":
							img = Image.open(io.BytesIO(data))
							images.append(img.convert("RGB"))
						elif filter_ == "/FlateDecode":
							mode = "RGB"
							if color_space == "/DeviceGray":
								mode = "L"
							img = Image.frombytes(mode, (width, height), data)
							images.append(img.convert("RGB"))
						elif filter_ == "/JPXDecode":
							img = Image.open(io.BytesIO(data))
							images.append(img.convert("RGB"))
					except Exception:
						# Ignore image parsing failures
						continue
	except Exception:
		# If any structure is unexpected, gracefully degrade
		pass

	return combined_text, images


def extract_text_from_image(file_stream: io.BytesIO) -> str:
	image = load_image(file_stream)
	# Basic pre-processing could be added here if needed (e.g., resize/threshold)
	ocr_text = pytesseract.image_to_string(image)
	return ocr_text or ""


# ---------------------------
# Summarization utilities
# ---------------------------
STOPWORDS = set(
	word.lower()
	for word in [
		"a","an","the","and","or","but","if","while","with","of","at","by","for","to","in","on","from","as","is","are","was","were","be","been","being","it","its","this","that","these","those","can","could","should","would","may","might","will","shall","do","does","did","doing","have","has","had","having","not","no","so","than","too","very","into","about","over","after","before","between","within"
	]
)


def split_into_sentences(text: str) -> List[str]:
	# Simple sentence splitter based on punctuation. Avoids external deps.
	sentences = re.split(r"(?<=[.!?])\s+", text.strip())
	return [s.strip() for s in sentences if s.strip()]


def tokenize_words(text: str) -> List[str]:
	return re.findall(r"[A-Za-z0-9']+", text.lower())


def score_sentences(sentences: List[str]) -> Tuple[List[float], List[str]]:
	# Frequency-based scoring
	all_words = tokenize_words(" ".join(sentences))
	freq: dict = {}
	for w in all_words:
		if w in STOPWORDS:
			continue
		freq[w] = freq.get(w, 0) + 1

	scores: List[float] = []
	for s in sentences:
		words = tokenize_words(s)
		score = sum(freq.get(w, 0) for w in words if w not in STOPWORDS)
		scores.append(score)
	return scores, sorted(freq, key=freq.get, reverse=True)


def summarize_text(text: str, length: str = "medium") -> dict:
	"""Return summary dict with 'summary', 'key_points', 'highlights'."""
	sentences = split_into_sentences(text)
	if not sentences:
		return {"summary": "", "key_points": [], "highlights": []}

	scores, keywords = score_sentences(sentences)

	length_map = {"short": 0.15, "medium": 0.25, "long": 0.4}
	fraction = length_map.get(length, 0.25)
	num_sentences = max(1, int(len(sentences) * fraction))

	# Rank by score but keep original order in final output
	indexed = list(enumerate(sentences))
	indexed_sorted = sorted(indexed, key=lambda x: scores[x[0]], reverse=True)[:num_sentences]
	selected_indices = sorted(i for i, _ in indexed_sorted)
	summary_sentences = [sentences[i] for i in selected_indices]

	# Key points: top N highest scoring sentences as bullets
	key_points = [s for _, s in sorted(indexed_sorted, key=lambda x: x[0])]

	# Highlights: top keywords (filter short tokens)
	highlights = [kw for kw in keywords if len(kw) > 3][:8]

	return {
		"summary": " ".join(summary_sentences),
		"key_points": key_points,
		"highlights": highlights,
	}


# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def root():
	return send_from_directory(app.static_folder, "index.html")


@app.post("/api/summarize")
def api_summarize():
	if "file" not in request.files:
		return jsonify({"error": "No file provided"}), 400
	file = request.files["file"]
	length = request.form.get("length", "medium")

	if file.filename == "":
		return jsonify({"error": "Empty filename"}), 400
	if not allowed_file(file.filename):
		return jsonify({"error": "Unsupported file type"}), 400

	filename = secure_filename(file.filename)
	extension = filename.rsplit(".", 1)[1].lower()

	try:
		buffer = io.BytesIO(file.read())
		buffer.seek(0)
		text_content = ""
		images_for_ocr: List[Image.Image] = []

		if extension == "pdf":
			text_content, images_for_ocr = extract_text_from_pdf(buffer)
			# If little to no text extracted, try OCR on images if any
			if (not text_content or len(text_content) < 50) and images_for_ocr:
				ocr_texts = []
				for img in images_for_ocr:
					try:
						ocr_texts.append(pytesseract.image_to_string(img))
					except Exception:
						continue
				text_content = (text_content + "\n" + "\n".join(ocr_texts)).strip()
		elif extension in {"png", "jpg", "jpeg", "bmp", "tiff"}:
			text_content = extract_text_from_image(buffer)

		txt = re.sub(r"\s+", " ", (text_content or "")).strip()
		if not txt:
			return jsonify({"error": "Could not extract text from the document."}), 422

		result = summarize_text(txt, length)
		return jsonify(result)
	except Exception as e:
		return jsonify({"error": f"Processing failed: {e}"}), 500


if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5000))
	app.run(host="0.0.0.0", port=port, debug=True)
