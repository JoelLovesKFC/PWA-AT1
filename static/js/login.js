document.addEventListener("DOMContentLoaded", function () {

    const loginForm = document.getElementById("loginForm");
    const submitBtn = document.getElementById("submitBtn");
    const originalButtonHTML = submitBtn.innerHTML;

    loginForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const errorDiv = document.getElementById('general-error');
        if (errorDiv) {
            errorDiv.textContent = '';
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Logging In...
        `;

        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const formData = new FormData(loginForm);
        const data = {};
        formData.forEach((value, key) => { data[key] = value; });

        fetch("/login", {
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
                    window.location.href = "/dashboard";
                }
            })
            .catch(error => {
                console.error("Error:", error);
                if (error.data && error.data.message) {
                    if (errorDiv) {
                        errorDiv.textContent = error.data.message;
                    }
                } else {
                    alert("An unknown error occurred.");
                }
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalButtonHTML;
            });
    });
});


window.addEventListener('pageshow', function (event) {

    if (event.persisted) {
        console.log('Page loaded from cache. Resetting form.');
        const loginForm = document.getElementById("loginForm");
        const submitBtn = document.getElementById("submitBtn");
        const errorDiv = document.getElementById('general-error');

        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Login';
        }
        if (loginForm) {
            loginForm.reset(); 
        }
        if (errorDiv) {
            errorDiv.textContent = ''; 
        }
    }
});