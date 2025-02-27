#!/usr/bin/env python3
import numpy as np
import wave
import math
import json
import argparse
import base64

# --- Helper Functions for Bit Conversions and Padding ---

def string_to_bits(s):
    """Convert a string to its binary representation (8 bits per character)."""
    return ''.join(format(b, '08b') for b in s.encode('utf-8'))

def bytes_to_bits(b_data):
    """Convert bytes to a binary string (8 bits per byte)."""
    return ''.join(format(b, '08b') for b in b_data)

def pad_bits(bits, group_size):
    """Pad a bit string to a multiple of the given group size."""
    r = len(bits) % group_size
    if r != 0:
        bits += '0' * (group_size - r)
    return bits

# --- Manchester Encoding and Tone Generation ---

def manchester_encode(bit_string):
    """
    Convert a binary string into Manchester encoding.
    For each bit, "0" becomes "10" and "1" becomes "01".
    """
    encoded = ""
    for bit in bit_string:
        encoded += "10" if bit == "0" else "01"
    return encoded

def generate_symbol_wave(symbol_bits, freqs, symbol_duration, sample_rate=44100, amplitude=0.5):
    """
    Generate a symbol waveform by summing sine waves for frequencies where the bit is '1'.
    Each symbol is generated over a duration determined by symbol_duration.
    """
    t = np.linspace(0, symbol_duration, int(sample_rate * symbol_duration), endpoint=False)
    wave_sum = np.zeros_like(t)
    for bit, f in zip(symbol_bits, freqs):
        if bit == '1':
            wave_sum += amplitude * np.sin(2 * math.pi * f * t)
    return wave_sum

def encode_segment_from_bits(bit_string, freqs, symbol_duration, sample_rate=44100):
    """
    Encode a complete segment from a bit string using a list of frequencies.
    The bit string is broken into groups (symbols) where each symbol length equals len(freqs).
    """
    bits_per_symbol = len(freqs)
    bit_string = pad_bits(bit_string, bits_per_symbol)
    symbols = [bit_string[i:i+bits_per_symbol] for i in range(0, len(bit_string), bits_per_symbol)]
    segment = np.concatenate([generate_symbol_wave(symbol, freqs, symbol_duration, sample_rate)
                               for symbol in symbols])
    return segment

def generate_manchester_clock_wave(clock_freqs, clock_speed, duration, sample_rate=44100, amplitude=0.2):
    """
    Generate a Manchester-encoded clock signal.
    
    clock_freqs: list of two frequencies; the first is used for a Manchester '1' and the
                 second for a '0'.
    clock_speed: clock cycles per second.
    duration: total duration of the clock signal in seconds.
    """
    period = 1.0 / clock_speed
    samples_per_period = int(sample_rate * period)
    
    # Use a simple repeating bit pattern for Manchester encoding.
    clock_bits = "1010101010"
    encoded_clock = manchester_encode(clock_bits)
    
    wave_segments = []
    for bit in encoded_clock:
        freq = clock_freqs[0] if bit == "1" else clock_freqs[1]
        t = np.linspace(0, period/2, samples_per_period // 2, endpoint=False)
        wave_segments.append(amplitude * np.sin(2 * math.pi * freq * t))
    
    clock_wave = np.concatenate(wave_segments)
    num_cycles = int(duration * clock_speed)
    clock_wave = np.tile(clock_wave, num_cycles)
    
    total_samples = int(sample_rate * duration)
    if len(clock_wave) > total_samples:
        clock_wave = clock_wave[:total_samples]
    else:
        clock_wave = np.pad(clock_wave, (0, total_samples - len(clock_wave)), 'constant')
    
    return clock_wave

# --- WAV File Output ---

def write_wav(filename, data, sample_rate=44100):
    """
    Write a numpy array (mono, 16-bit PCM) to a WAV file.
    Data is normalized to the int16 range.
    """
    if np.max(np.abs(data)) > 0:
        data_int16 = np.int16(data / np.max(np.abs(data)) * 32767)
    else:
        data_int16 = np.int16(data)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setparams((1, 2, sample_rate, len(data_int16), 'NONE', 'not compressed'))
        wav_file.writeframes(data_int16.tobytes())
    print(f"WAV file written to {filename}")

def add_mode_frequency_overlay(base_wave, mode_freq, sample_rate=44100, amplitude=0.2):
    """
    Overlay a continuous sine wave tone (mode frequency) over the entire base waveform.

    :param base_wave: The original waveform to overlay the mode frequency onto.
    :param mode_freq: The frequency of the mode tone.
    :param sample_rate: The audio sample rate.
    :param amplitude: The amplitude of the overlay tone.
    :return: The modified waveform with the mode frequency added.
    """
    duration = len(base_wave) / sample_rate  # Total duration of the wave
    t = np.linspace(0, duration, len(base_wave), endpoint=False)
    
    # Generate the mode frequency wave
    mode_wave = amplitude * np.sin(2 * np.pi * mode_freq * t)
    
    # Overlay the mode frequency onto the original waveform
    return base_wave + mode_wave


def add_prefix_wave(base_wave, prefix_freqs, clock_speed, sample_rate=44100, amplitude=0.5):
    """
    Generate a structured prefix wave using the given frequency list and clock timing.
    
    Sequence:
    1. Turn on all frequencies for 5 cycles.
    2. Turn off all frequencies for 1 cycle.
    3. Turn on all frequencies for 1 cycle.
    4. Step through the array, turning each frequency off for 1 cycle.
    5. Step through the array, turning each frequency on for 1 cycle.
    6. Turn off all frequencies for 1 final cycle.

    :param base_wave: Main signal to prepend prefix to.
    :param prefix_freqs: List of frequencies to use in the prefix.
    :param clock_cycles: Number of cycles per step.
    :param clock_speed: Clock speed (cycles per second).
    :param sample_rate: Audio sample rate.
    :param amplitude: Amplitude of the prefix wave.
    :return: Concatenated prefix + base wave.
    """
    period = 1.0 / clock_speed  # Duration of one cycle
    samples_per_cycle = int(sample_rate * period)  # Samples per clock cycle
    
    def generate_wave(frequencies, duration_cycles):
        """Generate a waveform with the given frequencies for a specified number of cycles."""
        t = np.linspace(0, duration_cycles * period, duration_cycles * samples_per_cycle, endpoint=False)
        wave = np.zeros_like(t)
        for freq in frequencies:
            wave += amplitude * np.sin(2 * np.pi * freq * t)
        return wave
    
    # 1. Turn on all frequencies for 5 cycles
    prefix_wave = generate_wave(prefix_freqs, 5)
    
    # 2. Turn off all frequencies for 1 cycle
    prefix_wave = np.concatenate([prefix_wave, np.zeros(samples_per_cycle)])
    
    # 3. Turn on all frequencies for 1 cycle
    prefix_wave = np.concatenate([prefix_wave, generate_wave(prefix_freqs, 1)])
    
    # 4. Step through the array, turning each frequency OFF for 1 cycle
    for i in range(len(prefix_freqs)):
        reduced_freqs = prefix_freqs[:i] + prefix_freqs[i+1:]  # Remove one frequency
        prefix_wave = np.concatenate([prefix_wave, generate_wave(reduced_freqs, 1)])
    
    # 5. Step through the array, turning each frequency ON for 1 cycle
    for i in range(len(prefix_freqs)):
        selective_freqs = prefix_freqs[:i+1]  # Include one more frequency
        prefix_wave = np.concatenate([prefix_wave, generate_wave(selective_freqs, 1)])
    
    # 6. Turn off all frequencies for 1 final cycle
    prefix_wave = np.concatenate([prefix_wave, np.zeros(samples_per_cycle)])

    return np.concatenate([prefix_wave, base_wave])


# --- Request File to Audio Transcription ---

def transcribe_request_to_audio(request, clock_speed, freq_config, sample_rate=44100):
    """
    Transcribe a binaric request into audio data.
    
    The request is a dictionary with keys:
      - "header": a dict containing file info (will be JSON-encoded).
      - "content": a base64-encoded string representing the raw file/data.
      - "footer": a string.
    
    freq_config should be a dictionary with keys:
      - "header": list of frequencies for header encoding.
      - "content": list of frequencies for content encoding.
      - "footer": list of frequencies for footer encoding.
      - "clock": list of two frequencies for the Manchester clock.
    
    Returns a numpy array with the final audio waveform.
    """
    symbol_duration = 1.0 / clock_speed
    
    # Process header: convert the header dict to a JSON string and then to bits.
    header_json = json.dumps(request.get("header", {}))
    header_bits = string_to_bits(header_json)
    
    # Process content: decode base64 to bytes, then convert to bits.
    content_b64 = request.get("content", "")
    try:
        content_bytes = base64.b64decode(content_b64)
    except Exception as e:
        print("Error decoding content from base64:", e)
        content_bytes = b""
    content_bits = bytes_to_bits(content_bytes)
    
    # Process footer: convert footer string to bits.
    footer_text = request.get("footer", "")
    footer_bits = string_to_bits(footer_text)
    
    # Encode each segment.
    header_wave = add_mode_frequency_overlay(encode_segment_from_bits(header_bits, freq_config.get("header", []), symbol_duration, sample_rate), mode_freq=freq_config["modes"][0])
    content_wave = add_mode_frequency_overlay(encode_segment_from_bits(content_bits, freq_config.get("content", []), symbol_duration, sample_rate), mode_freq=freq_config["modes"][1])
    footer_wave = add_mode_frequency_overlay(encode_segment_from_bits(footer_bits, freq_config.get("footer", []), symbol_duration, sample_rate), mode_freq=freq_config["modes"][2])
    
    data_wave = np.concatenate([header_wave, content_wave, footer_wave])
    
    total_duration = len(data_wave) / sample_rate
    clock_wave = generate_manchester_clock_wave(freq_config.get("clock", []),
                                                 clock_speed,
                                                 total_duration,
                                                 sample_rate,
                                                 amplitude=0.2)
    
    full_wave = data_wave + clock_wave
    return full_wave

# --- File Loading Utilities ---

def load_request_file(request_filename):
    """
    Load a request file (JSON format) and return its content as a dictionary.
    
    The JSON file must contain:
      - "header": a dictionary with file info.
      - "content": a base64-encoded string of the raw file/data.
      - "footer": a string.
    """
    with open(request_filename, 'r') as f:
        request = json.load(f)
    return request

def load_freq_config(json_file):
    """
    Load a frequency configuration from a JSON file.
    
    The configuration should provide frequency lists for:
      - "header", "content", "footer", and "clock".
    """
    with open(json_file, 'r') as f:
        return json.load(f)

# --- Standalone Execution ---

def main():
    parser = argparse.ArgumentParser(description="Transcribe a binaric request file into audio data (.wav).")
    parser.add_argument("request_file", help="Path to the binaric request file (JSON format).")
    parser.add_argument("output_wav", help="Path to the output WAV file.")
    parser.add_argument("--freq_config", default="binaric/utils/freq_bands_stable.json", help="Path to frequency configuration JSON file.")
    parser.add_argument("--clock_speed", type=float, default=5.0, help="Clock cycles per second.")
    parser.add_argument("--sample_rate", type=int, default=44100, help="Audio sample rate.")
    
    args = parser.parse_args()
    
    request = load_request_file(args.request_file)
    freq_config = load_freq_config(args.freq_config)
    
    audio_wave = transcribe_request_to_audio(request, args.clock_speed, freq_config, args.sample_rate)
    write_wav(args.output_wav, audio_wave, args.sample_rate)

if __name__ == "__main__":
    main()
