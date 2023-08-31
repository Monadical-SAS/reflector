import * as Sentry from "@sentry/react";

const handleError = (
  setError: Function,
  errorString: string,
  errorObj?: any,
) => {
  setError(errorString);

  if (errorObj) {
    Sentry.captureException(errorObj);
  } else {
    Sentry.captureMessage(errorString);
  }
};

export default handleError;
