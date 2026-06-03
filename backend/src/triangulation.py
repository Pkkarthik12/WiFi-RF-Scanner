import math
import numpy as np
from scipy.optimize import least_squares
from typing import List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

# Assuming SignalReading is imported, redefining here for completeness
@dataclass
class SignalReading:
    raw_rssi: float
    filtered_rssi: float
    timestamp: float
    confidence_score: float

@dataclass
class AccessPoint:
    id: str
    mac: str
    x: float
    y: float
    calibration_offset: float

@dataclass
class Position:
    x: float
    y: float
    z: float
    timestamp: datetime
    confidence: float
    error_estimate: float

class TriangulationEngine:
    """
    Performs WiFi trilateration and multilateration.
    """
    
    @staticmethod
    def rssi_to_distance(rssi: float, calibration_offset: float = -40, path_loss_exponent: float = 2.5) -> float:
        """
        Converts RSSI to distance using the Log-Distance Path Loss model.
        Formula: d = 10 ^ ((calibration_offset - RSSI) / (10 * path_loss_exponent))
        """
        # Constrain RSSI
        if rssi > -10: rssi = -10
        if rssi < -100: rssi = -100
        
        exponent = (calibration_offset - rssi) / (10.0 * path_loss_exponent)
        distance = math.pow(10, exponent)
        return distance

    def least_squares_optimization(self, positions: List[Tuple[float, float]], distances: List[float]) -> Tuple[float, float]:
        """
        Uses Gauss-Newton / Levenberg-Marquardt to find the best point that minimizes the error
        between expected distances and measured distances.
        """
        def error_function(guess_pt: np.ndarray, points: np.ndarray, dists: np.ndarray) -> np.ndarray:
            """Calculates error residuals for the optimizer."""
            residuals = []
            for pt, d in zip(points, dists):
                calc_dist = np.sqrt(np.sum((guess_pt - pt)**2))
                residuals.append(calc_dist - d)
            return np.array(residuals)
            
        pts_array = np.array(positions)
        dists_array = np.array(distances)
        
        # Initial guess: centroid of the APs
        initial_guess = np.mean(pts_array, axis=0)
        
        result = least_squares(error_function, initial_guess, args=(pts_array, dists_array))
        
        return float(result.x[0]), float(result.x[1])

    def trilaterate(self, readings: List[SignalReading], ap_positions: List[AccessPoint]) -> Optional[Position]:
        """
        Performs trilateration using exactly 3 APs. 
        Calls multilaterate under the hood as the math is identical for >=3.
        """
        if len(readings) != 3 or len(ap_positions) != 3:
            return None
            
        return self.multilaterate(readings, ap_positions)

    def multilaterate(self, readings: List[SignalReading], ap_positions: List[AccessPoint]) -> Optional[Position]:
        """
        Performs multilateration for N access points (N >= 3).
        """
        if len(readings) < 3 or len(ap_positions) < 3:
            # Fallback for < 3 APs could be implemented here (e.g., proximity to strongest AP)
            return None
            
        positions = []
        distances = []
        
        # Match readings to APs (assuming ordered or zipped for this example)
        # In reality, you'd match by AP ID/MAC
        for i in range(len(readings)):
            ap = ap_positions[i]
            reading = readings[i]
            
            d = self.rssi_to_distance(reading.filtered_rssi, ap.calibration_offset)
            positions.append((ap.x, ap.y))
            distances.append(d)
            
        x, y = self.least_squares_optimization(positions, distances)
        
        # Calculate a simple error estimate/confidence based on distance residuals
        calc_dists = [np.sqrt((x - px)**2 + (y - py)**2) for px, py in positions]
        residuals = [abs(cd - d) for cd, d in zip(calc_dists, distances)]
        avg_error = sum(residuals) / len(residuals)
        
        # Map error to a 0-100 confidence
        confidence = max(0.0, min(100.0, 100.0 - (avg_error * 10))) 
        
        return Position(
            x=x,
            y=y,
            z=0.0, # Height estimate not supported in 2D trilateration
            timestamp=datetime.now(),
            confidence=confidence,
            error_estimate=avg_error
        )

    def bayesian_position_estimation(self, position_samples: List[Position]) -> Optional[Position]:
        """
        Estimates the most likely position given a history of position samples.
        """
        if not position_samples:
            return None
            
        # Simple weighted average based on confidence
        total_confidence = sum(p.confidence for p in position_samples)
        if total_confidence == 0:
            total_confidence = 1e-6
            
        weighted_x = sum(p.x * p.confidence for p in position_samples) / total_confidence
        weighted_y = sum(p.y * p.confidence for p in position_samples) / total_confidence
        
        return Position(
            x=weighted_x,
            y=weighted_y,
            z=0.0,
            timestamp=datetime.now(),
            confidence=total_confidence / len(position_samples),
            error_estimate=0.0 # Could calculate variance here
        )

# Testing helpers
def generate_synthetic_measurements(true_pos: Tuple[float, float], ap_positions: List[AccessPoint]) -> List[float]:
    """Generates fake RSSI readings for testing."""
    readings = []
    engine = TriangulationEngine()
    for ap in ap_positions:
        true_dist = np.sqrt((true_pos[0] - ap.x)**2 + (true_pos[1] - ap.y)**2)
        # Reverse the path loss formula to get expected RSSI
        # d = 10 ^ ((cal - rssi)/25) -> log10(d)*25 = cal - rssi -> rssi = cal - 25*log10(d)
        expected_rssi = ap.calibration_offset - (10.0 * 2.5 * math.log10(true_dist if true_dist > 0 else 0.1))
        # Add noise
        noisy_rssi = expected_rssi + np.random.normal(0, 3) 
        readings.append(noisy_rssi)
    return readings

def validate_triangulation_accuracy():
    """Test function to validate the math."""
    engine = TriangulationEngine()
    aps = [
        AccessPoint("ap1", "00:11", 0, 0, -40),
        AccessPoint("ap2", "00:22", 10, 0, -40),
        AccessPoint("ap3", "00:33", 5, 10, -40)
    ]
    true_pos = (3.5, 4.2)
    rssis = generate_synthetic_measurements(true_pos, aps)
    
    readings = [SignalReading(r, r, 0, 100) for r in rssis]
    est_pos = engine.multilaterate(readings, aps)
    
    print(f"True Pos: {true_pos}")
    print(f"Est Pos: ({est_pos.x:.2f}, {est_pos.y:.2f})")
    print(f"Error: {est_pos.error_estimate:.2f}m")
