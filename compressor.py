import os
import mimetypes
import subprocess
import ffmpeg
from PIL import Image
from converter import MahaConvert


class MahaCompressor:
    """
    PRODUCTION-OPTIMIZED COMPRESSOR
    - Image: binary search quality
    - Audio: bitrate mapping (1x encode)
    - Video: CRF mapping (1x encode)
    - PDF: DPI mapping (Ghostscript)
    """

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        self.mc = MahaConvert(output_dir=output_dir)

    # ==================================================
    # PUBLIC
    # ==================================================
    def compress(self, input_path: str, target_percent: int = 70) -> str:
        ftype = self._detect_type(input_path)
        ext = os.path.splitext(input_path)[1].lower().replace(".", "")

        if ftype == "image":
            return self._compress_image(input_path, target_percent)

        if ftype == "audio":
            return self._compress_audio(input_path, target_percent)

        if ftype == "video":
            return self._compress_video(input_path, target_percent)

        if ftype == "pdf":
            return self._compress_pdf(input_path, target_percent)

        if ftype == "archive":
            return self._copy_archive(input_path)

        if ftype == "text":
            return self.mc.zstd(input_path, level=min(22, target_percent // 4))

        return self.mc.brotli(input_path, quality=min(11, target_percent // 8))

    def _copy_archive(self, input_path):
        """Archives are already compressed, just copy to output directory"""
        import shutil
        name = os.path.basename(input_path)
        output = os.path.join(self.output_dir, name)
        shutil.copy2(input_path, output)
        return output

    # ==================================================
    # IMAGE — DIRECT QUALITY MAPPING (FAST)
    # ==================================================
    def _compress_image(self, input_path, target_percent):
        """
        Direct quality mapping instead of binary search.
        target_percent 0 = minimal compression (quality 95)
        target_percent 90 = max compression (quality 5)
        PRESERVES ORIGINAL FORMAT
        """
        name, ext = os.path.splitext(os.path.basename(input_path))
        ext = ext.lower().replace(".", "")
        
        # Preserve original format, default to jpg if unknown
        if ext in ("jpg", "jpeg", "png", "webp"):
            out_ext = ext
        else:
            out_ext = "jpg"
            
        output = os.path.join(self.output_dir, f"{name}.{out_ext}")

        Image.MAX_IMAGE_PIXELS = None
        img = Image.open(input_path)
        print(f"[DEBUG] Opened image {input_path} with mode {img.mode} and size {img.size}")

        
        # Convert RGBA/P/F/I to RGB for JPEG
        if out_ext in ("jpg", "jpeg"):
            if img.mode != "RGB":
                img = img.convert("RGB")
        # Ensure compatible modes for other formats
        elif out_ext == "png" and img.mode not in ("RGB", "RGBA", "L", "P", "1"):
             img = img.convert("RGBA")

        # Map 0-90% to quality 95-5
        quality = max(5, int(95 - target_percent))

        # Determine PIL format string
        if out_ext in ("jpg", "jpeg"):
            pil_format = "JPEG"
        elif out_ext == "png":
            pil_format = "PNG"
        elif out_ext == "webp":
            pil_format = "WEBP"
        else:
            pil_format = "JPEG"

        img.save(output, format=pil_format, quality=quality, optimize=True)
        return output

    # ==================================================
    # AUDIO — BITRATE MAPPING (OPTIMIZED)
    # ==================================================
    def _compress_audio(self, input_path, target_percent):
        name, ext = os.path.splitext(os.path.basename(input_path))
        ext = ext.lower().replace(".", "")
        
        # Preserve original format, default to mp3 if unknown
        if ext in ("mp3", "wav", "opus", "aac", "ogg", "flac"):
            out_ext = ext
        else:
            out_ext = "mp3"
            
        output = os.path.join(self.output_dir, f"{name}.{out_ext}")

        # Map 0-90% to bitrate (higher = better quality)
        # 0% = 256k, 90% = 32k
        if target_percent <= 20:
            bitrate = "256k"
        elif target_percent <= 40:
            bitrate = "192k"
        elif target_percent <= 60:
            bitrate = "128k"
        elif target_percent <= 80:
            bitrate = "96k"
        else:
            bitrate = "64k"

        (
            ffmpeg
            .input(input_path)
            .output(output, audio_bitrate=bitrate)
            .overwrite_output()
            .run(quiet=True)
        )
        return output

    # ==================================================
    # VIDEO — CRF MAPPING (OPTIMIZED)
    # ==================================================
    def _compress_video(self, input_path, target_percent):
        name, ext = os.path.splitext(os.path.basename(input_path))
        ext = ext.lower().replace(".", "")
        
        # Preserve original format, default to mp4 if unknown
        if ext in ("mp4", "mkv", "webm", "avi", "mov"):
            out_ext = ext
        else:
            out_ext = "mp4"
            
        output = os.path.join(self.output_dir, f"{name}.{out_ext}")

        # Map 0-90% to CRF 18-45 (lower CRF = better quality)
        # 0% = CRF 18 (minimal compression)
        # 90% = CRF 45 (max compression)
        crf = int(18 + (target_percent * 0.3))
        crf = min(45, max(18, crf))

        (
            ffmpeg
            .input(input_path)
            .output(
                output,
                vcodec="libx264",
                crf=crf,
                preset="ultrafast",  # FASTEST preset
                acodec="aac",
                audio_bitrate="96k"  # Lower for faster processing
            )
            .overwrite_output()
            .run(quiet=True)
        )
        return output

    # ==================================================
    # PDF — DPI MAPPING (1x PASS)
    # ==================================================
    def _compress_pdf(self, input_path, target_percent):
        name = os.path.splitext(os.path.basename(input_path))[0]
        output = os.path.join(self.output_dir, f"{name}.pdf")

        if target_percent <= 30:
            dpi = 200
        elif target_percent <= 60:
            dpi = 150
        elif target_percent <= 80:
            dpi = 110
        else:
            dpi = 72

        cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen",
            f"-dColorImageResolution={dpi}",
            f"-dGrayImageResolution={dpi}",
            f"-dMonoImageResolution={dpi}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output}",
            input_path
        ]

        subprocess.run(cmd, check=True)
        return output

    # ==================================================
    # DETECTOR
    # ==================================================
    # ==================================================
    # DETECTOR
    # ==================================================
    def _detect_type(self, path: str) -> str:
        # 1. Force extension check first for robustness
        ext = os.path.splitext(path)[1].lower().replace(".", "")
        
        # Images
        if ext in ("jpg", "jpeg", "png", "webp", "avif", "bmp", "heic", "heif", "tiff", "tif", "ico", "jxl"):
            return "image"
            
        # Audio
        if ext in ("mp3", "wav", "opus", "aac", "ogg", "flac", "m4a", "aiff", "aif", "wma", "mid", "midi"):
            return "audio"
            
        # Video
        if ext in ("mp4", "webm", "mkv", "avi", "mov", "flv", "gif", "3gp", "3g2", "mpeg", "mpg", "ogv", "wmv"):
            return "video"
            
        # PDF
        if ext == "pdf":
            return "pdf"
            
        # Archives
        if ext in ("zip", "7z", "rar", "gz", "tar", "bz2", "xz"):
            return "archive"

        # 2. Fallback to mimetype
        mime, _ = mimetypes.guess_type(path)
        if mime:
            main, sub = mime.split("/")
            if main == "image": return "image"
            if main == "audio": return "audio"
            if main == "video": return "video"
            if mime == "application/pdf": return "pdf"
            if main == "text": return "text"

        return "binary"
