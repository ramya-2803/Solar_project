// Initialize map
let map = L.map("map").setView([20.59, 78.96], 4);
let marker;
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors"
}).addTo(map);

map.on("click", e => {
  const lat = e.latlng.lat.toFixed(6);
  document.getElementById("latitude").value = lat;
  
  if (marker) marker.remove();
  marker = L.marker([e.latlng.lat, e.latlng.lng]).addTo(map);
  
  document.getElementById("lat-pill").classList.remove("hidden");
  document.getElementById("lat-value").textContent = lat;
});

// Toggle map visibility
document.getElementById("map-toggle").addEventListener("click", () => {
  const mapContainer = document.getElementById("map-container");
  mapContainer.classList.toggle("hidden");
  if (!mapContainer.classList.contains("hidden")) {
    setTimeout(() => map.invalidateSize(), 200);
  }
});

// Try auto-detect location
async function tryAutoLocation() {
  const latInput = document.getElementById("latitude");
  
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => {
        const lat = pos.coords.latitude.toFixed(6);
        latInput.value = lat;
        document.getElementById("lat-pill").classList.remove("hidden");
        document.getElementById("lat-value").textContent = lat;
        map.setView([parseFloat(lat), pos.coords.longitude || 0], 6);
        if (marker) marker.remove();
        marker = L.marker([pos.coords.latitude, pos.coords.longitude]).addTo(map);
      },
      err => {
        // If browser geolocation fails or is denied, instruct the user to use the map.
        console.warn("Geolocation unavailable or denied", err);
        latInput.placeholder = "Click 'Select from Map' to pick latitude";
        // leave lat-pill hidden until user chooses manually
      },
      { timeout: 5000 }
    );
  }
}

// Sunrise + particle animation
function playTransitionAnimation() {
  const overlay = document.getElementById("transition-overlay");
  overlay.classList.remove("hidden");
  overlay.innerHTML = "";

  const sun = document.createElement("div");
  sun.className = "sun-burst";
  overlay.appendChild(sun);

  // Particles
  for (let i = 0; i < 40; i++) {
    const p = document.createElement("div");
    p.className = "particle-burst";
    p.style.left = Math.random() * 100 + "%";
    p.style.top = 50 + Math.random() * 40 + "%";
    p.style.opacity = Math.random() * 0.8;
    p.style.animationDelay = Math.random() * 0.5 + "s";
    overlay.appendChild(p);
  }

  return new Promise(res => setTimeout(() => {
    overlay.classList.add("hidden");
    overlay.innerHTML = "";
    res();
  }, 2000));
}

// Set today's date as default
const dateInput = document.getElementById("date");
const today = new Date().toISOString().split("T")[0];
dateInput.value = today;

// Auto-detect on load
tryAutoLocation();

// Form submission
document.getElementById("tilt-form").addEventListener("submit", async e => {
  e.preventDefault();
  
  const date = document.getElementById("date").value;
  const lat = document.getElementById("latitude").value;
  
  if (!date || !lat) {
    alert("Please enter date and latitude (or click the map).");
    return;
  }

  // Play transition animation
  await playTransitionAnimation();

  // Call backend
  try {
    const r = await fetch("/api/optimal-tilt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date, latitude: parseFloat(lat) })
    });
    
    if (!r.ok) throw new Error("Compute failed");
    const d = await r.json();
    
    // Navigate to results with all data
    const params = new URLSearchParams({
      tilt: d.optimal_tilt_deg,
      power: d.expected_power_w,
      temp: d.panel_temperature_c,
      gain: d.energy_gain_pct,
      lat: d.latitude,
      date: d.date,
      powerCurve: d.images.power_curve
    });
    
    location.href = `result.html?${params.toString()}`;
  } catch (err) {
    console.error(err);
    alert("Calculation failed — try again later.");
  }
});

// Smooth scroll nav links
document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", e => {
    const href = link.getAttribute("href");
    if (href.startsWith("#")) {
      e.preventDefault();
      const section = document.querySelector(href);
      if (section) {
        section.scrollIntoView({ behavior: "smooth" });
      }
    }
  });
});
