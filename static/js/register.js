document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("registerForm");
    const registerBtn = document.getElementById("registerBtn");
    const successButton = document.getElementById("successButton");

    form.addEventListener("submit", function (e) {
        e.preventDefault();

        // Collect form values
        const name = form.name.value.trim();
        const username = form.username.value.trim();
        const email = form.email.value.trim();
        const password = form.password.value.trim();
        const confirmPassword = form.confirm_password.value.trim();

        // Simple validation
        if (!name || !username || !email || !password || !confirmPassword) {
            alert("Please fill in all fields.");
            return;
        }

        if (password !== confirmPassword) {
            alert("Passwords do not match.");
            return;
        }

        // Validation passed → show success button
        registerBtn.style.display = "none";
        successButton.style.display = "block";
    });

    // Send data to Flask when success button is clicked
    successButton.addEventListener("click", function () {
        const payload = {
            name: form.name.value.trim(),
            username: form.username.value.trim(),
            email: form.email.value.trim(),
            password: form.password.value.trim()
        };

        fetch("/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    window.location.href = "/login"; // redirect to login page
                } else {
                    alert("Registration failed. Try again.");
                }
            })
            .catch(err => {
                console.error(err);
                alert("An error occurred. Try again."); 
            });
    });
});
