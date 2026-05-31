# Requirements Document

## Introduction

The EDGAR Extractor is a Python pipeline that ingests SEC EDGAR 8-K press-release filings in HTML format and produces a consistent, machine-readable JSON output containing structured financial data. The pipeline handles documents of arbitrary size by chunking content that exceeds the LLM context window, extracts data from both HTML tables and narrative prose, records the exact source location (data lineage) and a confidence score for every extracted value, and tracks token usage and dollar cost per filing. The output schema uniquely identifies each company and filing period so that results can be compared and aggregated across filings.

The existing codebase provides a partial implementation across `ingest.py`, `extract.py`, `pipeline.py`, `schema.py`, `serialize.py`, `validate.py`, `cost.py`, and LLM prompt templates. These requirements formalise the complete, correct behaviour that the finished system must exhibit.

---

## Glossary

- **Pipeline**: The end-to-end orchestration component (`pipeline.py`) that coordinates ingestion, extraction, validation, reconciliation, and serialisation.
- **Ingestor**: The HTML parsing component (`ingest.py`) that converts raw filing HTML into `TableData` and `ProseChunk` objects.
- **Extractor**: The LLM-calling component (`extract.py`) that sends structured prompts to the LLM and parses the JSON responses.
- **Validator**: The validation component (`validate.py`) that scores confidence, deduplicates entities, and cross-checks table and prose data.
- **Serializer**: The serialisation component (`serialize.py`) that converts a `FilingExtraction` object to and from JSON files.
- **CostTracker**: The cost-tracking component (`cost.py`) that accumulates token counts and dollar costs per model per filing.
- **Filing**: A single SEC EDGAR 8-K HTML document representing one company's earnings press release for one fiscal period.
- **FilingExtraction**: The root Pydantic model that holds all extracted data for one filing.
- **TableData**: A structured representation of one HTML `<table>` element, including headers, rows, source location, and confidence.
- **ProseChunk**: A structured representation of one narrative text section, including section header, text, source location, and confidence.
- **GuidanceSection**: A specialised `ProseChunk` that contains forward-looking management guidance.
- **Chunk**: A sub-segment of a `ProseChunk` or `TableData` created when the source content exceeds `MAX_INPUT_TOKENS`.
- **Data Lineage**: The exact source reference (XPath expression or equivalent CSS/positional selector) that identifies where in the original HTML document a specific extracted value was found.
- **Confidence Score**: A floating-point value in [0.0, 1.0] that expresses the Extractor's certainty that an extracted value is correct.
- **CIK**: The SEC Central Index Key — a unique numeric identifier assigned to each registrant.
- **Ticker**: The stock exchange ticker symbol for a company.
- **Fiscal Period**: A combination of fiscal year (YYYY) and quarter (Q1–Q4 or FY) that identifies the reporting period.
- **LLM**: The large language model used for extraction, accessed via an OpenAI-compatible API (currently Portkey for cloud models).
- **Portkey**: A cloud LLM gateway API used as an alternative to direct model access.
- **Golden File**: A manually verified JSON output used as the reference for evaluation.
- **F1 Score**: The harmonic mean of precision and recall, used to measure extraction quality against golden files.
- **Boilerplate**: Legally required but financially uninformative text (safe-harbour statements, forward-looking disclaimers) that the Ingestor filters out before extraction.

---

## Requirements

### Requirement 1: HTML Ingestion

**User Story:** As a data engineer, I want the pipeline to parse raw 8-K HTML filings into structured tables and prose chunks, so that downstream extraction has clean, typed inputs.

#### Acceptance Criteria

1. WHEN a valid HTML filing is provided, THE Ingestor SHALL parse all `<table>` elements and return a list of `TableData` objects, each containing a non-empty `headers` list and at least one row.
2. WHEN a valid HTML filing is provided, THE Ingestor SHALL parse all narrative text sections delimited by `<h1>`, `<h2>`, `<h3>`, or `<h4>` elements and return a list of `ProseChunk` objects, each containing the section header text and the paragraph text beneath it joined by a single newline character.
3. WHEN a `<table>` element contains merged cells (colspan or rowspan attributes), THE Ingestor SHALL expand merged cells so that every logical row contains the same number of columns as the header row, filling any added cells with an empty string.
4. WHEN a `<table>` element contains no row with at least one `<th>` element, or contains no data rows after the header row, THE Ingestor SHALL omit that table from the output list.
5. WHEN a paragraph matches a boilerplate pattern (case-insensitive match for safe-harbour, forward-looking disclaimer, or share-repurchase notice), THE Ingestor SHALL exclude that paragraph from the `ProseChunk` text.
6. WHEN a `<table>` element is encountered, THE Ingestor SHALL record the XPath expression of that element as the `source_xpath` field of the resulting `TableData` object.
7. WHEN a prose section is encountered, THE Ingestor SHALL record the XPath expression of the section header element as the `source_xpath` field of the resulting `ProseChunk` object.
8. WHEN an HTML filing is read, THE Ingestor SHALL detect the character encoding from the HTTP `Content-Type` header or HTML `<meta charset>` tag and decode accordingly; IF no encoding is declared, THE Ingestor SHALL attempt UTF-8, then Latin-1, then Windows-1252 in that order without raising an exception.

---

### Requirement 2: Large-Document Chunking

**User Story:** As a data engineer, I want the pipeline to handle filings that exceed the LLM context window, so that no filing is skipped or silently truncated.

#### Acceptance Criteria

1. WHEN the token count of a `TableData` object (including headers and all rows) exceeds `MAX_INPUT_TOKENS`, THE Extractor SHALL split the table rows into sequential batches such that each batch, when combined with the header row, contains at most `MAX_INPUT_TOKENS` tokens, and SHALL process each batch independently.
2. WHEN the token count of a `ProseChunk` object exceeds `MAX_INPUT_TOKENS`, THE Extractor SHALL split the chunk text into sequential sub-chunks at token boundaries, each containing at most `MAX_INPUT_TOKENS` tokens, and process each sub-chunk independently.
3. WHEN a `TableData` object is processed in batches, THE Pipeline SHALL merge the per-batch extraction results into a single `TableData.extracted_data` dictionary before serialisation, with later-batch values overwriting earlier-batch values for duplicate keys.
4. WHEN a `ProseChunk` object is processed in sub-chunks, THE Pipeline SHALL merge the per-sub-chunk extraction results into a single `ProseChunk.extracted_data` dictionary before serialisation, with later sub-chunk values overwriting earlier sub-chunk values for duplicate keys.
5. WHEN batching or splitting occurs for any content type (table batching, prose splitting, or both), THE Extractor SHALL assign a confidence score no greater than 0.75 to the merged result after all batches or sub-chunks have been processed.
6. THE Extractor SHALL use the `tiktoken` library with the `gpt-4` encoding to count tokens consistently across all chunking decisions.
7. WHEN an individual batch or sub-chunk LLM call fails, THE Extractor SHALL record the failure in `extraction_metadata.issues` and assign a confidence score of 0.0 to the affected batch result, then continue processing remaining batches.

---

### Requirement 3: Table Data Extraction

**User Story:** As a financial analyst, I want the pipeline to extract revenue, net income, EPS, and segment breakdowns from HTML tables, so that I can compare financial results across filings without reading the raw HTML.

#### Acceptance Criteria

1. WHEN a `TableData` object is classified as a financial statement table (identified by header keywords such as "revenue", "income", "earnings", or "loss"), THE Extractor SHALL extract the following metrics where present: total revenue, net income, basic EPS, diluted EPS, and operating income.
2. WHEN a `TableData` object contains segment data (identified by a column or row header containing "segment"), THE Extractor SHALL extract each segment name, its revenue, and its operating income as a list of segment objects within `extracted_data`.
3. WHEN a numeric value in a table is expressed in thousands (scale note contains "thousands" or "000s") or millions (scale note contains "millions"), THE Extractor SHALL multiply the parsed value by 1,000 or 1,000,000 respectively to produce the full integer representation; IF the scale factor cannot be determined, THE Extractor SHALL record the value as-is and set `confidence` to no greater than 0.5 for that metric.
4. WHEN a numeric value in a table is negative (expressed with parentheses, a leading minus sign, or a standalone dash in a numeric column), THE Extractor SHALL represent it as a negative number in the output; a standalone dash in a non-numeric context SHALL be treated as a missing value (null), not as zero or negative.
5. WHEN a `TableData` object is processed, THE Extractor SHALL include the `table_id` and `source_xpath` of the source `TableData` in the `lineage` field of every extracted metric.
6. WHEN a `TableData` object is processed, THE Extractor SHALL assign a `confidence` score in [0.0, 1.0] to each extracted metric based on the structural clarity of the table (e.g., presence of explicit headers, absence of merged cells) and the LLM response certainty.
7. WHEN a `TableData` object contains a column header that cannot be mapped to a known metric (total revenue, net income, basic EPS, diluted EPS, operating income, or segment fields), THE Extractor SHALL include that column's name and values in an `other_metrics` list rather than discarding it.

---

### Requirement 4: Prose Data Extraction

**User Story:** As a financial analyst, I want the pipeline to extract financial figures and key topics from narrative prose sections, so that data mentioned only in text (not in tables) is captured.

#### Acceptance Criteria

1. WHEN a `ProseChunk` object is processed, THE Extractor SHALL extract all financial figures mentioned in the text, including their metric type (one of: revenue, net_income, eps_basic, eps_diluted, operating_income, gross_profit, or other), numeric value normalised to full units, currency (ISO 4217 code), and fiscal period.
2. WHEN a `ProseChunk` object is processed, THE Extractor SHALL extract named entities of type company, person, and location; IF no entities of a given type are found, THE Extractor SHALL return an empty list for that type.
3. WHEN a `ProseChunk` object is processed, THE Extractor SHALL produce a `summary` field containing a concise (≤ 3 sentence) description of the section's content; IF the section text is 50 characters or fewer after stripping whitespace, or consists solely of boilerplate text, THE Extractor SHALL produce an empty string for the `summary` field.
4. WHEN a `ProseChunk` object is processed, THE Extractor SHALL include the `chunk_id` and `source_xpath` of the source `ProseChunk` in the `lineage` field of every extracted figure.
5. WHEN a `ProseChunk` object is processed, THE Extractor SHALL assign a `confidence` score in [0.0, 1.0] to each extracted figure.
6. WHEN a `ProseChunk` object is processed and no financial figures are found in the text, THE Extractor SHALL return an empty list for `figures` rather than omitting the field.

---

### Requirement 5: Forward Guidance Extraction

**User Story:** As a financial analyst, I want the pipeline to extract management guidance and verbatim executive quotes from the filing, so that forward-looking statements are captured alongside historical results.

#### Acceptance Criteria

1. WHEN a `GuidanceSection` object is processed, THE Extractor SHALL extract the guidance type (one of: revenue, earnings, outlook, strategic, or other), the target fiscal period (one of: Q1–Q4 or FY), and the target fiscal year (four-digit integer).
2. WHEN a `GuidanceSection` object contains quantitative guidance (text containing at least one numeric value with a currency or unit), THE Extractor SHALL extract each guided metric name, its low range value (or null if a single point estimate), its high range value (or null if a single point estimate), and its ISO 4217 currency code.
3. WHEN a `GuidanceSection` object contains a direct management quote (text enclosed in quotation marks or attributed to a named speaker), THE Extractor SHALL capture the verbatim quote text, the speaker's name (or null if not identifiable), and the speaker's title (or null if not identifiable).
4. WHEN a `GuidanceSection` object is processed, THE Extractor SHALL include the `section_id` and `source_xpath` fields of the source `GuidanceSection` in the `lineage` field of every extracted guidance item; the `source_xpath` field SHALL be present on the `GuidanceSection` input object.
5. WHEN a `GuidanceSection` object is processed, THE Extractor SHALL assign a `confidence` score in [0.0, 1.0] to each extracted guidance item, including both metric-level and quote-level items.
6. IF a filing contains no section whose header or content matches guidance keywords (e.g., "outlook", "guidance", "expects", "forecast"), THEN THE Pipeline SHALL record an empty `guidance_sections` list and SHALL NOT raise an exception.

---

### Requirement 6: Data Lineage

**User Story:** As a data auditor, I want every extracted value to carry an exact reference back to its location in the source HTML, so that I can verify any value without re-running the pipeline.

#### Acceptance Criteria

1. THE Ingestor SHALL record the XPath expression of every `<table>` element as the `source_xpath` field of the corresponding `TableData` object.
2. THE Ingestor SHALL record the XPath expression of every section-header element (`<h1>`–`<h4>`) as the `source_xpath` field of the corresponding `ProseChunk` object.
3. WHEN an extracted metric, figure, or guidance item is written to the output JSON, THE Serializer SHALL include a `lineage` object containing at minimum: `source_id` (the `table_id`, `chunk_id`, or `section_id`), `source_xpath`, and `filing_id`.
4. THE Serializer SHALL preserve `lineage` objects through round-trip serialisation and deserialisation without data loss.
5. FOR ALL extracted values in a `FilingExtraction`, parsing the output JSON then re-serialising it SHALL produce an equivalent JSON document (round-trip property).

---

### Requirement 7: Confidence Scoring

**User Story:** As a data consumer, I want each extracted value to carry a confidence score, so that I can filter out low-quality extractions before using the data.

#### Acceptance Criteria

1. THE Validator SHALL assign a `confidence` score in [0.0, 1.0] to every `TableData`, `ProseChunk`, and `GuidanceSection` object after extraction.
2. IF a `TableData` object was processed in multiple batches, THE Validator SHALL cap its `confidence` score at 0.75. IF a `TableData` object was processed in a single batch, THE Validator SHALL enforce a `confidence` score in [0.0, 1.0] with no additional cap.
3. IF a `ProseChunk` object was processed in multiple sub-chunks, THE Validator SHALL cap its `confidence` score at 0.75. IF a `ProseChunk` object was processed in a single pass, THE Validator SHALL enforce a `confidence` score in [0.0, 1.0] with no additional cap.
4. WHEN the LLM returns a response that cannot be parsed as valid JSON, THE Validator SHALL assign a `confidence` score of 0.0 to the affected object and SHALL record the parse failure in the `extraction_metadata.issues` list on the `FilingExtraction` object.
5. THE Validator SHALL compute an `overall_confidence` score for the `FilingExtraction` as the arithmetic mean of all per-object confidence scores; IF all per-object confidence scores are 0.0, THE Validator SHALL set `overall_confidence` to 0.0.
6. WHEN the `overall_confidence` of a `FilingExtraction` is below 0.5, THE Pipeline SHALL log a warning to stderr identifying the filing filename and the overall confidence value.

---

### Requirement 8: Output JSON Schema

**User Story:** As a data engineer, I want all pipeline outputs to conform to a consistent JSON schema that uniquely identifies each company and filing period, so that results can be joined and compared across filings programmatically.

#### Acceptance Criteria

1. THE Serializer SHALL produce a JSON document whose root object contains the fields: `filing_id`, `company_name`, `ticker`, `cik`, `filing_type`, `fiscal_year`, `fiscal_quarter`, `filing_date`, `tables`, `prose_chunks`, `guidance_sections`, and `extraction_metadata`.
2. THE Serializer SHALL populate `ticker` and `cik` from the filing metadata when available, and SHALL leave them `null` when not determinable.
3. THE Serializer SHALL populate `fiscal_year` (four-digit integer) and `fiscal_quarter` (one of `"Q1"`, `"Q2"`, `"Q3"`, `"Q4"`, `"FY"`) from the filing content or filename when available. IF the source provides a fiscal year value that is not exactly four digits, THEN THE Serializer SHALL reject it and leave `fiscal_year` as `null`. IF the source provides a `fiscal_quarter` value that is not one of the five permitted strings, THEN THE Serializer SHALL reject it and leave `fiscal_quarter` as `null`.
4. THE Serializer SHALL format all date fields as ISO 8601 strings (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`).
5. THE Serializer SHALL represent all monetary values as numbers (not strings), with a separate `currency` field at the table level containing the ISO 4217 currency code applicable to all monetary values in that table.
6. THE Serializer SHALL represent all monetary values in their full unit (e.g., dollars, not thousands of dollars), regardless of the scale used in the source table; IF the scale factor cannot be determined, THE Serializer SHALL record the value as-is and set the `scale_unresolved` flag to `true` on the affected metric.
7. WHEN a `FilingExtraction` is serialised and then deserialised by the Serializer, the resulting object SHALL be field-by-field equal to the original, with no fields added, removed, or changed in type or value.
8. WHEN the Serializer writes a `FilingExtraction` to disk, THE Serializer SHALL validate the output JSON against the `FilingExtraction` Pydantic schema before writing, and SHALL raise a `ValidationError` if the document does not conform.

---

### Requirement 9: Token Usage and Cost Tracking

**User Story:** As a platform operator, I want the pipeline to record token usage and dollar cost for every filing, so that I can monitor and optimise LLM spend.

#### Acceptance Criteria

1. WHEN an LLM API call completes, THE CostTracker SHALL record the prompt token count, completion token count, and total token count for that call as three separate values.
2. WHEN an LLM API call completes, THE CostTracker SHALL compute the dollar cost of that call using the per-1K-token rate for the model used, and SHALL accumulate it in the running total for that model.
3. WHEN a filing is fully processed, THE Pipeline SHALL write a `cost_report` object to `extraction_metadata` containing: `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, and `total_cost_usd` (rounded to 6 decimal places).
4. WHEN the pipeline processes a directory of filings, THE Pipeline SHALL print a summary cost report to stdout after all filings are processed, showing one row per model with columns: `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `total_cost_usd`, and a final grand-total row summing all models.
5. THE CostTracker SHALL support at minimum the following models with their per-1K-token rates: `gpt-4o` ($0.005), `gpt-4` ($0.030), `gpt-3.5-turbo` ($0.0015), and any model whose name contains the substring `local` at $0.000.
6. IF a model name is not in the CostTracker's rate table and does not match the `local` pattern, THE CostTracker SHALL apply a default rate of $0.010 per 1K tokens and SHALL write a warning to stderr identifying the unknown model name.

---

### Requirement 10: Pipeline Orchestration

**User Story:** As a data engineer, I want a single CLI command to process one filing or an entire directory of filings end-to-end, so that I can run batch extractions without writing custom scripts.

#### Acceptance Criteria

1. WHEN invoked with a path to a single HTML file, THE Pipeline SHALL execute the full ingest → extract → validate → reconcile → serialise sequence for that file and write the output JSON to `data/outputs/<stem>.json`.
2. WHEN invoked with a path to a directory, THE Pipeline SHALL process all `*.html` files in that directory in lexicographic order and write one output JSON per filing to `data/outputs/`.
3. WHEN a filing fails at any pipeline stage, THE Pipeline SHALL log the error and the filing filename to stdout and continue processing the remaining filings without exiting.
4. WHEN all filings in a directory have been processed, THE Pipeline SHALL print a summary to stdout showing the count of successful extractions, failed extractions, and total cost in USD to two decimal places.
5. WHEN the pipeline is invoked, THE Pipeline SHALL load configuration from `.env`.
6. WHEN the `data/outputs/` directory does not exist, THE Pipeline SHALL create it before writing any output file.
7. WHEN the directory contains no HTML files, THE Pipeline SHALL print a summary with zero counts for successful extractions, failed extractions, and total cost.

---

### Requirement 11: Validation and Cross-Checking

**User Story:** As a data quality engineer, I want the pipeline to cross-check extracted values between tables and prose, so that inconsistencies are flagged before the output is written.

#### Acceptance Criteria

1. WHEN a `FilingExtraction` contains both table-extracted and prose-extracted values for the same metric (matched by case-insensitive metric name), THE Validator SHALL compare the two values using the formula `|a − b| / max(|a|, |b|)` and record any discrepancy greater than 0.01 (1%) in `extraction_metadata.issues`; IF either value is zero, THE Validator SHALL skip the percentage check and record the discrepancy only if the absolute difference exceeds 1.0. Each issue entry SHALL contain at minimum: `metric`, `table_value`, `prose_value`, `discrepancy_pct`, and `source_ids`.
2. WHEN duplicate entities (same name and type, matched case-insensitively within `extracted_data`) appear across multiple `ProseChunk` objects, THE Validator SHALL deduplicate them and retain the instance with the highest confidence score; IF two instances have equal confidence scores, THE Validator SHALL retain the instance from the `ProseChunk` with the lexicographically smaller `chunk_id`.
3. WHEN a `FilingExtraction` is validated, THE Validator SHALL produce a `validation_report` containing: `overall_confidence` (arithmetic mean of all per-object confidence scores, or 0.0 if none), `table_confidence` (arithmetic mean of all `TableData` confidence scores, or 0.0 if none), `prose_confidence` (arithmetic mean of all `ProseChunk` confidence scores, or 0.0 if none), `guidance_confidence` (arithmetic mean of all `GuidanceSection` confidence scores, or 0.0 if none), and `issues` list.
4. WHEN the `issues` list is non-empty and validation has fully completed, THE Pipeline SHALL include the full `issues` list in `extraction_metadata.validation` in the output JSON. WHEN an unhandled exception occurs during validation, THE Pipeline SHALL set `extraction_metadata.validation_error` to the exception message, omit `extraction_metadata.validation`, and continue to serialise and write the current filing before moving to the next.

---

### Requirement 12: Evaluation Harness

**User Story:** As a machine learning engineer, I want an evaluation script that compares pipeline outputs against golden JSON files, so that I can measure and track extraction quality over time.

#### Acceptance Criteria

1. WHEN invoked with an outputs directory, THE Evaluator SHALL match each output JSON file to the golden JSON file in `data/golden/` with the identical filename (case-sensitive), and SHALL compare matched pairs using F1 score, exact match, and structural similarity metrics.
2. WHEN a golden file does not exist for an output file, THE Evaluator SHALL log a warning to stderr and skip that file without raising an exception.
3. WHEN an output JSON file cannot be read or parsed (e.g., file is corrupt or not valid JSON), THE Evaluator SHALL allow the exception to propagate.
4. WHEN all comparisons are complete, THE Evaluator SHALL print a summary table to stdout showing per-filing filename, F1 score, exact match result (true/false), and structural similarity score, plus a final row with the arithmetic mean of each metric across all evaluated filings.
5. THE Evaluator SHALL compute F1 score by treating each `(field_path, value)` pair in the output JSON as a predicted entity and each `(field_path, value)` pair in the golden JSON as a true entity, where `field_path` is the dot-notation path to the leaf node, array indices are included as numeric path segments, and value comparison is type-aware (string vs. number are not equal even if they represent the same quantity).
6. WHEN the average F1 score across all evaluated filings falls below 0.7, THE Evaluator SHALL exit with a non-zero return code.
7. WHEN no files are evaluated (outputs directory is empty or no golden matches exist), THE Evaluator SHALL print a summary with zero counts and exit with a non-zero return code.
