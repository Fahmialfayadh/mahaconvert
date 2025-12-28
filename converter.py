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


class MahaConvert:
    IMAGE_FORMATS = {"jpg", "jpeg", "png", "webp", "avif"}
    AUDIO_FORMATS = {"mp3", "wav", "opus", "aac"}

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

        # IMAGE → PNG
        if ftype == "image":
            return self.image_convert(
                input_path,
                to_format=request_format or "png",
                quality=85
            )

        # AUDIO → MP3
        if ftype == "audio":
            return self.audio_convert(
                input_path,
                to_format=request_format or "mp3",
                bitrate="128k"
            )

        # VIDEO → MP4
        if ftype == "video":
            # jika user minta format specific (misal convert container),
            # sementara kita paksa mp4 karena func video_compress hardcoded mp4.
            # TODO: support video conversion to other formats explicitly if needed
            return self.video_compress(
                input_path,
                crf=28
            )

        # PDF → IMAGE (HALAMAN 1)
        if ftype == "pdf":
            images = self.pdf_to_images(
                input_path,
                to_format=request_format or "png",
                dpi=200
            )
            return images[0]  # jelas: ambil halaman pertama

        raise ValueError(f"Unsupported file type: {ftype}")

    # ==================================================
    # IMAGE ⇄ IMAGE (ANY TO ANY)
    # ==================================================
    def image_convert(self, input_path, to_format, quality=85):
        to_format = to_format.lower()
        if to_format not in self.IMAGE_FORMATS:
            raise ValueError("Unsupported image format")

        img = Image.open(input_path)

        # PNG → JPG needs RGB
        if img.mode in ("RGBA", "P") and to_format in ("jpg", "jpeg"):
            img = img.convert("RGB")

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
