# -*- coding: utf-8 -*-
"""
Face Detection Module
Gesichtserkennung für Ryx (User-Präsenz, Identifikation)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class FaceResult:
    """Ergebnis einer Gesichtserkennung"""
    detected: bool = False
    count: int = 0
    faces: List[dict] = field(default_factory=list)  # [{x, y, w, h, confidence}]
    landmarks: List[dict] = field(default_factory=list)  # Facial landmarks
    embeddings: List[bytes] = field(default_factory=list)  # Face embeddings für Recognition
    recognized_names: List[str] = field(default_factory=list)
    
    @property
    def has_known_face(self) -> bool:
        return any(name not in ["unknown", ""] for name in self.recognized_names)


@dataclass
class FaceDetectorConfig:
    """Konfiguration für Face Detection"""
    backend: str = "auto"  # opencv, dlib, mediapipe, auto
    min_confidence: float = 0.5
    enable_recognition: bool = False  # Face recognition (benötigt mehr Setup)
    known_faces_dir: Optional[Path] = None  # Ordner mit bekannten Gesichtern


class FaceDetector:
    """
    Face Detection und Recognition für Ryx
    
    Backends (in Prioritätsreihenfolge):
    1. MediaPipe (schnell, GPU-unterstützt)
    2. dlib (hohe Genauigkeit)
    3. OpenCV Haar Cascade (immer verfügbar)
    
    Usage:
        detector = FaceDetector()
        await detector.initialize()
        
        # Detect faces in frame
        result = await detector.detect(frame)
        print(f"Found {result.count} faces")
        
        # With recognition
        detector = FaceDetector(FaceDetectorConfig(
            enable_recognition=True,
            known_faces_dir=Path("./known_faces")
        ))
        result = await detector.detect(frame)
        print(f"Recognized: {result.recognized_names}")
    """
    
    def __init__(self, config: Optional[FaceDetectorConfig] = None):
        self.config = config or FaceDetectorConfig()
        self._backend: Optional[str] = None
        self._detector = None
        self._recognizer = None
        self._known_encodings: dict = {}  # name -> embedding
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialisiere Face Detector"""
        if self._initialized:
            return True
            
        if self.config.backend == "auto":
            if self._try_mediapipe():
                self._backend = "mediapipe"
            elif self._try_dlib():
                self._backend = "dlib"
            elif self._try_opencv():
                self._backend = "opencv"
            else:
                logger.error("No face detection backend available")
                return False
        else:
            self._backend = self.config.backend
            
        # Load known faces for recognition
        if self.config.enable_recognition and self.config.known_faces_dir:
            await self._load_known_faces()
            
        self._initialized = True
        logger.info(f"Face detector initialized with {self._backend}")
        return True
        
    def _try_mediapipe(self) -> bool:
        """Versuche MediaPipe zu laden"""
        try:
            import mediapipe as mp
            self._detector = mp.solutions.face_detection.FaceDetection(
                min_detection_confidence=self.config.min_confidence
            )
            return True
        except ImportError:
            return False
            
    def _try_dlib(self) -> bool:
        """Versuche dlib zu laden"""
        try:
            import dlib
            self._detector = dlib.get_frontal_face_detector()
            return True
        except ImportError:
            return False
            
    def _try_opencv(self) -> bool:
        """Versuche OpenCV Haar Cascade"""
        try:
            import cv2
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._detector = cv2.CascadeClassifier(cascade_path)
            return self._detector is not None
        except ImportError:
            return False
            
    async def _load_known_faces(self):
        """Lade bekannte Gesichter für Recognition"""
        if not self.config.known_faces_dir or not self.config.known_faces_dir.exists():
            return
            
        try:
            import face_recognition
            
            for img_path in self.config.known_faces_dir.glob("*.{jpg,jpeg,png}"):
                name = img_path.stem
                image = face_recognition.load_image_file(str(img_path))
                encodings = face_recognition.face_encodings(image)
                
                if encodings:
                    self._known_encodings[name] = encodings[0]
                    logger.info(f"Loaded face: {name}")
                    
        except ImportError:
            logger.warning("face_recognition not installed. Recognition disabled.")
            self.config.enable_recognition = False
            
    async def detect(self, frame) -> FaceResult:
        """
        Erkenne Gesichter in einem Frame
        
        Args:
            frame: Frame-Objekt oder NumPy Array
            
        Returns:
            FaceResult mit erkannten Gesichtern
        """
        if not self._initialized:
            await self.initialize()
            
        if not self._initialized:
            return FaceResult()
            
        # Frame zu NumPy konvertieren falls nötig
        if hasattr(frame, 'to_numpy'):
            img = frame.to_numpy()
        else:
            img = frame
            
        if self._backend == "mediapipe":
            return await self._detect_mediapipe(img)
        elif self._backend == "dlib":
            return await self._detect_dlib(img)
        elif self._backend == "opencv":
            return await self._detect_opencv(img)
            
        return FaceResult()
        
    async def _detect_mediapipe(self, img) -> FaceResult:
        """Detection mit MediaPipe"""
        import cv2
        
        # MediaPipe erwartet RGB
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self._detector.process(rgb)
        
        faces = []
        if results.detections:
            h, w = img.shape[:2]
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                faces.append({
                    "x": int(bbox.xmin * w),
                    "y": int(bbox.ymin * h),
                    "w": int(bbox.width * w),
                    "h": int(bbox.height * h),
                    "confidence": detection.score[0]
                })
                
        result = FaceResult(
            detected=len(faces) > 0,
            count=len(faces),
            faces=faces
        )
        
        # Recognition
        if self.config.enable_recognition and faces:
            result.recognized_names = await self._recognize_faces(img, faces)
            
        return result
        
    async def _detect_dlib(self, img) -> FaceResult:
        """Detection mit dlib"""
        import cv2
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        rects = self._detector(gray, 1)
        
        faces = []
        for rect in rects:
            faces.append({
                "x": rect.left(),
                "y": rect.top(),
                "w": rect.width(),
                "h": rect.height(),
                "confidence": 1.0
            })
            
        result = FaceResult(
            detected=len(faces) > 0,
            count=len(faces),
            faces=faces
        )
        
        if self.config.enable_recognition and faces:
            result.recognized_names = await self._recognize_faces(img, faces)
            
        return result
        
    async def _detect_opencv(self, img) -> FaceResult:
        """Detection mit OpenCV Haar Cascade"""
        import cv2
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        rects = self._detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        faces = []
        for (x, y, w, h) in rects:
            faces.append({
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "confidence": 0.8  # Haar gibt keine Confidence
            })
            
        return FaceResult(
            detected=len(faces) > 0,
            count=len(faces),
            faces=faces
        )
        
    async def _recognize_faces(self, img, faces: List[dict]) -> List[str]:
        """Gesichtserkennung mit face_recognition"""
        if not self._known_encodings:
            return ["unknown"] * len(faces)
            
        try:
            import face_recognition
            import cv2
            
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Berechne Encodings für erkannte Gesichter
            face_locations = [
                (f["y"], f["x"] + f["w"], f["y"] + f["h"], f["x"])
                for f in faces
            ]
            encodings = face_recognition.face_encodings(rgb, face_locations)
            
            names = []
            for encoding in encodings:
                # Vergleiche mit bekannten Gesichtern
                matches = face_recognition.compare_faces(
                    list(self._known_encodings.values()),
                    encoding,
                    tolerance=0.6
                )
                
                name = "unknown"
                if True in matches:
                    idx = matches.index(True)
                    name = list(self._known_encodings.keys())[idx]
                    
                names.append(name)
                
            return names
            
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return ["unknown"] * len(faces)
            
    async def is_user_present(self) -> bool:
        """Schnelle Prüfung ob ein Gesicht sichtbar ist"""
        # Diese Methode kann mit einer Kamera verbunden werden
        # für präsenzbasierte Aktivierung
        return False  # Placeholder - benötigt Kamera-Integration
