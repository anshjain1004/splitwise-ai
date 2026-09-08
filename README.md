# SplitWise AI — Photograph to Fair Bill

A compact AI Developer round project for splitting restaurant bills from photographs.

## Flow

1. Upload 1–2 bill photos.
2. Gemini vision extracts a structured bill into Pydantic models.
3. Every important field has a confidence score.
4. The user reviews/corrects the extraction before calculations.
5. Add 2–3 members and assign each item using portions.
6. Item totals are split according to portions.
7. Discount, service charge, CGST/SGST and other taxes are distributed in proportion to what each person actually ate.
8. The app validates the printed total against the mathematically calculated total.

## Tech

- FastAPI + Pydantic
- Google Gemini multimodal vision + structured JSON
- Vanilla HTML/CSS/JS frontend for a fast, dependency-light demo
- No database required for the challenge

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
# Add GEMINI_API_KEY to .env

uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

### Demo mode

Set `DEMO_MODE=true` if you want the full UI/calculation flow without an API key. Uploading a bill will use a realistic sample extraction so the app remains demoable.

## Test

```bash
pytest -q
```

## Design decisions

**AI does extraction, not arithmetic.** The model produces structured bill data, while the split engine is deterministic Python. This makes the financial calculation auditable.

**Human review comes before arithmetic.** Extracted values are editable and the split button is only enabled after review.

**Tax/service charge follows consumption.** A person who consumed 50% of the food gets 50% of the service charge and tax—not 1/number_of_people.

**Printed-total anomaly detection.** If subtotal + discount + charges does not match the printed total, the UI shows a warning rather than silently trusting OCR.

## Gemini implementation

The backend uses Gemini's multimodal input and structured-output/Pydantic support. The model is asked to return only the `Bill` schema; FastAPI then validates it again with Pydantic.

For the challenge's 12-bill test set, store ground truth separately and compare extracted fields before accepting results.
