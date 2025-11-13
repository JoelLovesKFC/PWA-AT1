// static/js/profile_basic.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('editProfileForm');
    const saveBtn = document.getElementById('saveBtn');

    function setErrors(map = {}) {
        ['name', 'username', 'email'].forEach(f => {
            const slot = document.getElementById(`${f}-error`);
            if (slot) slot.textContent = map[f] || '';
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        setErrors({});
        saveBtn.disabled = true;

        const payload = {
            name: form.name.value.trim(),
            username: form.username.value.trim(),
            email: form.email.value.trim(),
        };

        try {
            const res = await fetch('/api/profile/basic', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                },
                credentials: 'same-origin',
                body: JSON.stringify(payload)
            });

            const data = await res.json().catch(() => ({}));

            if (!res.ok) {
                // Per-field error coming from backend? (field + message)
                if (data.field && data.message) {
                    setErrors({ [data.field]: data.message });
                } else if (data.message) {
                    alert(data.message);
                } else {
                    alert('Failed to save profile.');
                }
                return;
            }

            // Success: go back to profile so updated values render
            window.location.href = '/profile';
        } catch (err) {
            console.error(err);
            alert('Network error while saving profile.');
        } finally {
            saveBtn.disabled = false;
        }
    });
});
