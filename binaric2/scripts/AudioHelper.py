import numpy as np
import wave

class AudioHelper:
    """
    A helper class for generating, modifying, and combining NumPy-based audio waveforms.

    Provides functions for:
    - Generating basic waveforms (sine, square, noise).
    - Adding multiple waveforms together.
    - Normalizing and scaling audio.
    - Applying fade-in and fade-out effects.
    - Clearing and trimming audio buffers.
    """

    @staticmethod
    def create_sine_wave(frequency, duration, sample_rate=44100, amplitude=32767):
        """
        Generate a sine wave signal.

        Args:
            frequency (float): Frequency of the sine wave in Hz.
            duration (float): Duration in seconds.
            sample_rate (int): Sampling rate in Hz (default: 44100).
            amplitude (int): Amplitude of the wave (default: 32767 for 16-bit PCM).

        Returns:
            numpy.ndarray: Generated sine wave signal.
        """
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        wave = (np.sin(2 * np.pi * frequency * t) * amplitude).astype(np.int16)
        return wave

    @staticmethod
    def create_square_wave(frequency, duration, sample_rate=44100, amplitude=32767):
        """
        Generate a square wave signal.

        Args:
            frequency (float): Frequency of the square wave in Hz.
            duration (float): Duration in seconds.
            sample_rate (int): Sampling rate in Hz (default: 44100).
            amplitude (int): Amplitude of the wave (default: 32767 for 16-bit PCM).

        Returns:
            numpy.ndarray: Generated square wave signal.
        """
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        wave = (np.sign(np.sin(2 * np.pi * frequency * t)) * amplitude).astype(np.int16)
        return wave

    @staticmethod
    def create_white_noise(duration, sample_rate=44100, amplitude=32767):
        """
        Generate white noise.

        Args:
            duration (float): Duration in seconds.
            sample_rate (int): Sampling rate in Hz (default: 44100).
            amplitude (int): Amplitude of the noise (default: 32767 for 16-bit PCM).

        Returns:
            numpy.ndarray: Generated white noise.
        """
        samples = int(sample_rate * duration)
        noise = np.random.uniform(-1, 1, samples) * amplitude
        return noise.astype(np.int16)

    @staticmethod
    def combine_audio(*waveforms):
        """
        Combine multiple waveforms by summing them together.

        Args:
            *waveforms: Variable number of NumPy arrays representing waveforms.

        Returns:
            numpy.ndarray: Combined audio signal.
        """
        max_length = max(len(w) for w in waveforms)
        combined = np.zeros(max_length, dtype=np.int32)  # Use int32 to prevent overflow

        for wave in waveforms:
            combined[:len(wave)] += wave

        # Clip to int16 range
        return np.clip(combined, -32768, 32767).astype(np.int16)

    @staticmethod
    def normalize_audio(waveform):
        """
        Normalize audio to the full int16 range.

        Args:
            waveform (numpy.ndarray): Input waveform.

        Returns:
            numpy.ndarray: Normalized waveform.
        """
        max_val = np.max(np.abs(waveform))
        if max_val == 0:
            return waveform  # Avoid division by zero
        return (waveform / max_val * 32767).astype(np.int16)

    @staticmethod
    def apply_fade_in(waveform, duration, sample_rate=44100):
        """
        Apply a fade-in effect to the waveform.

        Args:
            waveform (numpy.ndarray): Input waveform.
            duration (float): Duration of the fade-in in seconds.
            sample_rate (int): Sampling rate in Hz.

        Returns:
            numpy.ndarray: Waveform with fade-in applied.
        """
        num_samples = int(sample_rate * duration)
        fade_curve = np.linspace(0, 1, num_samples)
        waveform[:num_samples] = (waveform[:num_samples] * fade_curve).astype(np.int16)
        return waveform

    @staticmethod
    def apply_fade_out(waveform, duration, sample_rate=44100):
        """
        Apply a fade-out effect to the waveform.

        Args:
            waveform (numpy.ndarray): Input waveform.
            duration (float): Duration of the fade-out in seconds.
            sample_rate (int): Sampling rate in Hz.

        Returns:
            numpy.ndarray: Waveform with fade-out applied.
        """
        num_samples = int(sample_rate * duration)
        fade_curve = np.linspace(1, 0, num_samples)
        waveform[-num_samples:] = (waveform[-num_samples:] * fade_curve).astype(np.int16)
        return waveform

    @staticmethod
    def clear_audio():
        """
        Returns an empty audio buffer.

        Returns:
            numpy.ndarray: Empty waveform.
        """
        return np.array([], dtype=np.int16)

    @staticmethod
    def trim_audio(waveform, start_time, end_time, sample_rate=44100):
        """
        Trim the audio waveform between specified start and end times.

        Args:
            waveform (numpy.ndarray): Input waveform.
            start_time (float): Start time in seconds.
            end_time (float): End time in seconds.
            sample_rate (int): Sampling rate in Hz.

        Returns:
            numpy.ndarray: Trimmed waveform.
        """
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate)
        return waveform[start_sample:end_sample]

    @staticmethod
    def save_wav(filename, waveform, sample_rate=44100, channels=1):
        """
        Save a waveform to a WAV file.

        Args:
            filename (str): Output filename.
            waveform (numpy.ndarray): Audio waveform.
            sample_rate (int): Sampling rate in Hz.
            channels (int): Number of audio channels.

        Returns:
            None
        """
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # Assuming 16-bit PCM
            wf.setframerate(sample_rate)
            wf.writeframes(waveform.tobytes())

    @staticmethod
    def concatenate_audio(*waveforms):
        """
        Concatenate multiple waveforms sequentially.

        Args:
            *waveforms: Variable-length list of NumPy arrays representing waveforms.

        Returns:
            numpy.ndarray: Concatenated audio signal.
        """
        return np.concatenate(waveforms)

    @staticmethod
    def load_wav(filename):
        """
        Load audio from a WAV file.

        Args:
            filename (str): Input WAV file.

        Returns:
            numpy.ndarray: Loaded audio waveform.
            int: Sample rate of the file.
            int: Number of channels.
        """
        with wave.open(filename, 'rb') as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            waveform = np.frombuffer(wf.readframes(-1), dtype=np.int16)
        return waveform, sample_rate, channels
