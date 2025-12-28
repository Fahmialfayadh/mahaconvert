// ===============================
// ELEMENTS
// ===============================
const fileInput = document.getElementById("fileInput");
const actionSelect = document.getElementById("action");
const compressBox = document.getElementById("compressBox");
const convertBox = document.getElementById("convertBox");
const toFormat = document.getElementById("toFormat");
const convertHint = document.getElementById("convertHint");
const percentLabel = document.getElementById("percent");
const rangeInput = document.querySelector('input[type="range"]');

const form = document.getElementById("mainForm");
const submitBtn = form.querySelector("button[type='submit']");

const overlay = document.getElementById("loadingOverlay");
const statusText = document.getElementById("loadingStatus");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");

// ===============================
// UI HELPERS
// ===============================
rangeInput.addEventListener("input", () => {
  percentLabel.textContent = rangeInput.value + "%";
});

actionSelect.addEventListener("change", () => {
  toggleAction();
  detectFile();
});

fileInput.addEventListener("change", detectFile);

function toggleAction() {
  const isConvert = actionSelect.value === "convert";
  compressBox.classList.toggle("d-none", isConvert);
  convertBox.classList.toggle("d-none", !isConvert);
}

function detectFile() {
  if (!fileInput.files.length) return;

  const ext = fileInput.files[0].name.split(".").pop().toLowerCase();
  toFormat.innerHTML = "";

  if (["jpg", "jpeg", "png", "webp", "avif"].includes(ext)) {
    addOptions(["jpg", "png", "webp", "avif"]);
    convertHint.textContent = "Gambar dapat dikonversi ke format umum & modern.";
  } else if (ext === "pdf") {
    addOptions(["png", "jpg", "webp"]);
    convertHint.textContent = "PDF akan dikonversi per halaman.";
  } else if (["wav", "mp3", "aac", "opus"].includes(ext)) {
    addOptions(["mp3", "opus", "aac"]);
    convertHint.textContent = "Konversi audio tanpa mengubah durasi.";
  } else if (["mp4", "mkv", "webm"].includes(ext)) {
    addOptions(["mp4"]);
    convertHint.textContent = "Video akan dire-encode ke MP4.";
  } else {
    convertHint.textContent = "Format ini belum mendukung konversi.";
  }
}

function addOptions(list) {
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
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  submitBtn.disabled = true;

  const formData = new FormData(form);

  // show loading
  overlay.classList.remove("d-none");
  statusText.innerText = "Uploading file…";
  progressBar.style.width = "5%";
  progressText.innerText = "5%";

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
    overlay.classList.add("d-none");
    submitBtn.disabled = false;
  }
});

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
      statusText.innerText = job.status || "Processing…";
      const pct = Math.min(100, Math.max(0, currentProgress.toFixed(1)));

      progressBar.style.width = pct + "%";
      progressText.innerText = Math.floor(pct) + "%";

      // DONE
      if (job.status === "done" || job.progress === 100) {
        clearInterval(interval);
        statusText.innerText = "Selesai 🎉";
        progressBar.style.width = "100%";
        progressText.innerText = "100%";

        setTimeout(() => {
          // HIDE OVERLAY
          overlay.classList.add("d-none");

          // DO NOT HIDE FORM CARD (Fixes disappearing home)
          // Instead, reset form or show simple alert
          submitBtn.disabled = false;
          statusText.innerText = "Initializing...";
          progressBar.style.width = "0%";
          progressText.innerText = "0%";

          // Trigger download
          window.location.href = `/download/${jobId}`;
        }, 800);
      }

      // ERROR / CANCEL
      if (job.status === "error" || job.status === "cancelled") {
        clearInterval(interval);
        statusText.innerText = job.status;
        submitBtn.disabled = false;
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
