import logging
from typing import List, Dict, Tuple
import os

try:
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    import joblib
except ImportError:
    logging.warning("scikit-learn not installed. Device Classifier disabled.")

logger = logging.getLogger(__name__)

class DeviceTypeClassifier:
    """
    Infers device type (phone, laptop, IoT) based on signal behavior and MAC OUI.
    Also includes Anomaly Detection for unusual movement/signals.
    """
    def __init__(self, model_path: str = "models/device_classifier.pkl"):
        self.model_path = model_path
        self.classifier = None
        self.anomaly_detector = IsolationForest(contamination=0.05, random_state=42)
        self.is_trained = False
        
        # Simple local OUI lookup fallback
        self.oui_db = {
            "00:1A:11": ("Google", "iot"),
            "DC:53:60": ("Apple", "phone"),
            "F4:0F:24": ("Apple", "laptop"),
            # Add more for real usage
        }

    def predict_vendor(self, mac_address: str) -> Tuple[str, str]:
        """Returns (Vendor, Suspected Type) based on OUI."""
        oui = mac_address[:8].upper()
        return self.oui_db.get(oui, ("Unknown", "unknown"))

    def extract_signal_signature(self, signal_history: List[Dict]) -> List[float]:
        """
        Extracts temporal features from a history of signals for a device.
        """
        if not signal_history:
            return [0.0, 0.0, 0.0, 0.0]
            
        rssi_values = [s.get('rssi', -90) for s in signal_history]
        
        # Features: variance in signal, max signal, min signal, transmission rate proxy (count)
        variance = float(np.var(rssi_values)) if len(rssi_values) > 1 else 0.0
        max_sig = float(np.max(rssi_values))
        min_sig = float(np.min(rssi_values))
        packet_count = float(len(signal_history))
        
        return [variance, max_sig, min_sig, packet_count]

    def train_classifier(self, training_data: List[List[float]], labels: List[str]):
        """Trains the Random Forest classifier for device types."""
        self.classifier = RandomForestClassifier(n_estimators=50, random_state=42)
        self.classifier.fit(training_data, labels)
        self.is_trained = True
        
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.classifier, self.model_path)
        logger.info("Trained and saved device classifier.")

    def classify_device(self, mac: str, signal_history: List[Dict]) -> Tuple[str, float]:
        """Returns (Device Type, Confidence 0-100)"""
        # 1. Check OUI first
        vendor, oui_type = self.predict_vendor(mac)
        
        # 2. Check ML model
        if self.is_trained and self.classifier and len(signal_history) >= 5:
            signature = self.extract_signal_signature(signal_history)
            try:
                probs = self.classifier.predict_proba([signature])[0]
                pred_idx = np.argmax(probs)
                ml_type = self.classifier.classes_[pred_idx]
                confidence = probs[pred_idx] * 100
                return ml_type, confidence
            except Exception as e:
                logger.error(f"Classification error: {e}")
                
        # Fallback to OUI
        return oui_type, 60.0 if oui_type != "unknown" else 10.0

    def detect_anomaly(self, signal_signature: List[float]) -> bool:
        """Returns True if the signal pattern is highly unusual."""
        # Note: In production, fit() needs to be called on historical normal data first
        # before predict() is valid.
        try:
            # -1 for anomaly, 1 for normal
            prediction = self.anomaly_detector.predict([signal_signature])
            return prediction[0] == -1
        except Exception:
            return False
