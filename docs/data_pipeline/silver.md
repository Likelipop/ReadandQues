# Silver Layer: Cleansing & Standardization

The **Silver Layer** transforms raw links into clean, standardized, and structured articles. It bridges the gap between raw web markup and production-grade ML/search ready documents by maintaining an exact raw HTML backup and enforcing strict sanitization and quality gates.

---

## 1. What It Does (Business & Functional Overview)

* **Raw HTML Archiving (`silver_raw_html`):** Downloads and stores the complete, unmodified HTML source of every candidate article in object storage (MinIO). This serves as the system's permanent raw audit trail.
* **Content Extraction (`silver_cleaned_articles`):** Strips HTML boilerplate (navigation bars, ads, cookie banners, sidebars, footers) and converts the primary article body into clean Markdown.
* **Text Sanitization:** Standardizes formatting, cleans up excessive whitespace, converts emphasized subheadings into semantic Markdown headers, and removes syndicated footer notices.
* **Quality Filtering Gate:** Evaluates word count and discards stubs, login walls, or malformed pages before they reach downstream indexing.
* **Staged Storage:** Stores sanitized, structured JSON documents in MinIO's `silver-cleaned` bucket for Gold layer consumption.

---

## 2. How It Works (Architectural & Technical Deep Dive)

The Silver layer is implemented across two partitioned assets in `NewsPipeline/src/NewsPipeline/assets/silver.py`:

```
bronze_links (from MongoIOManager)
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Asset: silver_raw_html                                      │
│ - For each item in bronze_links:                            │
│   1. trafilatura.fetch_url(url)                             │
│   2. If download fails, log warning & increment skipped     │
│   3. Save byte-for-byte to MinIO:                           │
│      Bucket: "raw-html"                                     │
│      Key: "<partition_date>/<article_id>.html"              │
│ - Return downloaded candidate list with metadata            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Asset: silver_cleaned_articles                              │
│ - For each item in silver_raw_html:                         │
│   1. Read raw HTML from MinIO "raw-html" bucket             │
│   2. trafilatura.extract(output_format="markdown", ...)     │
│   3. Apply sanitize_article_text(extracted_text)            │
│      - Truncate at FOOTER_MARKERS                           │
│      - Regex transform bold lines to "### Subheading"       │
│      - Normalize consecutive newlines (\n{3,} -> \n\n)      │
│   4. Quality Gate: check word_count >= 150 (drop if < 150)  │
│   5. Fallback image & title extraction via BeautifulSoup    │
│   6. Save structured JSON to MinIO:                         │
│      Bucket: "silver-cleaned"                               │
│      Key: "<partition_date>/<article_id>.json"              │
└─────────────────────────────────────────────────────────────┘
```

### Technical Details & Algorithms

#### A. Trafilatura for Web Scraping
Instead of using naive CSS selectors or simple `requests` calls, the pipeline uses **`trafilatura`**:
* `trafilatura.fetch_url(url)` handles redirect following, custom user-agent headers, and gzip decompression.
* `trafilatura.extract(html, output_format="markdown", include_formatting=True, include_links=True, include_comments=False)` uses heuristic layout analysis to extract only the substantive body text, preserving semantic markdown links and formatting while discarding menus, headers, and footers.

#### B. The Post-Processing Sanitization Engine (`sanitize_article_text`)
Even after extraction, news syndication sites (like ScienceDaily) attach boilerplate footers. The sanitization engine executes three linear passes:
1. **Footer Truncation:**
   Searches case-insensitively for known syndicated markers in `FOOTER_MARKERS`:
   ```python
   FOOTER_MARKERS = [
       "**Story Source:**",
       "Story Source:",
       "**Journal Reference:**",
       "Journal Reference:",
       "**Cite This Page:**",
       "Cite This Page:",
   ]
   ```
   The string is truncated immediately prior to the first occurring marker.
2. **Subheading Normalization:**
   Many web authors use standalone bold lines rather than Markdown headers. The engine scans each line with regex:
   ```python
   bold_match = re.match(r"^\*\*([A-Za-z0-9\s,.\'\"!?:;—–-]+)\*\*\.?$", trimmed)
   if bold_match and len(trimmed) < 120 and not trimmed.endswith("."):
       cleaned_lines.append(f"### {bold_match.group(1).strip()}")
   ```
   This standardizes bold lines into explicit Markdown `### Subheading` elements for optimal chunk splitting downstream.
3. **Newline Compression:**
   Compresses erratic line breaks (`re.sub(r"\n{3,}", "\n\n", combined)`), standardizing all paragraphs to clean double newlines.

#### C. The Quality Gate (`word_count >= 150`)
```python
clean_text = sanitize_article_text(extracted_text)
word_count = len(clean_text.split())

if word_count < 150:
    context.log.debug(f"Article skipped (clean word count {word_count} < 150).")
    continue
```
* **Why 150 words?** Pages returning 404 text, cookie consent popups, image galleries without text, or video placeholders typically extract to 20–80 words. Dropping them here guarantees that the Gold layer only indexes informative, high-signal articles.

#### D. BeautifulSoup Metadata Fallbacks
If the RSS entry had no thumbnail or title, the pipeline falls back to inspecting the raw HTML document:
* **Title:** Searches `<meta property="og:title">`, `<meta name="twitter:title">`, `<title>`, or `<h1>`.
* **Image:** Inspects `<meta property="og:image">`, `<meta name="twitter:image">`, `<link rel="image_src">`, and finally `<article> img[src]`.

---

## 3. Data Contract & Storage Schema

### A. Raw HTML Storage (`MinIO`)
* **Bucket:** `raw-html`
* **Object Key:** `{partition_date}/{article_id}.html` (e.g., `2026-09-06/art_b63f7920e6650b13.html`)
* **Content-Type:** `text/html; charset=utf-8`

### B. Cleaned JSON Storage (`MinIO`)
* **Bucket:** `silver-cleaned`
* **Object Key:** `{partition_date}/{article_id}.json` (e.g., `2026-09-06/art_b63f7920e6650b13.json`)
* **Content-Type:** `application/json; charset=utf-8`

#### Cleaned Article Schema Specification
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `article_id` | `string` | Deterministic MD5 identifier |
| `url` | `string` | Canonical source URL |
| `title` | `string` | Sanitized article title |
| `source` | `string` | Source publisher name |
| `image_url` | `string` | Extracted lead image/thumbnail URL |
| `thumbnail_url` | `string` | Mirror of image_url |
| `original_text` | `string` | Sanitized, clean Markdown article body |
| `word_count` | `integer`| Total words in `original_text` (guaranteed >= 150) |
| `published_at` | `string (ISO)`| Publication date in UTC |
| `partition_date` | `string` | Dagster partition key (`YYYY-MM-DD`) |
| `sanitized_at` | `string (ISO)`| Timestamp when the sanitization engine executed |

#### Sample Cleaned Article JSON (`silver-cleaned`)
```json
{
  "article_id": "art_b63f7920e6650b13",
  "url": "https://www.sciencedaily.com/releases/2026/09/260906101520.htm",
  "title": "Antarctica gained a record 695 billion tons of ice. Scientists found the surprising reason",
  "source": "ScienceDaily",
  "image_url": "https://sciencedaily.com/images/2026/09/ice_core.jpg",
  "thumbnail_url": "https://sciencedaily.com/images/2026/09/ice_core.jpg",
  "original_text": "### Surprising Ice Accumulation\n\nEast Antarctica experienced record-breaking snowfall during late 2025...\n\n### Climate Implications\n\nResearchers discovered that atmospheric rivers contributed to...",
  "word_count": 524,
  "published_at": "2026-09-06T14:15:20+00:00",
  "partition_date": "2026-09-06",
  "sanitized_at": "2026-09-10T04:10:25.432109+00:00"
}
```

---

## 4. Failure Modes & Edge Cases

| Failure Scenario | System Behavior & Handling |
| :--- | :--- |
| **HTTP 403 / 404 on target URL** | `trafilatura.fetch_url` returns `None`. Logged as a warning, increments `skipped_count`, pipeline proceeds to next URL. |
| **Article body has no readable text** | `trafilatura.extract` returns empty string. Handled gracefully; `word_count` evaluates to 0 and quality gate drops it. |
| **Article is a 50-word summary/stub** | Fails the `word_count >= 150` check and is dropped, preventing poor-quality text from entering ChromaDB. |
| **MinIO service restart during download** | Client has retry logic and auto-creates buckets (`ensure_bucket`) if missing. |
