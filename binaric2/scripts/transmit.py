import json
import math
import random
import numpy as np
from binaric2.classes.AudioBuffer import AudioBuffer as ab
from binaric2.scripts.AudioHelper import AudioHelper as ah

with open("binaric2/config/freq_config.json", "r") as f:
    FREQ_CONFIG = json.load(f)

def string_to_bitset(text, chunk_length):
    """Convert a string into a nested bitset array based on a given chunk length."""
    bit_string = ''.join(format(ord(char), '08b') for char in text)  # Convert each char to 8-bit binary
    bit_array = [int(bit) for bit in bit_string]  # Convert bit string to list of integers
    
    # Split into chunks of chunk_length
    bitset = [bit_array[i:i + chunk_length] for i in range(0, len(bit_array), chunk_length)]
    
    return bitset

def bitset_to_string(bitset):
    """Convert a nested bitset array back into a string."""
    flat_bits = [bit for chunk in bitset for bit in chunk]  # Flatten the list
    bit_string = ''.join(map(str, flat_bits))  # Convert bits to string
    char_list = [bit_string[i:i+8] for i in range(0, len(bit_string), 8)]  # Split into bytes
    
    return ''.join(chr(int(byte, 2)) for byte in char_list)  # Convert to characters and join


def build_content_sequence_from_bits(
    freqs,
    bitsets,
    clock_speed=FREQ_CONFIG["framework"]["clock_frequency"],
    sample_rate=44100
):
    """
    Minimal approach:
      - For each bitset, produce a segment of duration=1/clock_speed.
      - If bit=1, generate that freq's sine wave; if bit=0, silence.
      - Sum active frequencies and normalize to -1..1 per segment.
      - Concatenate all segments.
      - Return float32 array in range -1..1 (no final int16 conversion here).
    """
    
    seg_duration = 1.0 / clock_speed
    seg_length = int(seg_duration * sample_rate)

    # Pre-generate a sine wave for each freq (one segment long)
    tone_map = []
    for freq in freqs:
        # Sine wave in range -1..1 (float)
        wave = ah.create_sine_wave(freq, seg_duration, sample_rate).astype(np.float32)
        wave /= 32767.0  # convert from int16 amplitude to float -1..1
        tone_map.append(wave)

    all_segments = []

    for bitset in bitsets:
        if len(bitset) > len(freqs):
            raise ValueError(f"Bitset {bitset} has more bits than available freqs {len(freqs)}.")

        # Sum active tones
        segment = np.zeros(seg_length, dtype=np.float32)
        active_count = 0
        for i, bit in enumerate(bitset):
            if bit == 1:
                segment += tone_map[i]
                active_count += 1

        # If multiple bits were 1, scale down to avoid clipping
        if active_count > 1:
            segment /= active_count

        all_segments.append(segment)

    # Concatenate all segments
    if all_segments:
        audio_float = np.concatenate(all_segments)
    else:
        audio_float = np.zeros(0, dtype=np.float32)

    return audio_float  # still float in range -1..1





def convert_int_data_to_bits(num_freqs, data):
    """
    Convert a list of integers to their binary representation based on a given bit depth.

    Args:
        num_freqs (int): The number of bits to represent each integer.
        data (list or np.ndarray): A list of integers to convert.

    Returns:
        np.ndarray: A 2D NumPy array where each row represents an integer in binary.

    Raises:
        ValueError: If any integer in `data` exceeds the maximum value representable by `num_freqs` bits.
    """
    data=np.array(list(data))
    max_value = 2**num_freqs - 1  # Maximum value that can be represented in num_freqs bits

    if np.max(data) > max_value:
        raise ValueError(f"Cannot represent datapoint {np.max(data)} using {num_freqs} bits (max value: {max_value})")

    # Convert each integer to a binary string of length `num_freqs`
    bit_array = np.array(
        [list(f"{x:0{num_freqs}b}") for x in data], dtype=int  # Convert binary strings to integer array
    )

    return bit_array

def add_clock_signal(
    audio_float,
    freqs=FREQ_CONFIG["framework"]["clock"],
    clock_speed=FREQ_CONFIG["framework"]["clock_frequency"],
    sample_rate=44100
):
    """
    Minimal approach to add a clock signal:
      - audio_float is already in -1..1 range.
      - Build a clock track of same length in float range -1..1.
      - Sum them and normalize once at the end.
      - Convert to int16.
    """

    length_samples = len(audio_float)
    if length_samples == 0:
        return audio_float.astype(np.int16)  # Edge case: no audio

    total_time = length_samples / sample_rate
    cycles = int(math.floor(total_time * clock_speed))

    # Generate each clock cycle in float -1..1
    clock_segments = []
    seg_duration = 1.0 / clock_speed
    seg_length = int(seg_duration * sample_rate)

    for i in range(cycles):
        freq = freqs[i % len(freqs)]
        wave = ah.create_sine_wave(freq, seg_duration, sample_rate).astype(np.float32)
        wave /= 32767.0  # convert to -1..1 float
        clock_segments.append(wave)

    # Concatenate clock segments
    if clock_segments:
        clock_signal = np.concatenate(clock_segments)
    else:
        clock_signal = np.zeros(0, dtype=np.float32)

    # Pad or trim clock to match content length
    if len(clock_signal) < length_samples:
        clock_signal = np.pad(clock_signal, (0, length_samples - len(clock_signal)))
    else:
        clock_signal = clock_signal[:length_samples]

    # Combine in float
    combined = audio_float + clock_signal

    # Final normalization to avoid clipping
    max_val = np.max(np.abs(combined))
    if max_val > 1e-7:  # avoid divide-by-zero
        combined /= max_val
    # Scale to -1..1 at 90% to avoid borderline clipping
    combined *= 0.9

    # Convert to int16
    return (combined * 32767.0).astype(np.int16)



def build_transmission_sequence(data, mode="stable", freq_config = FREQ_CONFIG, debug = False):
    

    # Prepare AudioBuffer
    audio = ab()

    # 1. Generate random bitsets
    basis = freq_config["framework"]["basis_freq"]
    clockspeed = freq_config["framework"]["clock_frequency"]
    bitsets = string_to_bitset(data, len(basis))
    if debug: print(f"bitset is {bitsets}")
    # 2. Build content as float -1..1
    content_float = build_content_sequence_from_bits(
        freqs=basis,
        bitsets=bitsets,
        clock_speed=clockspeed,
        sample_rate=44100
    )

    # 3. Add clock (also in float, then final normalization -> int16)
    combined_int16 = add_clock_signal(
        audio_float=content_float,
        freqs=FREQ_CONFIG["framework"]["clock"],
        clock_speed=clockspeed,
        sample_rate=44100
    )

    audio.append_chunk(chunk=combined_int16.tobytes())
    return audio

if __name__ == "__main__":
    import random
    import numpy as np
    from binaric2.classes.AudioBuffer import AudioBuffer as ab

    audio = build_transmission_sequence("Hello World", debug=True)
    audio.save_to_wav("temp.wav")
