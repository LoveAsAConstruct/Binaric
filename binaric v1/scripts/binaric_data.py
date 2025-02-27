import json
import math

def int_to_base(n, base, pad=0):
    """Convert an integer to a list of digits in the given base with optional left padding."""
    if n < 0:
        raise ValueError("Negative numbers not supported.")
    digits = []
    if n == 0:
        digits = [0]
    else:
        while n:
            digits.append(n % base)
            n //= base
        digits.reverse()
    if pad > len(digits):
        digits = [0] * (pad - len(digits)) + digits
    return digits

def base_to_int(digits, base):
    """Convert a list of digits in the given base back to an integer."""
    value = 0
    for d in digits:
        value = value * base + d
    return value

class RawData:
    """
    Container for the raw data conversion.
    base: the numeric base (i.e. tone or bit depth)
    data: a list of digits representing the encoded value.
    """
    def __init__(self, base, data):
        self.base = base
        self.data = data  # list of integer digits

    def __repr__(self):
        return f"RawData(base={self.base}, data={self.data})"

class BinaricHeader:
    """
    Represents the header of a binaric request.
    In this version the header includes file information:
      - file_name (str)
      - file_size (int)
      - file_type (str)
      - content_base (int): the numeric base to be used when encoding the raw file data
    Additional metadata may also be included.
    
    The raw conversion encodes the header's file info as a JSON string, then converts
    each byte of the UTF-8 encoded string to digits in the specified base.
    """
    def __init__(self, file_name, file_size, file_type, content_base, metadata=None):
        self.file_name = file_name
        self.file_size = file_size
        self.file_type = file_type
        self.content_base = content_base  # base to use for content conversion
        self.metadata = metadata if metadata is not None else {}

    def __repr__(self):
        return (f"BinaricHeader(file_name='{self.file_name}', file_size={self.file_size}, "
                f"file_type='{self.file_type}', content_base={self.content_base}, "
                f"metadata={self.metadata})")

    def to_raw(self, base):
        """
        Convert the header file info to raw data using the given base (bit depth).
        The file info is first JSON-encoded and then each byte is converted.
        """
        info = {
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "content_base": self.content_base,
            "metadata": self.metadata
        }
        json_str = json.dumps(info)
        b = json_str.encode('utf-8')
        # For each byte, determine the number of digits needed in the given base.
        digits_per_byte = math.ceil(math.log(256, base))
        raw_digits = []
        for byte in b:
            raw_digits.extend(int_to_base(byte, base, pad=digits_per_byte))
        return RawData(base, raw_digits)

    @classmethod
    def from_raw(cls, raw_data, base):
        """
        Reconstruct a BinaricHeader from its RawData.
        Assumes the raw data represents a JSON string encoded as a sequence of bytes,
        where each byte was converted into digits using a fixed number of digits.
        """
        digits_per_byte = math.ceil(math.log(256, base))
        if len(raw_data.data) % digits_per_byte != 0:
            raise ValueError("Invalid header raw data length.")
        byte_values = []
        for i in range(0, len(raw_data.data), digits_per_byte):
            group = raw_data.data[i:i+digits_per_byte]
            byte_values.append(base_to_int(group, base))
        b = bytes(byte_values)
        info = json.loads(b.decode('utf-8'))
        return cls(info["file_name"], info["file_size"], info["file_type"],
                   info["content_base"], info.get("metadata"))

class BinaricContent:
    """
    Represents the content of a binaric request.
    Here the content is simply the raw file/data, stored as a bytes object.
    
    The raw conversion converts each byte of the file into digits in the specified base.
    Since a byte ranges from 0 to 255, we compute the number of digits needed for each byte.
    """
    def __init__(self, data):
        self.data = data  # expected to be a bytes object

    def __repr__(self):
        return f"BinaricContent(data_length={len(self.data)})"

    def to_raw(self, base):
        """
        Convert the raw file/data into a RawData object using the specified base.
        """
        digits_per_byte = math.ceil(math.log(256, base))
        raw_digits = []
        for byte in self.data:
            raw_digits.extend(int_to_base(byte, base, pad=digits_per_byte))
        return RawData(base, raw_digits)

    @classmethod
    def from_raw(cls, raw_data, base):
        """
        Reconstruct the BinaricContent from its RawData representation.
        """
        digits_per_byte = math.ceil(math.log(256, base))
        if len(raw_data.data) % digits_per_byte != 0:
            raise ValueError("Invalid content raw data length.")
        bytes_list = []
        for i in range(0, len(raw_data.data), digits_per_byte):
            group = raw_data.data[i:i+digits_per_byte]
            bytes_list.append(base_to_int(group, base))
        return cls(bytes(bytes_list))

class BinaricFooter:
    """
    Represents the footer of a binaric request.
    This remains mostly empty but can be extended (e.g. to include a checksum).
    """
    def __init__(self, metadata=None):
        self.metadata = metadata if metadata is not None else {}
        self.checksum = None  # Placeholder for a checksum

    def __repr__(self):
        return f"BinaricFooter(metadata={self.metadata}, checksum={self.checksum})"

    def to_raw(self, base):
        """
        Convert the footer into a RawData object.
        For now, if a checksum is present it is converted; otherwise, the result is empty.
        """
        if self.checksum is not None:
            digits = int_to_base(self.checksum, base)
        else:
            digits = []
        return RawData(base, digits)

    @classmethod
    def from_raw(cls, raw_data, base):
        """
        Reconstruct a BinaricFooter from RawData.
        """
        checksum = base_to_int(raw_data.data, base) if raw_data.data else None
        instance = cls()
        instance.checksum = checksum
        return instance

class BinaricRequest:
    """
    Top-level class representing a complete binaric request,
    composed of a header (with file info), the raw file/data as content, and a footer.
    
    The object is castable to a string (revealing all internal details) and can be
    converted to/from raw "binaric" data.
    """
    def __init__(self, header: BinaricHeader, content: BinaricContent, footer: BinaricFooter):
        self.header = header
        self.content = content
        self.footer = footer

    def __repr__(self):
        return (f"BinaricRequest(\n  header={self.header},\n  content_length={len(self.content.data)},\n  footer={self.footer}\n)")

    def __str__(self):
        return (f"BinaricRequest:\nHeader: {self.header}\nContent (raw data): {self.content.data}\nFooter: {self.footer}")

    def to_binaric(self, header_bitdepth=3, footer_bitdepth=3):
        """
        Converts the BinaricRequest into three RawData objects:
          - Header: using the provided header_bitdepth
          - Content: using the content_base specified in the header (file info)
          - Footer: using the provided footer_bitdepth
        """
        header_raw = self.header.to_raw(header_bitdepth)
        content_raw = self.content.to_raw(self.header.content_base)
        footer_raw = self.footer.to_raw(footer_bitdepth)
        return header_raw, content_raw, footer_raw

    @classmethod
    def from_binaric(cls, header_raw, content_raw, footer_raw, header_bitdepth=3):
        header = BinaricHeader.from_raw(header_raw, header_bitdepth)
        content = BinaricContent.from_raw(content_raw, header.content_base)
        footer = BinaricFooter.from_raw(footer_raw, header_bitdepth)
        return cls(header, content, footer)

# Example usage:
if __name__ == "__main__":
    # Suppose we have a file "example.txt" with the following properties:
    file_name = "example.txt"
    file_data = b"Hello, Binaric world!"
    file_size = len(file_data)
    file_type = "text"
    # Choose a content_base that is suitable for encoding raw bytes.
    # (For instance, base 16 allows each byte (0-255) to be encoded in at most 2 hex digits.)
    content_base = 16

    # Create the header with file info.
    header = BinaricHeader(file_name=file_name, file_size=file_size, file_type=file_type,
                           content_base=content_base, metadata={"version": "2.0"})

    # The content now simply holds the raw file data.
    content = BinaricContent(data=file_data)

    # Footer remains as before (could later include a checksum, etc.).
    footer = BinaricFooter(metadata={"note": "end-of-transmission"})

    # Create a complete binaric request.
    request = BinaricRequest(header, content, footer)

    # Display the full unravelled request.
    print(str(request))

    # Convert the request to raw binaric data.
    header_raw, content_raw, footer_raw = request.to_binaric(header_bitdepth=3, footer_bitdepth=3)
    print("\nRaw conversion:")
    print("Header raw:", header_raw)
    print("Content raw:", content_raw)
    print("Footer raw:", footer_raw)

    # Reconstruct the binaric request from its raw data.
    reconstructed_request = BinaricRequest.from_binaric(header_raw, content_raw, footer_raw, header_bitdepth=3)
    print("\nReconstructed Request:")
    print(reconstructed_request)
