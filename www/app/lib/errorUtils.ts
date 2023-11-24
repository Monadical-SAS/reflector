function shouldShowError(error: Error | null | undefined) {
  if (
    error?.name == "ResponseError" &&
    (error["response"].status == 404 || error["response"].status == 403)
  )
    return false;
  if (error?.name == "FetchError") return false;
  return true;
}

export { shouldShowError };
