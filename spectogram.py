import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display
import json
import wave
import time
from scipy.signal import spectrogram
from tqdm import tqdm

FFTSIZE = 2048
HOP_LEN = 512

def load_freq_config(json_file):
    """Loads frequency configuration from a JSON file."""
    with open(json_file, 'r') as f:
        return json.load(f)

def plot_spectrogram(wav_file, freq_config, fft_size=FFTSIZE, hop_length=HOP_LEN):
    """Generates and displays a spectrogram with overlayed frequency bands."""
    # Load WAV file
    y, sr = librosa.load(wav_file, sr=None)
    
    # Compute spectrogram
    f, t, Sxx = spectrogram(y, fs=sr, nperseg=fft_size, noverlap=hop_length)

    # Convert power to log scale (dB)
    Sxx_dB = 10 * np.log10(Sxx + 1e-10)

    # Plot the spectrogram
    plt.figure(figsize=(12, 6))
    plt.pcolormesh(t, f, Sxx_dB, shading='gouraud')
    plt.colorbar(label="Power (dB)")
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency (Hz)")
    plt.title("Spectrogram of " + wav_file)

    # Overlay frequency bands
    colors = {"clock": "red", "header": "blue", "content": "green", "footer": "purple"}
    
    for section, freqs in freq_config.items():
        color = colors.get(section, "black")
        for freq in freqs:
            plt.axhline(y=freq, color=color, linestyle="--", alpha=0.7, label=f"{section} {freq} Hz")

    plt.legend(loc="upper right")
    plt.show()

def estimate_decoding_speed(wav_file, fft_size=FFTSIZE, hop_length=HOP_LEN):
    """Estimates how fast the script can process a sample to determine real-time feasibility."""
    y, sr = librosa.load(wav_file, sr=None)
    
    # Start timer
    start_time = time.time()
    
    # Compute spectrogram (simulating real-time processing)
    _, _, Sxx = spectrogram(y, fs=sr, nperseg=fft_size, noverlap=hop_length)
    
    # End timer
    end_time = time.time()
    
    # Compute statistics
    processing_time = end_time - start_time
    audio_duration = len(y) / sr
    real_time_factor = audio_duration / processing_time

    print("\n=== Decoding Efficiency ===")
    print(f"Audio Duration: {audio_duration:.2f} sec")
    print(f"Processing Time: {processing_time:.2f} sec")
    print(f"Real-time Factor: {real_time_factor:.2f}x")
    
    # Determine if real-time processing is possible
    if real_time_factor > 1:
        print("✅ System CAN process this file in real-time.")
    else:
        print("❌ System CANNOT process this file in real-time.")

def analyze_wav(wav_file, json_file):
    """Full pipeline: Load freq_config, plot spectrogram, and estimate decoding speed."""
    freq_config = load_freq_config(json_file)
    plot_spectrogram(wav_file, freq_config)
    estimate_decoding_speed(wav_file)

# Example Usage
if __name__ == "__main__":
    analyze_wav("binaric_transmission_with_clock.wav", "freq_bands.json")
