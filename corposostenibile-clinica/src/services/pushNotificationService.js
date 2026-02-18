import api from './api';

const urlBase64ToUint8Array = (base64String) => {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
};

const canUsePush = () => (
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window
);

const getServiceWorkerRegistration = async () => {
  const registration = await navigator.serviceWorker.getRegistration();
  if (registration) return registration;
  return navigator.serviceWorker.ready;
};

const upsertSubscription = async (subscription) => {
  await api.post('/push/subscriptions', { subscription });
};

const ensureSubscription = async ({ allowPrompt = false } = {}) => {
  if (!canUsePush()) return;

  try {
    const keyRes = await api.get('/push/public-key');
    const { enabled, publicKey } = keyRes.data || {};
    if (!enabled || !publicKey) return;

    const registration = await getServiceWorkerRegistration();
    const existing = await registration.pushManager.getSubscription();

    if (existing) {
      await upsertSubscription(existing.toJSON());
      return { subscribed: true };
    }

    if (Notification.permission === 'default' && allowPrompt) {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') return { subscribed: false };
    } else if (Notification.permission !== 'granted') {
      return { subscribed: false };
    }

    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });

    await upsertSubscription(subscription.toJSON());
    return { subscribed: true };
  } catch (error) {
    console.warn('Push subscription setup failed:', error);
    return { subscribed: false, error };
  }
};

const getPushStatus = async () => {
  if (!canUsePush()) {
    return {
      supported: false,
      backendEnabled: false,
      permission: 'default',
      subscribed: false,
      enabled: false,
    };
  }

  try {
    const keyRes = await api.get('/push/public-key');
    const { enabled } = keyRes.data || {};
    const registration = await getServiceWorkerRegistration();
    const existing = registration ? await registration.pushManager.getSubscription() : null;
    const permission = Notification.permission;
    const subscribed = Boolean(existing);
    const backendEnabled = Boolean(enabled);

    return {
      supported: true,
      backendEnabled,
      permission,
      subscribed,
      enabled: backendEnabled && permission === 'granted' && subscribed,
    };
  } catch (error) {
    console.warn('Push status check failed:', error);
    return {
      supported: true,
      backendEnabled: false,
      permission: Notification.permission,
      subscribed: false,
      enabled: false,
      error,
    };
  }
};

const disablePushNotifications = async () => {
  if (!canUsePush()) return { unsubscribed: false };

  try {
    const registration = await getServiceWorkerRegistration();
    const existing = registration ? await registration.pushManager.getSubscription() : null;
    const endpoint = existing?.endpoint;

    if (existing) {
      await existing.unsubscribe();
    }

    if (endpoint) {
      await api.delete('/push/subscriptions', { data: { endpoint } });
    } else {
      await api.delete('/push/subscriptions');
    }

    return { unsubscribed: true };
  } catch (error) {
    console.warn('Push unsubscribe failed:', error);
    return { unsubscribed: false, error };
  }
};

const getNotifications = async ({ unreadOnly = true, limit = 6 } = {}) => {
  try {
    const response = await api.get('/push/notifications', {
      params: {
        unread_only: unreadOnly ? 1 : 0,
        limit,
      },
    });
    return {
      items: response.data?.items || [],
      unreadCount: Number(response.data?.unreadCount || 0),
    };
  } catch (error) {
    console.warn('Notifications fetch failed:', error);
    return { items: [], unreadCount: 0, error };
  }
};

const markNotificationAsRead = async (notificationId) => {
  try {
    const response = await api.post(`/push/notifications/${notificationId}/read`);
    return {
      ok: Boolean(response.data?.ok),
      unreadCount: Number(response.data?.unreadCount || 0),
      notification: response.data?.notification || null,
    };
  } catch (error) {
    console.warn('Mark notification read failed:', error);
    return { ok: false, unreadCount: null, notification: null, error };
  }
};

export default {
  initPushNotifications: () => ensureSubscription({ allowPrompt: false }),
  enablePushNotifications: () => ensureSubscription({ allowPrompt: true }),
  disablePushNotifications,
  getPushStatus,
  getNotifications,
  markNotificationAsRead,
};
