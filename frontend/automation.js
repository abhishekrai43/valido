// Automation functionality for Valido

let watchFolders = [];
let editingWatchFolderId = null;

// Utility: Show toast notification
function showToast(message, type = 'error') {
    const toast = document.createElement('div');
    toast.className = type === 'error' ? 'error-toast' : 'success-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Initialize automation page
async function initAutomation() {
    await loadWatchFolders();
    await loadRulesetsForDropdown();
    setupEventListeners();
}

// Load watch folders from server
async function loadWatchFolders() {
    try {
        const response = await fetch('/api/v1/watch-folders/');
        watchFolders = await response.json();
        renderWatchFolders();
    } catch (error) {
        console.error('Failed to load watch folders:', error);
    }
}

// Load rulesets for dropdown
async function loadRulesetsForDropdown() {
    try {
        const response = await fetch('/api/v1/rulesets/');
        const rulesets = await response.json();
        
        const select = document.getElementById('watchFolderRuleset');
        select.innerHTML = '<option value="">Select a ruleset...</option>';
        
        rulesets.forEach(ruleset => {
            const option = document.createElement('option');
            option.value = ruleset.id;
            option.textContent = ruleset.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load rulesets:', error);
    }
}

// Render watch folders list
function renderWatchFolders() {
    const container = document.getElementById('watchFoldersList');
    
    if (watchFolders.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <p>No watch folders configured yet</p>
                <p class="helper">Click "Add Watch Folder" to get started</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = watchFolders.map(folder => `
        <div class="watch-folder-card">
            <div class="watch-folder-header">
                <div class="watch-folder-info">
                    <h4>${folder.name}</h4>
                    <span class="watch-folder-status ${folder.enabled ? 'active' : 'inactive'}">
                        <span class="status-dot"></span>
                        ${folder.enabled ? 'Active' : 'Inactive'}
                    </span>
                </div>
                <div class="watch-folder-actions">
                    <button class="btn-icon" onclick="toggleWatchFolder(${folder.id})" title="${folder.enabled ? 'Disable' : 'Enable'}">
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                            ${folder.enabled ? 
                                '<path d="M4 10L8 14L16 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' :
                                '<circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="2"/><path d="M3 3L17 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'}
                        </svg>
                    </button>
                    <button class="btn-icon" onclick="editWatchFolder(${folder.id})" title="Edit">
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                            <path d="M14 2L18 6L7 17H3V13L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                    <button class="btn-icon" onclick="deleteWatchFolder(${folder.id})" title="Delete">
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                            <path d="M3 5H17M8 9V15M12 9V15M4 5L5 17C5 18 6 19 7 19H13C14 19 15 18 15 17L16 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </button>
                </div>
            </div>
            
            <div class="watch-folder-details">
                <div class="detail-row">
                    <span class="detail-label">Input Folder</span>
                    <span class="detail-value">${folder.input_path}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Output Folder</span>
                    <span class="detail-value">${folder.output_path}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Schedule</span>
                    <span class="detail-value">${formatSchedule(folder.schedule_times)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">After Processing</span>
                    <span class="detail-value">${formatAfterProcessing(folder)}</span>
                </div>
            </div>
            
            ${folder.last_run || folder.files_processed_total > 0 ? `
            <div class="watch-folder-stats">
                <div class="stat">
                    <span class="stat-label">Last Run</span>
                    <span class="stat-value">${folder.last_run ? new Date(folder.last_run).toLocaleString() : 'Never'}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Files Processed</span>
                    <span class="stat-value">${folder.files_processed_total || 0}</span>
                </div>
            </div>
            ` : ''}
        </div>
    `).join('');
}

// Format schedule times
function formatSchedule(scheduleJson) {
    try {
        const times = JSON.parse(scheduleJson || '[]');
        return times.length > 0 ? times.join(', ') : 'Not scheduled';
    } catch {
        return 'Not scheduled';
    }
}

// Format after processing text
function formatAfterProcessing(folder) {
    if (folder.delete_after) return 'Delete files';
    if (folder.move_processed) return `Move to ${folder.processed_path || '...'}`;
    return 'Leave in place';
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('btnAddWatchFolder').addEventListener('click', openAddWatchFolderModal);
    document.getElementById('watchFolderModalClose').addEventListener('click', closeWatchFolderModal);
    document.getElementById('watchFolderModalCancel').addEventListener('click', closeWatchFolderModal);
    document.getElementById('watchFolderModalSave').addEventListener('click', saveWatchFolder);
    document.getElementById('btnAddScheduleTime').addEventListener('click', addScheduleTimeRow);
    
    // Update server URL dynamically
    const serverUrl = document.getElementById('serverUrl');
    if (serverUrl) {
        serverUrl.textContent = `valido-agent.exe --server ${window.location.origin}`;
    }
}

// Open add watch folder modal
async function openAddWatchFolderModal() {
    editingWatchFolderId = null;
    document.getElementById('watchFolderModalTitle').textContent = 'Add Watch Folder';
    document.getElementById('watchFolderName').value = '';
    document.getElementById('watchFolderInput').value = '';
    document.getElementById('watchFolderOutput').value = '';
    document.getElementById('watchFolderRuleset').value = '';
    document.getElementById('watchFolderProcessedPath').value = '';
    
    // Reload rulesets to ensure dropdown is populated
    await loadRulesetsForDropdown();
    
    // Reset schedule times to one default
    const container = document.getElementById('scheduleTimes');
    container.innerHTML = `
        <div class="schedule-time-row">
            <input type="time" class="modal-input schedule-time-input" value="18:00" />
            <button type="button" class="btn-icon" onclick="removeScheduleTime(this)" title="Remove">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </button>
        </div>
    `;
    
    document.querySelector('input[name="afterProcessing"][value="move"]').checked = true;
    
    document.getElementById('watchFolderModal').style.display = 'flex';
}

// Close modal
function closeWatchFolderModal() {
    document.getElementById('watchFolderModal').style.display = 'none';
}

// Add schedule time row
function addScheduleTimeRow() {
    const container = document.getElementById('scheduleTimes');
    const row = document.createElement('div');
    row.className = 'schedule-time-row';
    row.innerHTML = `
        <input type="time" class="modal-input schedule-time-input" value="18:00" />
        <button type="button" class="btn-icon" onclick="removeScheduleTime(this)" title="Remove">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        </button>
    `;
    container.appendChild(row);
}

// Remove schedule time row
function removeScheduleTime(button) {
    const container = document.getElementById('scheduleTimes');
    if (container.children.length > 1) {
        button.parentElement.remove();
    }
}

// Save watch folder
async function saveWatchFolder() {
    const name = document.getElementById('watchFolderName').value.trim();
    const inputPath = document.getElementById('watchFolderInput').value.trim();
    const outputPath = document.getElementById('watchFolderOutput').value.trim();
    const rulesetId = parseInt(document.getElementById('watchFolderRuleset').value);
    const processedPath = document.getElementById('watchFolderProcessedPath').value.trim();
    
    if (!name || !inputPath || !outputPath || !rulesetId) {
        showToast('Please fill in all required fields', 'error');
        return;
    }
    
    // Get schedule times
    const timeInputs = document.querySelectorAll('.schedule-time-input');
    const scheduleTimes = Array.from(timeInputs).map(input => input.value);
    
    // Get after processing option
    const afterProcessing = document.querySelector('input[name="afterProcessing"]:checked').value;
    const moveProcessed = afterProcessing === 'move';
    const deleteAfter = afterProcessing === 'delete';
    
    const data = {
        name,
        input_path: inputPath,
        output_path: outputPath,
        ruleset_id: rulesetId,
        schedule_times: JSON.stringify(scheduleTimes),
        move_processed: moveProcessed,
        processed_path: moveProcessed ? processedPath : null,
        delete_after: deleteAfter,
        enabled: true
    };
    
    try {
        const url = editingWatchFolderId 
            ? `/api/v1/watch-folders/${editingWatchFolderId}`
            : '/api/v1/watch-folders/';
        
        const method = editingWatchFolderId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeWatchFolderModal();
            await loadWatchFolders();
            showToast('✓ Watch folder saved successfully!', 'success');
        } else {
            const error = await response.json();
            showToast(`Failed to save: ${error.detail || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Edit watch folder
async function editWatchFolder(id) {
    const folder = watchFolders.find(f => f.id === id);
    if (!folder) return;
    
    editingWatchFolderId = id;
    document.getElementById('watchFolderModalTitle').textContent = 'Edit Watch Folder';
    document.getElementById('watchFolderName').value = folder.name;
    document.getElementById('watchFolderInput').value = folder.input_path;
    document.getElementById('watchFolderOutput').value = folder.output_path;
    document.getElementById('watchFolderRuleset').value = folder.ruleset_id;
    document.getElementById('watchFolderProcessedPath').value = folder.processed_path || '';
    
    // Set schedule times
    const times = JSON.parse(folder.schedule_times || '["18:00"]');
    const container = document.getElementById('scheduleTimes');
    container.innerHTML = times.map(time => `
        <div class="schedule-time-row">
            <input type="time" class="modal-input schedule-time-input" value="${time}" />
            <button type="button" class="btn-icon" onclick="removeScheduleTime(this)" title="Remove">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </button>
        </div>
    `).join('');
    
    // Set after processing
    if (folder.delete_after) {
        document.querySelector('input[name="afterProcessing"][value="delete"]').checked = true;
    } else if (folder.move_processed) {
        document.querySelector('input[name="afterProcessing"][value="move"]').checked = true;
    } else {
        document.querySelector('input[name="afterProcessing"][value="leave"]').checked = true;
    }
    
    document.getElementById('watchFolderModal').style.display = 'flex';
}

// Toggle watch folder enabled/disabled
async function toggleWatchFolder(id) {
    try {
        const response = await fetch(`/api/v1/watch-folders/${id}/toggle`, {
            method: 'POST'
        });
        
        if (response.ok) {
            await loadWatchFolders();
        }
    } catch (error) {
        console.error('Failed to toggle watch folder:', error);
    }
}

// Delete watch folder
async function deleteWatchFolder(id) {
    if (!confirm('Are you sure you want to delete this watch folder configuration?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/watch-folders/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            await loadWatchFolders();
        }
    } catch (error) {
        console.error('Failed to delete watch folder:', error);
    }
}

// Copy server URL to clipboard
function copyServerUrl() {
    const text = document.getElementById('serverUrl').textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    });
}

// Browse for folder (uses File System Access API when available)
async function browseFolder(inputId) {
    const input = document.getElementById(inputId);
    
    // Check if browser supports File System Access API
    if ('showDirectoryPicker' in window) {
        try {
            const dirHandle = await window.showDirectoryPicker();
            // Get the path - this is limited in browsers for security
            // We'll show the directory name, user can edit to full path
            input.value = dirHandle.name + '\\';
            input.focus();
            
            // Show helper message
            const helper = input.nextElementSibling;
            if (helper && helper.classList.contains('helper')) {
                const originalText = helper.textContent;
                helper.textContent = '✓ Folder selected! Please enter the full path (e.g., C:\\' + dirHandle.name + '\\)';
                helper.style.color = 'var(--success, #10b981)';
                setTimeout(() => {
                    helper.textContent = originalText;
                    helper.style.color = '';
                }, 5000);
            }
        } catch (err) {
            // User cancelled or error
            console.log('Folder selection cancelled or failed:', err);
        }
    } else {
        // Fallback: Create a hidden file input with directory selection
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.webkitdirectory = true;
        fileInput.style.display = 'none';
        
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                // Extract path from first file
                const firstFile = this.files[0];
                const pathParts = firstFile.webkitRelativePath.split('/');
                if (pathParts.length > 0) {
                    input.value = pathParts[0] + '\\';
                    input.focus();
                }
            }
            document.body.removeChild(fileInput);
        });
        
        document.body.appendChild(fileInput);
        fileInput.click();
    }
}

// Initialize when automation section is shown
document.addEventListener('DOMContentLoaded', () => {
    const navAutomation = document.getElementById('navAutomation');
    if (navAutomation) {
        navAutomation.addEventListener('click', () => {
            initAutomation();
        });
    }
});

