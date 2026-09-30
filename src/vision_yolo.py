import os
import time
import logging
from typing import List, Optional
from pydantic import BaseModel

from .models import EvidenceState
from .vision import VisionProvider, VisionResult, VisionObservation

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logger = logging.getLogger("returns_manager.yolo")

class YOLODetectionProvider:
    def __init__(self):
        self.model_path = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
        self.confidence_threshold = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.25"))
        self.iou_threshold = float(os.getenv("YOLO_IOU_THRESHOLD", "0.45"))
        self.model = None
        self._loaded = False
        
    def _load_model(self):
        if not self._loaded:
            if YOLO is None:
                logger.warning("ultralytics not installed. YOLO inference will be skipped.")
                return
            try:
                # Load the model with CPU inference explicitly
                self.model = YOLO(self.model_path)
                self._loaded = True
                logger.info(f"YOLO model {self.model_path} loaded successfully for CPU execution")
            except Exception as e:
                logger.error(f"Failed to load YOLO model: {e}")
                
    def detect(self, images: List, img_refs: List[str]) -> List[VisionObservation]:
        """
        Runs YOLO detection on list of PIL Images or local paths.
        img_refs is used for the resulting evidence string reference.
        Returns generic observations.
        """
        self._load_model()
        if not self.model:
            logger.warning("YOLO model not loaded. Returning empty detections.")
            return []
            
        observations = []
        start_time = time.time()
        
        try:
            results = self.model(images, conf=self.confidence_threshold, iou=self.iou_threshold, device='cpu', verbose=False)
            
            for i, result in enumerate(results):
                img_ref = img_refs[i]
                if len(result.boxes) == 0:
                     # Wait! Missed detection doesn't mean MISSING.
                     # We just don't add OBSERVED if there's no box.
                     pass 
                else:
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        class_name = self.model.names[class_id]
                        conf = float(box.conf[0])
                        
                        bbox = box.xyxy[0].tolist() # [x1, y1, x2, y2]
                        
                        observations.append(VisionObservation(
                            observation_type="detection",
                            object_name=class_name,
                            state=EvidenceState.OBSERVED,
                            confidence=conf,
                            evidence_desc=f"YOLO detected '{class_name}' with {conf:.2f} confidence at {bbox}",
                            image_reference=img_ref
                        ))
                        
        except Exception as e:
            logger.error(f"YOLO inference error: {e}")
            
        latency = int((time.time() - start_time) * 1000)
        logger.info(f"YOLO detection latency: {latency}ms")
        
        return observations
