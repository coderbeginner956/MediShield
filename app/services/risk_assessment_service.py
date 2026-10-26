from typing import Dict, Any, List, Optional

def compute_multi_factor_risk(
    model_prediction: Optional[Dict[str, Any]],
    comparison_result: Optional[Dict[str, Any]],
    ocr_result: Optional[Dict[str, Any]],
    verification_result: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Transparent, rule-based risk assessment synthesizing multi-modal evidence.
    Returns: risk_level ('low', 'medium', 'high', 'insufficient_evidence'),
             risk_score (0.0 to 100.0 or None),
             risk_summary,
             reason_codes.
    """
    reason_codes: List[str] = []
    points = 0
    evidence_count = 0

    # 1. Active Recall Check (Critical High Risk)
    if verification_result:
        evidence_count += 1
        if verification_result.get("recall_status") == "active_recall_flagged":
            points += 50
            reason_codes.append("RC_ACTIVE_PRODUCT_RECALL")

        if verification_result.get("product_match_status") == "mismatch":
            points += 25
            reason_codes.append("RC_MANUFACTURER_OR_PRODUCT_MISMATCH")

        if verification_result.get("batch_match_status") == "mismatch":
            points += 20
            reason_codes.append("RC_BATCH_DATABASE_MISMATCH")

        if verification_result.get("expiry_match_status") == "expired":
            points += 30
            reason_codes.append("RC_BATCH_RECORD_EXPIRED")

    # 2. OCR and Label Inconsistencies
    if ocr_result:
        evidence_count += 1
        label_flags = ocr_result.get("label_flags", [])
        if "FLAG_EXPIRED_DATE" in label_flags:
            points += 30
            reason_codes.append("RC_LABEL_EXPIRED")
        if "FLAG_UNREADABLE_EXPIRY" in label_flags:
            points += 15
            reason_codes.append("RC_UNREADABLE_EXPIRY_INFO")
        if "FLAG_MISSING_BATCH" in label_flags:
            points += 15
            reason_codes.append("RC_MISSING_BATCH_IDENTIFIER")
        if "FLAG_SUSPICIOUS_MANUFACTURER_TYPO" in label_flags:
            points += 25
            reason_codes.append("RC_SUSPICIOUS_BRAND_TYPOGRAPHY")

    # 3. AI Visual Screening Result
    if model_prediction:
        evidence_count += 1
        pred_class = model_prediction.get("predicted_class", "")
        if "anomaly flagged" in pred_class.lower():
            points += 25
            reason_codes.append("RC_VISUAL_ANOMALY_FLAGGED")
        elif "unable to analyze" in pred_class.lower() or "unavailable" in pred_class.lower():
            reason_codes.append("RC_MODEL_UNAVAILABLE_OR_INCONCLUSIVE")

    # 4. Genuine Reference Comparison
    if comparison_result and comparison_result.get("comparison_possible"):
        evidence_count += 1
        score = comparison_result.get("similarity_score")
        if score is not None:
            if score < 0.40:
                points += 25
                reason_codes.append("RC_LOW_REFERENCE_SIMILARITY")
            elif score < 0.65:
                points += 10
                reason_codes.append("RC_MODERATE_REFERENCE_VARIANCE")

    # Check for Insufficient Evidence
    if evidence_count == 0 or (evidence_count == 1 and not points and "RC_MODEL_UNAVAILABLE_OR_INCONCLUSIVE" in reason_codes):
        return {
            "risk_level": "insufficient_evidence",
            "risk_score": None,
            "risk_summary": "Insufficient data available to compute a risk assessment. Please upload packaging imagery, perform label inspection, or link database records.",
            "reason_codes": ["RC_INSUFFICIENT_EVIDENCE"]
        }

    # Calculate bounded score (0 to 100)
    risk_score = float(min(100.0, max(0.0, points)))

    if risk_score >= 50.0:
        risk_level = "high"
        risk_summary = f"High screening risk flagged ({int(risk_score)}/100). Critical inconsistencies detected across multiple checks ({', '.join(reason_codes)}). Escalation to an authorized reviewer is strongly recommended."
    elif risk_score >= 20.0:
        risk_level = "medium"
        risk_summary = f"Moderate screening risk identified ({int(risk_score)}/100). Secondary discrepancies noted ({', '.join(reason_codes)}). Visual re-inspection recommended."
    else:
        risk_level = "low"
        risk_summary = f"Low screening risk observed ({int(risk_score)}/100). Available evidence shows no active recalls, valid date typography, and structural alignment with recorded standards. (Note: Screening aid only; does not guarantee physical authenticity)."

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_summary": risk_summary,
        "reason_codes": reason_codes
    }

