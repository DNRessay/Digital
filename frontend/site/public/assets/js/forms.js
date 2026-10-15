/**
 * Web3Forms submission handler for .php-email-form forms.
 * Replaces the template's own vendor validate.js, which expects its own
 * PHP backend to reply with the literal text "OK" — Web3Forms replies with
 * JSON ({success: true/false, message}), so that script would always
 * report an error even on a successful submission.
 */
(function () {
  "use strict";

  const WEB3FORMS_ENDPOINT = "https://api.web3forms.com/submit";

  document.querySelectorAll(".php-email-form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();

      const loading = form.querySelector(".loading");
      const errorMessage = form.querySelector(".error-message");
      const sentMessage = form.querySelector(".sent-message");

      loading.classList.add("d-block");
      errorMessage.classList.remove("d-block");
      sentMessage.classList.remove("d-block");

      const formData = new FormData(form);

      fetch(WEB3FORMS_ENDPOINT, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          loading.classList.remove("d-block");
          if (data.success) {
            sentMessage.classList.add("d-block");
            form.reset();
          } else {
            errorMessage.innerHTML = data.message || "Something went wrong. Please try again.";
            errorMessage.classList.add("d-block");
          }
        })
        .catch(() => {
          loading.classList.remove("d-block");
          errorMessage.innerHTML = "Network error. Please try again in a moment.";
          errorMessage.classList.add("d-block");
        });
    });
  });
})();
