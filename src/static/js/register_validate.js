(function () {
    const form = document.getElementById('registerForm');
    if (!form) return;

    const username = document.getElementById('username');
    const password = document.getElementById('password');
    const confirm = document.getElementById('password_confirm');

    function setError(input, hasError) {
        const field = input.closest('.field');
        field.classList.toggle('has-error', hasError);
        if (!hasError && input.value) {
            field.classList.add('is-valid');
        } else {
            field.classList.remove('is-valid');
        }
    }

    function validateUsername() {
        const ok = /^[A-Za-z0-9_]{4,}$/.test(username.value);
        setError(username, username.value.length > 0 && !ok);
        return ok;
    }

    function validatePassword() {
        const ok = password.value.length >= 8;
        setError(password, password.value.length > 0 && !ok);
        return ok;
    }

    function validateConfirm() {
        const ok = confirm.value.length > 0 && confirm.value === password.value;
        setError(confirm, confirm.value.length > 0 && !ok);
        return ok;
    }

    // Validasi langsung saat mengetik / pindah field
    username.addEventListener('input', validateUsername);
    password.addEventListener('input', () => {
        validatePassword();
        if (confirm.value) validateConfirm();
    });
    confirm.addEventListener('input', validateConfirm);

    // Validasi final saat submit
    form.addEventListener('submit', (e) => {
        const validUsername = validateUsername();
        const validPassword = validatePassword();
        const validConfirm = validateConfirm();

        if (!validUsername || !validPassword || !validConfirm) {
            e.preventDefault();
            const firstInvalid = form.querySelector('.field.has-error input');
            if (firstInvalid) firstInvalid.focus();
        }
    });
})();