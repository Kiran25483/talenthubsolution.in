const registrationForm = document.querySelector("[data-password-confirmation]");

if (registrationForm) {
    const password = registrationForm.querySelector("#password");
    const confirmation = registrationForm.querySelector("#confirm_password");

    const validatePasswords = () => {
        confirmation.setCustomValidity(
            confirmation.value && confirmation.value !== password.value
                ? "Passwords do not match."
                : ""
        );
    };

    password.addEventListener("input", validatePasswords);
    confirmation.addEventListener("input", validatePasswords);
}

window.setTimeout(() => {
    document.querySelectorAll(".alert-success").forEach((alert) => {
        alert.style.transition = "opacity 0.5s";
        alert.style.opacity = "0";

        window.setTimeout(() => alert.remove(), 500);
    });
}, 7000);