export type NonEmptyArray<T> = [T, ...T[]];
export const isNonEmptyArray = <T>(arr: T[]): arr is NonEmptyArray<T> =>
  arr.length > 0;
export const assertNonEmptyArray = <T>(
  arr: T[],
  err?: string,
): NonEmptyArray<T> => {
  if (isNonEmptyArray(arr)) {
    return arr;
  }
  throw new Error(err ?? "Expected non-empty array");
};
