let fileId = null;
let filename = null;

async function startDownload() {
  const url = document.getElementById("urlInput").value;
  const res = await fetch("http://localhost:8000/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url })
  });

  const data = await res.json();
  fileId = data.file_id;
  filename = data.filename;

  // Izlušči naslov iz filename
  const title = filename.split("-").slice(1).join("-").replace(/\.mp3$/, "").trim();

  document.getElementById("status").innerText = `Procesiranje uspešno.`;
  const downloadBtn = document.getElementById("downloadBtn");
  downloadBtn.innerText = `Prenesi: ${title}`;
  downloadBtn.disabled = false;
}

async function checkStatus() {
  if (!fileId) return;
  const res = await fetch(`http://localhost:8000/status/${fileId}`);
  const data = await res.json();
  document.getElementById("status").innerText = data.ready ? "MP3 pripravljen!" : "Še ni dokončano...";
}

function getMp3() {
  if (!fileId || !filename) return;
  const a = document.createElement("a");
  a.href = `http://localhost:8000/download/${fileId}`;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

async function deleteMp3() {
  if (!fileId) return;
  await fetch(`http://localhost:8000/delete/${fileId}`, { method: "DELETE" });
  document.getElementById("status").innerText = "MP3 izbrisan.";
  fileId = null;
  filename = null;
  const downloadBtn = document.getElementById("downloadBtn");
  downloadBtn.innerText = "Prenesi MP3";
  downloadBtn.disabled = true;
}