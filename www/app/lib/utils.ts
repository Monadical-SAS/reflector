export function isProjector() {
  return process.env.NEXT_PUBLIC_PROJECTOR_MODE === "true";
}

export function isDevelopment() {
  return process.env.NEXT_PUBLIC_ENV === "development";
}
