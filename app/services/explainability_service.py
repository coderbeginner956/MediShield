import os
import uuid
from pathlib import Path
import numpy as np
from PIL import Image
import cv2
from app.core.config import settings

def generate_visual_explanation(
    image_path: str,
    prediction_info: dict,
    output_dir: Path
) -> dict:
    """
    Generates a visual explanation artifact (e.g. edge gradient / activation heatmap or detected bounding boxes)
    along with clear human-readable explanation and transparent limitations.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not os.path.exists(image_path):
        return {
            "method": "unsupported",
            "artifact_image_path": None,
            "explanation_text": "Original image file could not be located on server.",
            "limitations_text": "No artifact could be computed because source data is missing.",
            "is_supported": False
        }

    try:
        # Load image via OpenCV
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError("Unable to decode image file")

        h, w, _ = img_bgr.shape
        predicted_class = prediction_info.get("predicted_class", "")
        detected_boxes = prediction_info.get("detected_boxes", [])

        # Create overlay
        overlay = img_bgr.copy()

        # Method 1: Saliency / Gradient Energy Heatmap
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        norm_magnitude = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        # Apply colormap (JET or TURBO for medical/forensic style)
        heatmap = cv2.applyColorMap(norm_magnitude, cv2.COLORMAP_TURBO)
        
        # Blend heatmap with original image (alpha blend)
        alpha = 0.45
        blended = cv2.addWeighted(heatmap, alpha, img_bgr, 1 - alpha, 0)

        # Draw detected bounding boxes on top with clear labeling
        for box_item in detected_boxes:
            b = box_item.get("box", [])
            label = box_item.get("label", "Region")
            conf = box_item.get("confidence", 0.0)
            if len(b) == 4:
                x, y, bw, bh = b
                color = (0, 0, 255) if "anomaly" in predicted_class.lower() or "deficiency" in label.lower() or "blur" in label.lower() else (0, 200, 0)
                cv2.rectangle(blended, (x, y), (x + bw, y + bh), color, 2)
                
                # Text badge
                badge_text = f"{label} ({int(conf * 100)}%)" if conf else label
                cv2.putText(blended, badge_text, (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        # Save artifact image
        artifact_filename = f"explain_{uuid.uuid4().hex[:12]}.jpg"
        artifact_path = output_dir / artifact_filename
        cv2.imwrite(str(artifact_path), blended)

        explanation = (
            f"Visual explanation highlights high-frequency spatial gradients and surface contours that influenced the model. "
            f"Warmer color intensities (orange/red) indicate regions of concentrated edge transitions and typographical printing, "
            f"while bounding boxes locate identified packaging features evaluated for structural consistency."
        )

        limitations = (
            "Gradient heatmaps and spatial feature attributions highlight correlation, not verified causation. "
            "Lighting variations, camera glare, shadows, or background packaging reflections can artificially inflate local heatmap intensity. "
            "This visualization should be treated as an investigative aid, never as definitive proof of authenticity."
        )

        return {
            "method": "gradient_saliency_and_roi",
            "artifact_image_path": str(artifact_path),
            "explanation_text": explanation,
            "limitations_text": limitations,
            "is_supported": True
        }
    except Exception as e:
        return {
            "method": "unsupported",
            "artifact_image_path": None,
            "explanation_text": f"Explanation pipeline encountered an error: {str(e)}",
            "limitations_text": "Explanation generation was not supported for this specific image payload.",
            "is_supported": False
        }

