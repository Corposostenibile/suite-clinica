const AVATAR_KEYS = new Set(['avatar_path', 'avatar_url']);

export const normalizeAvatarPath = (avatarPath) => {
  if (!avatarPath) return null;

  const rawPath = String(avatarPath).trim();
  if (!rawPath) return null;

  if (/^(data:|blob:)/i.test(rawPath)) return rawPath;

  if (/^https?:\/\//i.test(rawPath) || rawPath.startsWith('//')) {
    try {
      const parsed = new URL(rawPath, window.location.origin);
      const pathname = parsed.pathname || '';
      const search = parsed.search || '';

      if (pathname.startsWith('/uploads/')) return `${pathname}${search}`;
      if (pathname.startsWith('/avatars/')) return `/uploads${pathname}${search}`;
      if (pathname.startsWith('/')) return `${pathname}${search}`;

      return `/uploads/avatars/${pathname.replace(/^\/+/, '')}${search}`;
    } catch {
      return rawPath;
    }
  }

  if (rawPath.startsWith('/uploads/')) return rawPath;
  if (rawPath.startsWith('uploads/')) return `/${rawPath}`;
  if (rawPath.startsWith('/avatars/')) return `/uploads${rawPath}`;
  if (rawPath.startsWith('avatars/')) return `/uploads/${rawPath}`;
  if (rawPath.startsWith('/')) return rawPath;

  return `/uploads/avatars/${rawPath}`;
};

export const normalizeMediaUrlsDeep = (value, seen = new WeakSet()) => {
  if (!value || typeof value !== 'object') return value;
  if (seen.has(value)) return value;
  seen.add(value);

  if (Array.isArray(value)) {
    for (const item of value) {
      normalizeMediaUrlsDeep(item, seen);
    }
    return value;
  }

  for (const [key, nestedValue] of Object.entries(value)) {
    if (AVATAR_KEYS.has(key)) {
      value[key] = normalizeAvatarPath(nestedValue);
      continue;
    }
    normalizeMediaUrlsDeep(nestedValue, seen);
  }

  return value;
};

export const attachMediaUrlNormalizationInterceptor = (axiosInstance) => {
  axiosInstance.interceptors.response.use(
    (response) => {
      if (response?.data) {
        normalizeMediaUrlsDeep(response.data);
      }
      return response;
    },
    (error) => Promise.reject(error)
  );

  return axiosInstance;
};
