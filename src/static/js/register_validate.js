(function () {
    const form = document.getElementById('registerForm');
    if (!form) return;

    const username = document.getElementById('username');
    const password = document.getElementById('password');
    const confirm = document.getElementById('password_confirm');

    function setState(input, isValid, hasValue) {
        const field = input.closest('.field');
        field.classList.toggle('has-error', hasValue && !isValid);
        field.classList.toggle('is-valid', hasValue && isValid);
    }

    function validateUsername() {
        const hasValue = username.value.length > 0;
        const ok = /^[A-Za-z0-9_]{4,}$/.test(username.value);
        setState(username, ok, hasValue);
        return ok;
    }

    function validatePassword() {
        const hasValue = password.value.length > 0;
        const ok = password.value.length >= 8;
        setState(password, ok, hasValue);
        return ok;
    }

    function validateConfirm() {
        const hasValue = confirm.value.length > 0;
        const ok = hasValue && confirm.value === password.value;
        setState(confirm, ok, hasValue);
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