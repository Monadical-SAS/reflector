export function isDevelopment() {
  return process.env.NEXT_PUBLIC_ENV === "development";
}

export function featPrivacy() {
  return process.env.NEXT_PUBLIC_FEAT_PRIVACY === "1";
}

export function featBrowse() {
  return process.env.NEXT_PUBLIC_FEAT_BROWSE === "1";
}

export function featRequireLogin() {
  return process.env.NEXT_PUBLIC_FEAT_LOGIN_REQUIRED === "1";
}
