# form_analyzer.py
import anthropic
import base64
import json
import io
from pdf2image import convert_from_path
from typing import Dict, Any, Optional

# The prompt template for form analysis
FORM_ANALYSIS_PROMPT = """Analyze this PDF form and generate a complete JSON structure for my fillable PDF form generator.

**User Provided Info:**
- Form Name: {form_name}
- Category: {category}

## OUTPUT FORMAT

{{
  "{form_name_key}": {{
    "settings": {{}},
    "content": {{
      "{form_name_key}": {{
        "form_name": "{form_name_key}",
        "submission_url": "{{{{%/processors/forms/pdf_form_email}}}}",
        "subject": "Form Submission: {form_name}",
        "confirmation": "/custom/content/thank_you/thank_you.html",
        "pdf": "/custom/pdfs/{form_name_key}.pdf",
        "category": "{category}",
        "type": "intake",
        "fields": [
          // ALL FIELDS GO HERE
        ]
      }}
    }}
  }}
}}

---

## REQUIRED WRAPPER (Start of fields array)

{{"name": "pdf_download", "label": "<i class=\\"fad fa-file-download\\"></i>Download Printable Version", "type": "pdf_download"}},
{{"name": "form_container", "type": "group_start"}},
{{"name": "form_header", "label": "<h1>{form_name}</h1>", "type": "label"}},
{{"name": "form_content_container", "type": "group_start"}},

## REQUIRED CLOSING (End of fields array)

{{"label": "Submit", "type": "submit"}},
{{"type": "group_end"}},
{{"type": "group_end"}}

---

## FIELD TYPES

**Text input:** `{{"name": "field_name", "label": "Label", "email_label": "Label", "type": "text", "required": false}}`

**Date field:** `{{"name": "field_name", "label": "Label", "email_label": "Label", "type": "date", "required": false}}`

**Email:** `{{"name": "email_address", "label": "Email Address", "email_label": "Email Address", "type": "email", "required": false}}`

**Textarea (for "explain", "describe", "list" fields):** `{{"name": "field_name", "label": "Label", "email_label": "Label", "type": "textarea", "required": false}}`

**Select dropdown:** `{{"name": "field_name", "label": "Label", "email_label": "Label", "type": "select", "option": ["Option 1", "Option 2"]}}`

**Yes/No question (use radio):** `{{"name": "field_name", "label": "Question?", "email_label": "Question?", "type": "radio", "option": {{"yes": "Yes", "no": "No"}}}}`

**Multiple choice - pick ONE (use radio):** `{{"name": "field_name", "label": "Label", "email_label": "Label", "type": "radio", "option": ["Option A", "Option B", "Option C"]}}`

**Multiple choice - pick MANY (use checkbox):** `{{"name": "field_name", "label": "Label", "email_label": "Label", "type": "checkbox", "option": ["Option 1", "Option 2", "Option 3"]}}`

**Agreement checkbox:** `{{"name": "acknowledgement", "label": "", "email_label": "", "type": "checkbox", "option": {{"checked": "<p>I certify that the information provided is accurate...</p>"}}}}`

**Section header (h3):** `{{"name": "content", "label": "<h3>Section Title</h3>", "type": "label"}}`

**Subheader with instruction (h4):** `{{"name": "", "label": "<h4>Subheader <span>Instructions go in span tags</span></h4>", "type": "label"}}`

**Paragraph content:** `{{"name": "", "label": "<p>Paragraph text here...</p>", "type": "label"}}`

---

## LAYOUT GROUPS - ONLY USE THESE EXACT NAMES

**CRITICAL: You may ONLY use these exact group names. Do NOT invent new group names like "allergies_column1", "medical_conditions", etc. Unrecognized group names will be IGNORED and fields will not be grouped.**

**VALID LAYOUT GROUPS:**

1. **two_columns** - Use for lists of 2-23 similar Yes/No radio questions or checkboxes.
   {{"name": "two_columns", "type": "group_start"}}
   ... put ALL related fields here ...
   {{"type": "group_end"}}

2. **four_columns** - Use for lists of 24 or more similar Yes/No radio questions. This creates a more compact layout for long medical history sections.
   {{"name": "four_columns", "type": "group_start"}}
   ... put ALL related fields here ...
   {{"type": "group_end"}}

3. **name_details** - ONLY when form has EXACTLY 3 separate name fields: Last Name, First Name, Middle Initial
   {{"name": "*name_details", "type": "group_start"}}
   {{"name": "last_name", "label": "Last Name", ...}}
   {{"name": "first_name", "label": "First Name", ...}}
   {{"name": "middle_initial", "label": "M.I.", ...}}
   {{"type": "group_end"}}

4. **address_details** - ONLY when form needs EXACTLY 4 address fields: Street, City, State, Zip
   {{"name": "*address_details", "type": "group_start"}}
   {{"name": "mailing_address", "label": "Mailing Address", ...}}
   {{"name": "city", "label": "City", ...}}
   {{"name": "state", "label": "State", ...}}
   {{"name": "zip", "label": "Zip", ...}}
   {{"type": "group_end"}}

**Container groups (for structure only, no layout effect):**
- form_container
- form_content_container

---

## HOW TO USE COLUMN GROUPS

**Threshold rule: Count the Yes/No radio questions in a section:**
- 2-23 radio questions → use "two_columns"
- 24+ radio questions → use "four_columns" (more compact for long medical history lists)

**Note:** It's fine to include 1-2 text fields (like "Type and Date:" follow-ups) within a column group. Base your column choice on the radio button count, not strict uniformity.

**Example: PDF shows a long list of Yes/No medical questions (24+)**

If the PDF shows a medical history section with many conditions (Abnormal Bleeding, Blood Disease, Tuberculosis, Heart Disease, etc.), count them. If there are 24 or more, use four_columns:

{{"name": "four_columns", "type": "group_start"}}
{{"name": "abnormal_bleeding", "label": "Abnormal Bleeding", "email_label": "Abnormal Bleeding", "type": "radio", "option": {{"yes": "Yes", "no": "No"}}}}
{{"name": "blood_disease", "label": "Blood Disease", "email_label": "Blood Disease", "type": "radio", "option": {{"yes": "Yes", "no": "No"}}}}
... all 24+ conditions ...
{{"type": "group_end"}}

**Example: Shorter list (under 24 questions)**

For allergy sections or shorter condition lists with fewer than 24 items, use two_columns:

{{"name": "two_columns", "type": "group_start"}}
{{"name": "allergy_aspirin", "label": "Aspirin", "email_label": "Allergy - Aspirin", "type": "radio", "option": {{"yes": "Yes", "no": "No"}}}}
... up to 23 items ...
{{"type": "group_end"}}

The PDF generator will automatically arrange fields into the appropriate columns.

---

## CRITICAL RULES

1. Field naming: lowercase, underscores, no special characters
2. Every group_start MUST have a matching group_end
3. **ONLY use the exact group names listed above (two_columns, four_columns, name_details, address_details, form_container, form_content_container). Do NOT invent custom group names.**
4. "If yes, explain" patterns - A few follow-up text fields within a column group are OK, but lengthy explanations should go outside
5. Column groups should be MOSTLY similar field types - 1-2 text fields mixed in with radios is fine
6. Return ONLY valid JSON - no comments, no trailing commas
7. **COUNT Yes/No questions in a section: use "two_columns" for 2-23 items, use "four_columns" for 24+ items**

Now analyze the PDF form image(s) and generate the complete JSON structure."""


class FormAnalyzer:
    def __init__(self, api_key: str, model_name: str, inputs: Dict[str, str]):
        """Initialize with API key, model name, and user inputs."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model_name
        self.inputs = inputs

    def _pdf_to_images(self, pdf_path: str) -> list:
        """Convert PDF pages to base64-encoded images."""
        print(f"   Converting PDF to images...")
        images = convert_from_path(pdf_path, dpi=150)
        print(f"   Found {len(images)} page(s)")

        encoded_images = []
        for i, img in enumerate(images):
            # Convert to JPEG bytes
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)

            # Base64 encode
            encoded = base64.standard_b64encode(buffer.read()).decode('utf-8')
            encoded_images.append(encoded)
            print(f"   Encoded page {i + 1}")

        return encoded_images

    def _build_prompt(self) -> str:
        """Build the analysis prompt with user inputs."""
        form_name = self.inputs.get('form_name', 'Untitled Form')
        category = self.inputs.get('category', 'General')

        # Create snake_case key from form name
        form_name_key = form_name.lower().replace(' ', '_').replace('-', '_')
        # Remove any non-alphanumeric characters except underscore
        form_name_key = ''.join(c for c in form_name_key if c.isalnum() or c == '_')

        return FORM_ANALYSIS_PROMPT.format(
            form_name=form_name,
            form_name_key=form_name_key,
            category=category
        )

    def _extract_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from Claude's response."""
        # Try to find JSON in the response
        text = response_text.strip()

        # Look for JSON block
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            if end > start:
                text = text[start:end].strip()
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            if end > start:
                text = text[start:end].strip()

        # Try to find JSON object boundaries
        if text.startswith('{'):
            # Find matching closing brace
            brace_count = 0
            end_pos = 0
            for i, char in enumerate(text):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
            if end_pos > 0:
                text = text[:end_pos]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"   ⚠️  JSON parse error: {e}")
            # Try to save raw response for debugging
            with open('./output/debug_response.txt', 'w') as f:
                f.write(response_text)
            print(f"   Saved raw response to ./output/debug_response.txt")
            return None

    def analyze_pdf(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Analyze a PDF form using Claude's vision capabilities."""
        # Convert PDF to images
        images = self._pdf_to_images(pdf_path)

        # Build the message content with images
        content = []

        # Add all page images
        for i, img_data in enumerate(images):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_data
                }
            })

        # Add the prompt
        content.append({
            "type": "text",
            "text": self._build_prompt()
        })

        print(f"   Sending to Claude ({self.model})...")

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                messages=[{
                    "role": "user",
                    "content": content
                }]
            )

            # Extract response text
            response_text = response.content[0].text
            print(f"   Received response ({len(response_text)} chars)")

            # Parse JSON from response
            return self._extract_json(response_text)

        except anthropic.APIError as e:
            print(f"   ❌ API Error: {e}")
            return None
