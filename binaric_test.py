import numpy as np
import wave
import math
import json
import struct

# Helper: convert a string to a binary representation (8 bits per character)
def string_to_bits(s):
    return ''.join(format(b, '08b') for b in s.encode('utf-8'))

# Helper: pad bit string to a multiple of group_size
def pad_bits(bits, group_size):
    r = len(bits) % group_size
    if r != 0:
        bits += '0' * (group_size - r)
    return bits

# **Manchester Encoding for Clock**
def manchester_encode(bit_string):
    """Converts a binary string into Manchester encoding."""
    encoded = ""
    for bit in bit_string:
        encoded += "10" if bit == "0" else "01"
    return encoded

# Generate a symbol tone by summing sine waves for frequencies where the bit is '1'
def generate_symbol_wave(symbol_bits, freqs, symbol_duration, sample_rate=44100, amplitude=0.5):
    t = np.linspace(0, symbol_duration, int(sample_rate * symbol_duration), endpoint=False)
    wave_sum = np.zeros_like(t)
    # For each bit and its associated frequency, add the sine wave if bit is 1.
    for bit, f in zip(symbol_bits, freqs):
        if bit == '1':
            wave_sum += amplitude * np.sin(2 * math.pi * f * t)
    return wave_sum

# Encode a complete segment from a bit string using the provided frequency list and symbol duration.
def encode_segment_from_bits(bit_string, freqs, symbol_duration, sample_rate=44100):
    bits_per_symbol = len(freqs)
    bit_string = pad_bits(bit_string, bits_per_symbol)
    symbols = [bit_string[i:i+bits_per_symbol] for i in range(0, len(bit_string), bits_per_symbol)]
    segment = np.concatenate([generate_symbol_wave(symbol, freqs, symbol_duration, sample_rate) for symbol in symbols])
    return segment

# **Manchester-Encoded Clock Signal**
def generate_manchester_clock_wave(clock_freqs, clock_speed, duration, sample_rate=44100, amplitude=0.2):
    """Generates a Manchester-encoded clock signal."""
    period = 1.0 / clock_speed  # Period of one clock cycle
    samples_per_period = int(sample_rate * period)
    
    # Manchester encoding: "0" → 10, "1" → 01
    clock_bits = "1010101010"  # Repeating pattern (10 = 0, 01 = 1)
    encoded_clock = manchester_encode(clock_bits)  # Convert to Manchester
    
    # Generate waveform
    wave_segments = []
    for bit in encoded_clock:
        freq = clock_freqs[0] if bit == "1" else clock_freqs[1]
        t = np.linspace(0, period/2, samples_per_period // 2, endpoint=False)
        wave_segments.append(amplitude * np.sin(2 * math.pi * freq * t))
    
    clock_wave = np.concatenate(wave_segments)
    
    # Repeat to fill the entire duration
    num_cycles = int(duration * clock_speed)
    clock_wave = np.tile(clock_wave, num_cycles)

    # Trim or pad to exact duration
    total_samples = int(sample_rate * duration)
    if len(clock_wave) > total_samples:
        clock_wave = clock_wave[:total_samples]
    else:
        clock_wave = np.pad(clock_wave, (0, total_samples - len(clock_wave)), 'constant')

    return clock_wave

# Write a numpy array to a WAV file (mono, 16-bit PCM).
def write_wav(filename, data, sample_rate=44100):
    # Normalize data to int16 range.
    if np.max(np.abs(data)) > 0:
        data_int16 = np.int16(data / np.max(np.abs(data)) * 32767)
    else:
        data_int16 = np.int16(data)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setparams((1, 2, sample_rate, len(data_int16), 'NONE', 'not compressed'))
        wav_file.writeframes(data_int16.tobytes())
    print(f"WAV file written to {filename}")

# Main encoding function that takes a BinaricFile object, a clock speed, a frequency band config,
# and writes out a WAV file with the Manchester-encoded clock signal.
def encode_binaric_file_to_wav(binaric_file, clock_speed, freq_config, output_filename, sample_rate=44100):
    # Durations (in seconds) for the segments.
    symbol_duration = 1/clock_speed  # Duration per symbol for header, content, footer segments
    
    # --- Header, Content, Footer Segments ---
    # Convert text fields to bit strings.
    header_bits = string_to_bits(binaric_file.header)
    payload_bits = string_to_bits(binaric_file.payload)
    footer_bits = string_to_bits(binaric_file.footer)
    
    # Encode header
    header_wave = encode_segment_from_bits(header_bits, freq_config['header'], symbol_duration, sample_rate)
    
    # Encode payload
    content_wave = encode_segment_from_bits(payload_bits, freq_config['content'], symbol_duration, sample_rate)
    
    # Encode footer
    footer_wave = encode_segment_from_bits(footer_bits, freq_config['footer'], symbol_duration, sample_rate)
    
    # Combine data segments
    data_wave = np.concatenate([header_wave, content_wave, footer_wave])
    
    # --- Manchester-Encoded Clock ---
    total_duration = len(data_wave) / sample_rate
    clock_wave = generate_manchester_clock_wave(freq_config['clock'], clock_speed, total_duration, sample_rate, amplitude=0.2)
    
    # Mix data and Manchester clock
    full_wave = data_wave + clock_wave
    
    # Write to WAV file
    write_wav(output_filename, full_wave, sample_rate)

# Example BinaricFile class (for static transmissions)
class BinaricFile:
    def __init__(self, header, payload, footer):
        self.header = header
        self.payload = payload
        self.footer = footer

def load_freq_config(json_file):
    """Loads frequency configuration from a JSON file."""
    with open(json_file, 'r') as f:
        return json.load(f)

# Example usage:
if __name__ == "__main__":
    # Create a sample BinaricFile object.
    bin_file = BinaricFile(
        header="HEADER: Integrity Test 1234567890",
        payload="PAYLOAD: 0123456789 ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz !@#$%^&*()-_=+",
        footer="FOOTER: End of Integrity Check."
    )

    
    # Load frequency configuration
    freq_config = load_freq_config("freq_bands.json")
    
    clock_speed = 2  # Clock cycles per second.
    
    # Encode binaric file to WAV with Manchester clocking.
    encode_binaric_file_to_wav(bin_file, clock_speed, freq_config, "binaric_transmission_with_manchester_clock_2.wav")
