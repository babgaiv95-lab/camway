document.addEventListener("DOMContentLoaded", function () {
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });
  }

  // Exemples cliquables dans le chat
  document.querySelectorAll(".chat-examples button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var input = document.querySelector("#chat-message-input");
      if (input) {
        input.value = btn.getAttribute("data-text");
        input.focus();
      }
    });
  });

  // Auto-scroll vers le bas du chat
  var chatMessages = document.querySelector(".chat-messages");
  if (chatMessages) {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Indicateur "CamWay réfléchit..." pendant le traitement de la question.
  // Le formulaire reste un POST classique (rechargement de page) : cet
  var chatForm = document.querySelector(".chat-input-bar");
  if (chatForm && chatMessages) {
    chatForm.addEventListener("submit", function () {
      var input = chatForm.querySelector("#chat-message-input");
      var button = chatForm.querySelector("button[type=submit]");
      if (input && !input.value.trim()) return;

      var thinking = document.createElement("div");
      thinking.className = "chat-bubble assistant chat-thinking";
      thinking.innerHTML =
        '<i class="fa-solid fa-circle-notch fa-spin icon"></i> CamWay réfléchit' +
        '<span class="chat-thinking-dots"><span>.</span><span>.</span><span>.</span></span>';
      chatMessages.appendChild(thinking);
      chatMessages.scrollTop = chatMessages.scrollHeight;

      // IMPORTANT : ne jamais faire `input.disabled = true` ici. Un champ
      // désactivé pendant l'événement "submit" est exclu par le navigateur
      // des données envoyées avec le formulaire -> le champ "message" partirait
      // vide côté serveur, quoi que le visiteur ait tapé (d'où l'erreur
      // "Ce champ est obligatoire" systématique). `readOnly` empêche la
      // saisie sans empêcher l'envoi de la valeur déjà tapée.
      if (button) { button.disabled = true; button.textContent = "Envoi..."; }
      if (input) { input.readOnly = true; }
    });
  }

  // Filtrage / recommandation automatiques : les formulaires marqués

  document.querySelectorAll("form.auto-filter").forEach(function (form) {
    var debounceTimer = null;

    function submitNow() {
      if (form.requestSubmit) { form.requestSubmit(); } else { form.submit(); }
    }

    form.addEventListener("change", function (e) {
      var target = e.target;
      var tag = target.tagName ? target.tagName.toLowerCase() : "";
      var type = (target.getAttribute && target.getAttribute("type") || "").toLowerCase();
      if (tag === "select" || type === "checkbox" || type === "radio") {
        submitNow();
      }
    });

    form.addEventListener("input", function (e) {
      var target = e.target;
      var type = (target.getAttribute && target.getAttribute("type") || "").toLowerCase();
      if (type === "text" || type === "number" || type === "search") {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(submitNow, 500);
      }
    });

    // Après un rechargement déclenché par la saisie, remet le focus et le
    // curseur à la fin du champ texte pour ne pas casser la frappe.
    var params = new URLSearchParams(window.location.search);
    form.querySelectorAll("input[type=text], input[type=number], input[type=search]").forEach(function (el) {
      if (el.name && params.has(el.name) && params.get(el.name) === el.value && el.value) {
        el.focus();
        var v = el.value;
        el.value = "";
        el.value = v;
      }
    });
  });
});
