// consent.js
function sendConsentScreenshot(data, screenshot, callback) {
    const consentData = {
        fio: data.fio,
        kadastr: data.kadastr,
        phone: data.phone,
        email: data.email,
        operator: "Ларину Максиму Ивановичу",
        operator_email: "admin@tylarmacclane.site",
        consent: data.consent === "on" || data.consent === true,
        consent_datetime: new Date().toISOString(),
        screenshot
    };
    fetch('/survey/consent', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(consentData)
    }).then(res => {
        // После отправки на /survey/consent, отправляем на /survey/base
        const session_id = localStorage.getItem('session_id');
        if (session_id) {
            fetch('/survey/base', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id,
                    answers: [], // ответы не обновляем, только consent и screenshot
                    consent: true,
                    screenshot
                })
            });
        }
        if (callback) callback(res);
    });
} 