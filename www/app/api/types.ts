// in case the server side type generation is broken (e.g. non openai compatible) we need to apply manual fixes

import { SearchResult as SearchResultGen, SourceKind } from "./types.gen";
import { assertExists } from "../lib/utils";

export type SearchResult =
  | (SearchResultGen & {
      source_kind: Exclude<SourceKind, "room">;
    })
  | (SearchResultGen & {
      source_kind: "room";
      room_id: string;
    });

export const parseSearchResult = (
  searchResult: SearchResultGen,
): SearchResult => {
  if (searchResult.source_kind === "room") {
    const roomId = assertExists(searchResult.room_id);
    return searchResult as SearchResult & { room_id: typeof roomId };
  }
  // TODO should figure out itself without cast; probably strict: false problem.
  return searchResult as SearchResult & {
    source_kind: Exclude<SourceKind, "room">;
  };
};
