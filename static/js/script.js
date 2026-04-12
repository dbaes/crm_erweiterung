document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    });
});
function changeRole(userId, newRole) {
    if (!newRole) {
        console.error("Keine Rolle ausgewählt!");
        return;
    }

    console.log("Sende:", JSON.stringify({ role: newRole }));

    fetch(`/api/users/${userId}/role`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ role: newRole })
    })
    .then(async response => {
        const result = await response.json();
        if (response.ok) {
            location.reload();
        } else {
            console.error("Server meldet Fehler:", result);
            alert("Fehler: " + result.error);
        }
    })
    .catch(err => console.error("Netzwerkfehler:", err));
}

function deleteUser(userId, username) {
    if (confirm(`Bist du sicher, dass du den Benutzer "${username}" permanent löschen möchtest?`)) {
        fetch(`/api/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.ok) {
                location.reload();
            } else {
                response.json().then(data => alert("Fehler: " + data.error));
            }
        })
        .catch(err => console.error("Netzwerkfehler:", err));
    }
}