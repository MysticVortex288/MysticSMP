// Haupt-JavaScript-Datei für das Dashboard

// Bootstrap-Tooltips aktivieren
document.addEventListener('DOMContentLoaded', function() {
    // Tooltips initialisieren
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Alerts automatisch ausblenden nach 5 Sekunden
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-important)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Farb-Picker Previews aktualisieren
    var colorInputs = document.querySelectorAll('input[type="color"]');
    colorInputs.forEach(function(input) {
        // Initial-Preview setzen
        if (input.dataset.preview) {
            var preview = document.querySelector(input.dataset.preview);
            if (preview) {
                preview.style.backgroundColor = input.value;
            }
        }
        
        // Event-Listener für Änderungen
        input.addEventListener('input', function() {
            if (this.dataset.preview) {
                var preview = document.querySelector(this.dataset.preview);
                if (preview) {
                    preview.style.backgroundColor = this.value;
                }
            }
        });
    });
});

// Funktion zum Kopieren von Text in die Zwischenablage
function copyToClipboard(text) {
    var textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand("copy");
    document.body.removeChild(textArea);
    
    // Feedback anzeigen
    var toast = new bootstrap.Toast(document.getElementById('copyToast'));
    toast.show();
}

// Funktion zum Anzeigen von Bestätigungs-Dialogen
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Funktion zum Aktualisieren der Vorschau für Willkommensnachrichten
function updateWelcomePreview() {
    var welcomeText = document.getElementById('welcome_text').value;
    var textColor = document.getElementById('text_color').value;
    var fontSize = document.getElementById('font_size').value;
    
    var previewText = document.getElementById('welcome_preview_text');
    if (previewText) {
        previewText.innerText = welcomeText;
        previewText.style.color = textColor;
        previewText.style.fontSize = fontSize + 'px';
    }
}