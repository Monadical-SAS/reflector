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

export const highlightText = (text: string, query: string): HighlightResult => {
  const matches = highlightMatches(text, query);

  let highlightedText = text;
  let offset = 0;

  const sortedMatches = [...matches].sort((a, b) => a.index - b.index);

  for (const match of sortedMatches) {
    const startTag = "<mark>";
    const endTag = "</mark>";
    const adjustedIndex = match.index + offset;

    highlightedText =
      highlightedText.slice(0, adjustedIndex) +
      startTag +
      match.match +
      endTag +
      highlightedText.slice(adjustedIndex + match.match.length);

    offset += startTag.length + endTag.length;
  }

  return {
    text: highlightedText,
    matches: matches.map((m) => m.match),
  };
};

/**
 * Finds the first highlighted match in the text
 * Returns the longest consecutive sequence of query words starting from the first match
 *
 * @param text - The text to search in
 * @param query - The search query (can be multiple words)
 * @returns The first match or consecutive matches, or null if no match
 */
export function findFirstHighlight(text: string, query: string): string | null {
  if (!query || !text) {
    return null;
  }

  const queryWords = query.trim().split(/\s+/);
  const textLower = text.toLowerCase();

  // First, check if the exact phrase exists
  const exactPhraseLower = query.toLowerCase();
  const exactPhraseIndex = textLower.indexOf(exactPhraseLower);

  if (exactPhraseIndex !== -1) {
    // Extract the actual case-sensitive match
    return text.substr(exactPhraseIndex, query.length);
  }

  // Find the first occurrence of any query word
  let firstMatchIndex = -1;
  let firstMatchWord = "";

  for (const word of queryWords) {
    const wordLower = word.toLowerCase();
    const index = textLower.indexOf(wordLower);

    if (index !== -1 && (firstMatchIndex === -1 || index < firstMatchIndex)) {
      firstMatchIndex = index;
      firstMatchWord = word;
    }
  }

  if (firstMatchIndex === -1) {
    return null;
  }

  // Extract the actual matched word with original case
  const actualMatch = text.substr(firstMatchIndex, firstMatchWord.length);

  // Check if subsequent query words follow consecutively
  let consecutiveMatch = actualMatch;
  let currentIndex = firstMatchIndex + firstMatchWord.length;

  // Get the index of the first matched word in the query
  const firstWordIndex = queryWords.findIndex(
    (w) => w.toLowerCase() === firstMatchWord.toLowerCase(),
  );

  // Check for consecutive words following the first match
  for (let i = firstWordIndex + 1; i < queryWords.length; i++) {
    const nextWord = queryWords[i];
    const nextWordLower = nextWord.toLowerCase();

    // Skip whitespace
    while (currentIndex < text.length && /\s/.test(text[currentIndex])) {
      currentIndex++;
    }

    // Check if the next word matches at the current position
    const remainingText = text.substr(currentIndex).toLowerCase();
    if (remainingText.startsWith(nextWordLower)) {
      // Add the whitespace and the word to our consecutive match
      const whitespaceLength =
        currentIndex - (firstMatchIndex + consecutiveMatch.length);
      consecutiveMatch += text.substr(
        firstMatchIndex + consecutiveMatch.length,
        whitespaceLength + nextWord.length,
      );
      currentIndex += nextWord.length;
    } else {
      // No more consecutive matches
      break;
    }
  }

  return consecutiveMatch;
}

/**
 * Generates a Chrome Text Fragment URL hash for deep linking to specific text
 * Uses the first highlight from the search query
 *
 * @param text - The text to search in (can be a snippet)
 * @param query - The search query
 * @returns URL fragment like "#:~:text=..." or empty string if no match
 */
export function generateTextFragment(text: string, query: string): string {
  const firstMatch = findFirstHighlight(text, query);

  if (!firstMatch) {
    return "";
  }

  // URL encode the match for use in the fragment
  // Note: encodeURIComponent encodes spaces as %20, which is what we want
  const encoded = encodeURIComponent(firstMatch);

  return `#:~:text=${encoded}`;
}
