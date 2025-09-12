import { isNonEmptyArray, NonEmptyArray } from "./array";

export function shouldShowError(error: Error | null | undefined) {
  if (
    error?.name == "ResponseError" &&
    (error["response"].status == 404 || error["response"].status == 403)
  )
    return false;
  if (error?.name == "FetchError") return false;
  return true;
}

const defaultMergeErrors = (ex: NonEmptyArray<unknown>): unknown => {
  try {
    return new Error(
      ex
        .map((e) =>
          e ? (e.toString ? e.toString() : JSON.stringify(e)) : `${e}`,
        )
        .join("\n"),
    );
  } catch (e) {
    console.error("Error merging errors:", e);
    return ex[0];
  }
};

type ReturnTypes<T extends readonly (() => any)[]> = {
  [K in keyof T]: T[K] extends () => infer R ? R : never;
};

// sequence semantic for "throws"
// calls functions passed and collects its thrown values
export function sequenceThrows<Fns extends readonly (() => any)[]>(
  ...fs: Fns
): ReturnTypes<Fns> {
  const results: unknown[] = [];
  const errors: unknown[] = [];

  for (const f of fs) {
    try {
      results.push(f());
    } catch (e) {
      errors.push(e);
    }
  }
  if (errors.length) throw defaultMergeErrors(errors as NonEmptyArray<unknown>);
  return results as ReturnTypes<Fns>;
}
