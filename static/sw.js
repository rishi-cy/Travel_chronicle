const CACHE_NAME = 'travel-chronicle-v1';
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    'https://unpkg.com/leaflet/dist/leaflet.css',
    'https://unpkg.com/leaflet/dist/leaflet.js',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

// Install Service Worker
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

// Activate Service Worker
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Fetch Event Strategy (Cache First, then Network)
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached version if found
                if (response) {
                    return response;
                }

                // Clone the request because it can only be used once
                const fetchRequest = event.request.clone();

                // Make network request and cache the response
                return fetch(fetchRequest).then(response => {
                    // Check if we received a valid response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }

                    // Clone the response because it can only be used once
                    const responseToCache = response.clone();

                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });

                    return response;
                });
            })
    );
});

// Handle offline functionality
self.addEventListener('sync', event => {
    if (event.tag === 'syncLocations') {
        event.waitUntil(syncLocations());
    }
});

// Background sync for offline data
async function syncLocations() {
    try {
        const db = await openDB();
        const offlineLocations = await db.getAll('offlineLocations');
        
        for (const location of offlineLocations) {
            try {
                const response = await fetch('/upload_location', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(location)
                });
                
                if (response.ok) {
                    await db.delete('offlineLocations', location.id);
                }
            } catch (error) {
                console.error('Error syncing location:', error);
            }
        }
    } catch (error) {
        console.error('Error in sync:', error);
    }
} 