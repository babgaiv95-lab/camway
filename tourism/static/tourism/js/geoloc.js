/* =========================================================================
   CamWay — Position du visiteur & distance jusqu'aux sites.
   - Ne demande la position qu'à l'initiative du visiteur (bouton), jamais
     automatiquement : respect de la vie privée / permission explicite.
   - Une fois autorisée, la position est mémorisée en sessionStorage (durée
     de l'onglet) pour ne pas la redemander à chaque page.
   - Calcule la distance à vol d'oiseau (formule de Haversine) et une
     estimation de temps de trajet routier très approximative.
   ========================================================================= */
(function () {
  "use strict";

  var STORAGE_KEY = "camway_position";
  var MAX_AGE_MS = 20 * 60 * 1000; // 20 min : au-delà, on considère la position périmée

  function getStoredPosition() {
    try {
      var raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || (Date.now() - data.t) > MAX_AGE_MS) return null;
      return data;
    } catch (e) {
      return null;
    }
  }

  function storePosition(lat, lng) {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ lat: lat, lng: lng, t: Date.now() }));
    } catch (e) { /* stockage indisponible (navigation privée...) : on continue sans persister */ }
  }

  function haversineKm(lat1, lng1, lat2, lng2) {
    var R = 6371; // rayon moyen de la Terre en km
    var toRad = function (d) { return (d * Math.PI) / 180; };
    var dLat = toRad(lat2 - lat1);
    var dLng = toRad(lng2 - lng1);
    var a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
      Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function formatDistance(km) {
    if (km < 1) return Math.round(km * 1000) + " m";
    if (km < 10) return km.toFixed(1).replace(".", ",") + " km";
    return Math.round(km) + " km";
  }

  function formatEta(km) {
    // Estimation très approximative (route camerounaise moyenne) : à titre
    // indicatif seulement, jamais présentée comme un temps de trajet garanti.
    var speedKmh = 45;
    var hours = km / speedKmh;
    var minutes = Math.round(hours * 60);
    if (minutes < 60) return "~" + minutes + " min en voiture";
    var h = Math.floor(minutes / 60);
    var m = minutes % 60;
    return "~" + h + " h" + (m ? String(m).padStart(2, "0") : "");
  }

  function renderWidget(el, position) {
    var lat = parseFloat(el.getAttribute("data-lat"));
    var lng = parseFloat(el.getAttribute("data-lng"));
    if (isNaN(lat) || isNaN(lng)) { el.style.display = "none"; return; }

    if (!position) {
      el.innerHTML =
        '<button type="button" class="geo-btn" data-geo-request>' +
        '<i class="fa-solid fa-location-crosshairs icon"></i> ' +
        (el.getAttribute("data-geo-label") || "Distance depuis ma position") +
        "</button>";
      return;
    }

    var km = haversineKm(position.lat, position.lng, lat, lng);
    var directionsUrl =
      "https://www.google.com/maps/dir/?api=1&origin=" + position.lat + "," + position.lng +
      "&destination=" + lat + "," + lng + "&travelmode=driving";

    el.innerHTML =
      '<span class="geo-distance"><i class="fa-solid fa-route icon"></i> ' + formatDistance(km) +
      '<span class="geo-eta">' + formatEta(km) + "</span></span>" +
      '<a class="geo-directions" href="' + directionsUrl + '" target="_blank" rel="noopener">' +
      '<i class="fa-solid fa-diamond-turn-right icon"></i> Itinéraire</a>';
  }

  // Variante passive, texte seul, SANS bouton ni lien : à utiliser dans un
  // contexte déjà cliquable (ex. une carte de site qui est elle-même un
  // <a>...</a>), où imbriquer un bouton/lien casserait le HTML et le clic.
  // Ne s'affiche que si la position est déjà connue ; reste vide sinon
  // (l'activation de la position se fait via un bouton global sur la page).
  function renderPassiveText(el, position) {
    var lat = parseFloat(el.getAttribute("data-lat"));
    var lng = parseFloat(el.getAttribute("data-lng"));
    if (isNaN(lat) || isNaN(lng) || !position) { el.textContent = ""; return; }
    var km = haversineKm(position.lat, position.lng, lat, lng);
    el.innerHTML = '<i class="fa-solid fa-route icon"></i> ' + formatDistance(km) +
      '<span style="color:var(--cw-ink-soft); font-weight:500;"> · ' + formatEta(km) + "</span>";
  }

  function renderAll() {
    var position = getStoredPosition();
    var nodes = document.querySelectorAll("[data-cw-distance]");
    for (var i = 0; i < nodes.length; i++) renderWidget(nodes[i], position);
    var textNodes = document.querySelectorAll("[data-cw-distance-text]");
    for (var j = 0; j < textNodes.length; j++) renderPassiveText(textNodes[j], position);
    document.dispatchEvent(new CustomEvent("camway:position-rendered", { detail: { position: position } }));
  }

  function requestLocation(onDone) {
    if (!("geolocation" in navigator)) {
      window.alert("La géolocalisation n'est pas disponible sur ce navigateur.");
      return;
    }
    document.body.classList.add("geo-loading");
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        storePosition(pos.coords.latitude, pos.coords.longitude);
        document.body.classList.remove("geo-loading");
        renderAll();
        if (onDone) onDone(true);
      },
      function () {
        document.body.classList.remove("geo-loading");
        window.alert(
          "Impossible d'accéder à votre position. Vérifiez que la localisation est " +
          "autorisée pour ce site dans les réglages de votre navigateur."
        );
        if (onDone) onDone(false);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: MAX_AGE_MS }
    );
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-geo-request]");
    if (btn) {
      e.preventDefault();
      e.stopPropagation();
      requestLocation();
    }
  });

  document.addEventListener("DOMContentLoaded", renderAll);

  // API exposée pour les autres scripts (ex. tri par proximité sur /explorer/,
  // affichage de la distance dans le résultat de reconnaissance photo).
  window.CamwayGeo = {
    getStoredPosition: getStoredPosition,
    requestLocation: requestLocation,
    haversineKm: haversineKm,
    formatDistance: formatDistance,
    formatEta: formatEta,
    renderAll: renderAll,
  };
})();
