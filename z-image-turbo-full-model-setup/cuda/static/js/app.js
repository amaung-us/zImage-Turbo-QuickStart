"use strict";

let isGenerating = false;

async function generateImage() {
  if (isGenerating) return;

  const prompt = document.getElementById("prompt").value.trim();
  if (!prompt) {
    showError("Please enter a prompt.");
    return;
  }

  const width  = parseInt(document.getElementById("width").value, 10);
  const height   = parseInt(document.getElementById("height").value, 10);
  const steps    = parseInt(document.getElementById("steps").value, 10);
  const seed     = parseInt(document.getElementById("seed").value, 10);

  setGenerating(true);
  hideMessages();

  // Add a loading placeholder card
  const loadingCard = addLoadingCard(prompt);

  const payload = {
    prompt,
    size: `${width}x${height}`,
    num_steps: steps,
    seed,
    response_format: "b64_json",
  };

  try {
    const res = await fetch("/v1/images/generations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      const msg = data?.error?.message || `HTTP ${res.status}`;
      throw new Error(msg);
    }

    const imageData = data.data?.[0];
    if (!imageData) throw new Error("No image returned.");

    const imgUrl = imageData.url || buildB64Url(imageData.b64_json);
    const elapsed = data.elapsed_seconds ?? null;

    replaceLoadingCard(loadingCard, imgUrl, prompt, width, height, steps, seed, elapsed);

    showStatus(`Generated in ${elapsed != null ? elapsed + "s" : "unknown time"}.`);
  } catch (err) {
    loadingCard.remove();
    showError(err.message || "Generation failed.");
  } finally {
    setGenerating(false);
  }
}

// ---- UI helpers ----

function setGenerating(state) {
  isGenerating = state;
  const btn     = document.getElementById("generate-btn");
  const btnText = document.getElementById("btn-text");
  const spinner = document.getElementById("btn-spinner");
  btn.disabled = state;
  btnText.textContent = state ? "Generating…" : "Generate";
  spinner.classList.toggle("hidden", !state);
}

function showError(msg) {
  const el = document.getElementById("error-msg");
  el.textContent = msg;
  el.classList.remove("hidden");
  document.getElementById("status-msg").classList.add("hidden");
}

function showStatus(msg) {
  const el = document.getElementById("status-msg");
  el.textContent = msg;
  el.classList.remove("hidden");
  document.getElementById("error-msg").classList.add("hidden");
}

function hideMessages() {
  document.getElementById("error-msg").classList.add("hidden");
  document.getElementById("status-msg").classList.add("hidden");
}

function addLoadingCard(prompt) {
  const gallery = document.getElementById("gallery");

  // Remove placeholder if present
  const ph = gallery.querySelector(".placeholder");
  if (ph) ph.remove();

  const card = document.createElement("div");
  card.className = "loading-card";
  card.innerHTML = `
    <div class="spinner"></div>
    <span>Generating…</span>
    <small style="font-size:11px;max-width:260px;text-align:center;word-break:break-word;color:#555570">${escHtml(prompt)}</small>
  `;
  gallery.prepend(card);
  return card;
}

function replaceLoadingCard(card, imgUrl, prompt, width, height, steps, seed, elapsed) {
  const imgCard = document.createElement("div");
  imgCard.className = "img-card";

  const elapsedTag = elapsed != null ? `<span class="tag">${elapsed}s</span>` : "";

  imgCard.innerHTML = `
    <img src="${escHtml(imgUrl)}" alt="${escHtml(prompt)}" loading="lazy" />
    <div class="img-card-meta">
      <div class="img-card-prompt" title="${escHtml(prompt)}">${escHtml(prompt)}</div>
      <div class="img-card-info">
        <div class="img-card-tags">
          <span class="tag">${width}×${height}</span>
          <span class="tag">${steps} steps</span>
          <span class="tag">seed ${seed < 0 ? "rnd" : seed}</span>
          ${elapsedTag}
        </div>
        <div class="img-card-actions">
          <a class="btn-icon" href="${escHtml(imgUrl)}" download title="Download">&#8659;</a>
          <button class="btn-icon" onclick="copyPrompt(this)" data-prompt="${escHtml(prompt)}" title="Copy prompt">&#128203;</button>
        </div>
      </div>
    </div>
  `;

  card.replaceWith(imgCard);
}

function copyPrompt(btn) {
  const text = btn.getAttribute("data-prompt");
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = "&#10003;";
    setTimeout(() => { btn.innerHTML = orig; }, 1500);
  });
}

function buildB64Url(b64) {
  return `data:image/png;base64,${b64}`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Allow Ctrl+Enter / Cmd+Enter to generate
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("prompt").addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") generateImage();
  });
});
