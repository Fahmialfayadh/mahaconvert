
import sys

dependencies = [
    "flask", 
    "supabase",
    "PIL",          # Pillow
    "pillow_heif",
    "pdf2image",
    "pypdf",
    "pdf2docx",
    "pandas",
    "openpyxl",
    "reportlab",
    "svglib",
    "reportlab",
    "ffmpeg",
    "brotli",
    "zstandard",
    "cv2"           # opencv-python (optional usually but good for video)
]

missing = []

for dep in dependencies:
    try:
        __import__(dep)
        print(f"✅ {dep}")
    except ImportError:
        # Some packages have different import names
        if dep == "PIL":
            try:
                import PIL
                print(f"✅ PIL")
            except:
                missing.append(dep)
        elif dep == "pillow_heif":
            try:
                import pillow_heif
                print(f"✅ pillow_heif")
            except:
                missing.append(dep)
        elif dep == "pdf2image":
            try:
                import pdf2image
                print(f"✅ pdf2image")
            except:
                missing.append(dep)
        elif dep == "pypdf":
            try:
                import pypdf
                print(f"✅ pypdf")
            except:
                missing.append(dep)
        elif dep == "zstandard":
            try:
                import zstandard
                print(f"✅ zstandard")
            except:
                missing.append(dep)
        else:
            missing.append(dep)
            print(f"❌ {dep}")

if missing:
    print("\nMissing dependencies:")
    print("pip install " + " ".join(missing))
else:
    print("\nAll dependencies installed!")
