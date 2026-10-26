import os
import uuid
from pathlib import Path
from PIL import Image
import io

def save_uploaded_image(file_bytes: bytes, target_dir: Path, prefix: str = "img") -> dict:
    """Safely decodes, validates and persists an image to storage."""
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate with PIL
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify() # Verify integrity
        
        # Re-open after verify
        img = Image.open(io.BytesIO(file_bytes))
        width, height = img.size
        fmt = (img.format or "JPEG").lower()
        if fmt not in ["jpeg", "jpg", "png", "webp"]:
            fmt = "jpeg"
        
        ext = "jpg" if fmt in ["jpeg", "jpg"] else fmt
        filename = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
        filepath = target_dir / filename
        
        # Save image in standard RGB mode if saving as JPEG
        if fmt in ["jpeg", "jpg"] and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.save(str(filepath), quality=95)
        
        # Save thumbnail
        thumb = img.copy()
        thumb.thumbnail((250, 250))
        thumb_filename = f"thumb_{filename}"
        thumb_path = target_dir / thumb_filename
        thumb.save(str(thumb_path))

        return {
            "filepath": str(filepath),
            "filename": filename,
            "width": width,
            "height": height,
            "size_bytes": len(file_bytes),
            "mime_type": f"image/{fmt}"
        }
    except Exception as e:
        raise ValueError(f"Invalid or corrupted image format: {str(e)}")

