# PII Redaction Tool

A Python tool that reads a `.docx` file containing personally identifiable information (PII), replaces every sensitive value with a realistic fake alternative, and saves the result as a clean Word document — preserving all formatting, structure, and non-sensitive content throughout.

Built as part of the **Scaler AI Labs Round 2 Assessment**, using a real-world legal document (Red Herring Prospectus — KSH International Limited) as the test case.

---

## Results at a Glance

**Full-document test** (all PII extracted from original, verified against redacted output):

| Category | Found in Original | Redacted | Status |
|---|---|---|---|
| Email addresses | 26 | 26 / 26 | ✅ 100% |
| Phone numbers | 15 | 15 / 15 | ✅ 100% |
| Contact-person names | 16 | 16 / 16 | ✅ 100% |
| **Total** | **57** | **57 / 57** | ✅ **100%** |

**Evaluation on 30 hand-labelled sentences:**

| Metric | Score |
|---|---|
| Precision | 95.56% |
| Recall | **100.00%** |
| F1 Score | **97.73%** |

The 4.44% precision gap is from spaCy occasionally flagging generic financial phrases (e.g., "Mutual Funds") as organisation names — documented in the Error Analysis section of `Evaluation_Report.docx`.

---

## How It Works

The script runs two detection layers, then applies a fallback:

**Layer 1 — spaCy NER (runs first)**  
The `en_core_web_lg` model reads each paragraph and identifies `PERSON` and `ORG` entities using contextual language understanding. Running NER first — before any text has been touched — keeps the model's context window intact, which significantly improves name detection accuracy.

**Layer 2 — Regex (structured PII)**  
After NER, deterministic patterns handle PII with predictable formats: email addresses, Indian phone numbers (`+91` and STD landline formats), PAN card numbers, IP addresses, US-style SSNs, and date-of-birth patterns.

**Fallback — keyword-context extractor**  
For person names that NER misses in dense legal prose, a targeted regex catches names that appear directly after role labels like `Contact Person:`, `Compliance Officer:`, or `Company Secretary:`. This also handles slash-separated lists — e.g., `"Lokesh Shah / Soumavo Sarkar"` — which are common in Indian IPO documents.

**Consistent replacements throughout**  
A registry maps every unique real value to exactly one fake value. If `Sarthak Malvadkar` appears 12 times, it becomes the same fake name each time — keeping the redacted document internally coherent and readable.

---

## What Gets Redacted

| PII Type | Detection Method | Example |
|---|---|---|
| Full names | spaCy NER + keyword fallback | `Lokesh Shah` → `Rajesh Mehta` |
| Email addresses | Regex | `sarthak@ksh.com` → `rjmehta@fakecorp.in` |
| Phone numbers | Regex | `+91 22 40094400` → `+91 9823401782` |
| Organisation contacts | spaCy NER | `Nuvama Wealth Management` → `Tata Corp Ltd` |
| PAN card numbers | Regex | `ABCDE1234F` → `XYZPQ5678R` |
| IP addresses | Regex | `192.168.1.1` → `10.0.4.22` |
| SSNs | Regex | `123-45-6789` → `987-65-4321` |
| Dates of birth | Regex (context-scoped) | `DOB: 14/08/1985` → `DOB: 22/03/1971` |

**Deliberately not redacted:**  
Financial reporting dates (Q1 FY2025, March 31, etc.), regulatory acronyms (SEBI, RBI, NSE, NSDL), jurisdiction names (Maharashtra, Mumbai), and standard legal/financial terms — these are business content, not personal data.

---

## Setup & Usage

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg

python pii_redactor.py
```

Output: `Red_Herring_Prospectus_REDACTED.docx`

---

## Running the Tests

```bash
# Quick sanity check — 25 key PII targets + non-PII preservation
python run_tests.py

# Full data-driven test — extracts all PII from original, verifies nothing survives
python comprehensive_test.py

# Formal evaluation — precision / recall / F1 on 30 hand-labelled sentences
python evaluate_pii.py

# Regenerate the evaluation report .docx
python generate_report.py
```

---

## Project Structure

```
pii_redactor.py                       ← Main redaction script
evaluate_pii.py                       ← Precision / recall evaluation on labelled samples
comprehensive_test.py                 ← Data-driven audit against the full document
run_tests.py                          ← Quick sanity checks (PII gone + non-PII intact)
generate_report.py                    ← Generates Evaluation_Report.docx
requirements.txt                      ← Python dependencies
README.md                             ← This file
Red_Herring_Prospectus_REDACTED.docx  ← Redacted output (submitted)
Evaluation_Report.docx                ← Formal evaluation report (submitted)
```

---

## Tradeoffs & Known Gaps

**False positives (over-redaction)**  
spaCy's `ORG` entity can fire on common financial phrases like "Mutual Funds" or "Life Insurance". A whitelist of ~20 regulatory and domain terms suppresses most of these. The list is easy to extend.

**Financial dates are untouched by design**  
Redacting every date in a 400-page prospectus would destroy its usefulness. Only birth-context patterns (`Date of Birth:`, `born on`) are targeted.

**DOCX run merging**  
Word internally splits paragraphs into multiple "runs" (each with its own bold/italic/font style). We merge all run text, redact the merged string, then write it back into the first run. This preserves formatting in the vast majority of cases but can flatten extremely granular per-word styling in edge cases.

---

## Extending with a New PII Type

The `_REGEX_RULES` list in `pii_redactor.py` is the only place to touch. Add a tuple:

```python
("aadhaar",
 re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"),
 lambda m: _memo(_reg.misc, m.group(), lambda _: "XXXX XXXX XXXX")),
```

That's all. The registry, stats counter, and document traversal are fully generic — they automatically pick up any new rule.
