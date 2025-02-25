import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display
import json
import time
from scipy.signal import spectrogram
from tqdm import tqdm
from matplotlib.widgets import Slider, CheckButtons

# **Optimized FFT settings for the 10 Hz data rate**
DATA_RATE = 20  # Hz
FFTSIZE = 2048  # Larger for frequency resolution
HOP_LEN = 1500  # Match the data bit timing

def load_freq_config(json_file):
    """Loads frequency configuration from a JSON file."""
    with open(json_file, 'r') as f:
        return json.load(f)

def plot_spectrogram(wav_file, freq_config, fft_size=FFTSIZE, hop_length=HOP_LEN):
    """Generates and displays a spectrogram with controls for visibility."""
    # Load WAV file
    y, sr = librosa.load(wav_file, sr=None)
    
    # Compute spectrogram
    f, t, Sxx = spectrogram(y, fs=sr, nperseg=fft_size, noverlap=hop_length, window='hann')

    # Convert power to log scale (dB) and enhance contrast
    Sxx_dB = 10 * np.log10(Sxx + 1e-10)
    Sxx_dB -= Sxx_dB.min()  # Normalize contrast
    Sxx_dB = np.clip(Sxx_dB, 0, 80)  # Avoid excessive noise

    # **Create figure**
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.subplots_adjust(bottom=0.3)  # Adjust for UI elements

    # **Initial spectrogram display**
    img = ax.pcolormesh(t, f, Sxx_dB, shading='auto', cmap='inferno')
    plt.colorbar(img, ax=ax, label="Power (dB)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title("High-Resolution Spectrogram of " + wav_file)

    # **Overlay frequency bands**
    colors = {"clock": "red", "header": "blue", "content": "green", "footer": "purple"}
    freq_lines = []
    
    for section, freqs in freq_config.items():
        color = colors.get(section, "black")
        for freq in freqs:
            line = ax.axhline(y=freq, color=color, linestyle="--", alpha=0.7, label=f"{section} {freq} Hz")
            freq_lines.append(line)

    # **Overlay predicted data bit timing marks**
    bit_timing_lines = []
    for i in range(int(t[-1] * DATA_RATE)):  # Place tick marks every 1/DATA_RATE seconds
        time_pos = i / DATA_RATE
        line = ax.axvline(x=time_pos, color='white', linestyle="--", alpha=0.5)
        bit_timing_lines.append(line)

    # **Add checkbox for visibility toggles**
    ax_checkbox = plt.axes([0.01, 0.05, 0.15, 0.15])
    check = CheckButtons(ax_checkbox, ["Show Freq Bands", "Show Data Bits"], [True, True])

    # Checkbox callback
    def toggle_visibility(label):
        if label == "Show Freq Bands":
            visibility = not freq_lines[0].get_visible()
            for line in freq_lines:
                line.set_visible(visibility)
        elif label == "Show Data Bits":
            visibility = not bit_timing_lines[0].get_visible()
            for line in bit_timing_lines:
                line.set_visible(visibility)
        fig.canvas.draw_idle()

    check.on_clicked(toggle_visibility)

    # **Add a slider for power cutoff**
    ax_slider = plt.axes([0.2, 0.05, 0.65, 0.03], facecolor="lightgray")
    slider = Slider(ax_slider, "Cutoff", 0, 80, valinit=0)

    # Slider update function
    def update(val):
        cutoff = slider.val
        new_Sxx = np.where(Sxx_dB < cutoff, -100, Sxx_dB)
        img.set_array(new_Sxx.ravel())
        fig.canvas.draw_idle()

    slider.on_changed(update)
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
    """Full pipeline: Load freq_config, plot spectrogram with controls, and estimate decoding speed."""
    freq_config = load_freq_config(json_file)
    plot_spectrogram(wav_file, freq_config)
    estimate_decoding_speed(wav_file)

# Example Usage
if __name__ == "__main__":
    analyze_wav("binaric_transmission_with_manchester_clock_2.wav", "binaric/utils/freq_bands_max.json")
