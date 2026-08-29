(function () {
  "use strict";

  // --- Dark / Light Mode Toggle -------------------------------------------
  var root = document.documentElement;
  var toggleBtn = document.getElementById("theme-toggle");

  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") === "light" ? "light" : "dark";
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try {
        localStorage.setItem("rtwf-theme", next);
      } catch (e) {
        /* localStorage evtl. nicht verfuegbar (z.B. Privacy Mode) - kein Problem */
      }
    });
  }

  // --- Eigene Anzahl an Eintraegen ----------------------------------------
  var customForm = document.querySelector(".n-custom");
  if (customForm) {
    customForm.addEventListener("submit", function (evt) {
      evt.preventDefault();
      var input = customForm.querySelector("input[name='n']");
      var value = parseInt(input.value, 10);
      if (!value || value < 1) return;
      value = Math.min(value, 200);

      var mode = customForm.getAttribute("data-mode");
      var isCompare = customForm.getAttribute("data-compare") === "true";

      if (isCompare) {
        window.location.href = "/" + mode + "/" + value + "/compare";
      } else {
        var guild = customForm.getAttribute("data-guild");
        window.location.href = "/" + mode + "/" + value + "?guild=" + encodeURIComponent(guild);
      }
    });
  }
})();
