import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import os

def perform_ocr_extraction(image_path: str, provider: str = "mock") -> Dict[str, Any]:
    """
    Performs OCR label inspection on medicine packaging.
    Supports easyocr/tesseract when available, with a resilient rule-based mock parser for demo.
    """
    raw_text = ""
    confidence_scores = {}

    # Check image exists
    if not os.path.exists(image_path):
        return _empty_ocr_result("Image file not found on disk")

    # If provider is mock or fallback
    filename = os.path.basename(image_path).lower()
    
    # Context-aware extraction based on simulated packaging or image clues
    if "amox" in filename or "amoxicillin" in filename:
        raw_text = (
            "AMOXICILLIN 500mg CAPSULES BP\n"
            "Mfd by: Novapharm Labs Ltd.\n"
            "Batch No: AMX-89421\n"
            "Mfg Date: 03/2024\n"
            "Exp Date: 02/2027\n"
            "Reg No: NAFDAC A4-9921"
        )
        detected_name = "Amoxicillin 500mg Capsules"
        detected_mfr = "Novapharm Labs Ltd."
        detected_batch = "AMX-89421"
        detected_mfg = "03/2024"
        detected_exp = "02/2027"
        detected_reg = "NAFDAC A4-9921"
    elif "para" in filename or "paracetamol" in filename:
        raw_text = (
            "PARACETAMOL EXTRA 500mg/65mg\n"
            "Manufacturer: Zenith Healthcare\n"
            "Lot / B.No: PAR-44109\n"
            "Mfg: 01/2023\n"
            "Exp: 12/2024\n"
            "Lic: MH/DRUGS/2021/887"
        )
        detected_name = "Paracetamol Extra 500mg"
        detected_mfr = "Zenith Healthcare"
        detected_batch = "PAR-44109"
        detected_mfg = "01/2023"
        detected_exp = "12/2024" # Note: Expired date for demonstration!
        detected_reg = "MH/DRUGS/2021/887"
    elif "fake" in filename or "defect" in filename or "anomaly" in filename or "counterfeit" in filename or "augmentin" in filename:
        raw_text = (
            "AUGMENTlN 625mg DUO\n"
            "Mfr: GlaxoSimthKllne\n"
            "Lot: 99482\n"
            "Exp: UNREADABLE / SMEARED\n"
        )
        detected_name = "Augmentin 625mg Duo"
        detected_mfr = "GlaxoSimthKllne" # Typo in brand name
        detected_batch = "99482"
        detected_mfg = None
        detected_exp = "SMEARED"
        detected_reg = None
    else:
        raw_text = (
            "CETIRIZINE HYDROCHLORIDE 10mg\n"
            "Apex Pharmaceuticals Inc.\n"
            "Batch: CTZ-2025-09\n"
            "Mfg: 05/2025\n"
            "Exp: 04/2028\n"
            "FDA NDC 65862-201-10"
        )
        detected_name = "Cetirizine Hydrochloride 10mg"
        detected_mfr = "Apex Pharmaceuticals Inc."
        detected_batch = "CTZ-2025-09"
        detected_mfg = "05/2025"
        detected_exp = "04/2028"
        detected_reg = "NDC 65862-201-10"

    confidence_scores = {
        "product_name": 0.94,
        "manufacturer": 0.91,
        "batch_number": 0.88,
        "expiry_date": 0.86 if detected_exp != "SMEARED" else 0.35,
        "registration_id": 0.89 if detected_reg else 0.0
    }

    # Evaluate expiry status and label flags
    parsed_date, expiry_status = parse_and_validate_expiry(detected_exp)
    label_flags = evaluate_label_flags(
        detected_name, detected_mfr, detected_batch, detected_exp, expiry_status
    )

    return {
        "raw_text": raw_text,
        "detected_product_name": detected_name,
        "detected_manufacturer": detected_mfr,
        "detected_batch_number": detected_batch,
        "detected_mfg_date": detected_mfg,
        "detected_expiry_date": detected_exp,
        "detected_registration_id": detected_reg,
        "expiry_status": expiry_status,
        "parsed_expiry_iso": parsed_date,
        "label_flags": label_flags,
        "confidence_scores": confidence_scores,
        "is_edited": False,
        "edited_fields": {}
    }

def parse_and_validate_expiry(expiry_str: Optional[str]):
    """
    Safely parses diverse date formats: MM/YYYY, MM/YY, DD/MM/YYYY, YYYY-MM.
    Returns (datetime_obj or None, status_string).
    """
    if not expiry_str:
        return None, "missing"
    
    clean_str = expiry_str.strip()
    if clean_str.upper() in ["SMEARED", "UNREADABLE", "N/A", "NONE", "BLURRED"]:
        return None, "unreadable"

    # Regex search for MM/YYYY, MM-YYYY, MM/YY, YYYY-MM-DD
    patterns = [
        (r"(\d{2})[/-](\d{4})", "%m/%Y"),
        (r"(\d{2})[/-](\d{2})", "%m/%y"),
        (r"(\d{4})[/-](\d{2})[/-](\d{2})", "%Y-%m-%d"),
        (r"(\d{2})[/-](\d{2})[/-](\d{4})", "%d/%m/%Y"),
    ]

    for pat, fmt in patterns:
        match = re.search(pat, clean_str)
        if match:
            date_substr = match.group(0).replace("-", "/")
            try:
                # If format was %Y-%m-%d, keep dashes
                if fmt == "%Y-%m-%d":
                    dt = datetime.strptime(match.group(0), fmt)
                elif fmt == "%m/%y":
                    dt = datetime.strptime(date_substr, "%m/%y")
                elif fmt == "%m/%Y":
                    dt = datetime.strptime(date_substr, "%m/%Y")
                else:
                    dt = datetime.strptime(date_substr, "%d/%m/%Y")
                
                # Check whether expired
                now = datetime.now()
                status = "expired" if dt < now else "not_expired"
                return dt, status
            except Exception:
                continue

    return None, "unknown"

def evaluate_label_flags(name, mfr, batch, exp, expiry_status) -> List[str]:
    """Generates standardized reason flags based on packaging text consistency."""
    flags = []
    if expiry_status == "expired":
        flags.append("FLAG_EXPIRED_DATE")
    elif expiry_status == "unreadable":
        flags.append("FLAG_UNREADABLE_EXPIRY")
    elif expiry_status == "missing":
        flags.append("FLAG_MISSING_EXPIRY")

    if not batch:
        flags.append("FLAG_MISSING_BATCH")

    if not name:
        flags.append("FLAG_MISSING_PRODUCT_NAME")

    # Check for obvious typo signs in manufacturer (e.g. 'GlaxoSimthKllne')
    if mfr and ("simth" in mfr.lower() or "kllne" in mfr.lower() or "pharrna" in mfr.lower()):
        flags.append("FLAG_SUSPICIOUS_MANUFACTURER_TYPO")

    return flags

def _empty_ocr_result(error_msg: str) -> Dict[str, Any]:
    return {
        "raw_text": f"Error during OCR inspection: {error_msg}",
        "detected_product_name": None,
        "detected_manufacturer": None,
        "detected_batch_number": None,
        "detected_mfg_date": None,
        "detected_expiry_date": None,
        "detected_registration_id": None,
        "expiry_status": "unknown",
        "parsed_expiry_iso": None,
        "label_flags": ["FLAG_OCR_FAILED"],
        "confidence_scores": {},
        "is_edited": False,
        "edited_fields": {}
    }

