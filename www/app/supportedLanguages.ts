import Script from "next/script";

// type Script = 'Latn' | 'Ethi' | 'Arab' | 'Beng' | 'Cyrl' | 'Taml' | 'Hant' | 'Hans' | 'Grek' | 'Gujr' | 'Hebr'| 'Deva'| 'Armn' | 'Jpan' | 'Knda' | 'Geor';
type LanguageOption = {
  value: string | undefined;
  name: string;
  script?: string;
};

const supportedLanguages: LanguageOption[] = [
  {
    value: "af",
    name: "Afrikaans",
    script: "Latn",
  },
  {
    value: "am",
    name: "Amharic",
    script: "Ethi",
  },
  {
    value: "ar",
    name: "Modern Standard Arabic",
    script: "Arab",
  },
  {
    value: "ary",
    name: "Moroccan Arabic",
    script: "Arab",
  },
  {
    value: "arz",
    name: "Egyptian Arabic",
    script: "Arab",
  },
  {
    value: "as",
    name: "Assamese",
    script: "Beng",
  },
  {
    value: "az",
    name: "North Azerbaijani",
    script: "Latn",
  },
  {
    value: "be",
    name: "Belarusian",
    script: "Cyrl",
  },
  {
    value: "bn",
    name: "Bengali",
    script: "Beng",
  },
  {
    value: "bs",
    name: "Bosnian",
    script: "Latn",
  },
  {
    value: "bg",
    name: "Bulgarian",
    script: "Cyrl",
  },
  {
    value: "ca",
    name: "Catalan",
    script: "Latn",
  },
  {
    value: "ceb",
    name: "Cebuano",
    script: "Latn",
  },
  {
    value: "cs",
    name: "Czech",
    script: "Latn",
  },
  {
    value: "ku",
    name: "Central Kurdish",
    script: "Arab",
  },
  {
    value: "cmn",
    name: "Mandarin Chinese",
    script: "Hans",
  },
  {
    value: "cy",
    name: "Welsh",
    script: "Latn",
  },
  {
    value: "da",
    name: "Danish",
    script: "Latn",
  },
  {
    value: "de",
    name: "German",
    script: "Latn",
  },
  {
    value: "el",
    name: "Greek",
    script: "Grek",
  },
  {
    value: "en",
    name: "English",
    script: "Latn",
  },
  {
    value: "et",
    name: "Estonian",
    script: "Latn",
  },
  {
    value: "eu",
    name: "Basque",
    script: "Latn",
  },
  {
    value: "fi",
    name: "Finnish",
    script: "Latn",
  },
  {
    value: "fr",
    name: "French",
    script: "Latn",
  },
  {
    value: "gaz",
    name: "West Central Oromo",
    script: "Latn",
  },
  {
    value: "ga",
    name: "Irish",
    script: "Latn",
  },
  {
    value: "gl",
    name: "Galician",
    script: "Latn",
  },
  {
    value: "gu",
    name: "Gujarati",
    script: "Gujr",
  },
  {
    value: "he",
    name: "Hebrew",
    script: "Hebr",
  },
  {
    value: "hi",
    name: "Hindi",
    script: "Deva",
  },
  {
    value: "hr",
    name: "Croatian",
    script: "Latn",
  },
  {
    value: "hu",
    name: "Hungarian",
    script: "Latn",
  },
  {
    value: "hy",
    name: "Armenian",
    script: "Armn",
  },
  {
    value: "ig",
    name: "Igbo",
    script: "Latn",
  },
  {
    value: "id",
    name: "Indonesian",
    script: "Latn",
  },
  {
    value: "is",
    name: "Icelandic",
    script: "Latn",
  },
  {
    value: "it",
    name: "Italian",
    script: "Latn",
  },
  {
    value: "jv",
    name: "Javanese",
    script: "Latn",
  },
  {
    value: "ja",
    name: "Japanese",
    script: "Jpan",
  },
  {
    value: "kn",
    name: "Kannada",
    script: "Knda",
  },
  {
    value: "ka",
    name: "Georgian",
    script: "Geor",
  },
  {
    value: "kk",
    name: "Kazakh",
    script: "Cyrl",
  },
  {
    value: "khk",
    name: "Halh Mongolian",
    script: "Cyrl",
  },
  {
    value: "km",
    name: "Khmer",
    script: "Khmr",
  },
  {
    value: "ky",
    name: "Kyrgyz",
    script: "Cyrl",
  },
  {
    value: "ko",
    name: "Korean",
    script: "Kore",
  },
  {
    value: "lo",
    name: "Lao",
    script: "Laoo",
  },
  {
    value: "lt",
    name: "Lithuanian",
    script: "Latn",
  },
  {
    value: "lg",
    name: "Ganda",
    script: "Latn",
  },
  {
    value: "luo",
    name: "Luo",
    script: "Latn",
  },
  {
    value: "lv",
    name: "Standard Latvian",
    script: "Latn",
  },
  {
    value: "mai",
    name: "Maithili",
    script: "Deva",
  },
  {
    value: "ml",
    name: "Malayalam",
    script: "Mlym",
  },
  {
    value: "mr",
    name: "Marathi",
    script: "Deva",
  },
  {
    value: "mk",
    name: "Macedonian",
    script: "Cyrl",
  },
  {
    value: "mt",
    name: "Maltese",
    script: "Latn",
  },
  {
    value: "mni",
    name: "Meitei",
    script: "Beng",
  },
  {
    value: "my",
    name: "Burmese",
    script: "Mymr",
  },
  {
    value: "nl",
    name: "Dutch",
    script: "Latn",
  },
  {
    value: "nn",
    name: "Norwegian Nynorsk",
    script: "Latn",
  },
  {
    value: "nb",
    name: "Norwegian Bokmål",
    script: "Latn",
  },
  {
    value: "ne",
    name: "Nepali",
    script: "Deva",
  },
  {
    value: "ny",
    name: "Nyanja",
    script: "Latn",
  },
  {
    value: "or",
    name: "Odia",
    script: "Orya",
  },
  {
    value: "pa",
    name: "Punjabi",
    script: "Guru",
  },
  {
    value: "pbt",
    name: "Southern Pashto",
    script: "Arab",
  },
  {
    value: "pes",
    name: "Western Persian",
    script: "Arab",
  },
  {
    value: "pl",
    name: "Polish",
    script: "Latn",
  },
  {
    value: "pt",
    name: "Portuguese",
    script: "Latn",
  },
  {
    value: "ro",
    name: "Romanian",
    script: "Latn",
  },
  {
    value: "ru",
    name: "Russian",
    script: "Cyrl",
  },
  {
    value: "sk",
    name: "Slovak",
    script: "Latn",
  },
  {
    value: "sl",
    name: "Slovenian",
    script: "Latn",
  },
  {
    value: "sn",
    name: "Shona",
    script: "Latn",
  },
  {
    value: "sd",
    name: "Sindhi",
    script: "Arab",
  },
  {
    value: "so",
    name: "Somali",
    script: "Latn",
  },
  {
    value: "es",
    name: "Spanish",
    script: "Latn",
  },
  {
    value: "sr",
    name: "Serbian",
    script: "Cyrl",
  },
  {
    value: "sv",
    name: "Swedish",
    script: "Latn",
  },
  {
    value: "sw",
    name: "Swahili",
    script: "Latn",
  },
  {
    value: "ta",
    name: "Tamil",
    script: "Taml",
  },
  {
    value: "te",
    name: "Telugu",
    script: "Telu",
  },
  {
    value: "tg",
    name: "Tajik",
    script: "Cyrl",
  },
  {
    value: "tl",
    name: "Tagalog",
    script: "Latn",
  },
  {
    value: "th",
    name: "Thai",
    script: "Thai",
  },
  {
    value: "tr",
    name: "Turkish",
    script: "Latn",
  },
  {
    value: "uk",
    name: "Ukrainian",
    script: "Cyrl",
  },
  {
    value: "ur",
    name: "Urdu",
    script: "Arab",
  },
  {
    value: "uz",
    name: "Northern Uzbek",
    script: "Latn",
  },
  {
    value: "vi",
    name: "Vietnamese",
    script: "Latn",
  },
  {
    value: "yo",
    name: "Yoruba",
    script: "Latn",
  },
  {
    value: "yue",
    name: "Cantonese",
    script: "Hant",
  },
  {
    value: "ms",
    name: "Standard Malay",
    script: "Latn",
  },
  {
    value: "zu",
    name: "Zulu",
    script: "Latn",
  },
];

const supportedLatinLanguages = supportedLanguages.filter(
  (lan) => lan.script == "Latn",
);
supportedLatinLanguages.push({ value: undefined, name: "None" });

export { supportedLatinLanguages };

export default supportedLanguages;
