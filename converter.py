import os
import mimetypes
import subprocess
import ffmpeg
import brotli
import zstandard as zstd
from PIL import Image
from pydub import AudioSegment
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_path
import zipfile

# HEIC Support (iPhone photos)
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

# SVG Support
try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    SVG_SUPPORTED = True
except ImportError:
    SVG_SUPPORTED = False

# PDF to DOCX Support
try:
    from pdf2docx import Converter as PDFConverter
    PDF2DOCX_SUPPORTED = True
except ImportError:
    PDF2DOCX_SUPPORTED = False


class MahaConvert:
    # Extended format sets for bidirectional support
    IMAGE_FORMATS = {"jpg", "jpeg", "png", "webp", "avif", "bmp", "heic", "heif", "tiff", "tif", "ico", "jxl"}
    AUDIO_FORMATS = {"mp3", "wav", "opus", "aac", "ogg", "flac", "m4a", "aiff", "aif", "wma", "mid", "midi", "weba"}
    VIDEO_FORMATS = {"mp4", "webm", "mkv", "avi", "mov", "flv", "gif", "3gp", "3g2", "mpeg", "mpg", "ogv", "wmv"}
    DOC_FORMATS = {"pdf", "docx", "pptx", "xlsx", "doc", "ppt", "xls", "csv", "rtf", "txt", "md", "json", "xml", "epub"}
    ARCHIVE_FORMATS = {"zip", "7z", "rar"}

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ==================================================
    # UTILS
    # ==================================================
    def _out(self, name, ext):
        return os.path.join(self.output_dir, f"{name}.{ext}")

    def detect_mime(self, path):
        mime, _ = mimetypes.guess_type(path)
        return mime or "application/octet-stream"

    def detect_type(self, path):
        mime = self.detect_mime(path)

        if mime.startswith("image/"):
            return "image"
        if mime.startswith("audio/"):
            return "audio"
        if mime.startswith("video/"):
            return "video"
        if mime == "application/pdf":
            return "pdf"
        if mime.startswith("text/"):
            return "text"

        return "binary"

    def detect_ext(self, path):
        return os.path.splitext(path)[1].lower().replace(".", "")

    # ==================================================
    # AUTO CONVERT (DEFAULT SAFE)
    # ==================================================
    def detect_and_convert(self, input_path, request_format=None):
        """
        Auto convert ke format AMAN & UMUM
        (dipakai worker kalau user tidak specify format)
        Atau ke format request user
        """
        ftype = self.detect_type(input_path)
        input_ext = self.detect_ext(input_path)
        request_format = request_format.lower() if request_format else None

        # ========== IMAGE ==========
        if ftype == "image":
            # SVG special handling
            if input_ext == "svg":
                return self.svg_to_png(input_path)
            
            # Image → PDF
            if request_format == "pdf":
                return self.image_to_pdf(input_path)
            
            # Image → Image (including HEIC)
            return self.image_convert(
                input_path,
                to_format=request_format or "png",
                quality=85
            )

        # ========== AUDIO ==========
        if ftype == "audio":
            return self.audio_convert(
                input_path,
                to_format=request_format or "mp3",
                bitrate="192k"
            )

        # ========== VIDEO ==========
        if ftype == "video":
            if request_format == "webm":
                return self.video_to_webm(input_path)
            elif request_format == "gif":
                return self.video_to_gif(input_path)
            elif request_format in ("mp3", "aac", "wav", "ogg", "flac", "opus"):
                return self.video_to_audio(input_path, to_format=request_format)
            elif request_format in ("mp4", "mkv", "avi", "mov"):
                return self.video_convert(input_path, to_format=request_format)
            else:
                # Default: compress to MP4
                return self.video_compress(input_path, crf=28)

        # ========== PDF ==========
        if ftype == "pdf":
            if request_format == "docx":
                return self.pdf_to_docx(input_path)
            elif request_format in ("png", "jpg", "jpeg", "webp"):
                images = self.pdf_to_images(
                    input_path,
                    to_format=request_format,
                    dpi=200
                )
                # Return first page or all pages if multiple
                if len(images) == 1:
                    return images[0]
                else:
                    # Zip multiple pages
                    return self._zip_files(images, input_path)
            else:
                # Default: first page as PNG
                images = self.pdf_to_images(input_path, to_format="png", dpi=200)
                return images[0]

        # ========== CSV ==========
        if input_ext == "csv":
            if request_format == "xlsx":
                return self.csv_to_xlsx(input_path)
            elif request_format == "pdf":
                return self.office_to_pdf(input_path)
            else:
                # Default: convert to XLSX
                return self.csv_to_xlsx(input_path)

        # ========== TEXT/MARKUP FILES ==========
        if input_ext in ("txt", "md", "markdown", "json", "xml"):
            if request_format == "pdf":
                return self.text_to_pdf(input_path)
            else:
                return self.text_to_pdf(input_path)

        # ========== EPUB ==========
        if input_ext == "epub":
            if request_format == "pdf":
                return self.office_to_pdf(input_path)
            else:
                return self.office_to_pdf(input_path)

        # ========== RTF ==========
        if input_ext == "rtf":
            if request_format == "pdf":
                return self.office_to_pdf(input_path)
            else:
                return self.office_to_pdf(input_path)

        # ========== OFFICE DOCUMENTS ==========
        if input_ext in ("docx", "doc", "pptx", "ppt", "xlsx", "xls"):
            if request_format == "pdf":
                return self.office_to_pdf(input_path)
            else:
                # Default: convert to PDF
                return self.office_to_pdf(input_path)

        raise ValueError(f"Unsupported file type: {ftype}")

    def _zip_files(self, files, original_path):
        """Zip multiple output files"""
        name = os.path.splitext(os.path.basename(original_path))[0]
        output = self._out(name, "zip")
        
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(f, os.path.basename(f))
                # Clean up individual files
                os.remove(f)
        
        return output

    # ==================================================
    # IMAGE ⇄ IMAGE (ANY TO ANY)
    # ==================================================
    def image_convert(self, input_path, to_format, quality=85):
        to_format = to_format.lower()
        if to_format not in self.IMAGE_FORMATS:
            raise ValueError("Unsupported image format")

        img = Image.open(input_path)

        # Convert RGBA/P/F/I to RGB if target is JPEG
        if to_format in ("jpg", "jpeg"):
            if img.mode != "RGB":
                try:
                    img = img.convert("RGB")
                    print(f"[DEBUG] Converted {img.mode} to RGB")
                except:
                    # Fallback for complex modes like F
                    if img.mode == 'F':
                         img = img.convert('L').convert('RGB')
                    else:
                        img = img.convert("RGB")
        
        # Ensure compatible mode for PNG
        elif to_format == "png" and img.mode not in ("RGB", "RGBA", "L", "P", "1"):
            img = img.convert("RGBA")

        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, to_format)

        pil_format = "JPEG" if to_format in ("jpg", "jpeg") else to_format.upper()

        img.save(
            output,
            format=pil_format,
            quality=quality,
            optimize=True
        )
        return output

    # ==================================================
    # PDF → IMAGE (PNG / JPG / WEBP / AVIF)
    # ==================================================
    def pdf_to_images(self, input_path, to_format="png", dpi=200):
        to_format = to_format.lower()
        pages = convert_from_path(input_path, dpi=dpi)

        base = os.path.splitext(os.path.basename(input_path))[0]
        outputs = []

        for i, page in enumerate(pages, start=1):
            if page.mode == "RGBA" and to_format in ("jpg", "jpeg"):
                page = page.convert("RGB")

            filename = f"{base}_page{i}.{to_format}"
            out = os.path.join(self.output_dir, filename)

            pil_format = "JPEG" if to_format in ("jpg", "jpeg") else to_format.upper()
            page.save(out, format=pil_format, quality=90)

            outputs.append(out)

        return outputs

    # ==================================================
    # AUDIO ⇄ AUDIO
    # ==================================================
    def audio_convert(self, input_path, to_format, bitrate="128k"):
        to_format = to_format.lower()
        if to_format not in self.AUDIO_FORMATS:
            raise ValueError("Unsupported audio format")

        audio = AudioSegment.from_file(input_path)
        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, to_format)

        audio.export(output, format=to_format, bitrate=bitrate)
        return output

    # ==================================================
    # VIDEO → VIDEO (COMPRESS) - OPTIMIZED
    # ==================================================
    def video_compress(self, input_path, crf=28):
        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, "mp4")

        (
            ffmpeg
            .input(input_path)
            .output(
                output,
                vcodec="libx264",
                crf=crf,
                preset="veryfast",  # OPTIMIZED: was "slow"
                acodec="aac",
                audio_bitrate="128k"
            )
            .overwrite_output()
            .run(quiet=True)
        )
        return output

    # ==================================================
    # VIDEO → IMAGE FRAMES
    # ==================================================
    def video_to_images(self, input_path, to_format="png", fps=1):
        to_format = to_format.lower()
        base = os.path.splitext(os.path.basename(input_path))[0]
        pattern = os.path.join(self.output_dir, f"{base}_%03d.{to_format}")

        (
            ffmpeg
            .input(input_path)
            .output(pattern, vf=f"fps={fps}")
            .overwrite_output()
            .run(quiet=True)
        )

        return pattern  # wildcard path

    # ==================================================
    # PDF COMPRESS (REAL)
    # ==================================================
    def pdf_compress(self, input_path, dpi=150):
        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, "pdf")

        cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen",
            f"-dColorImageResolution={dpi}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output}",
            input_path
        ]
        subprocess.run(cmd, check=True)
        return output

    # ==================================================
    # GENERIC DATA
    # ==================================================
    def zstd(self, input_path, level=10):
        name = os.path.basename(input_path)
        output = self._out(name, "zst")

        cctx = zstd.ZstdCompressor(level=level)
        with open(input_path, "rb") as fin, open(output, "wb") as fout:
            fout.write(cctx.compress(fin.read()))
        return output

    def brotli(self, input_path, quality=9):
        name = os.path.basename(input_path)
        output = self._out(name, "br")

        with open(input_path, "rb") as f:
            data = f.read()

        with open(output, "wb") as f:
            f.write(brotli.compress(data, quality=quality))
        return output

    # ==================================================
    # VIDEO → WEBM (VP9) 
    # ==================================================
    def video_to_webm(self, input_path, crf=30):
        """Convert video to WebM format with VP9 codec"""
        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, "webm")

        (
            ffmpeg
            .input(input_path)
            .output(
                output,
                vcodec="libvpx-vp9",
                crf=crf,
                preset="veryfast",
                acodec="libopus",
                audio_bitrate="128k"
            )
            .overwrite_output()
            .run(quiet=True)
        )
        return output

    # ==================================================
    # VIDEO → AUDIO (EXTRACT MP3/AAC)
    # ==================================================
    def video_to_audio(self, input_path, to_format="mp3", bitrate="128k"):
        """Extract audio from video file"""
        to_format = to_format.lower()
        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, to_format)

        # Map format to codec
        codec_map = {
            "mp3": "libmp3lame",
            "aac": "aac",
            "opus": "libopus",
            "wav": "pcm_s16le",
            "ogg": "libvorbis",
            "flac": "flac"
        }
        acodec = codec_map.get(to_format, "libmp3lame")

        (
            ffmpeg
            .input(input_path)
            .output(
                output,
                vn=None,  # No video
                acodec=acodec,
                audio_bitrate=bitrate
            )
            .overwrite_output()
            .run(quiet=True)
        )
        return output

    # ==================================================
    # VIDEO → GIF (ANIMATED)
    # ==================================================
    def video_to_gif(self, input_path, fps=10, scale=480):
        """Convert short video to animated GIF with palette optimization"""
        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, "gif")
        palette = self._out(name, "palette.png")

        # Step 1: Generate palette
        (
            ffmpeg
            .input(input_path)
            .output(
                palette,
                vf=f"fps={fps},scale={scale}:-1:flags=lanczos,palettegen"
            )
            .overwrite_output()
            .run(quiet=True)
        )

        # Step 2: Create GIF with palette
        (
            ffmpeg
            .input(input_path)
            .input(palette)
            .output(
                output,
                filter_complex=f"fps={fps},scale={scale}:-1:flags=lanczos[x];[x][1:v]paletteuse"
            )
            .overwrite_output()
            .run(quiet=True)
        )

        # Cleanup palette
        if os.path.exists(palette):
            os.remove(palette)

        return output

    # ==================================================
    # VIDEO → ANY FORMAT (GENERAL)
    # ==================================================
    def video_convert(self, input_path, to_format="mp4", crf=28):
        """General video format conversion"""
        to_format = to_format.lower()
        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, to_format)

        if to_format == "webm":
            return self.video_to_webm(input_path, crf=crf)
        elif to_format == "gif":
            return self.video_to_gif(input_path)
        elif to_format in ("mp3", "aac", "wav", "ogg", "flac", "opus"):
            return self.video_to_audio(input_path, to_format=to_format)
        else:
            # Default: H.264 MP4/MKV/MOV/AVI
            vcodec = "libx264"
            acodec = "aac"
            
            (
                ffmpeg
                .input(input_path)
                .output(
                    output,
                    vcodec=vcodec,
                    crf=crf,
                    preset="veryfast",
                    acodec=acodec,
                    audio_bitrate="128k"
                )
                .overwrite_output()
                .run(quiet=True)
            )
            return output

    # ==================================================
    # SVG → PNG (VECTOR TO RASTER)
    # ==================================================
    def svg_to_png(self, input_path, scale=2.0):
        """Convert SVG vector to PNG raster image"""
        if not SVG_SUPPORTED:
            raise ValueError("SVG conversion requires svglib and reportlab")

        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, "png")

        drawing = svg2rlg(input_path)
        if drawing is None:
            raise ValueError("Failed to parse SVG file")

        # Scale the drawing
        drawing.width = drawing.width * scale
        drawing.height = drawing.height * scale
        drawing.scale(scale, scale)

        renderPM.drawToFile(drawing, output, fmt="PNG")
        return output

    # ==================================================
    # IMAGE → PDF (SINGLE OR MULTIPLE)
    # ==================================================
    def image_to_pdf(self, input_path):
        """Convert single image to PDF"""
        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, "pdf")

        img = Image.open(input_path)
        
        # Convert to RGB if needed (PDF doesn't support RGBA)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(output, "PDF", resolution=100.0)
        return output

    def images_to_pdf(self, input_paths):
        """Combine multiple images into a single PDF"""
        if not input_paths:
            raise ValueError("No images provided")

        # Use first image name for output
        name = os.path.splitext(os.path.basename(input_paths[0]))[0]
        output = self._out(name + "_combined", "pdf")

        images = []
        for path in input_paths:
            img = Image.open(path)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            images.append(img)

        # Save first image with append_images
        images[0].save(
            output,
            "PDF",
            resolution=100.0,
            save_all=True,
            append_images=images[1:] if len(images) > 1 else []
        )
        return output

    # ==================================================
    # PDF → DOCX (WORD)
    # ==================================================
    def pdf_to_docx(self, input_path):
        """Convert PDF to Word document"""
        if not PDF2DOCX_SUPPORTED:
            raise ValueError("PDF to DOCX requires pdf2docx library. Install with: pip install pdf2docx")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"PDF file not found: {input_path}")

        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, "docx")

        try:
            cv = PDFConverter(input_path)
            cv.convert(output)
            cv.close()
        except Exception as e:
            raise ValueError(f"PDF to DOCX conversion failed: {str(e)}")

        if not os.path.exists(output):
            raise ValueError("Conversion completed but output file not created")

        return output

    # ==================================================
    # DOCX/PPTX/XLSX → PDF (VIA LIBREOFFICE)
    # ==================================================
    def office_to_pdf(self, input_path):
        """Convert Office documents (DOCX, PPTX, XLSX) to PDF using LibreOffice"""
        name = os.path.splitext(os.path.basename(input_path))[0]
        
        # LibreOffice outputs to the same directory by default
        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", self.output_dir,
            input_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except FileNotFoundError:
            raise ValueError("LibreOffice not installed. Required for Office to PDF conversion.")
        except subprocess.TimeoutExpired:
            raise ValueError("Conversion timed out")

        output = self._out(name, "pdf")
        return output

    # ==================================================
    # CSV → XLSX (EXCEL)
    # ==================================================
    def csv_to_xlsx(self, input_path):
        """Convert CSV to Excel XLSX format"""
        try:
            import pandas as pd
        except ImportError:
            raise ValueError("pandas and openpyxl required for CSV conversion. Install with: pip install pandas openpyxl")

        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, "xlsx")

        try:
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(input_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Could not decode CSV file with any common encoding")

            df.to_excel(output, index=False, engine='openpyxl')
        except Exception as e:
            raise ValueError(f"CSV to XLSX conversion failed: {str(e)}")

        return output

    # ==================================================
    # TEXT → PDF
    # ==================================================
    def text_to_pdf(self, input_path):
        """Convert text/markdown/json/xml files to PDF"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.units import inch
        except ImportError:
            raise ValueError("reportlab required for text to PDF conversion. Install with: pip install reportlab")

        name = os.path.splitext(os.path.basename(input_path))[0]
        output = self._out(name, "pdf")

        # Read text content with encoding fallback
        content = None
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(input_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise ValueError("Could not decode text file with any common encoding")

        # Create PDF
        doc = SimpleDocTemplate(output, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)

        styles = getSampleStyleSheet()
        code_style = ParagraphStyle(
            'Code',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=9,
            leading=12,
            spaceAfter=6
        )

        story = []
        
        # Split content into lines and create paragraphs
        lines = content.split('\n')
        for line in lines:
            # Escape special characters for reportlab
            line = line.replace('&', '&amp;')
            line = line.replace('<', '&lt;')
            line = line.replace('>', '&gt;')
            line = line.replace(' ', '&nbsp;') if line.startswith(' ') else line
            
            if line.strip():
                story.append(Paragraph(line, code_style))
            else:
                story.append(Spacer(1, 6))

        doc.build(story)
        return output
