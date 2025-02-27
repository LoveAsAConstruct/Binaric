#!/usr/bin/env python3
import numpy as np
import librosa
import json
import sys
import argparse
import base64
import math
from scipy.signal import find_peaks, spectrogram
import matplotlib.pyplot as plt

# --- Helper Functions for Bit Conversion ---

def bits_to_string(bit_str):
    """Convert a string of bits (grouped in 8) into a UTF-8 string."""
    chars = []
    for i in range(0, len(bit_str), 8):
        byte = bit_str[i:i+8]
        if len(byte) < 8:
            continue
        chars.append(chr(int(byte, 2)))
    return "".join(chars)

def bits_to_bytes(bit_str):
    """Convert a string of bits (grouped in 8) into bytes."""
    byte_array = bytearray()
    for i in range(0, len(bit_str), 8):
        byte = bit_str[i:i+8]
        if len(byte) < 8:
            continue
        byte_array.append(int(byte, 2))
    return bytes(byte_array)

# --- Frequency Config Loader ---

def load_freq_config(json_file):
    """Loads frequency configuration from a JSON file."""
    with open(json_file, 'r') as f:
        return json.load(f)

# --- Spectrogram and Clock Edge Detection ---

def detect_clock_edges(audio, sr, clock_freqs, data_rate, debug=False):
    """
    Detect rising edges in the Manchester-encoded clock signal and interpolate falling edges.
    
    Returns:
        transition_times: list of clock transition times,
        t: time vector from the spectrogram,
        Sxx: spectrogram power matrix,
        f: frequency vector from the spectrogram.
    """
    f, t, Sxx = spectrogram(audio, fs=sr, nperseg=2048, noverlap=1500)
    clock_indices = [np.argmin(np.abs(f - freq)) for freq in clock_freqs]
    clock_power = np.mean(Sxx[clock_indices, :], axis=0)
    clock_power = (clock_power - np.min(clock_power)) / (np.max(clock_power) - np.min(clock_power))
    clock_gradient = np.gradient(clock_power)
    
    min_distance = 1#int(sr / data_rate / (t[1] - t[0]))
    peaks, _ = find_peaks(np.abs(clock_gradient), height=0.25, distance=min_distance)
    #falling_edges = (peaks[:-1] + peaks[1:]) / 2
    all_transitions = peaks#np.sort(np.concatenate((peaks, falling_edges)))
    transition_times = t[all_transitions.astype(int)]
    
    if debug:
        print(f"Detected {len(transition_times)} clock transitions.")
        plt.figure(figsize=(12, 6))
        plt.plot(clock_gradient, label="Clock Gradient")
        plt.scatter(peaks, clock_gradient[peaks], color='red', label="Rising Edges")
        #plt.scatter(falling_edges, clock_gradient[falling_edges.astype(int)], color='blue', label="Interpolated Falling Edges")
        plt.legend()
        plt.title("Clock Gradient with Detected Transitions")
        plt.xlabel("Time index (spectrogram)")
        plt.ylabel("Gradient value")
        plt.show()
    
    return transition_times, t, Sxx, f

# --- Bit Extraction from Audio ---
    
def extract_bits_from_wav(wav_file, json_file, data_rate, debug=False):
    """
    Extracts bit symbols from the Manchester-encoded WAV file at clock transitions.
    
    Returns a tuple containing:
      - bit_data: List of tuples (time, header_bits, content_bits, footer_bits, mode_bits)
      - t, Sxx, f: Spectrogram parameters
      - transition_times: List of detected clock transition times
      - frequency index lists for header, content, footer, and modes.
    """
    freq_config = load_freq_config(json_file)
    data_freqs = freq_config.get("content", [])
    header_freqs = freq_config.get("header", [])
    footer_freqs = freq_config.get("footer", [])
    mode_freqs = freq_config.get("modes", [])
    clock_freqs = freq_config.get("clock", [])
    
    audio, sr = librosa.load(wav_file, sr=None)
    transition_times, t, Sxx, f = detect_clock_edges(audio, sr, clock_freqs, data_rate, debug=debug)
    
    data_indices = [np.argmin(np.abs(f - freq)) for freq in data_freqs]
    header_indices = [np.argmin(np.abs(f - freq)) for freq in header_freqs]
    footer_indices = [np.argmin(np.abs(f - freq)) for freq in footer_freqs]
    mode_indices = [np.argmin(np.abs(f - freq)) for freq in mode_freqs]
    
    bit_data = []
    for time in transition_times:
        t_index = np.argmin(np.abs(t - time))
        data_power = Sxx[data_indices, t_index] if data_indices else np.array([])
        header_power = Sxx[header_indices, t_index] if header_indices else np.array([])
        footer_power = Sxx[footer_indices, t_index] if footer_indices else np.array([])
        mode_power = Sxx[mode_indices, t_index] if mode_indices else np.array([])
        
        threshold_value = 0.2

        threshold = np.max(data_power) * threshold_value if data_power.size > 0 else 0
        header_threshold = np.max(header_power) * threshold_value if header_power.size > 0 else 0
        footer_threshold = np.max(footer_power) * threshold_value if footer_power.size > 0 else 0
        mode_threshold = np.max(mode_power) * threshold_value if mode_power.size > 0 else 0
        
        content_bits = [1 if p > threshold else 0 for p in data_power] if data_power.size > 0 else []
        header_bits = [1 if p > header_threshold else 0 for p in header_power] if header_power.size > 0 else []
        footer_bits = [1 if p > footer_threshold else 0 for p in footer_power] if footer_power.size > 0 else []
        mode_bits = [1 if p > mode_threshold else 0 for p in mode_power] if mode_power.size > 0 else []
        
        bit_data.append((time, header_bits, content_bits, footer_bits, mode_bits))
    
    return bit_data, t, Sxx, f, transition_times, data_indices, header_indices, footer_indices, mode_indices

# --- Decoding BinaricRequest from Audio ---

def decode_binaric_request(wav_file, json_file, data_rate, debug=False):
    """
    Decodes a Manchester-encoded WAV file back into a BinaricRequest object.
    
    Returns a dictionary with keys "header", "content", "footer" where:
      - header is a dict (parsed from a JSON string),
      - content is a base64-encoded string representing the raw data,
      - footer is a plain text string.
    """
    bit_data, t, Sxx, f, transitions, data_indices, header_indices, footer_indices, mode_indices = extract_bits_from_wav(
        wav_file, json_file, data_rate, debug=debug)
    
    header_bits_str = ""
    content_bits_str = ""
    footer_bits_str = ""
    
    for time, h_bits, c_bits, f_bits, m_bits in bit_data:
        # Only add bits if the corresponding mode is active.
        if len(m_bits) >= 1 and m_bits[0] == 1:
            header_bits_str += "".join(str(bit) for bit in h_bits)
        if len(m_bits) >= 2 and m_bits[1] == 1:
            content_bits_str += "".join(str(bit) for bit in c_bits)
        if len(m_bits) >= 3 and m_bits[2] == 1:
            footer_bits_str += "".join(str(bit) for bit in f_bits)
    
    header_str = bits_to_string(header_bits_str)
    footer_str = bits_to_string(footer_bits_str)
    content_bytes = bits_to_bytes(content_bits_str)
    print(f"header string is: {header_str}\ncontent string is: {content_bytes}\nfooter string is: {footer_str}")
    try:
        header_obj = json.loads(header_str)
    except Exception as e:
        print("Error decoding header JSON:", e)
        header_obj = {}
    
    content_b64 = base64.b64encode(content_bytes).decode('utf-8')
    
    if debug:
        print("Decoded Bit Strings:")
        print("Header bits:", header_bits_str)
        print("Content bits:", content_bits_str)
        print("Footer bits:", footer_bits_str)
    
    binaric_request = {
        "header": header_obj,
        "content": content_b64,
        "footer": footer_str
    }
    
    return binaric_request

# --- Optional Debug Plotting ---

def plot_extraction_results(wav_file, json_file, data_rate):
    """
    Displays the spectrogram with detected clock transitions and overlays markers for the extracted bit values.
    Only the bits corresponding to an active mode (as indicated by mode bits) are shown.
    The bits are drawn as circles with black (for 0) or white (for 1) fill, and a colored outline.
    """
    bit_data, t, Sxx, f, transitions, data_indices, header_indices, footer_indices, mode_indices = extract_bits_from_wav(
        wav_file, json_file, data_rate, debug=True)
    Sxx_dB = 10 * np.log10(Sxx + 1e-10)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    img = ax.pcolormesh(t, f, Sxx_dB, shading='gouraud', cmap='inferno')
    plt.colorbar(img, ax=ax, label="Power (dB)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title("Spectrogram with Clock Transitions & Active Mode Bit Extraction")
    
    # Plot clock transitions.
    for time in transitions:
        ax.axvline(time, color='red', linestyle='--', alpha=0.6)
    
    # Overlay extracted bit markers.
    for i, (time, header_bits, content_bits, footer_bits, m_bits) in enumerate(bit_data):
        # Only display bits for active mode.
        if len(m_bits) >= 1 and m_bits[0] == 1 and header_bits:
            header_freq_values = [f[idx] for idx in header_indices]
            # For each bit, use white if 1, black if 0; outline in blue.
            fill_colors = ['white' if bit == 1 else 'black' for bit in header_bits]
            ax.scatter([time]*len(header_freq_values), header_freq_values,
                       marker='o', s=50, c=fill_colors, edgecolors='blue',
                       label="Header Bits" if i == 0 else "")
        if len(m_bits) >= 2 and m_bits[1] == 1 and content_bits:
            content_freq_values = [f[idx] for idx in data_indices]
            fill_colors = ['white' if bit == 1 else 'black' for bit in content_bits]
            ax.scatter([time]*len(content_freq_values), content_freq_values,
                       marker='o', s=50, c=fill_colors, edgecolors='green',
                       label="Content Bits" if i == 0 else "")
        if len(m_bits) >= 3 and m_bits[2] == 1 and footer_bits:
            footer_freq_values = [f[idx] for idx in footer_indices]
            fill_colors = ['white' if bit == 1 else 'black' for bit in footer_bits]
            ax.scatter([time]*len(footer_freq_values), footer_freq_values,
                       marker='o', s=50, c=fill_colors, edgecolors='red',
                       label="Footer Bits" if i == 0 else "")
    
    plt.legend()
    plt.show()

# --- Standalone Execution ---

def main():
    parser = argparse.ArgumentParser(
        description="Decode a Manchester-encoded WAV file into a BinaricRequest object with optional matplotlib debug output."
    )
    parser.add_argument("wav_file", help="Path to the input WAV file.")
    parser.add_argument("freq_config", help="Path to the frequency configuration JSON file.")
    parser.add_argument("--data_rate", type=float, default=10, help="Data rate (clock cycles per second).")
    parser.add_argument("--output", help="Output file to save the decoded request as JSON.")
    parser.add_argument("--plot", action="store_true", help="Display debug plots using matplotlib.")
    
    args = parser.parse_args()
    
    decoded_request = decode_binaric_request(args.wav_file, args.freq_config, args.data_rate, debug=args.plot)
    
    print("Decoded BinaricRequest object:")
    print(json.dumps(decoded_request, indent=4))
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(decoded_request, f, indent=4)
        print(f"Decoded request saved to {args.output}")
    
    if args.plot:
        plot_extraction_results(args.wav_file, args.freq_config, args.data_rate)

if __name__ == "__main__":
    main()
