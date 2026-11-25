/* ═══════════════════════════════════════════════════════════════════════════
   VisionTrack — app.js
   Frontend logic: upload → analyse → select → track → display results
═══════════════════════════════════════════════════════════════════════════ */

const API = "http://localhost:5000";

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  sessionId:   null,
  selectedId:  null,
  videoSummary: null,
};

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const uploadZone    = $("uploadZone");
const videoInput    = $("videoInput");
const browseBtn     = $("browseBtn");
const filePreview   = $("filePreview");
const fileName      = $("fileName");
const fileSize      = $("fileSize");
const confSlider    = $("confSlider");
const confVal       = $("confVal");
const uploadBtn     = $("uploadBtn");
const classFilter   = $("classFilter");
const objectGrid    = $("objectGrid");
const trackBtn      = $("trackBtn");
const progressBar   = $("progressBar");
const progressLabel = $("progressLabel");
const resultVideo   = $("resultVideo");
const statsGrid     = $("statsGrid");
const statusBadge   = $("statusBadge");
const toast         = $("toast");

// Sections
const sections = {
  upload:  $("sec-upload"),
  detect:  $("sec-detect"),
  track:   $("sec-track"),
  results: $("sec-results"),
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function showSection(name) {
  Object.values(sections).forEach(s => s.classList.add("hidden"));
  sections[name]?.classList.remove("hidden");
  document.querySelectorAll(".pill").forEach(p => {
    p.classList.toggle("active", p.dataset.section === name);
  });
}

function setStatus(label, type = "") {
  statusBadge.textContent = "";
  const dot = document.createElement("span");
  dot.className = "dot";
  statusBadge.appendChild(dot);
  statusBadge.appendChild(document.createTextNode(" " + label));
  statusBadge.className = "status-badge" + (type ? " " + type : "");
}

function showToast(msg, type = "") {
  toast.textContent = msg;
  toast.className = "toast" + (type ? " " + type : "");
  setTimeout(() => { toast.className = "toast hidden"; }, 3500);
}

function fmtSize(bytes) {
  if (bytes < 1024)       return bytes + " B";
  if (bytes < 1048576)    return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

function animateProgress(target, label) {
  progressBar.style.width = target + "%";
  progressLabel.textContent = label;
}

// ── Nav pills ─────────────────────────────────────────────────────────────────
document.querySelectorAll(".pill").forEach(pill => {
  pill.addEventListener("click", () => {
    const s = pill.dataset.section;
    if (!sections[s]?.classList.contains("hidden")) showSection(s);
  });
});

// ── Confidence slider ─────────────────────────────────────────────────────────
confSlider.addEventListener("input", () => {
  confVal.textContent = parseFloat(confSlider.value).toFixed(2);
});

// ── File selection ─────────────────────────────────────────────────────────────
browseBtn.addEventListener("click", () => videoInput.click());
uploadZone.addEventListener("click", e => {
  if (e.target !== browseBtn) videoInput.click();
});

videoInput.addEventListener("change", () => {
  const f = videoInput.files[0];
  if (f) handleFile(f);
});

// Drag & drop
uploadZone.addEventListener("dragover",  e => { e.preventDefault(); uploadZone.classList.add("drag-over"); });
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
uploadZone.addEventListener("drop", e => {
  e.preventDefault();
  uploadZone.classList.remove("drag-over");
  const f = e.dataTransfer.files[0];
  if (f) handleFile(f);
});

function handleFile(f) {
  const allowed = ["video/mp4", "video/avi", "video/quicktime",
                   "video/x-matroska", "video/webm", "video/x-msvideo"];
  if (!allowed.some(t => f.type.startsWith("video/"))) {
    showToast("Unsupported file type — please upload a video", "error");
    return;
  }
  fileName.textContent = f.name;
  fileSize.textContent = fmtSize(f.size);
  filePreview.classList.remove("hidden");
  uploadBtn.disabled = false;
}

// ── Upload & Analyse ──────────────────────────────────────────────────────────
uploadBtn.addEventListener("click", async () => {
  const f = videoInput.files[0];
  if (!f) return;

  uploadBtn.disabled = true;
  setStatus("Uploading…", "busy");
  showSection("track");
  animateProgress(20, "Uploading video…");

  // 1. Upload
  const form = new FormData();
  form.append("video", f);
  let res;
  try {
    res = await fetch(`${API}/api/upload`, { method: "POST", body: form });
  } catch {
    return handleError("Cannot reach server — is Flask running on port 5000?");
  }
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return handleError(e.error || "Upload failed");
  }

  const { session_id } = await res.json();
  state.sessionId = session_id;
  animateProgress(45, "Detecting & tracking objects with YOLOv8…");

  // 2. Analyse
  try {
    res = await fetch(`${API}/api/analyse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id, conf: parseFloat(confSlider.value) }),
    });
  } catch {
    return handleError("Analysis request failed");
  }
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return handleError(e.error || "Analysis failed");
  }

  const data = await res.json();
  state.videoSummary = data.summary;
  animateProgress(100, "Done — select an object below");

  setStatus("Objects detected", "active");
  showToast(`Found ${data.summary.objects.length} unique objects`, "success");

  renderObjectList(data.summary);
  showSection("detect");
  uploadBtn.disabled = false;
});

// ── Object list ───────────────────────────────────────────────────────────────
function renderObjectList(summary) {
  // Video meta
  $("videoMeta").innerHTML = [
    `<div class="meta-chip"><span>Frames: </span>${summary.total_frames}</div>`,
    `<div class="meta-chip"><span>FPS: </span>${Math.round(summary.fps)}</div>`,
    `<div class="meta-chip"><span>Resolution: </span>${summary.width}×${summary.height}</div>`,
    `<div class="meta-chip"><span>Objects: </span>${summary.objects.length}</div>`,
  ].join("");

  renderCards(summary.objects);

  classFilter.addEventListener("input", () => {
    const q = classFilter.value.toLowerCase();
    const filtered = summary.objects.filter(o =>
      o.class.includes(q) || String(o.track_id).includes(q)
    );
    renderCards(filtered);
  });
}

function renderCards(objects) {
  if (!objects.length) {
    objectGrid.innerHTML = `<p style="color:var(--text-muted);grid-column:1/-1">No objects match your filter.</p>`;
    return;
  }

  objectGrid.innerHTML = objects.map(o => `
    <div class="obj-card" data-id="${o.track_id}" onclick="selectObject(${o.track_id})">
      <div class="obj-card-id">#${o.track_id}</div>
      <div class="obj-card-class">${o.class}</div>
      <div class="obj-card-info">
        Frames: ${o.first_frame}–${o.last_frame}<br>
        Confidence: ${(o.conf * 100).toFixed(1)}%
      </div>
      <div class="obj-card-conf">
        <div class="conf-bar" style="width:${(o.conf * 100).toFixed(0)}%"></div>
      </div>
    </div>
  `).join("");

  // restore selection highlight
  if (state.selectedId !== null) {
    document.querySelector(`.obj-card[data-id="${state.selectedId}"]`)
            ?.classList.add("selected");
  }
}

function selectObject(id) {
  state.selectedId = id;
  document.querySelectorAll(".obj-card").forEach(c => {
    c.classList.toggle("selected", parseInt(c.dataset.id) === id);
  });
  trackBtn.disabled = false;
}

// ── Track selected object ─────────────────────────────────────────────────────
trackBtn.addEventListener("click", async () => {
  if (state.selectedId === null) return;

  trackBtn.disabled = true;
  setStatus("Tracking…", "busy");
  showSection("track");
  animateProgress(30, `Rendering annotated video for ID #${state.selectedId}…`);

  // simulate incremental progress while waiting
  let pct = 30;
  const ticker = setInterval(() => {
    pct = Math.min(pct + 5, 85);
    progressBar.style.width = pct + "%";
  }, 800);

  let res;
  try {
    res = await fetch(`${API}/api/track`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId, track_id: state.selectedId }),
    });
  } catch {
    clearInterval(ticker);
    return handleError("Track request failed");
  }

  clearInterval(ticker);

  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return handleError(e.error || "Tracking failed");
  }

  const data = await res.json();
  animateProgress(100, "Complete!");
  setStatus("Done", "active");

  renderResults(data);
  showSection("results");
  trackBtn.disabled = false;
});

// ── Results ───────────────────────────────────────────────────────────────────
function renderResults(data) {
  const a = data.analysis;

  // Stats
  statsGrid.innerHTML = [
    stat("Track ID",     `#${a.track_id}`),
    stat("Class",        a.class),
    stat("Avg Speed",    `${a.avg_speed_px_s} <small>px/s</small>`),
    stat("Max Speed",    `${a.max_speed_px_s} <small>px/s</small>`),
    stat("Total Dist",   `${a.total_distance_px} <small>px</small>`),
    stat("Direction",    a.primary_direction),
    stat("Frames",       a.frames_tracked),
    stat("Net Δ",        `${a.net_displacement[0]},${a.net_displacement[1]} <small>px</small>`),
  ].join("");

  // Video — use <source> tag for proper MIME type handling
  const videoUrl = `${API}${data.video_url}`;
  const src = $("resultVideoSource");
  const vid = $("resultVideo");
  const hint = $("videoHint");
  const dl   = $("videoDownloadLink");

  if (src) {
    src.src = videoUrl;
    vid.load();   // reload the video element with the new source
  } else {
    vid.src = videoUrl;
    vid.load();
  }

  // Show download link in case inline play fails
  if (hint && dl) {
    dl.href = videoUrl;
    hint.style.display = "block";
  }

  // Error handler — show download link prominently
  vid.onerror = () => {
    if (hint) hint.style.display = "block";
    vid.style.display = "none";
  };

  // Graphs
  const g = data.graph_urls;
  const set = (id, url) => { const el = $(id); if (el && url) el.src = API + url; };
  set("imgTrajectory",   g.trajectory);
  set("imgSpeed",        g.speed);
  set("imgDisplacement", g.displacement);
  set("imgDirection",    g.direction);
  set("imgDashboard",    g.dashboard);
}

function stat(label, value) {
  return `<div class="stat-card">
    <div class="stat-value">${value}</div>
    <div class="stat-label">${label}</div>
  </div>`;
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.add("hidden"));
    btn.classList.add("active");
    $(btn.dataset.tab)?.classList.remove("hidden");
  });
});

// ── Action buttons ────────────────────────────────────────────────────────────
$("trackAnotherBtn").addEventListener("click", () => {
  state.selectedId = null;
  trackBtn.disabled = true;
  document.querySelectorAll(".obj-card").forEach(c => c.classList.remove("selected"));
  showSection("detect");
});

$("newVideoBtn").addEventListener("click", () => {
  state.sessionId   = null;
  state.selectedId  = null;
  state.videoSummary = null;
  videoInput.value  = "";
  filePreview.classList.add("hidden");
  uploadBtn.disabled = true;
  trackBtn.disabled  = true;
  objectGrid.innerHTML = "";
  classFilter.value = "";
  resultVideo.src   = "";
  showSection("upload");
  setStatus("Idle", "");
});

// ── Error handler ─────────────────────────────────────────────────────────────
function handleError(msg) {
  setStatus("Error", "error");
  showToast(msg, "error");
  animateProgress(0, "");
  progressLabel.textContent = msg;
  uploadBtn.disabled = false;
  trackBtn.disabled  = false;
  showSection("upload");
}

// ── Init ──────────────────────────────────────────────────────────────────────
showSection("upload");
setStatus("Idle", "");
