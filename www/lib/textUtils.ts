import React from 'react';

/**
 * Render text with ** markers as bold HTML elements
 * 
 * @param text Text containing ** markers for bold sections
 * @returns React elements with bold sections
 */
export function renderHighlightedText(text: string): React.ReactNode {
  // Split on ** markers, capturing the content between them
  const parts = text.split(/\*\*(.*?)\*\*/g);
  
  return parts.map((part, i) => 
    // Odd indices are the captured groups (text between **)
    i % 2 === 1 ? <strong key={i}>{part}</strong> : part
  );
}

/**
 * Parse highlighted text for testing without React
 * 
 * @param text Text containing ** markers
 * @returns Array of text segments with bold flags
 */
export function parseHighlightedText(text: string): Array<{bold: boolean, text: string}> {
  const parts = text.split(/\*\*(.*?)\*\*/g);
  
  return parts.map((part, i) => ({
    bold: i % 2 === 1,
    text: part
  })).filter(p => p.text); // Remove empty strings
}