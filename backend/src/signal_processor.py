import numpy as np
from typing import List, Tuple
from dataclasses import dataclass
import matplotlib.pyplot as plt

@dataclass
class SignalReading:
    raw_rssi: float
    filtered_rssi: float
    timestamp: float
    confidence_score: float

class KalmanFilter:
    """
    1D Kalman Filter for RSSI smoothing.
    State: [position (rssi), velocity (rate of change)]
    """
    def __init__(self, process_noise: float = 1e-5, measurement_noise: float = 1e-2):
        # State [x, dx/dt]
        self.state_matrix = np.zeros((2, 1))
        # Covariance matrix
        self.covariance_matrix = np.eye(2)
        
        self.process_noise_cov = np.array([[process_noise, 0], [0, process_noise]])
        self.measurement_noise_cov = np.array([[measurement_noise]])
        
        # State transition model (assuming dt=1 for simplicity, update dynamically if needed)
        self.F = np.array([[1, 1], [0, 1]])
        
        # Observation model
        self.H = np.array([[1, 0]])

    def predict(self, dt: float = 1.0):
        """Predict step of Kalman filter."""
        self.F[0, 1] = dt
        self.state_matrix = np.dot(self.F, self.state_matrix)
        self.covariance_matrix = np.dot(np.dot(self.F, self.covariance_matrix), self.F.T) + self.process_noise_cov

    def update(self, measurement: float):
        """Update step with new measurement."""
        z = np.array([[measurement]])
        
        # Innovation
        y = z - np.dot(self.H, self.state_matrix)
        
        # Innovation covariance
        S = np.dot(np.dot(self.H, self.covariance_matrix), self.H.T) + self.measurement_noise_cov
        
        # Kalman gain
        K = np.dot(np.dot(self.covariance_matrix, self.H.T), np.linalg.inv(S))
        
        # Update state
        self.state_matrix = self.state_matrix + np.dot(K, y)
        
        # Update covariance
        I = np.eye(self.covariance_matrix.shape[0])
        self.covariance_matrix = np.dot((I - np.dot(K, self.H)), self.covariance_matrix)
        
    def get_state(self) -> float:
        """Returns the current smoothed value."""
        return float(self.state_matrix[0, 0])


class SignalProcessor:
    """
    Signal processing functions for WiFi RSSI data.
    """
    
    @staticmethod
    def kalman_filter(rssi_readings: List[float], process_noise: float = 1e-4, measurement_noise: float = 1e-1) -> List[float]:
        """Applies Kalman filtering to a list of RSSI values."""
        if not rssi_readings:
            return []
            
        kf = KalmanFilter(process_noise, measurement_noise)
        
        # Initialize with first reading
        kf.state_matrix[0, 0] = rssi_readings[0]
        
        smoothed = []
        for reading in rssi_readings:
            kf.predict()
            kf.update(reading)
            smoothed.append(kf.get_state())
            
        return smoothed

    @staticmethod
    def moving_average(values: List[float], window_size: int = 5, exponential: bool = False) -> List[float]:
        """Calculates simple or exponential moving average."""
        if not values:
            return []
            
        if exponential:
            alpha = 2.0 / (window_size + 1)
            ema = [values[0]]
            for i in range(1, len(values)):
                ema.append(alpha * values[i] + (1 - alpha) * ema[-1])
            return ema
        else:
            ma = []
            for i in range(len(values)):
                if i < window_size:
                    ma.append(sum(values[:i+1]) / (i+1))
                else:
                    ma.append(sum(values[i-window_size+1:i+1]) / window_size)
            return ma

    @staticmethod
    def outlier_removal(values: List[float], std_dev_threshold: float = 2.0) -> List[float]:
        """Removes outliers using Z-score method. Replaces outliers with median."""
        if not values or len(values) < 3:
            return values
            
        mean = np.mean(values)
        std_dev = np.std(values)
        
        if std_dev == 0:
            return values
            
        median = np.median(values)
        cleaned = []
        for v in values:
            z_score = abs(v - mean) / std_dev
            if z_score > std_dev_threshold:
                cleaned.append(float(median)) # Replace with median
            else:
                cleaned.append(v)
                
        return cleaned

    @staticmethod
    def fft_analysis(time_series: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        """Performs Fast Fourier Transform analysis on time series data."""
        if not time_series:
            return np.array([]), np.array([])
            
        # Remove DC component
        centered = np.array(time_series) - np.mean(time_series)
        
        fft_result = np.fft.fft(centered)
        frequencies = np.fft.fftfreq(len(time_series))
        
        # Return magnitude spectrum and frequencies (positive half)
        half_n = len(time_series) // 2
        return np.abs(fft_result[:half_n]), frequencies[:half_n]

    @staticmethod
    def signal_quality_score(rssi: float, timestamp: float) -> float:
        """
        Calculates a 0-100 quality score for a signal reading.
        -30 dBm -> ~100
        -90 dBm -> ~0
        """
        # Clamp values
        max_rssi = -30
        min_rssi = -90
        
        clamped_rssi = max(min_rssi, min(max_rssi, rssi))
        
        # Linear scale
        score = ((clamped_rssi - min_rssi) / (max_rssi - min_rssi)) * 100
        return float(score)

def plot_raw_vs_filtered(raw: List[float], filtered: List[float]):
    """Helper to visualize filtering results."""
    plt.figure(figsize=(10, 5))
    plt.plot(raw, label='Raw RSSI', alpha=0.5)
    plt.plot(filtered, label='Filtered RSSI', color='red')
    plt.title('Raw vs Filtered RSSI')
    plt.xlabel('Sample')
    plt.ylabel('RSSI (dBm)')
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_frequency_spectrum(time_series: List[float]):
    """Helper to visualize frequency components."""
    magnitudes, frequencies = SignalProcessor.fft_analysis(time_series)
    plt.figure(figsize=(10, 5))
    plt.plot(frequencies, magnitudes)
    plt.title('Frequency Spectrum')
    plt.xlabel('Normalized Frequency')
    plt.ylabel('Magnitude')
    plt.grid(True)
    plt.show()
