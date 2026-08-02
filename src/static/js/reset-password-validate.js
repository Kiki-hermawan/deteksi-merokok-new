(function () {
    const form = document.getElementById('resetPasswordForm');
    if (!form) return;

    const newPassword = document.getElementById('new_password');
    const confirmPassword = document.getElementById('confirm_password');

    function setState(input, isValid, hasValue) {
        const field = input.closest('.field');
        field.classList.toggle('has-error', hasValue && !isValid);
        field.classList.toggle('is-valid', hasValue && isValid);
    }

    function validateNewPassword() {
        const hasValue = newPassword.value.length > 0;
        const ok = newPassword.value.length >= 8;
        setState(newPassword, ok, hasValue);
        return ok;
    }

    function validateConfirmPassword() {
        const hasValue = confirmPassword.value.length > 0;
        const ok = hasValue && confirmPassword.value === newPassword.value;
        setState(confirmPassword, ok, hasValue);
        return ok;
    }

    // Validasi langsung saat mengetik
    newPassword.addEventListener('input', () => {
        validateNewPassword();
        if (confirmPassword.value) validateConfirmPassword();
    });
    confirmPassword.addEventListener('input', validateConfirmPassword);

    // Validasi final saat submit
    form.addEventListener('submit', (e) => {
        const validNewPassword = validateNewPassword();
        const validConfirmPassword = validateConfirmPassword();

        if (!validNewPassword || !validConfirmPassword) {
            e.preventDefault();
            const firstInvalid = form.querySelector('.field.has-error input');
            if (firstInvalid) firstInvalid.focus();
        }
    });
})();
