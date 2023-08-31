import * as Sentry from "@sentry/react";
import { Dispatch, SetStateAction } from "react";

const handleError = (
  setError: Dispatch<SetStateAction<String>>,
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
