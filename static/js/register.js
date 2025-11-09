document.addEventListener("DOMContentLoaded", function () {
      
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
        formData.forEach((value, key) => {
            data[key] = value;
        });

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
                setTimeout(() => {
                    window.location.href = "/login";
                }, 1000);
            }
        })
        .catch(error => {
            console.error("Error:", error);

            if (error.data && error.data.errors) {
                for (const field in error.data.errors) {
                    const errorDiv = document.getElementById(`${field}-error`);
                    const errorMessage = error.data.errors[field];
                    
                    if (errorDiv) {
                        errorDiv.textContent = errorMessage;
                    } else {
                        alert(errorMessage);
                    }
                }
            } else {
                alert("An unknown error occurred. Please try again.");
            }
      
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalButtonHTML;
        });
    });
});