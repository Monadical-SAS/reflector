import { components } from "../reflector-api";
import { isArray } from "remeda";

export type ApiError = {
  detail?: components["schemas"]["ValidationError"][];
} | null;

// errors as declared on api types is not != as they in reality e.g. detail may be a string
export const printApiError = (error: ApiError) => {
  if (!error || !error.detail) {
    return null;
  }
  const detail = error.detail as unknown;
  if (isArray(error.detail)) {
    return error.detail.map((e) => e.msg).join(", ");
  }
  if (typeof detail === "string") {
    if (detail.length > 0) {
      return detail;
    }
    console.error("Error detail is empty");
    return null;
  }
  console.error("Error detail is not a string or array");
  return null;
};
