"""Create a simple Open Graph image for JustMailIt"""
import struct

def create_simple_png(filename, width=1200, height=630, color=(0, 123, 255)):
    """Create a simple solid color PNG image"""
    
    # PNG header
    png_header = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr_crc = 0x13c07693  # Pre-calculated CRC for typical IHDR
    ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
    
    # Create simple blue gradient image data
    idat_data = b''
    for y in range(height):
        # Each row starts with filter type 0 (none)
        row = bytes([0])
        for x in range(width):
            # RGB values - create a gradient effect
            r = color[0]
            g = color[1] + int((255 - color[1]) * (y / height) * 0.3)
            b = color[2]
            row += bytes([r, g, b])
        idat_data += row
    
    # Compress the image data
    import zlib
    compressed = zlib.compress(idat_data, 9)
    
    # IDAT chunk
    idat_chunk = struct.pack('>I', len(compressed)) + b'IDAT' + compressed
    idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
    idat_chunk += struct.pack('>I', idat_crc)
    
    # IEND chunk
    iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', 0xae426082)
    
    # Write PNG file
    with open(filename, 'wb') as f:
        f.write(png_header + ihdr_chunk + idat_chunk + iend_chunk)
    
    print(f"✅ Created {width}x{height} PNG image: {filename}")

if __name__ == '__main__':
    create_simple_png('sendmail/static/images/justmailit-og-image.png', color=(0, 123, 255))
