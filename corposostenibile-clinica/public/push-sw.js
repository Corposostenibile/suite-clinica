self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (_err) {
    data = { body: event.data ? event.data.text() : 'Nuova notifica' };
  }

  const title = data.title || 'Corposostenibile Suite';
  const options = {
    body: data.body || 'Hai una nuova notifica',
    icon: data.icon || '/suitemind.png',
    badge: data.badge || '/suitemind.png',
    tag: data.tag || 'general-notification',
    data: {
      url: data.url || '/task',
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || '/task';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(targetUrl) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
      return undefined;
    }),
  );
});
