// Parse URL parameters
const params = new URLSearchParams(window.location.search);

const tilt = parseFloat(params.get("tilt")) || 0;
const power = parseFloat(params.get("power")) || 0;
const temp = parseFloat(params.get("temp")) || 0;
const gain = parseFloat(params.get("gain")) || 0;
const lat = params.get("lat") || "—";
const date = params.get("date") || "—";
const powerCurveUrl = params.get("powerCurve") || "";

// Populate stats
document.getElementById("res-tilt").textContent = tilt.toFixed(0);
document.getElementById("res-power").textContent = power.toFixed(0);
document.getElementById("res-temp").textContent = temp.toFixed(1);
document.getElementById("res-gain").textContent = gain.toFixed(1);
document.getElementById("res-date").textContent = date;
document.getElementById("res-lat").textContent = lat;

// Fixed tilt is latitude (rule of thumb)
const fixedTilt = parseInt(lat);
document.getElementById("fixed-tilt").textContent = isNaN(fixedTilt) ? "—" : fixedTilt;

// Set images
if (powerCurveUrl) {
  document.getElementById("power-curve").src = powerCurveUrl;
}

// Save PDF
document.getElementById("save-pdf").addEventListener("click", async () => {
  const payload = { date, latitude: parseFloat(lat) };
  try {
    const r = await fetch("/api/export-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!r.ok) throw new Error("Export failed");
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `solar_report_${date}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("PDF export failed");
    console.error(err);
  }
});

// Share results
document.getElementById("share").addEventListener("click", async () => {
  const shareUrl = location.href;
  const text = `Optimal solar tilt: ${tilt.toFixed(0)}° | Power: ${power.toFixed(0)}W | Temp: ${temp.toFixed(1)}°C | Gain: ${gain.toFixed(1)}%`;
  
  if (navigator.share) {
    try {
      await navigator.share({
        title: "Solar Tilt Optimization Results",
        text: text,
        url: shareUrl
      });
    } catch (e) {
      console.log("Share cancelled", e);
    }
  } else {
    try {
      await navigator.clipboard.writeText(shareUrl);
      alert("Link copied to clipboard!");
    } catch (e) {
      prompt("Copy this link:", shareUrl);
    }
  }
});

// Recalculate
document.getElementById("recalc").addEventListener("click", () => {
  location.href = `index.html?date=${encodeURIComponent(date)}&lat=${encodeURIComponent(lat)}`;
});

// Gratitude overlay with universe particles
document.getElementById("show-gratitude").addEventListener("click", () => {
  const overlay = document.getElementById("gratitude-overlay");
  overlay.classList.remove("hidden");
  
  const container = document.getElementById("universe-container");
  container.innerHTML = "";
  
  // Add drifting particles
  for (let i = 0; i < 50; i++) {
    const star = document.createElement("div");
    star.className = "universe-particle";
    star.style.left = Math.random() * 100 + "%";
    star.style.width = Math.random() * 3 + 1 + "px";
    star.style.height = star.style.width;
    star.style.animationDelay = Math.random() * 3 + "s";
    star.style.opacity = Math.random() * 0.8 + 0.2;
    container.appendChild(star);
  }
});

// Populate date/lat if returning from home
window.addEventListener("load", () => {
  const returnDate = params.get("date");
  const returnLat = params.get("lat");
  // (already populated above)
});
