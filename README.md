# 🩺 ICD-10 A–Z Web Scraper  
### Python | Web Scraping | JSON Data Extraction

---


## 📖 About

This project is a **Python-based web scraper** that automatically extracts **ICD-10 A–Z root codes** from medical coding websites.

The scraper intelligently reads the HTML structure—specifically the  
`<ul class="codeHierarchy">` element—and **recursively traverses all nested child codes**, building a **complete hierarchical representation** of ICD-10 codes.

The final output is a **clean, well-structured JSON file** containing full ICD-10 code hierarchy along with clinical metadata.

---

## 🎯 What This Scraper Does

- Scrapes **ICD-10 root codes (A–Z)**
- Parses the **hierarchical `<ul class="codeHierarchy">` structure**
- Recursively collects:
  - Parent codes
  - Child codes
  - Sub-child codes (any depth)
- Cleans and normalizes code descriptions
- Extracts additional clinical details
- Saves everything into a structured JSON file.

---

## 🔍 Data Extracted

For each ICD-10 code, the scraper extracts:

- 📌 **ICD Code**
- 📝 **Cleaned Description**
- 🧠 **Clinical Information**
- 📋 **Applicable To** points
- 🔁 **Synonyms / Includes**
- 🌳 **Parent–Child Relationships**

---

## 🧠 How It Works (Logic Flow)

1. Load ICD-10 A–Z root pages  
2. Locate `<ul class="codeHierarchy">`  
3. Parse `<li>` elements recursively  
4. Extract code & description  
5. Detect section headers (e.g., *Clinical Information*, *Applicable To*)  
6. Extract list items under each section  
7. Normalize and clean text  
8. Build nested Python dictionaries  
9. Export full hierarchy as JSON  
