/**
 * Text highlighting and text fragment generation utilities
 * Used for search result highlighting and deep linking with Chrome Text Fragments
 */

import React from "react";

export interface HighlightResult {
  text: string;
  matches: string[];
}

/**
 * Escapes special regex characters in a string
 */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export const highlightMatches = (
  text: string,
  query: string,
): { match: string; index: number }[] => {
  if (!query || !text) {
    return [];
  }

  const queryWords = query.trim().split(/\s+/);

  const regex = new RegExp(
    `(${queryWords.map((word) => escapeRegex(word)).join("|")})`,
    "gi",
  );

  return Array.from(text.matchAll(regex)).map((result) => ({
    match: result[0],
    index: result.index!,
  }));
};

export function findFirstHighlight(text: string, query: string): string | null {
  const matches = highlightMatches(text, query);
  if (matches.length === 0) {
    return null;
  }
  return matches[0].match;
}

export function generateTextFragment(
  text: string,
  query: string,
): {
  k: ":~:text";
  v: string;
} | null {
  const firstMatch = findFirstHighlight(text, query);
  if (!firstMatch) return null;
  return {
    k: ":~:text",
    v: firstMatch,
  };
}
