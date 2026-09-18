/* =========================================================================
   CamWay — Capture photo depuis la caméra du téléphone (§25.2).
   Deux chemins complémentaires, pour couvrir tous les navigateurs :
   1) Aperçu caméra en direct (getUserMedia) avec bouton "Capturer" : le rendu
      le plus proche d'une vraie appli mobile.
   2) Repli natif : l'input file avec `capture="environment"` ouvre
      directement l'appareil photo du téléphone (fonctionne même si
      getUserMedia est indisponible/refusé, et sert aussi sur desktop pour
      choisir un fichier).
   ========================================================================= */
(function () {
  "use strict";

  var root = document.getElementById("camera-capture");
  if (!root) return;

  var fileInput = root.querySelector("[data-camera-file-input]");
  var startBtn = root.querySelector("[data-camera-start]");
  var shotBtn = root.querySelector("[data-camera-shot]");
  var retakeBtn = root.querySelector("[data-camera-retake]");
  var video = root.querySelector("[data-camera-video]");
  var canvas = root.querySelector("[data-camera-canvas]");
  var preview = root.querySelector("[data-camera-preview]");
  var liveWrap = root.querySelector("[data-camera-live]");
  var stream = null;

  function stopStream() {
    if (stream) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      stream = null;
    }
  }

  function showPreview(dataUrl) {
    preview.src = dataUrl;
    preview.hidden = false;
    liveWrap.hidden = true;
    retakeBtn.hidden = false;
    startBtn.hidden = true;
  }

  function resetToLive() {
    preview.hidden = true;
    retakeBtn.hidden = true;
    fileInput.value = "";
  }

  if (startBtn) {
    startBtn.addEventListener("click", function () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        // Pas d'API caméra en direct dans ce navigateur : on retombe sur
        // l'input natif, qui ouvre quand même l'appareil photo sur mobile.
        fileInput.click();
        return;
      }
      navigator.mediaDevices
        .getUserMedia({ video: { facingMode: "environment" }, audio: false })
        .then(function (s) {
          stream = s;
          video.srcObject = s;
          liveWrap.hidden = false;
          startBtn.hidden = true;
          shotBtn.hidden = false;
        })
        .catch(function () {
          // Permission refusée ou caméra indisponible : repli sur l'input natif.
          fileInput.click();
        });
    });
  }

  if (shotBtn) {
    shotBtn.addEventListener("click", function () {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(function (blob) {
        if (!blob) return;
        var file = new File([blob], "photo-camway.jpg", { type: "image/jpeg" });
        var dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        showPreview(canvas.toDataURL("image/jpeg", 0.9));
        shotBtn.hidden = true;
        stopStream();
      }, "image/jpeg", 0.9);
    });
  }

  if (retakeBtn) {
    retakeBtn.addEventListener("click", function () {
      resetToLive();
      startBtn.hidden = false;
    });
  }

  // Si le visiteur choisit un fichier via le sélecteur natif (repli, ou
  // desktop), on affiche aussi un aperçu pour rester cohérent visuellement.
  fileInput.addEventListener("change", function () {
    var file = fileInput.files && fileInput.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function (e) { showPreview(e.target.result); };
    reader.readAsDataURL(file);
  });

  window.addEventListener("beforeunload", stopStream);
})();
