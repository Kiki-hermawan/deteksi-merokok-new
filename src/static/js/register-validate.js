(function () {
    const form = document.getElementById('registerForm');
    if (!form) return;

    const username = document.getElementById('username');
    const email = document.getElementById('email');
    const phone = document.getElementById('phone');
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

    function validateEmail() {
        const hasValue = email.value.length > 0;
        const ok = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value);
        setState(email, ok, hasValue);
        return ok;
    }

    function validatePhone() {
        const hasValue = phone.value.length > 0;
        const ok = /^(\+62|62|0)8[1-9][0-9]{6,10}$/.test(phone.value);
        setState(phone, ok, hasValue);
        return ok;
    }

    // Kata sandi wajib: minimal 8 karakter + huruf besar + huruf kecil +
    // angka + simbol. Sama persis dengan aturan di backend (auth.py).
    function isStrongPassword(value) {
        return (
            value.length >= 8 &&
            /[a-z]/.test(value) &&
            /[A-Z]/.test(value) &&
            /\d/.test(value) &&
            /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(value)
        );
    }

    function validatePassword() {
        const hasValue = password.value.length > 0;
        const ok = isStrongPassword(password.value);
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
    email.addEventListener('input', validateEmail);
    phone.addEventListener('input', validatePhone);
    password.addEventListener('input', () => {
        validatePassword();
        if (confirm.value) validateConfirm();
    });
    confirm.addEventListener('input', validateConfirm);

    // Validasi final saat submit
    form.addEventListener('submit', (e) => {
        const validUsername = validateUsername();
        const validEmail = validateEmail();
        const validPhone = validatePhone();
        const validPassword = validatePassword();
        const validConfirm = validateConfirm();

        if (!validUsername || !validEmail || !validPhone || !validPassword || !validConfirm) {
            e.preventDefault();
            const firstInvalid = form.querySelector('.field.has-error input');
            if (firstInvalid) firstInvalid.focus();
        }
    });
})();