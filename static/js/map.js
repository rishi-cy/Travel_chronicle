document.getElementById("search-place-btn").addEventListener("click", function () {
    var placeName = document.getElementById("place-name-input").value.trim();

    if (!placeName) {
        alert("Please enter a place name.");
        return;
    }

    // Use Nominatim API for geocoding
    fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(placeName)}&format=json&limit=1`)
        .then(response => response.json())
        .then(data => {
            if (data.length === 0) {
                alert("Place not found. Try again.");
                return;
            }

            // Extract coordinates from the API response
            var latitude = parseFloat(data[0].lat);
            var longitude = parseFloat(data[0].lon);

            // Center the map on the fetched location
            map.setView([latitude, longitude], 13);

            // Create a new marker
            var marker = L.marker([latitude, longitude]).addTo(map);

            // Attach a popup form to the marker
            var popupContent = `
                <form action="/upload_location" method="POST" enctype="multipart/form-data">
                    <input type="text" name="name" placeholder="Place Name" value="${placeName}" required><br>
                    <textarea name="description" placeholder="Description" required></textarea><br>
                    <textarea name="experience" placeholder="Your Experience" required></textarea><br>
                    <input type="file" name="pictures" multiple><br>
                    <input type="hidden" name="latitude" value="${latitude}">
                    <input type="hidden" name="longitude" value="${longitude}">
                    <button type="submit">Upload Place</button>
                </form>
            `;
            marker.bindPopup(popupContent).openPopup();
        })
        .catch(error => {
            console.error("Error fetching geocoding data:", error);
            alert("An error occurred while fetching the location. Please try again.");
        });
});
