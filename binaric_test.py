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

# Generate a continuous clock waveform over a given duration.
def generate_continuous_clock_wave(clock_freqs, clock_speed, duration, sample_rate=44100, amplitude=0.2):
    # clock_freqs: list of two frequencies, e.g., [f_on, f_off]
    # clock_speed: clock cycles per second; period = 1/clock_speed.
    period = 1.0 / clock_speed
    samples_per_period = int(sample_rate * period)
    # First half of the period uses clock_freqs[0], second half uses clock_freqs[1]
    samples_half = samples_per_period // 2
    t_half = np.linspace(0, period/2, samples_half, endpoint=False)
    # Ensure we fill the full period in case of rounding differences.
    cycle = np.concatenate([
        amplitude * np.sin(2 * math.pi * clock_freqs[0] * t_half),
        amplitude * np.sin(2 * math.pi * clock_freqs[1] * np.linspace(0, period/2, samples_per_period - samples_half, endpoint=False))
    ])
    num_cycles = int(duration * clock_speed)
    clock_wave = np.tile(cycle, num_cycles)
    # Trim or pad to match the exact number of samples for the given duration.
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
# and writes out a WAV file with the clock signal underlaying the entire transmission.
def encode_binaric_file_to_wav(binaric_file, clock_speed, freq_config, output_filename, sample_rate=44100):
    # Durations (in seconds) for the segments. These can be tuned.
    symbol_duration = 0.1  # Duration per symbol for header, content, footer segments
    
    # --- Header, Content, Footer Segments ---
    # Convert text fields to bit strings.
    header_bits = string_to_bits(binaric_file.header)
    payload_bits = string_to_bits(binaric_file.payload)
    footer_bits = string_to_bits(binaric_file.footer)
    
    # Encode header (using its dedicated frequency band, e.g., 3 frequencies => 3 bits per symbol).
    header_wave = encode_segment_from_bits(header_bits, freq_config['header'], symbol_duration, sample_rate)
    
    # Encode payload (using its dedicated frequency band, e.g., 10 frequencies => 10 bits per symbol).
    content_wave = encode_segment_from_bits(payload_bits, freq_config['content'], symbol_duration, sample_rate)
    
    # Encode footer (using footer frequency band, for instance, same as header).
    footer_wave = encode_segment_from_bits(footer_bits, freq_config['footer'], symbol_duration, sample_rate)
    
    # Combine data segments in order: header, content, footer.
    data_wave = np.concatenate([header_wave, content_wave, footer_wave])
    
    # --- Clock Underlay ---
    # Generate a continuous clock signal spanning the full duration of the data transmission.
    total_duration = len(data_wave) / sample_rate
    clock_wave = generate_continuous_clock_wave(freq_config['clock'], clock_speed, total_duration, sample_rate, amplitude=0.2)
    
    # Mix the data and clock signals (the clock underlays the data).
    full_wave = data_wave + clock_wave
    
    # Write the combined waveform to a WAV file.
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
        header="HEADER: file metadata",
        payload="PAYLOAD: This is the main content of the binaric transmission.",
        footer="FOOTER: end of transmission"
    )
    
    # Frequency band configuration.
    # Each key defines the frequency list for that segment.
    freq_config = load_freq_config("freq_bands.json")
    
    clock_speed = 10  # Clock cycles per second.
    
    # Encode the binaric file into a WAV file with clock underlay.
    encode_binaric_file_to_wav(bin_file, clock_speed, freq_config, "binaric_transmission_with_clock.wav")
