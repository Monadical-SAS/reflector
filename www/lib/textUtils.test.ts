import { parseHighlightedText } from './textUtils';

describe('textUtils', () => {
  describe('parseHighlightedText', () => {
    it('should parse simple highlighted text', () => {
      const result = parseHighlightedText('Hello **world** test');
      expect(result).toEqual([
        { bold: false, text: 'Hello ' },
        { bold: true, text: 'world' },
        { bold: false, text: ' test' }
      ]);
    });

    it('should handle multiple highlights', () => {
      const result = parseHighlightedText('**First** and **second** highlights');
      expect(result).toEqual([
        { bold: true, text: 'First' },
        { bold: false, text: ' and ' },
        { bold: true, text: 'second' },
        { bold: false, text: ' highlights' }
      ]);
    });

    it('should handle text without highlights', () => {
      const result = parseHighlightedText('No highlights here');
      expect(result).toEqual([
        { bold: false, text: 'No highlights here' }
      ]);
    });

    it('should handle empty text', () => {
      const result = parseHighlightedText('');
      expect(result).toEqual([]);
    });

    it('should handle text starting with highlight', () => {
      const result = parseHighlightedText('**Bold** start');
      expect(result).toEqual([
        { bold: true, text: 'Bold' },
        { bold: false, text: ' start' }
      ]);
    });

    it('should handle text ending with highlight', () => {
      const result = parseHighlightedText('End with **bold**');
      expect(result).toEqual([
        { bold: false, text: 'End with ' },
        { bold: true, text: 'bold' }
      ]);
    });
  });
});