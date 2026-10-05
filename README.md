# steg-png
Hide short messages in PNG images using LSB steganography. Pure Python, standard library only.
steg-png

Hide short text messages inside PNG images using LSB (least significant bit) steganography.

Pure Python, standard library only — no Pillow, no NumPy, nothing to install.

Features
Hides up to 510 ASCII characters in a PNG image
Changes are invisible to the eye (each colour value shifts by at most 1/256)
Bits are spread across the whole image instead of packed in one corner
Reads and writes PNG files natively (zlib decompression, PNG filters, CRC)
The message is typed at a prompt, so it never ends up in your shell history
Requirements
Python 3 (preinstalled on most Linux distributions)
A PNG image: 8 bits per channel, RGB or RGBA, non-interlaced (screenshots usually qualify)
Usage

Hide a message:

```bash
python3 steg_png.py hide input.png output.png
```

You will be prompted for the message.

Extract it:

```bash
python3 steg_png.py extract output.png
```

How it works
Data = 2-byte length (big-endian) + the message in ASCII.
Only the R, G, B colour bytes are used (alpha is ignored), numbered row by row from the top-left pixel. step = (width × height × 3) // 4096
Bit k of the data (byte by byte, most significant bit first) replaces the least significant bit of the colour byte at rank k × step.

The output PNG is re-encoded losslessly, so its file size may differ from the original.

Limitations
No encryption, no key. Anyone with this tool can extract the message. Encrypt your message before hiding it if it must stay confidential.
Fragile. Any lossy conversion destroys the message: resizing, editing, or sending through messaging apps that recompress images.
Detectable. Statistical steganalysis tools may flag the image as modified. This tool hides the presence of a message from casual inspection, not from forensic analysis.
Palette-based, 16-bit and interlaced PNGs are not supported.

Tips
Use an image you created yourself (e.g. a screenshot) and delete the original afterwards, so nobody can compare the two.
Always run extract right after hide to check the message was stored correctly.
