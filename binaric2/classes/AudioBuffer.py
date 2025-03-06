import numpy as np
import wave

class AudioBuffer:
    """
    A simple audio buffer for storing, modifying, and processing audio signals.

    This class provides functionalities to:
    - Append audio data chunks dynamically.
    - Retrieve the latest chunk of audio data.
    - Save the stored audio to a WAV file.
    - Load audio from a WAV file.
    - Clear the buffer when needed.

    Attributes:
        sample_rate (int): The sample rate of the audio in Hz (default: 44100).
        channels (int): The number of audio channels (default: 1).
        dtype (numpy.dtype): The data type for audio samples (default: np.int16).
        buffer (numpy.ndarray): The array storing audio samples.

    Usage Example:
    --------------
    ```python
    import numpy as np

    # Create an AudioBuffer instance
    audio_buffer = AudioBuffer(sample_rate=44100, channels=1)

    # Generate a short sine wave (for demonstration purposes)
    duration = 1  # 1 second
    t = np.linspace(0, duration, int(audio_buffer.sample_rate * duration), endpoint=False)
    sine_wave = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)  # 440Hz tone

    # Append the generated audio data
    audio_buffer.append_chunk(sine_wave.tobytes())

    # Retrieve the latest chunk of 1024 samples
    latest_chunk = audio_buffer.get_latest_chunk(chunk_size=1024)

    # Save to a WAV file
    audio_buffer.save_to_wav("test_output.wav")

    # Load audio from an existing WAV file
    audio_buffer.load_from_wav("test_output.wav")

    # Clear the buffer
    audio_buffer.clear()
    ```
    """
    
    def __init__(self, sample_rate=44100, channels=1, dtype=np.int16):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.buffer = np.array([], dtype=dtype)  # Stores audio samples
    
    def append_chunk(self, chunk):
        """ 
        Append new audio data for streaming. 
        
        Args:
            chunk (bytes): Raw audio data to append.
        """
        data = np.frombuffer(chunk, dtype=self.dtype)
        self.buffer = np.append(self.buffer, data)

    def get_latest_chunk(self, chunk_size=1024):
        """ 
        Retrieve the latest chunk for streaming output.
        
        Args:
            chunk_size (int): Number of samples to retrieve (default: 1024).

        Returns:
            numpy.ndarray or None: The latest audio samples or None if insufficient data.
        """
        if len(self.buffer) < chunk_size:
            return None
        return self.buffer[-chunk_size:]

    def save_to_wav(self, filename="output.wav"):
        """ 
        Save the current buffer as a WAV file.

        Args:
            filename (str): The output filename (default: "output.wav").
        """
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # Assuming 16-bit PCM
            wf.setframerate(self.sample_rate)
            wf.writeframes(self.buffer.tobytes())

    def load_from_wav(self, filename):
        """ 
        Load audio data from a WAV file into the buffer.

        Args:
            filename (str): The input filename.
        """
        with wave.open(filename, 'rb') as wf:
            self.channels = wf.getnchannels()
            self.sample_rate = wf.getframerate()
            self.buffer = np.frombuffer(wf.readframes(-1), dtype=self.dtype)

    def clear(self):
        """ 
        Reset the buffer, removing all stored audio data.
        """
        self.buffer = np.array([], dtype=self.dtype)
