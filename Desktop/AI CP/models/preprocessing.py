"""
Layer 1: Text Preprocessing
Handles obfuscation, normalization, and text cleaning
"""

import re
import unicodedata

class TextPreprocessor:
    """Layer 1 - Preprocessing"""
    
    def __init__(self):
        # Leetspeak mapping
        self.leetspeak_map = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a',
            '5': 's', '7': 't', '8': 'b', '9': 'g',
            '@': 'a', '$': 's', '!': 'i'
        }
        
        # Homoglyph confusables (basic set)
        self.homoglyphs = {
            'а': 'a',  # Cyrillic a
            'е': 'e',  # Cyrillic e
            'о': 'o',  # Cyrillic o
            'р': 'p',  # Cyrillic р
            'с': 'c',  # Cyrillic c
            'у': 'y',  # Cyrillic y
            'х': 'x',  # Cyrillic x
        }
    
    def remove_zero_width_chars(self, text):
        """Remove zero-width and invisible characters"""
        # Zero-width characters
        zero_width = [
            '\u200B',  # Zero width space
            '\u200C',  # Zero width non-joiner
            '\u200D',  # Zero width joiner
            '\uFEFF',  # Zero width no-break space
            '\u00AD',  # Soft hyphen
        ]
        
        for char in zero_width:
            text = text.replace(char, '')
        
        return text
    
    def normalize_homoglyphs(self, text):
        """Replace lookalike characters with Latin equivalents"""
        for homoglyph, latin in self.homoglyphs.items():
            text = text.replace(homoglyph, latin)
        
        # Unicode normalization
        text = unicodedata.normalize('NFKD', text)
        
        return text
    
    def decode_leetspeak(self, text):
        """Convert leetspeak to normal text (selective)"""
        # Only convert in mixed alphanumeric contexts
        words = text.split()
        decoded_words = []
        
        for word in words:
            # Check if word has both letters and numbers
            has_letters = any(c.isalpha() for c in word)
            has_numbers = any(c.isdigit() for c in word)
            
            if has_letters and has_numbers:
                # Apply leetspeak conversion
                decoded = ''
                for char in word:
                    if char in self.leetspeak_map:
                        decoded += self.leetspeak_map[char]
                    else:
                        decoded += char
                decoded_words.append(decoded)
            else:
                decoded_words.append(word)
        
        return ' '.join(decoded_words)
    
    def normalize_whitespace(self, text):
        """Normalize spacing"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def preprocess(self, text, keep_original=True):
        """
        Complete preprocessing pipeline
        
        Args:
            text: Input text
            keep_original: If True, return both original and cleaned
        
        Returns:
            Cleaned text or tuple (original, cleaned)
        """
        if not isinstance(text, str):
            text = str(text)
        
        original = text
        
        # Apply all preprocessing steps
        text = self.remove_zero_width_chars(text)
        text = self.normalize_homoglyphs(text)
        text = self.decode_leetspeak(text)
        text = self.normalize_whitespace(text)
        
        if keep_original:
            return original, text
        return text

# Test
if __name__ == "__main__":
    preprocessor = TextPreprocessor()
    
    test_cases = [
        "C0ngr4tul4ti0ns! Y0u w0n",
        "Your\u200Baccount\u200Bis\u200Bblocked",
        "Pay­ment pen­ding",  # with soft hyphens
        "PаyTM account",  # Cyrillic 'а'
    ]
    
    print("Testing Preprocessor:\n")
    for text in test_cases:
        original, cleaned = preprocessor.preprocess(text)
        print(f"Original: {repr(original)}")
        print(f"Cleaned:  {repr(cleaned)}")
        print()
