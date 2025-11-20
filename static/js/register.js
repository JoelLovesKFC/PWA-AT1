document.addEventListener("DOMContentLoaded", function () {
  // ----- One eye toggle for BOTH fields -----
  const pw1 = document.getElementById('reg_password');
  const pw2 = document.getElementById('reg_confirm_password');
  const toggleAll = document.getElementById('togglePwAll');

  if (toggleAll && pw1 && pw2) {
    toggleAll.addEventListener('click', () => {
      // If both currently are password -> show; otherwise hide
      const show = pw1.type === 'password' && pw2.type === 'password';
      const newType = show ? 'text' : 'password';
      pw1.type = newType;
      pw2.type = newType;

      toggleAll.setAttribute('aria-pressed', String(show));
      toggleAll.setAttribute('aria-label', show ? 'Hide passwords' : 'Show passwords');

      const icon = toggleAll.querySelector('i');
      if (icon) {
        icon.classList.toggle('bi-eye', !show);
        icon.classList.toggle('bi-eye-slash', show);
      }
    });
  }
  // ------------------------------------------

  const registerForm = document.getElementById("registerForm");
  const submitBtn = document.getElementById("submitBtn");
  const originalButtonHTML = submitBtn.innerHTML;

  registerForm.addEventListener("submit", function (event) {
    event.preventDefault();

    document.querySelectorAll('.text-danger').forEach(el => el.textContent = '');

    submitBtn.disabled = true;
    submitBtn.innerHTML = `
      <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
      Registering...
    `;

    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    const formData = new FormData(registerForm);
    const data = {};
    formData.forEach((value, key) => { data[key] = value; });

    fetch("/api/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify(data)
    })
      .then(response => {
        if (!response.ok) {
          return response.json().then(errorData => {
            const error = new Error('Server responded with an error.');
            error.data = errorData;
            throw error;
          });
        }
        return response.json();
      })
      .then(result => {
        if (result.status === "success") {
          submitBtn.innerHTML = 'Success!';
          submitBtn.classList.remove('btn-primary');
          submitBtn.classList.add('btn-success');
          setTimeout(() => { window.location.href = "/login"; }, 1000);
        }
      })
      .catch(error => {
        console.error("Error:", error);

        if (error.data && error.data.errors) {
          for (const field in error.data.errors) {
            const errorDiv = document.getElementById(`${field}-error`);
            const errorMessage = error.data.errors[field];
            if (errorDiv) errorDiv.textContent = errorMessage; else alert(errorMessage);
          }
        } else {
          alert("An unknown error occurred. Please try again.");
        }

        submitBtn.disabled = false;
        submitBtn.innerHTML = originalButtonHTML;
      });
  });
});
