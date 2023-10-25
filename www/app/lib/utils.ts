export function isDevelopment() {
  return process.env.NEXT_PUBLIC_ENV === "development";
}

// Function to calculate WCAG contrast ratio
export const getContrastRatio = (
  foreground: [number, number, number],
  background: [number, number, number],
) => {
  const [r1, g1, b1] = foreground;
  const [r2, g2, b2] = background;

  const lum1 =
    0.2126 * Math.pow(r1 / 255, 2.2) +
    0.7152 * Math.pow(g1 / 255, 2.2) +
    0.0722 * Math.pow(b1 / 255, 2.2);
  const lum2 =
    0.2126 * Math.pow(r2 / 255, 2.2) +
    0.7152 * Math.pow(g2 / 255, 2.2) +
    0.0722 * Math.pow(b2 / 255, 2.2);

  return (Math.max(lum1, lum2) + 0.05) / (Math.min(lum1, lum2) + 0.05);
};

// Function to hash string into 32-bit integer
// 🔴 DO NOT USE FOR CRYPTOGRAPHY PURPOSES 🔴

export function murmurhash3_32_gc(key: string, seed: number = 0) {
  let remainder, bytes, h1, h1b, c1, c2, k1, i;

  remainder = key.length & 3; // key.length % 4
  bytes = key.length - remainder;
  h1 = seed;
  c1 = 0xcc9e2d51;
  c2 = 0x1b873593;
  i = 0;

  while (i < bytes) {
    k1 =
      (key.charCodeAt(i) & 0xff) |
      ((key.charCodeAt(++i) & 0xff) << 8) |
      ((key.charCodeAt(++i) & 0xff) << 16) |
      ((key.charCodeAt(++i) & 0xff) << 24);

    ++i;

    k1 =
      ((k1 & 0xffff) * c1 + ((((k1 >>> 16) * c1) & 0xffff) << 16)) & 0xffffffff;
    k1 = (k1 << 15) | (k1 >>> 17);
    k1 =
      ((k1 & 0xffff) * c2 + ((((k1 >>> 16) * c2) & 0xffff) << 16)) & 0xffffffff;

    h1 ^= k1;
    h1 = (h1 << 13) | (h1 >>> 19);
    h1b =
      ((h1 & 0xffff) * 5 + ((((h1 >>> 16) * 5) & 0xffff) << 16)) & 0xffffffff;
    h1 = (h1b & 0xffff) + 0x6b64 + ((((h1b >>> 16) + 0xe654) & 0xffff) << 16);
  }

  k1 = 0;

  switch (remainder) {
    case 3:
      k1 ^= (key.charCodeAt(i + 2) & 0xff) << 16;
    case 2:
      k1 ^= (key.charCodeAt(i + 1) & 0xff) << 8;
    case 1:
      k1 ^= key.charCodeAt(i) & 0xff;

      k1 =
        ((k1 & 0xffff) * c1 + ((((k1 >>> 16) * c1) & 0xffff) << 16)) &
        0xffffffff;
      k1 = (k1 << 15) | (k1 >>> 17);
      k1 =
        ((k1 & 0xffff) * c2 + ((((k1 >>> 16) * c2) & 0xffff) << 16)) &
        0xffffffff;
      h1 ^= k1;
  }

  h1 ^= key.length;

  h1 ^= h1 >>> 16;
  h1 =
    ((h1 & 0xffff) * 0x85ebca6b +
      ((((h1 >>> 16) * 0x85ebca6b) & 0xffff) << 16)) &
    0xffffffff;
  h1 ^= h1 >>> 13;
  h1 =
    ((h1 & 0xffff) * 0xc2b2ae35 +
      ((((h1 >>> 16) * 0xc2b2ae35) & 0xffff) << 16)) &
    0xffffffff;
  h1 ^= h1 >>> 16;

  return h1 >>> 0;
}

// Generates a color that is guaranteed to have high contrast with the given background color (optional)

export const generateHighContrastColor = (
  name: string,
  backgroundColor: [number, number, number] | null = null,
) => {
  const hash = murmurhash3_32_gc(name);
  let red = (hash & 0xff0000) >> 16;
  let green = (hash & 0x00ff00) >> 8;
  let blue = hash & 0x0000ff;

  const getCssColor = (red: number, green: number, blue: number) =>
    `rgb(${red}, ${green}, ${blue})`;

  if (!backgroundColor) return getCssColor(red, green, blue);

  const contrast = getContrastRatio([red, green, blue], backgroundColor);

  // Adjust the color to achieve better contrast if necessary (WCAG recommends at least 4.5:1 for text)
  if (contrast < 4.5) {
    red = Math.abs(255 - red);
    green = Math.abs(255 - green);
    blue = Math.abs(255 - blue);
  }

  return getCssColor(red, green, blue);
};

export function featPrivacy() {
  return process.env.NEXT_PUBLIC_FEAT_PRIVACY === "1";
}

export function featBrowse() {
  return process.env.NEXT_PUBLIC_FEAT_BROWSE === "1";
}

export function featRequireLogin() {
  return process.env.NEXT_PUBLIC_FEAT_LOGIN_REQUIRED === "1";
}
