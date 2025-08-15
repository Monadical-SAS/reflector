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

/**
 * Highlights all occurrences of query words in text
 * For multi-word queries, highlights each word individually (not as a phrase)
 *
 * @param text - The text to highlight in
 * @param query - The search query (can be multiple words)
 * @returns Object with highlighted text and array of matched strings
 */
export function highlightText(text: string, query: string): HighlightResult {
  if (!query || !text) {
    return { text, matches: [] };
  }

  const matches: string[] = [];
  let highlightedText = text;

  // Split query into individual words
  const queryWords = query.trim().split(/\s+/);

  // Create a regex that matches any of the query words
  const regexPattern = queryWords.map((word) => escapeRegex(word)).join("|");

  const regex = new RegExp(`(${regexPattern})`, "gi");

  // Replace all matches with marked version and collect matches
  highlightedText = text.replace(regex, (match) => {
    matches.push(match);
    return `<mark>${match}</mark>`;
  });

  return { text: highlightedText, matches };
}

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

/**
 * React component helper: Converts highlighted text with <mark> tags to React nodes
 * This is used to render the highlighted text in React components
 */
export function renderHighlightedText(
  highlightedText: string,
): React.ReactNode {
  if (!highlightedText.includes("<mark>")) {
    return highlightedText;
  }

  const parts = highlightedText.split(/(<mark>.*?<\/mark>)/g);

  return parts.map((part, index) => {
    if (part.startsWith("<mark>")) {
      const content = part.replace(/<\/?mark>/g, "");
      return (
        <mark
          key={index}
          style={{ backgroundColor: "#fef3c7", padding: "0 2px" }}
        >
          {content}
        </mark>
      );
    }
    return part;
  });
}
