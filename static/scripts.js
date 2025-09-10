let map, marker;

function initializeMap(lat, lng) {
    map = L.map('map').setView([lat, lng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    marker = L.marker([lat, lng]).addTo(map);
}

function updateBusLocation(busId) {
    fetch(`/update_location/${busId}`)
        .then(response => response.json())
        .then(data => {
            marker.setLatLng([data.latitude, data.longitude]);
            map.setView([data.latitude, data.longitude], 13);
        });
    setTimeout(() => updateBusLocation(busId), 5000); // Update every 5 seconds
}