// ===============================
// ELEMENTS
// ===============================
const fileInput = document.getElementById("fileInput");
const actionSelect = document.getElementById("action");
const compressBox = document.getElementById("compressBox");
const convertBox = document.getElementById("convertBox");
const toFormat = document.getElementById("toFormat");
const convertHint = document.getElementById("convertHint");
const compressHint = document.getElementById("compressHint");
const percentLabel = document.getElementById("percent");
const rangeInput = document.getElementById("targetRange");

const form = document.getElementById("mainForm");
const submitBtn = form ? form.querySelector("button[type='submit']") : null;

const overlay = document.getElementById("loadingOverlay");
const statusText = document.getElementById("loadingStatus");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");

// Supported formats for compression
const COMPRESS_FORMATS = [
  // Images
  "jpg", "jpeg", "png", "webp", "avif", "bmp", "heic", "heif", "tiff", "tif", "ico", "jxl",
  // Videos
  "mp4", "mkv", "webm", "avi", "mov", "flv", "3gp", "3g2", "mpeg", "mpg", "ogv", "wmv",
  // Audio
  "mp3", "wav", "aac", "ogg", "flac", "m4a", "aiff", "aif", "wma", "opus",
  // Documents
  "pdf",
  // Archives
  "zip", "7z", "rar", "gz", "tar", "bz2", "xz"
];

// ===============================
// UI HELPERS
// ===============================
if (rangeInput && percentLabel) {
  rangeInput.addEventListener("input", () => {
    percentLabel.textContent = rangeInput.value + "%";
  });
}

if (actionSelect) {
  actionSelect.addEventListener("change", () => {
    toggleAction();
    detectFile();
  });
}

if (fileInput) {
  fileInput.addEventListener("change", detectFile);
}

function toggleAction() {
  if (!actionSelect || !compressBox || !convertBox) return;

  const isConvert = actionSelect.value === "convert";
  compressBox.classList.toggle("d-none", isConvert);
  convertBox.classList.toggle("d-none", !isConvert);
}

function detectFile() {
  if (!fileInput || !fileInput.files.length) return;

  const ext = fileInput.files[0].name.split(".").pop().toLowerCase();
  if (toFormat) toFormat.innerHTML = "";

  // ========== IMAGE FORMATS ==========
  if (["jpg", "jpeg", "png", "webp", "avif", "bmp", "tiff", "tif", "ico", "jxl"].includes(ext)) {
    addOptions(["jpg", "png", "webp", "avif", "pdf"]);
    if (convertHint) convertHint.textContent = "Convert image or create PDF from image.";

    // HEIC/HEIF (iPhone photos)
  } else if (["heic", "heif"].includes(ext)) {
    addOptions(["jpg", "png", "webp", "pdf"]);
    if (convertHint) convertHint.textContent = "iPhone photos will be converted to universal format.";

    // SVG (Vector to Raster)
  } else if (ext === "svg") {
    addOptions(["png"]);
    if (convertHint) convertHint.textContent = "Vector SVG will be rasterized to PNG.";

    // ========== VIDEO FORMATS ==========
  } else if (["mp4", "mkv", "webm", "avi", "mov", "flv", "3gp", "3g2", "mpeg", "mpg", "ogv", "wmv"].includes(ext)) {
    addOptions(["mp4", "webm", "gif", "mp3", "aac", "wav"]);
    if (convertHint) convertHint.textContent = "Convert video, create GIF, or extract audio.";

    // ========== AUDIO FORMATS ==========
  } else if (["wav", "mp3", "aac", "opus", "ogg", "flac", "m4a", "aiff", "aif", "wma", "mid", "midi", "weba"].includes(ext)) {
    addOptions(["mp3", "wav", "ogg", "aac", "opus", "flac"]);
    if (convertHint) convertHint.textContent = "Convert audio to any format.";

    // ========== PDF ==========
  } else if (ext === "pdf") {
    addOptions(["docx", "png", "jpg", "webp"]);
    if (convertHint) convertHint.textContent = "Convert PDF to Word or image.";

    // ========== OFFICE DOCUMENTS ==========
  } else if (["docx", "doc", "rtf"].includes(ext)) {
    addOptions(["pdf"]);
    if (convertHint) convertHint.textContent = "Convert document to PDF.";

  } else if (["pptx", "ppt"].includes(ext)) {
    addOptions(["pdf"]);
    if (convertHint) convertHint.textContent = "Convert PowerPoint to PDF.";

  } else if (["xlsx", "xls"].includes(ext)) {
    addOptions(["pdf"]);
    if (convertHint) convertHint.textContent = "Convert Excel to PDF.";

  } else if (ext === "csv") {
    addOptions(["xlsx", "pdf"]);
    if (convertHint) convertHint.textContent = "Convert CSV to Excel or PDF.";

    // ========== TEXT/MARKUP ==========
  } else if (["txt", "md", "markdown", "json", "xml"].includes(ext)) {
    addOptions(["pdf"]);
    if (convertHint) convertHint.textContent = "Convert text to PDF.";

    // ========== EBOOK ==========
  } else if (ext === "epub") {
    addOptions(["pdf"]);
    if (convertHint) convertHint.textContent = "Convert EPUB to PDF.";

    // ========== ARCHIVES (already compressed) ==========
  } else if (["zip", "7z", "rar", "gz", "tar", "bz2", "xz"].includes(ext)) {
    if (convertHint) {
      convertHint.innerHTML = '<span class="text-muted">Archives are already compressed</span>';
    }
    if (compressHint) {
      compressHint.innerHTML = '<span class="text-muted">Archives are already compressed (will copy original)</span>';
    }

    // ========== UNSUPPORTED FOR CONVERT ==========
  } else {
    if (convertHint) {
      convertHint.innerHTML = '<span class="text-danger">Format not supported for conversion</span>';
    }
  }

  // ========== COMPRESS VALIDATION ==========
  if (COMPRESS_FORMATS.includes(ext)) {
    // Format supported for compression
    if (compressHint) {
      compressHint.innerHTML = '<span class="text-muted">Compression available for this format</span>';
    }
  } else {
    // Format NOT supported for compression
    if (compressHint) {
      compressHint.innerHTML = '<span class="text-danger">Format not supported for compression</span>';
    }
  }

  // ========== ENABLE/DISABLE SUBMIT BASED ON ACTION ==========
  updateSubmitState(ext);
}

function updateSubmitState(ext) {
  if (!submitBtn || !actionSelect) return;

  const action = actionSelect.value;

  if (action === "compress") {
    submitBtn.disabled = !COMPRESS_FORMATS.includes(ext);
  } else if (action === "convert") {
    // Check if toFormat has options
    submitBtn.disabled = toFormat && toFormat.options.length === 0;
  }
}

function addOptions(list) {
  if (!toFormat) return;

  list.forEach(fmt => {
    const opt = document.createElement("option");
    opt.value = fmt;
    opt.textContent = fmt.toUpperCase();
    toFormat.appendChild(opt);
  });
}

// ===============================
// FORM SUBMIT (UPLOAD)
// ===============================
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (submitBtn) submitBtn.disabled = true;

    const formData = new FormData(form);

    // show loading
    if (overlay) overlay.classList.remove("d-none");
    if (statusText) statusText.innerText = "Uploading file...";
    if (progressBar) progressBar.style.width = "5%";
    if (progressText) progressText.innerText = "5%";

    try {
      const res = await fetch("/upload", {
        method: "POST",
        body: formData
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Upload failed");
      }

      // lanjut ke polling job
      pollJob(data.job_id);

    } catch (err) {
      alert(err.message);
      if (overlay) overlay.classList.add("d-none");
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

// ===============================
// JOB POLLING (REAL PROGRESS + SIMULATION)
// ===============================
let progressInterval = null;
let currentProgress = 0;

function pollJob(jobId) {
  // Reset
  currentProgress = 0;
  if (progressInterval) clearInterval(progressInterval);

  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/job/${jobId}`);
      const job = await res.json();

      // --- SIMULATED PROGRESS LOGIC ---
      let displayProgress = job.progress || 0;

      // Make sure we don't go backward
      if (displayProgress < currentProgress) {
        displayProgress = currentProgress;
      }

      // If backend says "Compressing" or "Converting" (usually stuck at 20%)
      // We simulate progress up to 90%
      if (
        job.status &&
        (job.status.toLowerCase().includes("compressing") ||
          job.status.toLowerCase().includes("converting") ||
          job.status.toLowerCase().includes("starting"))
        && displayProgress < 90
      ) {
        // Auto increment slowly if backend is static
        // Random increment between 0.2 and 0.8
        const inc = Math.random() * 0.6 + 0.2;
        displayProgress += inc;
        if (displayProgress > 90) displayProgress = 90;
      }

      // Sync local state
      currentProgress = displayProgress;

      // Update UI
      if (statusText) statusText.innerText = job.status || "Processing...";
      const pct = Math.min(100, Math.max(0, currentProgress.toFixed(1)));

      if (progressBar) progressBar.style.width = pct + "%";
      if (progressText) progressText.innerText = Math.floor(pct) + "%";

      // DONE
      if (job.status === "done" || job.progress === 100) {
        clearInterval(interval);
        if (statusText) statusText.innerText = "Complete";
        if (progressBar) progressBar.style.width = "100%";
        if (progressText) progressText.innerText = "100%";

        setTimeout(() => {
          // HIDE OVERLAY
          if (overlay) overlay.classList.add("d-none");

          // Reset form
          if (submitBtn) submitBtn.disabled = false;
          if (statusText) statusText.innerText = "Initializing...";
          if (progressBar) progressBar.style.width = "0%";
          if (progressText) progressText.innerText = "0%";

          // Trigger download
          window.location.href = `/download/${jobId}`;
        }, 800);
      }

      // ERROR / CANCEL
      if (job.status === "error" || job.status === "cancelled") {
        clearInterval(interval);
        if (statusText) statusText.innerText = job.status;
        if (submitBtn) submitBtn.disabled = false;
        if (overlay) overlay.classList.add("d-none");
      }

    } catch (err) {
      console.error("Polling error:", err);
    }
  }, 1000);
}

// ===============================
// INIT
// ===============================
toggleAction();
detectFile();
