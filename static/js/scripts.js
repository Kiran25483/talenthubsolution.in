console.log("TalentHub Solutions website loaded.");


// Automatically hide alerts

setTimeout(function () {

    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(function (alert) {

        alert.style.transition = "opacity 0.5s";

        alert.style.opacity = "0";

        setTimeout(function () {
            alert.remove();
        }, 500);

    });

}, 4000);