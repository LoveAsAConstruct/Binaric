from dataclasses import dataclass, field
from typing import Optional, Any
import hashlib
import json

@dataclass
class NegotiationPackage:
    """
    Reserved for future negotiation of payload transmission parameters.
    """
    payload_frequency: int = 440    # Default frequency in Hz (example)
    payload_speed: float = 1.0      # Default transmission speed (units arbitrary)

    def to_dict(self) -> dict:
        return {"payload_frequency": self.payload_frequency, "payload_speed": self.payload_speed}

@dataclass
class ControlHeader:
    """
    This header is always sent using a constant clock and preset audio frequencies.
    It contains metadata, timing information and a field for future negotiation.
    """
    file_id: str
    file_type: str
    dynamic: bool
    clock: float                   # Clock signal value (e.g., timestamp or frequency marker)
    preset_frequency: int = 1000   # Fixed frequency for control channel (Hz)
    negotiation: NegotiationPackage = field(default_factory=NegotiationPackage)
    checksum: Optional[str] = None

    def compute_checksum(self, content: Any) -> str:
        """
        Compute a checksum from the header and content.
        Here we simply use a hash of the JSON representation.
        """
        data = json.dumps({
            "file_id": self.file_id,
            "file_type": self.file_type,
            "dynamic": self.dynamic,
            "clock": self.clock,
            "preset_frequency": self.preset_frequency,
            "negotiation": self.negotiation.to_dict(),
            "content": content
        }, sort_keys=True).encode('utf-8')
        self.checksum = hashlib.sha256(data).hexdigest()
        return self.checksum

@dataclass
class ControlMessage:
    """
    Represents a control message, which always uses the fixed header settings.
    This is used for synchronization, handshake, and error reporting.
    """
    header: ControlHeader
    message: str

@dataclass
class PayloadMessage:
    """
    Represents the payload part of the transmission.
    Initially, payload transmission settings are not negotiated, but
    this class is designed to eventually incorporate variable parameters.
    """
    content: bytes
    # Future field: custom_payload_frequency, custom_payload_speed

@dataclass
class BinaricFile:
    """
    Represents the overall file used in the protocol, including header (control),
    content (payload), and a simple footer.
    """
    header: ControlHeader
    payload: PayloadMessage
    footer: dict = field(default_factory=lambda: {"end_flag": True})

    def compute_checksum(self):
        """
        Computes and updates the checksum in the header using the payload content.
        """
        return self.header.compute_checksum(self.payload.content.decode('utf-8', errors='ignore'))

    def to_wav(self, filename: str):
        """
        Convert the BinaricFile to a BINARIC WAV format.
        This is a stub to indicate where the conversion would occur.
        """
        # Implementation would convert header, payload, and footer into an audio file
        with open(filename, 'wb') as f:
            # Example: write header JSON, payload bytes, and footer JSON as an audio container.
            f.write(json.dumps(self.header.__dict__).encode('utf-8'))
            f.write(self.payload.content)
            f.write(json.dumps(self.footer).encode('utf-8'))
        print(f"WAV file written to {filename}")

# Example usage:
if __name__ == "__main__":
    # Create a control header with fixed clock signal
    header = ControlHeader(
        file_id="file123",
        file_type="request",
        dynamic=True,
        clock=1234567890.0  # This could be a timestamp or defined clock signal value
    )

    # Create a payload message (this could be binary data from a file)
    payload = PayloadMessage(content=b"Sample payload content.")

    # Create a BinaricFile instance
    binaric_file = BinaricFile(header=header, payload=payload)

    # Compute checksum
    checksum = binaric_file.compute_checksum()
    print("Computed Checksum:", checksum)

    # Convert to a BINARIC WAV file (stub implementation)
    binaric_file.to_wav("output.binaric.wav")
