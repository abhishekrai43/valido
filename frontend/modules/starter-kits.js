(() => {
  const STARTER_EXAMPLES = {
    invoice: {
      label: 'Invoice Demo',
      fileName: 'starter-invoice-demo.pdf',
      pdfPath: '/sample-docs/starter-invoice-demo.pdf',
      ruleset: {
        name: 'Invoice Starter',
        rules: {
          validations: {
            must_contain: { text: 'INVOICE', case_sensitive: false },
            page_count: { operator: '==', value: 1 }
          },
          fields: [
            { name: 'Invoice Number', type: 'text', strategy: 'first', lookFor: 'Invoice Number', validations: [] },
            { name: 'Invoice Date', type: 'date', strategy: 'first', lookFor: 'Invoice Date', validations: [] },
            { name: 'Customer Name', type: 'text', strategy: 'first', lookFor: 'Customer Name', validations: [] },
            { name: 'Subtotal', type: 'number', strategy: 'first', lookFor: 'Subtotal', validations: [] },
            { name: 'Tax', type: 'number', strategy: 'first', lookFor: 'Tax', validations: [] },
            { name: 'Shipping', type: 'number', strategy: 'first', lookFor: 'Shipping', validations: [] },
            { name: 'Total Amount', type: 'number', strategy: 'first', lookFor: 'Total Amount', validations: [] },
            { name: 'Balance Due', type: 'number', strategy: 'first', lookFor: 'Balance Due', validations: [] }
          ],
          calculations: [
            { name: 'Expected Total', formula: 'Subtotal + Tax + Shipping' }
          ]
        }
      }
    },
    purchaseOrder: {
      label: 'Purchase Order Demo',
      fileName: 'starter-purchase-order-demo.pdf',
      pdfPath: '/sample-docs/starter-purchase-order-demo.pdf',
      ruleset: {
        name: 'Purchase Order Starter',
        rules: {
          validations: {
            must_contain: { text: 'Approved For Fulfillment', case_sensitive: false },
            page_count: { operator: '==', value: 1 }
          },
          fields: [
            { name: 'PO Number', type: 'text', strategy: 'first', lookFor: 'PO Number', validations: [] },
            { name: 'PO Date', type: 'date', strategy: 'first', lookFor: 'PO Date', validations: [] },
            { name: 'Supplier', type: 'text', strategy: 'first', lookFor: 'Supplier', validations: [] },
            { name: 'Requested By', type: 'text', strategy: 'first', lookFor: 'Requested By', validations: [] },
            { name: 'Delivery Date', type: 'date', strategy: 'first', lookFor: 'Delivery Date', validations: [] },
            { name: 'Subtotal', type: 'number', strategy: 'first', lookFor: 'Subtotal', validations: [] },
            { name: 'Tax', type: 'number', strategy: 'first', lookFor: 'Tax', validations: [] },
            { name: 'Total Amount', type: 'number', strategy: 'first', lookFor: 'Total Amount', validations: [] }
          ],
          calculations: [
            { name: 'Expected Total', formula: 'Subtotal + Tax' }
          ]
        }
      }
    },
    vendorTax: {
      label: 'Vendor Tax Demo',
      fileName: 'starter-vendor-tax-demo.pdf',
      pdfPath: '/sample-docs/starter-vendor-tax-demo.pdf',
      ruleset: {
        name: 'Vendor Tax Starter',
        rules: {
          validations: {
            must_contain: { text: 'Certification', case_sensitive: false },
            page_count: { operator: '==', value: 1 }
          },
          fields: [
            { name: 'Business Name', type: 'text', strategy: 'first', lookFor: 'Business Name', validations: [] },
            { name: 'Federal Tax Classification', type: 'text', strategy: 'first', lookFor: 'Federal Tax Classification', validations: [] },
            { name: 'Tax ID (EIN)', type: 'text', strategy: 'first', lookFor: 'Tax ID (EIN)', validations: [] },
            { name: 'Contact Email', type: 'text', strategy: 'first', lookFor: 'Contact Email', validations: [] },
            { name: 'Business Address', type: 'text', strategy: 'first', lookFor: 'Business Address', validations: [] },
            { name: 'Certification Status', type: 'text', strategy: 'first', lookFor: 'Certification Status', validations: [] },
            { name: 'Date Signed', type: 'date', strategy: 'first', lookFor: 'Date Signed', validations: [] }
          ]
        }
      }
    }
  };

  async function fetchStarterFile(example) {
    const response = await fetch(example.pdfPath);
    if (!response.ok) {
      throw new Error(`Could not load ${example.fileName}`);
    }
    const blob = await response.blob();
    return new File([blob], example.fileName, { type: 'application/pdf' });
  }

  function updateDemoActions(example) {
    const actions = document.getElementById('starterDemoActions');
    const previewBtn = document.getElementById('previewStarterPdfBtn');
    const hint = document.getElementById('starterDemoHint');

    if (!actions || !previewBtn || !hint) {
      return;
    }

    actions.style.display = 'flex';
    previewBtn.textContent = 'Preview Current PDF';
    hint.textContent = 'Use the guided walkthrough to inspect the sample file first, then see how the starter rules were set up.';
  }

  function startStarterWalkthrough(example) {
    if (!window.ValidoTour || typeof window.ValidoTour.start !== 'function') {
      return;
    }

    try {
      if (typeof window.ValidoTour.isActive === 'function' && window.ValidoTour.isActive() && typeof window.ValidoTour.stop === 'function') {
        window.ValidoTour.stop({ dismiss: false });
      }
    } catch (error) {
      console.debug('Could not reset existing tour before starter walkthrough', error);
    }

    window.ValidoTour.start([
      {
        selector: '#filesList',
        title: `${example.label}: sample file loaded`,
        body: 'This starter demo has already loaded the sample PDF into Step 1 so you can begin with a real example instead of guessing.',
        placement: 'top'
      },
      {
        selector: '#previewStarterPdfBtn',
        title: 'First, inspect the sample PDF',
        body: 'Open the demo PDF to see the actual layout, labels, and values that the starter rules are based on.',
        placement: 'top',
        advanceOn: { event: 'click' }
      },
      {
        getTarget: () => document.getElementById('pdfCanvasWrapper') || document.getElementById('pdfViewerModal'),
        title: 'This is what the file looks like',
        body: 'Notice the repeating structure and labels. That consistency is why reusable rules work so well on this kind of document.',
        placement: 'left'
      },
      {
        getTarget: () => document.getElementById('closePdfViewerModal'),
        title: 'Close preview when you are ready',
        body: 'Once the sample makes sense visually, close the preview and move to the rules step.',
        placement: 'left',
        advanceOn: { event: 'click' }
      },
      {
        selector: '#continueToRules',
        title: 'Now go to the starter rules',
        body: 'Continue to Step 2 to see exactly which fields, checks, and calculations were preloaded for this demo.',
        placement: 'top',
        advanceOn: { event: 'click' }
      },
      {
        selector: '#rulesPreview',
        title: 'These are the prebuilt demo rules',
        body: 'The starter rules are already loaded here. They match the labels and values from the sample PDF you just inspected.',
        placement: 'top'
      },
      {
        selector: '#continueToValidate',
        title: 'Then validate the sample',
        body: 'When the rules make sense, continue to validate. After that, you can reuse the same ruleset on similar PDFs, folders, or cloud sources.',
        placement: 'top'
      }
    ]);
  }

  async function loadExample(exampleId) {
    const example = STARTER_EXAMPLES[exampleId];
    if (!example) {
      throw new Error(`Unknown starter example: ${exampleId}`);
    }
    if (!window.ValidoApp || typeof window.ValidoApp.loadFilesIntoFlow !== 'function') {
      throw new Error('Valido app helpers are not available yet');
    }

    const file = await fetchStarterFile(example);
    window.ValidoApp.showUploadSection({ step: 1, showGuide: false, forceReset: true });
    window.ValidoApp.loadFilesIntoFlow([file]);

    if (typeof window.loadRuleset === 'function') {
      window.loadRuleset(example.ruleset);
    }
    if (typeof window.buildRulesPreview === 'function') {
      window.buildRulesPreview();
    }
    updateDemoActions(example);
    const filesList = document.getElementById('filesList');
    if (filesList && typeof filesList.scrollIntoView === 'function') {
      filesList.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (window.toast && typeof window.toast.success === 'function') {
      window.toast.success(`${example.label} loaded. Follow the guided walkthrough to inspect the sample PDF and starter rules.`);
    }

    window.setTimeout(() => startStarterWalkthrough(example), 300);
  }

  function bindPreviewButton() {
    const previewBtn = document.getElementById('previewStarterPdfBtn');
    if (!previewBtn || previewBtn.dataset.bound === 'true') {
      return;
    }

    previewBtn.dataset.bound = 'true';
    previewBtn.addEventListener('click', async () => {
      if (window.pdfViewer && typeof window.pdfViewer.showPdfInWizard === 'function') {
        await window.pdfViewer.showPdfInWizard();
      }
    });
  }

  function bindButtons() {
    bindPreviewButton();
    document.querySelectorAll('[data-starter-example]').forEach((button) => {
      button.addEventListener('click', async () => {
        const exampleId = button.dataset.starterExample;
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Loading...';
        try {
          await loadExample(exampleId);
        } catch (error) {
          console.error('Failed to load starter example:', error);
          if (window.toast && typeof window.toast.error === 'function') {
            window.toast.error(error.message || 'Failed to load starter example');
          }
        } finally {
          button.disabled = false;
          button.textContent = originalText;
        }
      });
    });
  }

  window.ValidoStarterKits = {
    examples: STARTER_EXAMPLES,
    loadExample
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindButtons);
  } else {
    bindButtons();
  }
})();
