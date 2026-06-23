const form = document.getElementById("generateForm");
const btn = document.getElementById("generateBtn");
const statusEl = document.getElementById("status");
const promptEl = document.getElementById("prompt");
const emptyState = document.getElementById("emptyState");
const gifPreview = document.getElementById("gifPreview");
const saveBtn = document.getElementById("saveBtn");
const directDownloadLink = document.getElementById("directDownloadLink");
const openGifLink = document.getElementById("openGifLink");
const savePath = document.getElementById("savePath");
const metadata = document.getElementById("metadata");
const durationMeta = document.getElementById("durationMeta");
const frameMeta = document.getElementById("frameMeta");
const providerMeta = document.getElementById("providerMeta");
const serverSaveEnabled = document.body.dataset.serverSaveEnabled === "1";
let currentFile = null;

function setLoading(isLoading) {
  btn.disabled = isLoading;
  btn.textContent = isLoading ? "생성 중..." : "GIF 생성";
}

function showStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "error" : "";
}

function resetPreview() {
  currentFile = null;
  emptyState.classList.remove("hidden");
  gifPreview.classList.add("hidden");
  directDownloadLink.classList.add("hidden");
  openGifLink.classList.add("hidden");
  saveBtn.classList.add("hidden");
  savePath.classList.add("hidden");
  metadata.classList.add("hidden");
}

function containsKorean(text) {
  return /[가-힣]/.test(text);
}

function showPreview(data) {
  currentFile = {
    filename: data.filename,
    downloadUrl: data.downloadUrl,
    viewUrl: data.viewUrl,
    saveUrl: data.saveUrl,
  };

  emptyState.classList.add("hidden");
  gifPreview.src = `${data.url}?t=${Date.now()}`;
  gifPreview.classList.remove("hidden");

  directDownloadLink.href = `${data.downloadUrl}?t=${Date.now()}`;
  directDownloadLink.download = data.filename;
  directDownloadLink.classList.remove("hidden");

  openGifLink.href = data.viewUrl || data.url;
  openGifLink.classList.remove("hidden");

  if (serverSaveEnabled && data.downloadToServerEnabled) {
    saveBtn.classList.remove("hidden");
  }

  durationMeta.textContent = `${data.metadata.durationSeconds}s`;
  frameMeta.textContent = `${data.metadata.frameCount}`;
  providerMeta.textContent = data.metadata.note
    ? `${data.metadata.provider} - ${data.metadata.note}`
    : data.metadata.provider;
  metadata.classList.remove("hidden");
}

saveBtn.addEventListener("click", async () => {
  if (!currentFile) return;

  saveBtn.disabled = true;
  showStatus("GIF 파일을 서버 폴더에 저장합니다.");

  try {
    const res = await fetch(currentFile.saveUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: currentFile.filename }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.message || "저장에 실패했습니다.");
    }

    savePath.textContent = data.path;
    savePath.classList.remove("hidden");
    showStatus("저장 완료. 아래 경로에서 GIF 파일을 확인하세요.");
  } catch (err) {
    showStatus(err.message || "저장 중 오류가 발생했습니다.", true);
  } finally {
    saveBtn.disabled = false;
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptEl.value.trim();
  const style = document.getElementById("style").value;
  const ratio = document.getElementById("ratio").value;

  if (!prompt) {
    showStatus("먼저 영어 프롬프트를 입력해 주세요.", true);
    return;
  }

  if (containsKorean(prompt)) {
    showStatus("현재 테스트 버전은 영어만 지원합니다. 예: cherry blossom petals blowing in the wind", true);
    return;
  }

  setLoading(true);
  resetPreview();

  try {
    showStatus("GIF 생성을 시작합니다.");
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, style, ratio }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      throw new Error(data.message || "생성에 실패했습니다.");
    }

    showPreview(data);
    showStatus("GIF 생성이 완료되었습니다. 휴대폰에서는 '모바일에서 GIF 열기/저장'을 눌러 저장하세요.");
  } catch (err) {
    showStatus(err.message || "오류가 발생했습니다. 다시 시도해 주세요.", true);
  } finally {
    setLoading(false);
  }
});
