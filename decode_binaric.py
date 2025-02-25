import numpy as np
import librosa
import json
import sys
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, spectrogram

def load_freq_config(json_file):
    """Loads frequency configuration from a JSON file."""
    with open(json_file, 'r') as f:
        return json.load(f)

def detect_clock_edges(audio, sr, clock_freqs, data_rate):
    """
    Detects only rising edges in the Manchester-encoded clock signal
    and interpolates falling edges to reconstruct the timing grid.
    
    Returns:
        - transition_times: List of all clock transition times (both rising and interpolated falling edges).
    """
    # Compute spectrogram
    f, t, Sxx = spectrogram(audio, fs=sr, nperseg=2048, noverlap=1024)

    # Find indices of clock frequencies
    clock_indices = [np.argmin(np.abs(f - freq)) for freq in clock_freqs]

    # Extract power at clock frequencies
    clock_power = np.mean(Sxx[clock_indices, :], axis=0)

    # Normalize power
    clock_power = (clock_power - np.min(clock_power)) / (np.max(clock_power) - np.min(clock_power))

    # Compute the first derivative (gradient) of clock power
    clock_gradient = np.gradient(clock_power)

    # Detect rising edges (positive gradient peaks)
    min_distance = int(sr / (data_rate) / (t[1] - t[0]))  # Adjusted spacing
    peaks, _ = find_peaks(clock_gradient, height=0.2, distance=1)

    # Interpolate falling edges at midpoints between rising edges
    falling_edges = (peaks[:-1] + peaks[1:]) / 2  # Midpoint interpolation
    all_transitions = np.sort(np.concatenate((peaks, falling_edges)))  # Merge & sort

    # Convert to time values
    transition_times = t[all_transitions.astype(int)]

    print(f"Detected {len(transition_times)} clock transitions.")

    # Debug Plot
    plt.figure(figsize=(12, 6))
    plt.plot(clock_gradient, label="Clock Power Gradient")
    plt.scatter(peaks, clock_gradient[peaks], color='red', label="Rising Edges")
    plt.scatter(falling_edges, clock_gradient[falling_edges.astype(int)], color='blue', label="Interpolated Falling Edges")
    plt.legend()
    plt.title("Clock Power Gradient with Rising and Falling Edges")
    plt.show()

    return transition_times, t, Sxx, f


def extract_bits_from_wav(wav_file, json_file, data_rate):
    """
    Extracts bit arrays from the Manchester-encoded WAV file at clock transitions.

    Returns:
        - List of bit arrays at each clock transition.
    """
    # Load configuration
    freq_config = load_freq_config(json_file)
    data_freqs = freq_config["content"]
    clock_freqs = freq_config["clock"]
    
    header_freqs = freq_config.get("header", [])
    footer_freqs = freq_config.get("footer", [])

    # Load audio
    audio, sr = librosa.load(wav_file, sr=None)
    
    # Detect clock edges
    transition_times, t, Sxx, f = detect_clock_edges(audio, sr, clock_freqs, data_rate)
    
    # Convert frequency list to indices
    data_indices = [np.argmin(np.abs(f - freq)) for freq in data_freqs]
    header_indices = [np.argmin(np.abs(f - freq)) for freq in header_freqs]
    footer_indices = [np.argmin(np.abs(f - freq)) for freq in footer_freqs]
    
    # Extract bit values at each transition time
    bit_array = []
    for time in transition_times:
        # Find closest time index in the spectrogram
        t_index = np.argmin(np.abs(t - time))
        
        # Get power levels at bit frequencies
        power_levels = Sxx[data_indices, t_index]
        header_levels = Sxx[header_indices, t_index] if header_freqs else []
        footer_levels = Sxx[footer_indices, t_index] if footer_freqs else []
        
        # Convert to binary (1 if above threshold)
        threshold = np.max(power_levels) * 0.6
        header_threshold = np.max(header_levels) * 0.3  # Lower threshold for header

        bits = [1 if p > threshold else 0 for p in power_levels]
        header_bits = [1 if p > header_threshold else 0 for p in header_levels]

        footer_bits = [1 if p > threshold else 0 for p in footer_levels]

        bit_array.append((time, header_bits, bits, footer_bits))

    return bit_array, t, Sxx, f, transition_times, data_indices, header_indices, footer_indices

def plot_spectrogram(wav_file, json_file, data_rate):
    """
    Plots the spectrogram with clock transition markers and bit value dots.
    """
    bit_data, t, Sxx, f, transition_times, data_indices, header_indices, footer_indices = extract_bits_from_wav(wav_file, json_file, data_rate)

    # Convert power to dB
    Sxx_dB = 10 * np.log10(Sxx + 1e-10)

    # Plot spectrogram
    fig, ax = plt.subplots(figsize=(12, 6))
    img = ax.pcolormesh(t, f, Sxx_dB, shading='gouraud', cmap='inferno')
    plt.colorbar(img, ax=ax, label="Power (dB)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title("Spectrogram with Clock Transitions and Bit Values")

    # Plot clock transitions as vertical red lines
    for time in transition_times:
        ax.axvline(time, color='red', linestyle='--', alpha=0.6)

    # Overlay detected bits as dots
    for i, (time, header_bits, content_bits, footer_bits) in enumerate(bit_data):
        y_header = [f[idx] for idx in header_indices]  # Header bit frequencies
        y_content = [f[idx] for idx in data_indices]   # Content bit frequencies
        y_footer = [f[idx] for idx in footer_indices]  # Footer bit frequencies

        # Header bits (Blue)
        ax.scatter([time] * len(y_header), y_header, c=['white' if b else 'black' for b in header_bits], edgecolors='blue', s=50, marker='o', label="Header" if i == 0 else "")

        # Content bits (Green)
        ax.scatter([time] * len(y_content), y_content, c=['white' if b else 'black' for b in content_bits], edgecolors='green', s=50, marker='o', label="Content" if i == 0 else "")

        # Footer bits (Purple)
        ax.scatter([time] * len(y_footer), y_footer, c=['white' if b else 'black' for b in footer_bits], edgecolors='purple', s=50, marker='o', label="Footer" if i == 0 else "")

    plt.legend()
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python decode_binaric.py <wav_file> <json_file>")
        sys.exit(1)

    wav_file = sys.argv[1]
    json_file = sys.argv[2]

    plot_spectrogram(wav_file, json_file, data_rate=10)
