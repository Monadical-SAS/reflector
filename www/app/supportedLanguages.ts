import Script from "next/script";

// type Script = 'Latn' | 'Ethi' | 'Arab' | 'Beng' | 'Cyrl' | 'Taml' | 'Hant' | 'Hans' | 'Grek' | 'Gujr' | 'Hebr'| 'Deva'| 'Armn' | 'Jpan' | 'Knda' | 'Geor';
type LanguageOption = {
  value: string | undefined;
  name: string;
  script?: string;
};

const supportedLanguages: LanguageOption[] = [
  { value: "afr", name: "Afrikaans", script: "Latn" },
  {
    value: "amh",
    name: "Amharic",
    script: "Ethi",
  },
  {
    value: "arb",
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
    value: "asm",
    name: "Assamese",
    script: "Beng",
  },
  {
    value: "azj",
    name: "North Azerbaijani",
    script: "Latn",
  },
  {
    value: "bel",
    name: "Belarusian",
    script: "Cyrl",
  },
  {
    value: "ben",
    name: "Bengali",
    script: "Beng",
  },
  {
    value: "bos",
    name: "Bosnian",
    script: "Latn",
  },
  {
    value: "bul",
    name: "Bulgarian",
    script: "Cyrl",
  },
  {
    value: "cat",
    name: "Catalan",
    script: "Latn",
  },
  {
    value: "ceb",
    name: "Cebuano",
    script: "Latn",
  },
  {
    value: "ces",
    name: "Czech",
    script: "Latn",
  },
  {
    value: "ckb",
    name: "Central Kurdish",
    script: "Arab",
  },
  {
    value: "cmn",
    name: "Mandarin Chinese",
    script: "Hans",
  },
  {
    value: "cmn_Ha",
    name: "Mandarin Chinese",
    script: "Hant",
  },
  {
    value: "cym",
    name: "Welsh",
    script: "Latn",
  },
  {
    value: "dan",
    name: "Danish",
    script: "Latn",
  },
  {
    value: "deu",
    name: "German",
    script: "Latn",
  },
  {
    value: "ell",
    name: "Greek",
    script: "Grek",
  },
  {
    value: "eng",
    name: "English",
    script: "Latn",
  },
  {
    value: "est",
    name: "Estonian",
    script: "Latn",
  },
  {
    value: "eus",
    name: "Basque",
    script: "Latn",
  },
  {
    value: "fin",
    name: "Finnish",
    script: "Latn",
  },
  {
    value: "fra",
    name: "French",
    script: "Latn",
  },
  {
    value: "gaz",
    name: "West Central Oromo",
    script: "Latn",
  },
  {
    value: "gle",
    name: "Irish",
    script: "Latn",
  },
  {
    value: "glg",
    name: "Galician",
    script: "Latn",
  },
  {
    value: "guj",
    name: "Gujarati",
    script: "Gujr",
  },
  {
    value: "heb",
    name: "Hebrew",
    script: "Hebr",
  },
  {
    value: "hin",
    name: "Hindi",
    script: "Deva",
  },
  {
    value: "hrv",
    name: "Croatian",
    script: "Latn",
  },
  {
    value: "hun",
    name: "Hungarian",
    script: "Latn",
  },
  {
    value: "hye",
    name: "Armenian",
    script: "Armn",
  },
  {
    value: "ibo",
    name: "Igbo",
    script: "Latn",
  },
  {
    value: "ind",
    name: "Indonesian",
    script: "Latn",
  },
  {
    value: "isl",
    name: "Icelandic",
    script: "Latn",
  },
  {
    value: "ita",
    name: "Italian",
    script: "Latn",
  },
  {
    value: "jav",
    name: "Javanese",
    script: "Latn",
  },
  {
    value: "jpn",
    name: "Japanese",
    script: "Jpan",
  },
  {
    value: "kan",
    name: "Kannada",
    script: "Knda",
  },
  {
    value: "kat",
    name: "Georgian",
    script: "Geor",
  },
  {
    value: "kaz",
    name: "Kazakh",
    script: "Cyrl",
  },
  {
    value: "khk",
    name: "Halh Mongolian",
    script: "Cyrl",
  },
  {
    value: "khm",
    name: "Khmer",
    script: "Khmr",
  },
  {
    value: "kir",
    name: "Kyrgyz",
    script: "Cyrl",
  },
  {
    value: "kor",
    name: "Korean",
    script: "Kore",
  },
  {
    value: "lao",
    name: "Lao",
    script: "Laoo",
  },
  {
    value: "lit",
    name: "Lithuanian",
    script: "Latn",
  },
  {
    value: "lug",
    name: "Ganda",
    script: "Latn",
  },
  {
    value: "luo",
    name: "Luo",
    script: "Latn",
  },
  {
    value: "lvs",
    name: "Standard Latvian",
    script: "Latn",
  },
  {
    value: "mai",
    name: "Maithili",
    script: "Deva",
  },
  {
    value: "mal",
    name: "Malayalam",
    script: "Mlym",
  },
  {
    value: "mar",
    name: "Marathi",
    script: "Deva",
  },
  {
    value: "mkd",
    name: "Macedonian",
    script: "Cyrl",
  },
  {
    value: "mlt",
    name: "Maltese",
    script: "Latn",
  },
  {
    value: "mni",
    name: "Meitei",
    script: "Beng",
  },
  {
    value: "mya",
    name: "Burmese",
    script: "Mymr",
  },
  {
    value: "nld",
    name: "Dutch",
    script: "Latn",
  },
  {
    value: "nno",
    name: "Norwegian Nynorsk",
    script: "Latn",
  },
  {
    value: "nob",
    name: "Norwegian Bokmål",
    script: "Latn",
  },
  {
    value: "npi",
    name: "Nepali",
    script: "Deva",
  },
  {
    value: "nya",
    name: "Nyanja",
    script: "Latn",
  },
  {
    value: "ory",
    name: "Odia",
    script: "Orya",
  },
  {
    value: "pan",
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
    value: "pol",
    name: "Polish",
    script: "Latn",
  },
  {
    value: "por",
    name: "Portuguese",
    script: "Latn",
  },
  {
    value: "ron",
    name: "Romanian",
    script: "Latn",
  },
  {
    value: "rus",
    name: "Russian",
    script: "Cyrl",
  },
  {
    value: "slk",
    name: "Slovak",
    script: "Latn",
  },
  {
    value: "slv",
    name: "Slovenian",
    script: "Latn",
  },
  {
    value: "sna",
    name: "Shona",
    script: "Latn",
  },
  {
    value: "snd",
    name: "Sindhi",
    script: "Arab",
  },
  {
    value: "som",
    name: "Somali",
    script: "Latn",
  },
  {
    value: "spa",
    name: "Spanish",
    script: "Latn",
  },
  {
    value: "srp",
    name: "Serbian",
    script: "Cyrl",
  },
  {
    value: "swe",
    name: "Swedish",
    script: "Latn",
  },
  {
    value: "swh",
    name: "Swahili",
    script: "Latn",
  },
  {
    value: "tam",
    name: "Tamil",
    script: "Taml",
  },
  {
    value: "tel",
    name: "Telugu",
    script: "Telu",
  },
  {
    value: "tgk",
    name: "Tajik",
    script: "Cyrl",
  },
  {
    value: "tgl",
    name: "Tagalog",
    script: "Latn",
  },
  {
    value: "tha",
    name: "Thai",
    script: "Thai",
  },
  {
    value: "tur",
    name: "Turkish",
    script: "Latn",
  },
  {
    value: "ukr",
    name: "Ukrainian",
    script: "Cyrl",
  },
  {
    value: "urd",
    name: "Urdu",
    script: "Arab",
  },
  {
    value: "uzn",
    name: "Northern Uzbek",
    script: "Latn",
  },
  {
    value: "vie",
    name: "Vietnamese",
    script: "Latn",
  },
  {
    value: "yor",
    name: "Yoruba",
    script: "Latn",
  },
  {
    value: "yue",
    name: "Cantonese",
    script: "Hant",
  },
  {
    value: "zsm",
    name: "Standard Malay",
    script: "Latn",
  },
  {
    value: "zul",
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
