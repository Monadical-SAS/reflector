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
  backgroundColor: [number, number, number],
) => {
  let loopNumber = 0;
  let minAcceptedContrast = 3.5;
  while (true && /* Just as a safeguard */ loopNumber < 100) {
    ++loopNumber;

    if (loopNumber > 5) minAcceptedContrast -= 0.5;

    const hash = murmurhash3_32_gc(name + loopNumber);
    let red = (hash & 0xff0000) >> 16;
    let green = (hash & 0x00ff00) >> 8;
    let blue = hash & 0x0000ff;

    let contrast = getContrastRatio([red, green, blue], backgroundColor);

    if (contrast > minAcceptedContrast) return `rgb(${red}, ${green}, ${blue})`;

    // Try to invert the color to increase contrat - this works best the more away the color is from gray
    red = Math.abs(255 - red);
    green = Math.abs(255 - green);
    blue = Math.abs(255 - blue);

    contrast = getContrastRatio([red, green, blue], backgroundColor);

    if (contrast > minAcceptedContrast) return `rgb(${red}, ${green}, ${blue})`;
  }
};

export function extractDomain(url) {
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.host;
  } catch (error) {
    console.error("Invalid URL:", error.message);
    return null;
  }
}

export type NonEmptyString = string & { __brand: "NonEmptyString" };
export const parseMaybeNonEmptyString = (
  s: string,
  trim = true,
): NonEmptyString | null => {
  s = trim ? s.trim() : s;
  return s.length > 0 ? (s as NonEmptyString) : null;
};
export const parseNonEmptyString = (
  s: string,
  trim = true,
  e?: string,
): NonEmptyString =>
  assertExists(
    parseMaybeNonEmptyString(s, trim),
    "Expected non-empty string" + (e ? `: ${e}` : ""),
  );

export const assertExists = <T>(
  value: T | null | undefined,
  err?: string,
): T => {
  if (value === null || value === undefined) {
    throw new Error(`Assertion failed: ${err ?? "value is null or undefined"}`);
  }
  return value;
};

export const assertNotExists = <T>(
  value: T | null | undefined,
  err?: string,
): void => {
  if (value !== null && value !== undefined) {
    throw new Error(
      `Assertion failed: ${err ?? "value is not null or undefined"}`,
    );
  }
};

export const assertExistsAndNonEmptyString = (
  value: string | null | undefined,
  err?: string,
): NonEmptyString =>
  parseNonEmptyString(
    assertExists(value, err || "Expected non-empty string"),
    true,
    err,
  );
