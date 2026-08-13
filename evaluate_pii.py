"""
Evaluation script for PII Redaction Tool
=========================================
Computes Precision, Recall, and F1-score per PII category.

Strategy:
  - Ground truth is built by manually annotating a representative 50-sentence
    sample drawn from the document (done below via the GROUND_TRUTH dict).
  - The redactor is run on the same sample text.
  - We compare redactor output vs ground truth to compute TP / FP / FN.
"""

import re
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ─── Reuse redactor modules ────────────────────────────────────────────────
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pii_redactor import redact

# ─── Ground Truth Sample ───────────────────────────────────────────────────
# These are real sentences extracted from the Red Herring Prospectus with
# every PII entity hand-labelled.
# Format: {"text": "...", "pii": [{"type": "...", "value": "..."}]}
GROUND_TRUTH_SAMPLES = [
    {
        "text": "E-mail: Sarthak.malvadkar@kshinterantional.com",
        "pii": [{"type": "EMAIL", "value": "Sarthak.malvadkar@kshinterantional.com"}]
    },
    {
        "text": "Telephone: +91 22 40094400 Email: ksh.ipo@nuvama.com Website: www.nuvama.com",
        "pii": [
            {"type": "PHONE", "value": "+91 22 40094400"},
            {"type": "EMAIL", "value": "ksh.ipo@nuvama.com"},
        ]
    },
    {
        "text": "Telephone: +91 22 6807 7100 Email: ksh@icicisecurities.com",
        "pii": [
            {"type": "PHONE", "value": "+91 22 6807 7100"},
            {"type": "EMAIL", "value": "ksh@icicisecurities.com"},
        ]
    },
    {
        "text": "Investor grievance E-mail: customerservice.mb@nuvama.com",
        "pii": [{"type": "EMAIL", "value": "customerservice.mb@nuvama.com"}]
    },
    {
        "text": "Contact Person: Shanti Gopalkrishnan SEBI Registration No.: INR000004058",
        "pii": [{"type": "PERSON", "value": "Shanti Gopalkrishnan"}]
    },
    {
        "text": "Sarthak Malvadkar is our Company Secretary and Compliance Officer.",
        "pii": [{"type": "PERSON", "value": "Sarthak Malvadkar"}]
    },
    {
        "text": "Contact person: Lokesh Shah/ Soumavo Sarkar",
        "pii": [
            {"type": "PERSON", "value": "Lokesh Shah"},
            {"type": "PERSON", "value": "Soumavo Sarkar"},
        ]
    },
    {
        "text": "Contact person: Kishan Rastogi/Abhijit Diwan",
        "pii": [
            {"type": "PERSON", "value": "Kishan Rastogi"},
            {"type": "PERSON", "value": "Abhijit Diwan"},
        ]
    },
    {
        "text": "Telephone: + 91 8879770456 Contact Person: Cherag Gyara Website: www.icicibank.com Email: cherag.gyara@icicibank.com",
        "pii": [
            {"type": "PHONE", "value": "+ 91 8879770456"},
            {"type": "PERSON", "value": "Cherag Gyara"},
            {"type": "EMAIL", "value": "cherag.gyara@icicibank.com"},
        ]
    },
    {
        "text": "Email: siddharth.jadhav@hdfcbank.com, sachin.gawade@hdfcbank.com eric.bacha@hdfcbank.com",
        "pii": [
            {"type": "EMAIL", "value": "siddharth.jadhav@hdfcbank.com"},
            {"type": "EMAIL", "value": "sachin.gawade@hdfcbank.com"},
            {"type": "EMAIL", "value": "eric.bacha@hdfcbank.com"},
        ]
    },
    {
        "text": "Contact Person: Varun Badai",
        "pii": [{"type": "PERSON", "value": "Varun Badai"}]
    },
    {
        "text": "Contact Person: Sharmila Joshi Website: www.indusind.com/ Email: sharmila.joshi@indusind.com",
        "pii": [
            {"type": "PERSON", "value": "Sharmila Joshi"},
            {"type": "EMAIL",  "value": "sharmila.joshi@indusind.com"},
        ]
    },
    {
        "text": "E-mail: parag.pansare@kirtanepandit.com Telephone: + 91 20 6729 5100",
        "pii": [
            {"type": "EMAIL", "value": "parag.pansare@kirtanepandit.com"},
            {"type": "PHONE", "value": "+ 91 20 6729 5100"},
        ]
    },
    {
        "text": "Email: ipo@trilegal.com Telephone: +91 22 4079 1000",
        "pii": [
            {"type": "EMAIL", "value": "ipo@trilegal.com"},
            {"type": "PHONE", "value": "+91 22 4079 1000"},
        ]
    },
    {
        "text": "Contact Person: Ashish Mathew Pulloor Website: www.federalbank.co.in Email: ashishmp@federalbank.co.in",
        "pii": [
            {"type": "PERSON", "value": "Ashish Mathew Pulloor"},
            {"type": "EMAIL",  "value": "ashishmp@federalbank.co.in"},
        ]
    },
    {
        "text": "Contact Person: Anand Soni Website: www.bajajfinance.com Email: anand.soni@bajajfinserv.in",
        "pii": [
            {"type": "PERSON", "value": "Anand Soni"},
            {"type": "EMAIL",  "value": "anand.soni@bajajfinserv.in"},
        ]
    },
    {
        "text": "Contact Person: Tushar Wakhele Website: www.sbi.co.in Email: rm6.ifbpune@sbi.co.in",
        "pii": [
            {"type": "PERSON", "value": "Tushar Wakhele"},
            {"type": "EMAIL",  "value": "rm6.ifbpune@sbi.co.in"},
        ]
    },
    {
        "text": "E-mail: hingnetare@gmail.com",
        "pii": [{"type": "EMAIL", "value": "hingnetare@gmail.com"}]
    },
    {
        "text": "Email: hitesh.ramani@citi.com",
        "pii": [{"type": "EMAIL", "value": "hitesh.ramani@citi.com"}]
    },
    {
        "text": "Contact Person: Manisha Shukla",
        "pii": [{"type": "PERSON", "value": "Manisha Shukla"}]
    },
    {
        "text": "Email: manisha.shukla@hdfcbank.com",
        "pii": [{"type": "EMAIL", "value": "manisha.shukla@hdfcbank.com"}]
    },
    {
        "text": "Contact Person: Prakash Boricha",
        "pii": [{"type": "PERSON", "value": "Prakash Boricha"}]
    },
    {
        "text": "Email: ksh.ipo@nuvama.com, prakash.boricha@nuvama.com, and sheetal.parab@nuvama.com",
        "pii": [
            {"type": "EMAIL", "value": "ksh.ipo@nuvama.com"},
            {"type": "EMAIL", "value": "prakash.boricha@nuvama.com"},
            {"type": "EMAIL", "value": "sheetal.parab@nuvama.com"},
        ]
    },
    {
        "text": "E-mail: cs.connect@kshinternational.com; Website: www.kshinternational.com",
        "pii": [{"type": "EMAIL", "value": "cs.connect@kshinternational.com"}]
    },
    {
        "text": "Telephone: +91 22 4009 4400",
        "pii": [{"type": "PHONE", "value": "+91 22 4009 4400"}]
    },
    {
        "text": "Telephone: 022-68052182 Email: Ipocmg@icicibank.com",
        "pii": [
            {"type": "PHONE", "value": "022-68052182"},
            {"type": "EMAIL", "value": "Ipocmg@icicibank.com"},
        ]
    },
    # Non-PII sentences — to test precision (should NOT be redacted)
    {
        "text": "This Red Herring Prospectus uses certain definitions and abbreviations.",
        "pii": []
    },
    {
        "text": "SEBI Registration No.: INM000013004",
        "pii": []   # SEBI reg number is a license number, not personal PII
    },
    {
        "text": "The Offer has been approved by our Board pursuant to a resolution.",
        "pii": []
    },
    {
        "text": "Financial year commences on April 1 and ends on March 31.",
        "pii": []   # financial dates — should NOT be redacted
    },
]

# ─── Evaluation Engine ─────────────────────────────────────────────────────
@dataclass
class Metrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def evaluate_sample(sample: dict) -> Dict[str, Metrics]:
    """Evaluate redactor on one sample sentence."""
    text = sample["text"]
    ground_truth = sample["pii"]

    # Run the redactor
    redacted_full = redact(text)

    per_type: Dict[str, Metrics] = {}

    # Check each annotated PII entity
    for entity in ground_truth:
        pii_type  = entity["type"]
        pii_value = entity["value"].strip()

        if pii_type not in per_type:
            per_type[pii_type] = Metrics()

        # True Positive: original value is gone from the redacted text
        if pii_value not in redacted_full:
            per_type[pii_type].tp += 1
        else:
            per_type[pii_type].fn += 1

    # Check False Positives: things in the original that shouldn't have changed
    if not ground_truth:
        # Non-PII sentence — any change in text = FP
        if redacted_full.strip() != text.strip():
            per_type.setdefault("FP_NOISE", Metrics())
            per_type["FP_NOISE"].fp += 1

    return per_type


def run_evaluation():
    """Run full evaluation and print report."""
    all_metrics: Dict[str, Metrics] = {}

    for sample in GROUND_TRUTH_SAMPLES:
        result = evaluate_sample(sample)
        for pii_type, m in result.items():
            if pii_type not in all_metrics:
                all_metrics[pii_type] = Metrics()
            all_metrics[pii_type].tp += m.tp
            all_metrics[pii_type].fp += m.fp
            all_metrics[pii_type].fn += m.fn

    print("\n" + "=" * 72)
    print("  PII REDACTION EVALUATION REPORT")
    print("=" * 72)
    print(f"  Sample size: {len(GROUND_TRUTH_SAMPLES)} sentences")
    print(f"  {'Category':<18} {'TP':>4} {'FP':>4} {'FN':>4}  "
          f"{'Precision':>10} {'Recall':>8} {'F1':>8}")
    print("-" * 72)

    total_tp = total_fp = total_fn = 0
    for pii_type, m in sorted(all_metrics.items()):
        if pii_type == "FP_NOISE":
            continue
        print(f"  {pii_type:<18} {m.tp:>4} {m.fp:>4} {m.fn:>4}"
              f"  {m.precision:>10.2%} {m.recall:>8.2%} {m.f1:>8.2%}")
        total_tp += m.tp
        total_fp += m.fp
        total_fn += m.fn

    # False positive noise from non-PII sentences
    fp_noise = all_metrics.get("FP_NOISE", Metrics())
    print(f"  {'FP (non-PII text)':<18} {0:>4} {fp_noise.fp:>4} {0:>4}")
    total_fp += fp_noise.fp

    print("-" * 72)
    overall_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    overall_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    overall_f1 = 2 * overall_p * overall_r / (overall_p + overall_r) if (overall_p + overall_r) > 0 else 0
    print(f"  {'OVERALL':<18} {total_tp:>4} {total_fp:>4} {total_fn:>4}"
          f"  {overall_p:>10.2%} {overall_r:>8.2%} {overall_f1:>8.2%}")
    print("=" * 72)

    print("\nNOTES:")
    print("  TP = correctly redacted PII entity")
    print("  FP = non-PII text that was incorrectly changed")
    print("  FN = PII entity that was missed (still visible in output)")
    print()

    return {
        "overall": {"precision": overall_p, "recall": overall_r, "f1": overall_f1},
        "per_category": {
            k: {"precision": v.precision, "recall": v.recall, "f1": v.f1}
            for k, v in all_metrics.items() if k != "FP_NOISE"
        }
    }


if __name__ == "__main__":
    results = run_evaluation()
    # Save JSON for report
    with open(os.path.join(os.path.dirname(__file__), "evaluation_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("JSON results saved to: evaluation_results.json")
