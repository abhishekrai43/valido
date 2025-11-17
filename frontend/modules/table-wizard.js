/**
 * Table Wizard Module
 * Provides UI for selecting and previewing tables from PDFs
 */

class TableWizard {
    constructor() {
        this.currentFile = null;
        this.tableSummary = null;
        this.selectedPage = 1;
        this.selectedTableIndex = 1;
    }

    /**
     * Initialize table wizard for a file
     */
    async init(file) {
        this.currentFile = file;
        await this.loadTableSummary();
        this.render();
    }

    /**
     * Load table summary from backend
     */
    async loadTableSummary() {
        if (!this.currentFile) {
            console.error('No file loaded');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('file', this.currentFile);

            const response = await fetch('/api/v1/tables/table-summary', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.success) {
                this.tableSummary = result.summary;
            } else {
                console.error('Failed to load table summary:', result.message);
            }
        } catch (error) {
            console.error('Error loading table summary:', error);
        }
    }

    /**
     * Extract specific table
     */
    async extractTable(pageNum, tableIndex) {
        if (!this.currentFile) {
            console.error('No file loaded');
            return null;
        }

        try {
            const formData = new FormData();
            formData.append('file', this.currentFile);

            const response = await fetch(
                `/api/v1/tables/extract-table?page_num=${pageNum}&table_index=${tableIndex}`,
                {
                    method: 'POST',
                    body: formData
                }
            );

            const result = await response.json();
            if (result.success) {
                return result.table;
            } else {
                console.error('Failed to extract table:', result.message);
                return null;
            }
        } catch (error) {
            console.error('Error extracting table:', error);
            return null;
        }
    }

    /**
     * Extract all tables from a page
     */
    async extractAllTables(pageNum) {
        if (!this.currentFile) {
            console.error('No file loaded');
            return [];
        }

        try {
            const formData = new FormData();
            formData.append('file', this.currentFile);

            const response = await fetch(
                `/api/v1/tables/extract-all-tables?page_num=${pageNum}`,
                {
                    method: 'POST',
                    body: formData
                }
            );

            const result = await response.json();
            if (result.success) {
                return result.tables || [];
            } else {
                console.error('Failed to extract tables:', result.message);
                return [];
            }
        } catch (error) {
            console.error('Error extracting all tables:', error);
            return [];
        }
    }

    /**
     * Render table wizard UI
     */
    render() {
        const container = document.getElementById('table-wizard-container');
        if (!container) {
            console.error('Table wizard container not found');
            return;
        }

        if (!this.tableSummary || Object.keys(this.tableSummary).length === 0) {
            container.innerHTML = `
                <div class="table-wizard-empty">
                    <p>No tables found in this PDF</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="table-wizard">
                <div class="table-wizard-header">
                    <h3>Table Extraction</h3>
                    <p>Found ${this.getTotalTableCount()} table(s) across ${Object.keys(this.tableSummary).length} page(s)</p>
                </div>
                
                <div class="table-wizard-controls">
                    <div class="control-group">
                        <label for="page-select">Page:</label>
                        <select id="page-select" onchange="tableWizard.onPageChange(this.value)">
                            ${this.renderPageOptions()}
                        </select>
                    </div>
                    
                    <div class="control-group">
                        <label for="table-select">Table:</label>
                        <select id="table-select" onchange="tableWizard.onTableChange(this.value)">
                            ${this.renderTableOptions()}
                        </select>
                    </div>
                    
                    <button onclick="tableWizard.previewTable()" class="btn-primary">
                        Preview Table
                    </button>
                    
                    <button onclick="tableWizard.extractAllFromPage()" class="btn-secondary">
                        Extract All Tables (Page ${this.selectedPage})
                    </button>
                    
                    <button onclick="tableWizard.extractAllFromAllPages()" class="btn-primary" style="background: #059669;">
                        Extract All Tables (All Pages)
                    </button>
                </div>
                
                <div id="table-preview-container" class="table-preview-container">
                    <!-- Preview will be rendered here -->
                </div>
            </div>
        `;
    }

    /**
     * Render page options dropdown
     */
    renderPageOptions() {
        return Object.keys(this.tableSummary)
            .sort((a, b) => parseInt(a) - parseInt(b))
            .map(page => {
                const count = this.tableSummary[page];
                return `<option value="${page}" ${parseInt(page) === this.selectedPage ? 'selected' : ''}>
                    Page ${page} (${count} table${count > 1 ? 's' : ''})
                </option>`;
            })
            .join('');
    }

    /**
     * Render table options dropdown
     */
    renderTableOptions() {
        const tableCount = this.tableSummary[this.selectedPage] || 0;
        const options = [];
        
        for (let i = 1; i <= tableCount; i++) {
            options.push(`
                <option value="${i}" ${i === this.selectedTableIndex ? 'selected' : ''}>
                    Table ${i}
                </option>
            `);
        }
        
        // Add "Last Table" option
        if (tableCount > 0) {
            options.push(`
                <option value="-1" ${this.selectedTableIndex === -1 ? 'selected' : ''}>
                    Last Table (Table ${tableCount})
                </option>
            `);
        }
        
        return options.join('');
    }

    /**
     * Get total table count across all pages
     */
    getTotalTableCount() {
        return Object.values(this.tableSummary).reduce((sum, count) => sum + count, 0);
    }

    /**
     * Handle page selection change
     */
    onPageChange(pageNum) {
        this.selectedPage = parseInt(pageNum);
        this.selectedTableIndex = 1; // Reset to first table
        this.render();
    }

    /**
     * Handle table selection change
     */
    onTableChange(tableIndex) {
        this.selectedTableIndex = parseInt(tableIndex);
    }

    /**
     * Preview selected table
     */
    async previewTable() {
        const tableData = await this.extractTable(this.selectedPage, this.selectedTableIndex);
        if (tableData) {
            this.renderTablePreview(tableData);
        }
    }

    /**
     * Extract all tables from current page
     */
    async extractAllFromPage() {
        const tables = await this.extractAllTables(this.selectedPage);
        if (tables && tables.length > 0) {
            this.renderMultipleTablesPreview(tables);
        }
    }

    /**
     * Extract all tables from all pages
     */
    async extractAllFromAllPages() {
        // Dispatch event to add all-pages table extraction field
        const event = new CustomEvent('table-selected', {
            detail: {
                extractionType: 'all-pages'
            }
        });
        document.dispatchEvent(event);
        this.showToast('All tables from all pages will be extracted');
    }

    /**
     * Render single table preview
     */
    renderTablePreview(tableData) {
        const container = document.getElementById('table-preview-container');
        if (!container) return;

        container.innerHTML = `
            <div class="table-preview">
                <div class="table-preview-header">
                    <h4>Table ${tableData.table_index} from Page ${tableData.page}</h4>
                    <p>${tableData.rows} rows × ${tableData.columns} columns</p>
                </div>
                
                <div class="table-preview-data">
                    ${this.renderTableHTML(tableData)}
                </div>
                
                <div class="table-preview-actions">
                    <button onclick="tableWizard.copyTableJSON(${JSON.stringify(tableData).replace(/"/g, '&quot;')})" class="btn-secondary">
                        Copy as JSON
                    </button>
                    <button onclick="tableWizard.useInRule(${tableData.page}, ${tableData.table_index})" class="btn-primary">
                        Use in Rule
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render multiple tables preview
     */
    renderMultipleTablesPreview(tables) {
        const container = document.getElementById('table-preview-container');
        if (!container) return;

        const tablesHTML = tables.map(table => `
            <div class="table-preview-item">
                <h5>Table ${table.table_index}</h5>
                <p>${table.rows} rows × ${table.columns} columns</p>
                ${this.renderTableHTML(table)}
            </div>
        `).join('');

        container.innerHTML = `
            <div class="multiple-tables-preview">
                <div class="table-preview-header">
                    <h4>All Tables from Page ${this.selectedPage}</h4>
                    <p>Found ${tables.length} table(s)</p>
                </div>
                
                <div class="tables-grid">
                    ${tablesHTML}
                </div>
                
                <div class="table-preview-actions">
                    <button onclick="tableWizard.copyAllTablesJSON()" class="btn-secondary">
                        Copy All as JSON
                    </button>
                    <button onclick="tableWizard.useAllInRule(${this.selectedPage})" class="btn-primary">
                        Use All in Rule
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render table data as HTML table
     */
    renderTableHTML(tableData) {
        if (!tableData.raw || tableData.raw.length === 0) {
            return '<p>No table data</p>';
        }

        const rows = tableData.raw.map((row, idx) => {
            const tag = idx === 0 ? 'th' : 'td';
            const cells = row.map(cell => `<${tag}>${this.escapeHTML(cell)}</${tag}>`).join('');
            return `<tr>${cells}</tr>`;
        }).join('');

        return `<table class="preview-table">${rows}</table>`;
    }

    /**
     * Escape HTML special characters
     */
    escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Copy table data as JSON to clipboard
     */
    async copyTableJSON(tableData) {
        try {
            await navigator.clipboard.writeText(JSON.stringify(tableData, null, 2));
            this.showToast('Table data copied to clipboard');
        } catch (error) {
            console.error('Failed to copy:', error);
            this.showToast('Failed to copy to clipboard', 'error');
        }
    }

    /**
     * Copy all tables as JSON to clipboard
     */
    async copyAllTablesJSON() {
        try {
            const tables = await this.extractAllTables(this.selectedPage);
            await navigator.clipboard.writeText(JSON.stringify(tables, null, 2));
            this.showToast('All tables copied to clipboard');
        } catch (error) {
            console.error('Failed to copy:', error);
            this.showToast('Failed to copy to clipboard', 'error');
        }
    }

    /**
     * Use selected table in rule builder
     */
    useInRule(pageNum, tableIndex) {
        // Dispatch custom event for rule builder to listen to
        const event = new CustomEvent('table-selected', {
            detail: {
                page: pageNum,
                tableIndex: tableIndex,
                extractionType: 'single'
            }
        });
        document.dispatchEvent(event);
        this.showToast('Table selection ready for rule builder');
    }

    /**
     * Use all tables from page in rule builder
     */
    useAllInRule(pageNum) {
        const event = new CustomEvent('table-selected', {
            detail: {
                page: pageNum,
                extractionType: 'all'
            }
        });
        document.dispatchEvent(event);
        this.showToast('All tables selection ready for rule builder');
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'success') {
        // Check if toast module exists
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else {
        }
    }
}

// Global instance
const tableWizard = new TableWizard();
window.tableWizard = tableWizard;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TableWizard;
}
