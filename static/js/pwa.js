// PWA Installation
let deferredPrompt;
const installButton = document.createElement('button');
installButton.style.display = 'none';
installButton.textContent = 'Install App';
document.body.appendChild(installButton);

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    installButton.style.display = 'block';
});

installButton.addEventListener('click', async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
        console.log('User accepted the install prompt');
    }
    deferredPrompt = null;
});

// Offline Support
const dbName = 'travelChronicleDB';
const dbVersion = 1;

async function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(dbName, dbVersion);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('offlineLocations')) {
                db.createObjectStore('offlineLocations', { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

// Handle offline form submissions
async function handleOfflineSubmission(formData) {
    try {
        const db = await openDB();
        const location = {
            name: formData.get('name'),
            description: formData.get('description'),
            experience: formData.get('experience'),
            latitude: formData.get('latitude'),
            longitude: formData.get('longitude'),
            pictures: [],
            timestamp: new Date().toISOString()
        };

        // Handle file uploads
        const files = formData.getAll('pictures');
        for (const file of files) {
            if (file instanceof File) {
                const reader = new FileReader();
                reader.onload = async (e) => {
                    location.pictures.push(e.target.result);
                    await db.add('offlineLocations', location);
                };
                reader.readAsDataURL(file);
            }
        }

        // If no files, just save the location
        if (files.length === 0) {
            await db.add('offlineLocations', location);
        }

        // Register for background sync
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            const registration = await navigator.serviceWorker.ready;
            await registration.sync.register('syncLocations');
        }

        return { success: true, message: 'Location saved offline' };
    } catch (error) {
        console.error('Error saving offline:', error);
        return { success: false, message: 'Error saving location offline' };
    }
}

// Network status handling
window.addEventListener('online', () => {
    showMessage('You are back online!', 'success');
    // Trigger sync when back online
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
        navigator.serviceWorker.ready.then(registration => {
            registration.sync.register('syncLocations');
        });
    }
});

window.addEventListener('offline', () => {
    showMessage('You are offline. Some features may be limited.', 'error');
});

// Initialize PWA features
async function initPWA() {
    if ('serviceWorker' in navigator) {
        try {
            const registration = await navigator.serviceWorker.register('/static/sw.js');
            console.log('ServiceWorker registration successful:', registration);
        } catch (error) {
            console.error('ServiceWorker registration failed:', error);
        }
    }

    // Check if app is installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
        installButton.style.display = 'none';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initPWA); 