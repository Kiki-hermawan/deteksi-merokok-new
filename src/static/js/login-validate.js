(function () {
    const form = document.getElementById('loginForm');
    if (!form) return;

    const username = document.getElementById('username');
    const password = document.getElementById('password');

    function markFilled(input) {
        const field = input.closest('.field');
        const hasValue = input.value.trim().length > 0;
        // Begitu user mulai mengetik ulang, hapus status error dari percobaan login sebelumnya
        field.classList.remove('has-error');
        field.classList.toggle('is-valid', hasValue);
    }

    username.addEventListener('input', () => markFilled(username));
    password.addEventListener('input', () => markFilled(password));

    form.addEventListener('submit', (e) => {
        let ok = true;
        [username, password].forEach((input) => {
            const field = input.closest('.field');
            const hasValue = input.value.trim().length > 0;
            field.classList.toggle('has-error', !hasValue);
            field.classList.toggle('is-valid', hasValue);
            if (!hasValue) ok = false;
        });
        if (!ok) {
            e.preventDefault();
            form.querySelector('.field.has-error input').focus();
        }
    });
})();