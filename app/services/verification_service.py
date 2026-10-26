from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.product import Product, ProductBatch
from app.models.recall import Recall

def verify_extracted_records(
    db: Session,
    product_name: Optional[str],
    manufacturer: Optional[str],
    batch_number: Optional[str],
    expiry_date: Optional[str],
    selected_product_id: Optional[int] = None,
    selected_batch_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Performs record verification by checking extracted or user-supplied details
    against the registered product database, batch ledger, and active recall database.
    """
    product_match_status = "not_found"
    batch_match_status = "not_found"
    expiry_match_status = "unknown"
    recall_status = "none"
    matched_product_id = None
    matched_batch_id = None
    summary_notes = []

    # 1. Product Lookup
    product = None
    if selected_product_id:
        product = db.query(Product).filter(Product.id == selected_product_id).first()
    elif product_name:
        # Flexible case-insensitive query
        product = db.query(Product).filter(Product.name.ilike(f"%{product_name.strip()}%")).first()

    if product:
        matched_product_id = product.id
        product_match_status = "matched"
        summary_notes.append(f"Product verified against local registry: '{product.name}' ({product.brand_or_manufacturer}).")
        
        # Check manufacturer consistency
        if manufacturer and manufacturer.lower() not in product.brand_or_manufacturer.lower():
            product_match_status = "mismatch"
            summary_notes.append(f"Manufacturer mismatch: Packaging specifies '{manufacturer}' but registry indicates '{product.brand_or_manufacturer}'.")
    else:
        product_match_status = "not_found"
        summary_notes.append(f"No matching product entry found in local registry for '{product_name or 'N/A'}'.")

    # 2. Batch Lookup
    batch = None
    if selected_batch_id:
        batch = db.query(ProductBatch).filter(ProductBatch.id == selected_batch_id).first()
    elif batch_number:
        clean_batch = batch_number.strip().upper()
        batch = db.query(ProductBatch).filter(ProductBatch.batch_number.ilike(clean_batch)).first()

    if batch:
        matched_batch_id = batch.id
        batch_match_status = "matched"
        summary_notes.append(f"Batch code '{batch.batch_number}' confirmed in registered batch ledger.")

        # Check if product and batch are linked
        if product and batch.product_id != product.id:
            batch_match_status = "mismatch"
            summary_notes.append(f"Cross-reference mismatch: Batch '{batch.batch_number}' is registered to product ID #{batch.product_id}, not #{product.id}.")

        # Check recorded expiry against current date
        if batch.expiry_date and batch.expiry_date < datetime.now():
            expiry_match_status = "expired"
            summary_notes.append(f"Batch expiry date ({batch.expiry_date.strftime('%Y-%m-%d')}) has lapsed.")
        else:
            expiry_match_status = "valid"
    else:
        if batch_number:
            batch_match_status = "not_found"
            summary_notes.append(f"Batch code '{batch_number}' not present in internal batch registry.")
        else:
            batch_match_status = "not_found"
            summary_notes.append("No batch code available to verify.")

    # 3. Active Recall Check
    # Check if this product or this batch is flagged in active recalls
    active_recalls = []
    if matched_batch_id:
        active_recalls = db.query(Recall).filter(
            Recall.batch_id == matched_batch_id,
            Recall.status == "active"
        ).all()

    if not active_recalls and matched_product_id:
        active_recalls = db.query(Recall).filter(
            Recall.product_id == matched_product_id,
            Recall.batch_id.is_(None), # Product-wide recall
            Recall.status == "active"
        ).all()

    if active_recalls:
        recall_status = "active_recall_flagged"
        recall_codes = [r.recall_code for r in active_recalls]
        summary_notes.append(f"ALERT: Active regulatory/manufacturer recall recorded: {', '.join(recall_codes)} ({active_recalls[0].title}).")

    summary_text = " | ".join(summary_notes)
    summary_text += " [DISCLAIMER: Database record consistency is an administrative indicator and does not prove physical chemical authenticity.]"

    return {
        "product_match_status": product_match_status,
        "batch_match_status": batch_match_status,
        "expiry_match_status": expiry_match_status,
        "recall_status": recall_status,
        "verification_source": "Local MediShield Registry & Recall Ledger",
        "summary_text": summary_text,
        "matched_product_id": matched_product_id,
        "matched_batch_id": matched_batch_id
    }

