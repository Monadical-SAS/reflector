function shouldShowError(error: Error | null | undefined) {
  if (error?.name == "ResponseError" && error["response"].status == 404)
    return false;
  if (error?.name == "FetchError") return false;
  return true;
}

export { shouldShowError };
