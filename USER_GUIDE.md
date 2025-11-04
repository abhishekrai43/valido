# Valido - Quick Start Guide for Users

## What is Valido?

Valido helps you validate and extract information from your PDF documents automatically. It's simple, private, and runs entirely on your device.

## Getting Started

### Step 1: Upload Your Documents

1. Click on the **"New Validation"** tab at the top
2. You'll see a large upload area
3. Either:
   - **Drag and drop** your PDF files onto the area, OR
   - **Click** the upload area to browse and select files
4. You can upload:
   - Individual PDF files
   - Multiple PDF files at once
   - ZIP files containing multiple PDFs
5. Your files will appear in a list below the upload area
6. Click the **X** button next to any file to remove it
7. When ready, click **"Continue to Rules"**

### Step 2: Choose What to Check

You have two options:

#### Option A: Simple Checks (Recommended for Beginners)

Perfect if you know exactly what you want to check:

1. **Select validation checks** by clicking the checkboxes:
   - ✍️ Check for Signature
   - 📅 Check for Date  
   - ✅ Check for both Signature AND Date

2. **Add fields to extract** (optional):
   - Type a field name like `invoice_number` or `total_amount`
   - Click **"Add Field"** or press Enter
   - Or click the blue suggestion chips for common fields
   - You can add up to 5 fields
   - Remove any field by clicking the X next to it

3. Your rules will appear in the **"Your Validation Rules"** summary box

#### Option B: Describe in Your Words (AI-Powered)

Perfect if you want to describe what you need in plain language:

1. Click the **"Describe in Your Words"** tab
2. In the text area, describe what you want to check. For example:
   > "I need to check that invoices are signed and extract the invoice number, date, total amount, and vendor name."
3. Click **"Create Rules with AI"**
4. Wait a moment while the AI understands your request
5. Your rules will be created automatically!

**Note:** You can save your rules for future use by clicking **"Save These Rules"**

### Step 3: Validate Your Documents

1. Click **"Continue to Validation"**
2. Review the summary of your documents and rules
3. Click **"Start Validation"**
4. Watch the progress as your documents are validated
5. When complete, you'll see a success message ✨
6. Click **"Download Results"** to get your validation report
7. The report contains all the information extracted from your documents

## Viewing Recent Validations

1. Click the **"Recent"** tab at the top
2. You'll see a list of your previous validations
3. For each validation, you can:
   - See when it was run and what rules were used
   - Click **"Re-run"** to repeat the same validation with new files
   - Click the **X** to remove it from history

## Tips for Best Results

### File Names
- Use clear, descriptive file names
- Avoid special characters in file names

### Validation Rules
- Be specific about field names (e.g., `invoice_number` not just `number`)
- Use underscores instead of spaces (e.g., `total_amount` not `total amount`)
- Start simple - you can always add more rules later

### AI Descriptions
- Be clear and specific about what you want to extract
- Mention both validations (e.g., "must be signed") and extractions (e.g., "extract invoice number")
- Use examples when possible

### File Size
- For best performance, validate files in batches of 10-20 at a time
- Very large files may take longer to process

## Common Scenarios

### Scenario 1: Invoice Validation
**Goal:** Extract key invoice information

**Simple Rules:**
- Add fields: `invoice_number`, `date`, `total`, `vendor`
- Check: "Contains a date"

### Scenario 2: Contract Verification
**Goal:** Ensure contracts are properly signed and dated

**Simple Rules:**
- Check: "Signature AND Date"
- Add fields: `contract_number`, `party_name`

### Scenario 3: Receipt Processing
**Goal:** Extract purchase details from receipts

**AI Description:**
> "Extract the merchant name, date, total amount, and payment method from receipts. Ensure the total is present."

## Privacy & Security

🔒 **Your documents never leave your device**
- All processing happens locally on your computer
- No documents are uploaded to external servers
- Only rule descriptions (if using AI) may be sent for processing
- Your data is safe and private

## Troubleshooting

### "Something went wrong"
- Check that your PDF files are not corrupted
- Ensure files are actual PDFs (not images renamed as PDFs)
- Try with fewer files at once

### AI Rules Not Working
- Check your internet connection
- Try rephrasing your description
- Fall back to Simple Checks mode

### Files Won't Upload
- Check file size (very large files may not upload)
- Ensure files are PDF or ZIP format
- Try refreshing the page

### Results Don't Look Right
- Review your validation rules - they may be too broad or too specific
- Try adjusting field names to match exactly what's in your documents
- Use AI mode to let the system understand your intent better

## Need Help?

If you encounter issues:
1. Check this guide for troubleshooting tips
2. Try the "Recent" tab to see if past validations work
3. Contact your system administrator
4. Visit the documentation for technical details

## Keyboard Shortcuts

- **Enter** in field input = Add field
- **Escape** = Cancel current action
- **Tab** = Navigate between inputs

## Best Practices

✅ **DO:**
- Test with a few files first before processing large batches
- Save frequently-used rules for quick access
- Use descriptive field names
- Review the summary before validating

❌ **DON'T:**
- Upload sensitive documents on shared computers
- Process files you don't have permission to view
- Use special characters in field names
- Close the browser while validation is in progress

---

**Enjoy using Valido!** 🎉

For questions or feedback, please contact your system administrator.
