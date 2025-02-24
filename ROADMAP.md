# BINARIC Project Roadmap

## Overview
BINARIC is a modular audio-based data transfer system designed to facilitate efficient, structured communication between nearby devices using sound. The system consists of multiple components, each handling a specific role within the network, ensuring seamless data transmission, reception, and management.

## Project Structure
```
BINARIC/
│── binaric/
│   │── __init__.py
│   │── core/
│   │   │── binaric_stream.py
│   │   │── binaric_file.py
│   │   │── modulation.py
│   │   │── error_correction.py
│   │   │── handshake.py
│   │   │── packet_manager.py
│   │── scripts/
│   │   │── uploader.py
│   │   │── downloader.py
│   │   │── stream_node.py
│   │   │── wav_generator.py
│   │── utils/
│   │   │── audio_processing.py
│   │   │── config.py
│   │   │── logger.py
│── tests/
│── docs/
│── ROADMAP.md
│── README.md
```

## Core Modules
These modules handle the core functionalities of BINARIC and are designed to be reusable across different scripts.

### 1. `binaric_stream.py`
- Manages BINARIC instances and keeps track of active connections.
- Handles message queuing, request caching, and real-time data synchronization.
- Supports both real-time and stored file transmission.

### 2. `binaric_file.py`
- Defines a BINARIC file object that encapsulates a request/query.
- Includes a **header**, **content**, and **footer**.
- Supports streaming to files and conversion into `.wav` format for offline transmission.
- Provides methods for reading and writing BINARIC files efficiently.

#### **Schema of BINARIC File Object**
```json
{
  "header": {
    "file_id": "unique_id",
    "file_type": "data/query",
    "timestamp": "ISO-8601",
    "checksum": "hash"
  },
  "content": "base64_encoded_data",
  "footer": {
    "signature": "optional_digital_signature",
    "end_flag": true
  }
}
```

### 3. `modulation.py`
- Implements Frequency Shift Keying (FSK), Phase Shift Keying (PSK), and Quadrature Amplitude Modulation (QAM) for encoding data into sound.
- Ensures efficient conversion of binary data into sound waves.

### 4. `error_correction.py`
- Implements error detection and correction mechanisms such as CRC and Reed-Solomon codes.
- Ensures data integrity across transmissions.

### 5. `handshake.py`
- Manages initial communication between BINARIC instances.
- Negotiates transmission parameters such as modulation type, error correction level, and transmission speed.

### 6. `packet_manager.py`
- Splits files into transmission-ready packets.
- Adds necessary headers, sequence numbers, and error-checking bits.
- Reassembles received packets into the original file.

## Scripts
These scripts utilize the core modules to perform specific tasks.

### 1. `uploader.py`
**Functionality:**
- Uses a microphone to detect nearby BINARIC instances.
- Establishes a connection and transmits a selected file.
- Terminates the session after successful file transfer.

**Inputs:**
- File to be sent.
- Transmission mode (real-time or pre-recorded).

**Outputs:**
- Transmission confirmation.
- Error log in case of failure.

### 2. `downloader.py`
**Functionality:**
- Listens for incoming BINARIC file transfers.
- Automatically downloads and reassembles files sent to the device.
- Saves received files to a specified directory.

**Inputs:**
- Active listening mode enabled.

**Outputs:**
- Received file stored on disk.
- Metadata logs.

### 3. `stream_node.py`
**Functionality:**
- Acts as a persistent BINARIC relay node.
- Maintains active connections with multiple instances, handling both uploads and downloads.
- Caches ongoing transfers and optimizes bandwidth usage.

**Inputs:**
- List of active BINARIC connections.

**Outputs:**
- Continuous data exchange between nodes.
- Connection stability metrics.

### 4. `wav_generator.py`
**Functionality:**
- Generates BINARIC `.wav` files for pre-programmed audio data transfers.
- Can encode a file’s binary data into an audio file for offline transmission.
- Includes metadata headers to specify transmission mode and error correction settings.
- Supports generating non-interactive BINARIC audio that does not require real-time negotiation.

**Inputs:**
- File to be converted.
- Modulation and error correction settings.

**Outputs:**
- `.wav` file ready for playback.

## Utility Modules
Helper functions that support the core functionalities and scripts.

### 1. `audio_processing.py`
- Handles audio input/output.
- Converts microphone recordings into digital signals.
- Performs real-time audio filtering and noise reduction.

### 2. `config.py`
- Stores global configuration settings.
- Defines modulation schemes, error correction parameters, and session timeouts.

### 3. `logger.py`
- Handles logging and debugging.
- Records session data, errors, and performance metrics.

## High-Level Functionalities
### **File Upload & Download**
- The uploader detects nearby BINARIC instances and transmits files using modulation and error correction.
- The downloader listens for transmissions and reassembles received files.

### **Streaming Data**
- The BINARIC stream node manages active connections and ensures smooth data exchange.
- Real-time streaming between multiple BINARIC nodes.

### **Audio File Generation**
- The wav generator produces pre-encoded BINARIC audio files for offline transfers.

### **Microphone-Based Communication**
- The system supports direct transmission via speakers and reception via microphones.
- Enables ad-hoc file sharing without requiring internet or traditional networks.

## Future Enhancements
- **Adaptive Modulation:** Implement dynamic switching between modulation schemes based on signal quality.
- **Encryption Layer:** Secure file transfers using lightweight encryption.
- **Mobile App Integration:** Create a mobile-friendly interface for BINARIC-based communication.
- **Compression Mechanism:** Improve data transmission efficiency using audio-optimized compression.

## Conclusion
This roadmap outlines the structured implementation of BINARIC, ensuring modularity, scalability, and robust performance for audio-based data communication. The combination of core functionalities, flexible scripting, and utility modules provides a solid foundation for real-world deployment and future expansion.

