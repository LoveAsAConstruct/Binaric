import json
import wave
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import spectrogram

def read_config(config_path):
    """Read and return the JSON configuration."""
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

def read_wav(filename):
    """
    Read a WAV file and return a mono audio waveform and its sample rate.
    If the file is stereo, it is averaged to mono.
    """
    with wave.open(filename, 'rb') as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        n_frames = wf.getnframes()
        frames = wf.readframes(n_frames)
        # Assuming 16-bit PCM
        audio = np.frombuffer(frames, dtype=np.int16)
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels)
            audio = audio.mean(axis=1).astype(np.int16)
    return audio, sample_rate

def get_frequency_bounds(config):
    """
    Determine the frequency bounds to display from the config.
    Here we take the union of various frequency lists and add a small margin.
    """
    freq_list = []
    framework = config["framework"]
    
    # Basis frequencies, clock frequencies, and sequences from framework:
    freq_list.extend(framework.get("basis_freq", []))
    freq_list.extend(framework.get("clock", []))
    freq_list.extend(framework.get("init_sequence", []))
    freq_list.extend(framework.get("end_sequence", []))
    
    # Also include frequencies from all modes (optional if you want them too)
    for mode in config.get("modes", {}).values():
        freq_list.extend(mode.get("fingerprint_freq", []))
        freq_list.extend(mode.get("content", []))
    
    if not freq_list:
        return 0, None  # default: no bound if list is empty
    
    freq_array = np.array(freq_list, dtype=float)
    # Add a margin (e.g., 20% above max, 20% below min)
    lower_bound = np.min(freq_array) * 0.8
    upper_bound = np.max(freq_array) * 1.2
    return lower_bound, upper_bound

def main():
    # Path to the config file
    config_path = os.path.join("binaric2", "config", "freq_config.json")
    config = read_config(config_path)
    
    # Use the clock frequency from the framework (default to 1Hz if not provided)
    clock_frequency = config["framework"].get("clock_frequency", 1)
    
    # Get frequency bounds for display
    lower_bound, upper_bound = get_frequency_bounds(config)
    
    # Relevant y-axis ticks: clock freqs + basis freqs
    relevant_freqs = sorted(set(config["framework"].get("clock", []) +
                                config["framework"].get("basis_freq", [])))
    
    # Get the WAV file to process (passed as a command-line argument)
    if len(sys.argv) < 2:
        print("Usage: python -m binaric2.scripts.transmit path_to_audio.wav")
        sys.exit(1)
    
    wav_file = sys.argv[1]
    audio, sample_rate = read_wav(wav_file)
    
    # Now that we have sample_rate, compute spectrogram parameters
    # We'll choose a window (nperseg) and overlap (noverlap) so that
    # one "hop" ~ 1/clock_frequency, or some fraction thereof.
    hop_samples = int(sample_rate / (clock_frequency * 4))  # step size
    nperseg = hop_samples * 2 if hop_samples > 0 else 256     # window length
    
    f, t, Sxx = spectrogram(audio, fs=sample_rate,
                            nperseg=nperseg,
                            noverlap=hop_samples)
    
    # Plot the spectrogram (in dB)
    plt.figure(figsize=(10, 6))
    plt.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-12), shading='gouraud')
    plt.ylabel('Frequency [Hz]')
    plt.xlabel('Time [sec]')
    plt.title('Spectrogram')
    plt.colorbar(label='Power/Frequency (dB/Hz)')
    
    # Limit frequency axis to the bounds from the config (if available)
    if upper_bound is not None:
        plt.ylim(lower_bound, upper_bound)
    
    # ---- Add X-Axis Ticks for Each Clock Cycle ----
    total_time = len(audio) / sample_rate
    num_cycles = int(np.floor(total_time * clock_frequency))
    # Times at which each clock cycle starts:
    clock_times = [i / clock_frequency for i in range(num_cycles + 1)]
    plt.xticks(clock_times)
    
    # ---- Add Y-Axis Ticks for Relevant Frequencies ----
    if relevant_freqs:
        plt.yticks(relevant_freqs, [str(freq) for freq in relevant_freqs])
    
    plt.show()

if __name__ == "__main__":
    main()
