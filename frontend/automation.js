// Automation functionality for Valido

let watchFolders = [];
let editingWatchFolderId = null;
let autoRefreshInterval = null;
let loadedJobRunFolders = new Set(); // Track which folders have loaded job runs

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
    console.log('initAutomation called');
    await loadWatchFolders();
    await loadRulesetsForDropdown();
    setupEventListeners();
    clearWatchFolderForm(); // Clear form on initialization
    // Configure browse buttons: show local-folder browse when available; otherwise advise pasting UNC network paths
    setupBrowseButtons();
    
    // Start auto-refresh for job runs
    startAutoRefresh();
}

// Expose to window for app.js to call
window.initAutomation = initAutomation;

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

// Render watch folders list in the new Jobs section
function renderWatchFolders() {
    const loadingEl = document.getElementById('jobsListLoading');
    const emptyEl = document.getElementById('jobsListEmpty');
    const listEl = document.getElementById('jobsList');
    
    // Hide loading
    if (loadingEl) loadingEl.style.display = 'none';
    
    if (watchFolders.length === 0) {
        if (emptyEl) emptyEl.style.display = 'block';
        if (listEl) listEl.style.display = 'none';
        return;
    }
    
    // Show list, hide empty state
    if (emptyEl) emptyEl.style.display = 'none';
    if (listEl) {
        listEl.style.display = 'block';
        listEl.innerHTML = watchFolders.map(folder => `
            <div class="watch-folder-card" style="margin-bottom: 1.5rem; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.5rem; background: white;">
                <div class="watch-folder-header" style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                    <div class="watch-folder-info">
                        <h4 style="margin: 0 0 0.5rem 0; font-size: 1.25em; color: #333;">${folder.name}</h4>
                        <span class="watch-folder-status ${folder.enabled ? 'active' : 'inactive'}" style="display: inline-flex; align-items: center; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.875em; font-weight: 600; ${folder.enabled ? 'background: #d4edda; color: #155724;' : 'background: #f8d7da; color: #721c24;'}">
                            <span class="status-dot" style="width: 8px; height: 8px; border-radius: 50%; background: currentColor; margin-right: 0.5rem;"></span>
                            ${folder.enabled ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div class="watch-folder-actions" style="display: flex; gap: 0.5rem;">
                        <button class="btn-icon" onclick="runWatchFolderNow(${folder.id})" title="Run Now" style="padding: 0.5rem; border: 1px solid #28a745; border-radius: 4px; background: white; cursor: pointer; color: #28a745;">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                <path d="M5 4L16 10L5 16V4Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </button>
                        <button class="btn-icon" onclick="toggleWatchFolder(${folder.id})" title="${folder.enabled ? 'Disable' : 'Enable'}" style="padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer;">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                ${folder.enabled ? 
                                    '<path d="M4 10L8 14L16 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' :
                                    '<circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="2"/><path d="M3 3L17 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'}
                            </svg>
                        </button>
                        <button class="btn-icon" onclick="editWatchFolder(${folder.id})" title="Edit" style="padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer;">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                <path d="M14 2L18 6L7 17H3V13L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </button>
                        <button class="btn-icon" onclick="deleteWatchFolder(${folder.id})" title="Delete" style="padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; color: #dc3545;">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                <path d="M3 5H17M8 9V15M12 9V15M4 5L5 17C5 18 6 19 7 19H13C14 19 15 18 15 17L16 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                            </svg>
                        </button>
                    </div>
                </div>
                
                <div class="watch-folder-details" style="display: grid; gap: 0.75rem; margin-bottom: 1rem;">
                    <div class="detail-row" style="display: flex; padding: 0.5rem; background: #f8f9fa; border-radius: 4px;">
                        <span class="detail-label" style="font-weight: 600; color: #666; min-width: 140px;">Input Folder:</span>
                        <span class="detail-value" style="color: #333; word-break: break-all;">${folder.input_path}</span>
                    </div>
                    <div class="detail-row" style="display: flex; padding: 0.5rem; background: #f8f9fa; border-radius: 4px;">
                        <span class="detail-label" style="font-weight: 600; color: #666; min-width: 140px;">Output Folder:</span>
                        <span class="detail-value" style="color: #333; word-break: break-all;">${folder.output_path}</span>
                    </div>
                    <div class="detail-row" style="display: flex; padding: 0.5rem; background: #f8f9fa; border-radius: 4px;">
                        <span class="detail-label" style="font-weight: 600; color: #666; min-width: 140px;">Schedule:</span>
                        <span class="detail-value" style="color: #333;">${formatSchedule(folder.schedule_times)}</span>
                    </div>
                    <div class="detail-row" style="display: flex; padding: 0.5rem; background: #f8f9fa; border-radius: 4px;">
                        <span class="detail-label" style="font-weight: 600; color: #666; min-width: 140px;">After Processing:</span>
                        <span class="detail-value" style="color: #333;">${formatAfterProcessing(folder)}</span>
                    </div>
                </div>
                
                ${folder.last_run || (folder.files_processed_total && folder.files_processed_total > 0) ? `
                <div class="watch-folder-stats" style="display: flex; gap: 2rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;">
                    <div class="stat">
                        <span class="stat-label" style="display: block; font-size: 0.875em; color: #666; margin-bottom: 0.25rem;">Last Run</span>
                        <span class="stat-value" style="font-weight: 600; color: #333;">${folder.last_run ? new Date(folder.last_run).toLocaleString() : 'Never'}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label" style="display: block; font-size: 0.875em; color: #666; margin-bottom: 0.25rem;">Files Processed</span>
                        <span class="stat-value" style="font-weight: 600; color: #333;">${folder.files_processed_total || 0}</span>
                    </div>
                </div>
                ` : ''}
                
                <!-- Execution History Section -->
                <div class="execution-history" style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <h5 style="margin: 0; font-size: 1em; color: #666;">
                            Recent Executions
                            <span style="font-size: 0.75em; color: #999; font-weight: normal;">• Auto-refreshes</span>
                        </h5>
                        <button onclick="loadJobRuns(${folder.id})" style="padding: 0.25rem 0.75rem; font-size: 0.875em; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; color: #0066cc;">
                            Refresh Now
                        </button>
                    </div>
                    <div id="jobRuns_${folder.id}" style="min-height: 50px;">
                        <div style="text-align: center; color: #999; padding: 1rem;">
                            <small>Loading...</small>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        // After rendering, auto-load job runs for all folders
        console.log('Auto-loading job runs for', watchFolders.length, 'folders');
        setTimeout(() => {
            watchFolders.forEach(folder => {
                console.log('Loading job runs for folder:', folder.id, folder.name);
                loadJobRuns(folder.id);
            });
        }, 100);
    }
}

// Load job runs for a specific watch folder
async function loadJobRuns(watchFolderId) {
    console.log('loadJobRuns called for folder:', watchFolderId);
    const container = document.getElementById(`jobRuns_${watchFolderId}`);
    console.log('Container found:', container ? 'yes' : 'no');
    if (!container) return;
    
    // Track that this folder has been loaded (for auto-refresh)
    loadedJobRunFolders.add(watchFolderId);
    
    container.innerHTML = '<div style="text-align: center; color: #999; padding: 1rem;"><small>Loading...</small></div>';
    
    try {
        const response = await fetch(`/api/v1/watch-folders/${watchFolderId}/runs`);
        const runs = await response.json();
        console.log('Job runs loaded:', runs.length);
        
        if (!runs || runs.length === 0) {
            container.innerHTML = '<div style="text-align: center; color: #999; padding: 1rem;"><small>No executions yet</small></div>';
            return;
        }
        
        // Show only last 3 executions
        const recentRuns = runs.slice(0, 3);
        console.log('Showing recent runs:', recentRuns.length);
        
        container.innerHTML = recentRuns.map(run => {
            const statusColors = {
                'running': { bg: '#fff3cd', color: '#856404', icon: '⏳' },
                'success': { bg: '#d4edda', color: '#155724', icon: '✓' },
                'failed': { bg: '#f8d7da', color: '#721c24', icon: '✗' },
                'partial': { bg: '#ffeaa7', color: '#856404', icon: '⚠' }
            };
            const style = statusColors[run.status] || statusColors['running'];
            const duration = run.completed_at ? 
                Math.round((new Date(run.completed_at) - new Date(run.started_at)) / 1000) + 's' :
                'In progress...';
            
            return `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; margin-bottom: 0.5rem; background: ${style.bg}; border-left: 3px solid ${style.color}; border-radius: 4px;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                            <span style="font-size: 1.2em;">${style.icon}</span>
                            <span style="font-weight: 600; color: ${style.color};">${run.status.toUpperCase()}</span>
                            <span style="color: #666; font-size: 0.875em;">${new Date(run.started_at).toLocaleString()}</span>
                        </div>
                        <div style="font-size: 0.875em; color: #666;">
                            ${run.files_found} files found, ${run.files_succeeded} succeeded, ${run.files_failed} failed
                            ${run.error_message ? `<br><span style="color: ${style.color};">Error: ${run.error_message}</span>` : ''}
                        </div>
                    </div>
                    <div style="text-align: right; color: #666; font-size: 0.875em;">
                        ${duration}
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load job runs:', error);
        container.innerHTML = '<div style="text-align: center; color: #dc3545; padding: 1rem;"><small>Failed to load execution history</small></div>';
    }
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
    document.getElementById('btnSaveWatchFolder').addEventListener('click', saveWatchFolder);
    document.getElementById('btnCancelWatchFolder').addEventListener('click', cancelEditWatchFolder);
    
    // After processing radio buttons
    document.querySelectorAll('input[name="afterProcessing"]').forEach(radio => {
        radio.addEventListener('change', toggleProcessedPathField);
    });
    
    // Update server URL dynamically (for any remaining references)
    const serverUrl = document.getElementById('serverUrl');
    if (serverUrl) {
        serverUrl.textContent = `valido-agent.exe --server ${window.location.origin}`;
    }
}

// Setup browse buttons based on browser capabilities
// Setup browse buttons based on browser capabilities
function setupBrowseButtons() {
    const browseButtons = ['browseInputBtn', 'browseOutputBtn', 'browseProcessedBtn'];
    browseButtons.forEach(btnId => {
        const btn = document.getElementById(btnId);
        const inputId = btnId === 'browseInputBtn' ? 'watchFolderInput' : (btnId === 'browseOutputBtn' ? 'watchFolderOutput' : 'watchFolderProcessed');
        const input = document.getElementById(inputId);
        if (!btn || !input) return;

        // If the browser supports showDirectoryPicker we keep the Browse button visible
        if ('showDirectoryPicker' in window) {
            btn.style.display = '';
            // Helper text: instruct user to paste UNC for network shares because browser cannot return the full UNC path
            const helper = input.parentElement.querySelector('.helper') || input.parentElement.parentElement.querySelector('.helper');
            if (helper) {
                helper.textContent = 'Click Browse to choose a folder on your system, or paste a network path (\\SERVER\\Share) if the folder is on the network.';
                helper.style.color = 'var(--text-secondary, #6b7280)';
            }
        } else {
            // Hide the browse button if the browser doesn't support directory picker and instruct to paste UNC
            btn.style.display = 'none';
            const helper = input.parentElement.querySelector('.helper') || input.parentElement.parentElement.querySelector('.helper');
            if (helper) {
                helper.textContent = 'Paste the full path (e.g., C:\\Folder or \\\\SERVER\\Share\\Folder)';
                helper.style.color = 'var(--text-secondary, #6b7280)';
            }
        }
    });
}

// Browse folder function (called by inline onclick in HTML)
async function browseFolder(inputId) {
    console.log('browseFolder called with inputId:', inputId);
    if ('showDirectoryPicker' in window) {
        console.log('showDirectoryPicker is supported');
        try {
            const dirHandle = await window.showDirectoryPicker();
            const path = dirHandle.name; // Browser returns folder name only
            console.log('Selected path:', path);
            document.getElementById(inputId).value = path;
        } catch (error) {
            console.log('User cancelled directory picker or error:', error);
        }
    } else {
        console.log('showDirectoryPicker NOT supported in this browser');
        alert('Your browser does not support the directory picker. Please paste the full path manually (e.g., C:\\Folder or \\\\SERVER\\Share\\Folder)');
    }
}

// Make browseFolder available globally
window.browseFolder = browseFolder;
console.log('browseFolder function exposed to window:', typeof window.browseFolder);

// Toggle processed path field visibility
function toggleProcessedPathField() {
    const moveRadio = document.querySelector('input[name="afterProcessing"][value="move"]');
    const processedPathGroup = document.getElementById('processedPathGroup');
    processedPathGroup.style.display = moveRadio.checked ? 'block' : 'none';
}

// Clear watch folder form
function clearWatchFolderForm() {
    // Reset form title
    const titleEl = document.getElementById('watchFolderFormTitle');
    if (titleEl) titleEl.textContent = 'Create New Automation Job';
    
    document.getElementById('watchFolderName').value = '';
    document.getElementById('watchFolderInput').value = '';
    document.getElementById('watchFolderOutput').value = '';
    document.getElementById('watchFolderRuleset').value = '';
    document.getElementById('watchFolderProcessed').value = '';
    
    // Reset schedule times to one default
    const container = document.getElementById('scheduleTimes');
    container.innerHTML = `
        <div class="schedule-time-row">
            <input type="time" class="form-input schedule-time-input" value="18:00" />
            <button type="button" class="btn-icon" onclick="removeScheduleTime(this)" title="Remove">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </button>
        </div>
    `;
    
    document.querySelector('input[name="afterProcessing"][value="leave"]').checked = true;
    toggleProcessedPathField();
    
    document.getElementById('btnCancelWatchFolder').style.display = 'none';
}

// Cancel edit (clear form and reset to add mode)
function cancelEditWatchFolder() {
    editingWatchFolderId = null;
    clearWatchFolderForm();
}

// Remove schedule time row
function removeScheduleTime(button) {
    const container = document.getElementById('scheduleTimes');
    if (container.children.length > 1) {
        button.parentElement.remove();
    }
}

// Add schedule time row
function addScheduleTime() {
    const container = document.getElementById('scheduleTimes');
    const row = document.createElement('div');
    row.className = 'schedule-time-row';
    row.innerHTML = `
        <input type="time" class="form-input schedule-time-input" style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 1.1em; padding: 0.8rem;" value="18:00" />
        <button type="button" class="btn-icon" onclick="removeScheduleTime(this)" title="Remove">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        </button>
    `;
    container.appendChild(row);
}

// Save watch folder
async function saveWatchFolder() {
    const name = document.getElementById('watchFolderName').value.trim();
    const inputPath = document.getElementById('watchFolderInput').value.trim();
    const outputPath = document.getElementById('watchFolderOutput').value.trim();
    const rulesetId = parseInt(document.getElementById('watchFolderRuleset').value);
    const processedPath = document.getElementById('watchFolderProcessed').value.trim();
    
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
            cancelEditWatchFolder(); // Clear form instead of closing modal
            await loadWatchFolders();
            showToast('Watch folder saved successfully!', 'success');
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
    
    // Update form title
    const titleEl = document.getElementById('watchFolderFormTitle');
    if (titleEl) titleEl.textContent = 'Edit Automation Job';
    
    // Populate form fields
    document.getElementById('watchFolderName').value = folder.name;
    document.getElementById('watchFolderInput').value = folder.input_path;
    document.getElementById('watchFolderOutput').value = folder.output_path;
    document.getElementById('watchFolderRuleset').value = folder.ruleset_id;
    document.getElementById('watchFolderProcessed').value = folder.processed_path || '';
    
    // Set schedule times
    const times = JSON.parse(folder.schedule_times || '["18:00"]');
    const container = document.getElementById('scheduleTimes');
    container.innerHTML = times.map(time => `
        <div class="schedule-time-row">
            <input type="time" class="form-input schedule-time-input" value="${time}" />
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
    
    toggleProcessedPathField();
    
    // Show cancel button
    document.getElementById('btnCancelWatchFolder').style.display = 'inline-block';
    
    // Scroll to form
    document.querySelector('.watch-folder-form').scrollIntoView({ behavior: 'smooth' });
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

// Run watch folder job immediately
async function runWatchFolderNow(id) {
    const container = document.getElementById(`jobRuns_${id}`);
    if (container) {
        container.innerHTML = '<div style="text-align: center; color: #0066cc; padding: 1rem;"><small>Starting job...</small></div>';
    }
    
    try {
        const response = await fetch(`/api/v1/watch-folders/${id}/run`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start job');
        }
        
        const result = await response.json();
        
        // Show success message
        showToast(`Job started! Processing ${result.files_count} files...`, 'success');
        
        // Reload watch folders to update stats
        await loadWatchFolders();
        
        // Load job runs after a short delay to see the new run
        setTimeout(() => loadJobRuns(id), 2000);
    } catch (error) {
        console.error('Failed to run watch folder:', error);
        showToast(error.message || 'Failed to start job', 'error');
        if (container) {
            container.innerHTML = `<div style="text-align: center; color: #dc3545; padding: 1rem;"><small>Error: ${error.message}</small></div>`;
        }
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
                helper.textContent = 'Folder selected! Please enter the full path (e.g., C:\\' + dirHandle.name + '\\)';
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

// Auto-refresh functionality
function startAutoRefresh() {
    // Clear any existing interval
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    // Note: Initial load happens in renderWatchFolders()
    
    // Refresh every 30 seconds
    autoRefreshInterval = setInterval(() => {
        // Only refresh folders that have been loaded at least once
        loadedJobRunFolders.forEach(folderId => {
            loadJobRuns(folderId);
        });
    }, 30000); // 30 seconds
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Stop auto-refresh when leaving automation page
document.addEventListener('DOMContentLoaded', () => {
    const sections = document.querySelectorAll('section');
    const observer = new MutationObserver(() => {
        const automationSection = document.getElementById('automationSection');
        if (automationSection && automationSection.style.display === 'none') {
            stopAutoRefresh();
        }
    });
    
    sections.forEach(section => {
        observer.observe(section, { attributes: true, attributeFilter: ['style'] });
    });
});

