from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.product import Product, ProductBatch
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductBatchCreate,
    ProductBatchResponse
)
from app.services.audit_service import log_audit_event

router = APIRouter(tags=["Products & Batches"])

# =========================================================================
# Products Endpoints
# =========================================================================
@router.get("/products", response_model=List[ProductResponse])
def list_products(
    search: Optional[str] = None,
    record_status: Optional[str] = None,
    include_demo: bool = True,
    db: Session = Depends(get_db)
):
    """Retrieves all registered pharmaceutical products with optional filtering."""
    query = db.query(Product)
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.brand_or_manufacturer.ilike(f"%{search}%")) |
            (Product.product_identifier.ilike(f"%{search}%"))
        )
    if record_status:
        query = query.filter(Product.record_status == record_status)
    if not include_demo:
        query = query.filter(Product.is_demo == False)

    return query.order_by(Product.name.asc()).all()

@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    prod_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "reviewer"]))
):
    """Registers a new pharmaceutical product in the verified registry."""
    if prod_in.product_identifier:
        existing = db.query(Product).filter(Product.product_identifier == prod_in.product_identifier).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with identifier '{prod_in.product_identifier}' already exists."
            )

    product = Product(
        name=prod_in.name,
        brand_or_manufacturer=prod_in.brand_or_manufacturer,
        dosage_form=prod_in.dosage_form,
        packaging_type=prod_in.packaging_type,
        product_identifier=prod_in.product_identifier,
        description=prod_in.description,
        record_status=prod_in.record_status or "active",
        notes=prod_in.notes,
        is_demo=False
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    log_audit_event(
        db=db,
        action="PRODUCT_REGISTERED",
        target_type="product",
        target_id=str(product.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details={"name": product.name, "mfr": product.brand_or_manufacturer}
    )

    return product

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieves product details including its associated batches."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product

@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    prod_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "reviewer"]))
):
    """Updates product attributes and record status."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    update_data = prod_update.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(product, key, val)

    db.commit()
    db.refresh(product)

    log_audit_event(
        db=db,
        action="PRODUCT_UPDATED",
        target_type="product",
        target_id=str(product.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details=update_data
    )

    return product

# =========================================================================
# Batches Endpoints
# =========================================================================
@router.get("/batches", response_model=List[ProductBatchResponse])
def list_batches(
    product_id: Optional[int] = None,
    search: Optional[str] = None,
    include_demo: bool = True,
    db: Session = Depends(get_db)
):
    """Retrieves registered product batches."""
    query = db.query(ProductBatch)
    if product_id:
        query = query.filter(ProductBatch.product_id == product_id)
    if search:
        query = query.filter(ProductBatch.batch_number.ilike(f"%{search}%"))
    if not include_demo:
        query = query.filter(ProductBatch.is_demo == False)

    return query.order_by(ProductBatch.created_at.desc()).all()

@router.post("/batches", response_model=ProductBatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    product_id: int,
    batch_in: ProductBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "reviewer"]))
):
    """Adds a new manufactured batch to a registered product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    existing_batch = db.query(ProductBatch).filter(
        ProductBatch.product_id == product_id,
        ProductBatch.batch_number.ilike(batch_in.batch_number.strip())
    ).first()
    if existing_batch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch '{batch_in.batch_number}' is already registered for this product."
        )

    batch = ProductBatch(
        product_id=product_id,
        batch_number=batch_in.batch_number.strip().upper(),
        manufacturer=batch_in.manufacturer or product.brand_or_manufacturer,
        manufacturing_date=batch_in.manufacturing_date,
        expiry_date=batch_in.expiry_date,
        reference_source=batch_in.reference_source or "Internal Registry",
        verification_notes=batch_in.verification_notes,
        is_demo=False
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    log_audit_event(
        db=db,
        action="BATCH_REGISTERED",
        target_type="batch",
        target_id=str(batch.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details={"batch_number": batch.batch_number, "product_id": product_id}
    )

    return batch

@router.get("/batches/{batch_id}", response_model=ProductBatchResponse)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    """Retrieves batch details."""
    batch = db.query(ProductBatch).filter(ProductBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    return batch

