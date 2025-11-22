// Automation functionality for Valido

let watchFolders = [];
let editingWatchFolderId = null;
let autoRefreshInterval = null;
let activeJobsPollingInterval = null;  // Deprecated - replaced by WebSocket
let loadedJobRunFolders = new Set(); // Track which folders have loaded job runs
let activeJobPollers = new Map(); // Track active job polling intervals: jobId -> {taskId, intervalId}
let jobStatusWebSocket = null;  // WebSocket connection for real-time updates
let wsReconnectAttempts = 0;
let wsReconnectDelay = 1000;  // Start with 1 second
const WS_MAX_RECONNECT_DELAY = 30000;  // Max 30 seconds

// Add CSS for spinner animation
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

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
    clearWatchFolderForm(); // Clear form on initialization
    // Configure browse buttons: show local-folder browse when available; otherwise advise pasting UNC network paths
    setupBrowseButtons();
    
    // Start auto-refresh for job runs
    startAutoRefresh();
    
    // Connect WebSocket for real-time job status (replaces polling)
    connectJobStatusWebSocket();
}

//===============================
// ENTERPRISE: WebSocket Real-Time Updates
//===============================

function connectJobStatusWebSocket() {
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/job-status`;
        
        console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);
        
        jobStatusWebSocket = new WebSocket(wsUrl);
        
        jobStatusWebSocket.onopen = () => {
            console.log('✅ WebSocket connected - Real-time job updates active');
            wsReconnectAttempts = 0;
            wsReconnectDelay = 1000;  // Reset delay on successful connection
        };
        
        jobStatusWebSocket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
        
        jobStatusWebSocket.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
        };
        
        jobStatusWebSocket.onclose = () => {
            console.warn('⚠️ WebSocket disconnected - Attempting reconnection...');
            jobStatusWebSocket = null;
            
            // Exponential backoff reconnection
            wsReconnectAttempts++;
            wsReconnectDelay = Math.min(wsReconnectDelay * 2, WS_MAX_RECONNECT_DELAY);
            
            console.log(`Reconnecting in ${wsReconnectDelay/1000}s (attempt ${wsReconnectAttempts})...`);
            setTimeout(() => {
                if (document.getElementById('automationSection') && 
                    document.getElementById('automationSection').style.display !== 'none') {
                    connectJobStatusWebSocket();
                }
            }, wsReconnectDelay);
        };
        
    } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
    }
}

function handleWebSocketMessage(message) {
    console.log('📨 WebSocket message:', message);
    
    switch (message.type) {
        case 'ping':
            // Server keepalive - respond with pong
            if (jobStatusWebSocket && jobStatusWebSocket.readyState === WebSocket.OPEN) {
                jobStatusWebSocket.send(JSON.stringify({ type: 'pong' }));
            }
            break;
            
        case 'job_status':
            handleJobStatusUpdate(message);
            break;
            
        default:
            console.log('Unknown message type:', message.type);
    }
}

function handleJobStatusUpdate(message) {
    const { watch_folder_id, status, data } = message;
    
    console.log(`📊 Job status update for folder ${watch_folder_id}: ${status}`, data);
    
    switch (status) {
        case 'started':
            showJobRunningBadge(watch_folder_id, data);
            break;
            
        case 'progress':
            updateJobProgress(watch_folder_id, data);
            break;
            
        case 'completed':
            removeJobRunningBadge(watch_folder_id);
            // Refresh execution history immediately
            loadJobRuns(watch_folder_id);
            // Reload watch folders to update stats
            loadWatchFolders();
            break;
    }
}

function showJobRunningBadge(watchFolderId, data) {
    const playButton = document.querySelector(`button[onclick*="runWatchFolderNow(${watchFolderId})"]`);
    if (playButton) {
        const card = playButton.closest('.watch-folder-card');
        if (card) {
            const headerInfo = card.querySelector('.watch-folder-info');
            if (headerInfo) {
                // Remove old badge if exists
                const oldBadge = headerInfo.querySelector('.running-badge');
                if (oldBadge) oldBadge.remove();
                
                // Add new badge
                const badge = createRunningBadge({
                    watch_folder_id: watchFolderId,
                    files_found: data.files_found || 0,
                    files_processed: data.files_processed || 0
                });
                headerInfo.appendChild(badge);
            }
        }
    }
}

function updateJobProgress(watchFolderId, data) {
    const badge = document.querySelector(`.running-badge[data-folder-id="${watchFolderId}"]`);
    if (badge) {
        badge.innerHTML = `
            <div class="spinner" style="width: 12px; height: 12px; border: 2px solid #1976d2; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 0.5rem;"></div>
            Running... (${data.files_processed || 0}/${data.files_found || 0} files)
        `;
    }
}

function removeJobRunningBadge(watchFolderId) {
    const playButton = document.querySelector(`button[onclick*="runWatchFolderNow(${watchFolderId})"]`);
    if (playButton) {
        const card = playButton.closest('.watch-folder-card');
        if (card) {
            const badge = card.querySelector('.running-badge');
            if (badge) {
                badge.remove();
                console.log(`✅ Job ${watchFolderId} completed - badge removed`);
            }
        }
    }
}

function disconnectJobStatusWebSocket() {
    if (jobStatusWebSocket) {
        console.log('🔌 Disconnecting WebSocket...');
        jobStatusWebSocket.close();
        jobStatusWebSocket = null;
    }
}

// DEPRECATED: Polling replaced by WebSocket real-time updates
// Keeping for backward compatibility / fallback only
function startActiveJobsPolling() {
    console.log('⚠️ startActiveJobsPolling() is deprecated - using WebSocket instead');
    // Don't start polling - WebSocket handles this now
}

// DEPRECATED: Update logic moved to WebSocket message handler
function updateActiveJobIndicators(activeJobs) {
    console.log('⚠️ updateActiveJobIndicators() is deprecated - using WebSocket instead');
    // This function is no longer used
}

// Create running status badge
function createRunningBadge(job) {
    const badge = document.createElement('span');
    badge.className = 'running-badge';
    badge.dataset.folderId = job.watch_folder_id;  // For easy lookup during updates
    badge.style.cssText = `
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875em;
        font-weight: 600;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        color: #1976d2;
        margin-left: 0.5rem;
        animation: pulse 1.5s ease-in-out infinite;
    `;
    
    badge.innerHTML = `
        <div class="spinner" style="width: 12px; height: 12px; border: 2px solid #1976d2; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 0.5rem;"></div>
        Running... (${job.files_processed || 0}/${job.files_found || 0} files)
    `;
    
    return badge;
}

// Add pulse animation for badge
const pulseStyle = document.createElement('style');
pulseStyle.textContent = `
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
`;
document.head.appendChild(pulseStyle);

// Expose to window for app.js to call
window.initAutomation = initAutomation;

// Stop connections when leaving automation tab
window.stopAutomationPolling = function() {
    // Disconnect WebSocket
    disconnectJobStatusWebSocket();
    
    // Clear any legacy polling intervals
    if (activeJobsPollingInterval) {
        clearInterval(activeJobsPollingInterval);
        activeJobsPollingInterval = null;
    }
    
    // Clear running badges
    document.querySelectorAll('.running-badge').forEach(badge => badge.remove());
};

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
                
                <!-- Progress Bar (hidden by default) -->
                <div id="progressBar_${folder.id}" class="job-progress-bar" style="display: none; margin-top: 1rem; padding: 1rem; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 8px; border-left: 4px solid #2196f3;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <div class="spinner" style="width: 16px; height: 16px; border: 2px solid #2196f3; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
                            <span id="progressText_${folder.id}" style="font-weight: 600; color: #1976d2;">Starting job...</span>
                        </div>
                        <span id="progressPercent_${folder.id}" style="font-weight: 600; color: #1976d2;">0%</span>
                    </div>
                    <div style="background: #fff; border-radius: 4px; height: 8px; overflow: hidden;">
                        <div id="progressFill_${folder.id}" style="background: linear-gradient(90deg, #2196f3 0%, #1976d2 100%); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
                    </div>
                    <div id="progressDetails_${folder.id}" style="margin-top: 0.5rem; font-size: 0.875em; color: #1565c0;"></div>
                </div>
                
                <!-- Execution History Section -->
                <div class="execution-history" style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <h5 style="margin: 0; font-size: 1em; color: #666;">
                            Recent Executions (Last 3)
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
        setTimeout(() => {
            watchFolders.forEach(folder => {
                loadJobRuns(folder.id);
            });
        }, 100);
    }
}

// Load job runs for a specific watch folder
async function loadJobRuns(watchFolderId) {
    const container = document.getElementById(`jobRuns_${watchFolderId}`);
    if (!container) return;
    
    // Track that this folder has been loaded (for auto-refresh)
    loadedJobRunFolders.add(watchFolderId);
    
    container.innerHTML = '<div style="text-align: center; color: #999; padding: 1rem;"><small>Loading...</small></div>';
    
    try {
        const response = await fetch(`/api/v1/watch-folders/${watchFolderId}/runs`);
        const runs = await response.json();
        
        if (!runs || runs.length === 0) {
            container.innerHTML = '<div style="text-align: center; color: #999; padding: 1rem;"><small>No executions yet</small></div>';
            return;
        }
        
        // Show only last 3 executions
        const recentRuns = runs.slice(0, 3);
        
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
        // Try parsing as JSON array first (old format)
        const times = JSON.parse(scheduleJson || '[]');
        if (times.length > 0) {
            return `Daily at ${times.join(', ')}`;
        }
        return 'Not scheduled';
    } catch {
        // If JSON parse fails, treat as comma-separated string (new format)
        if (scheduleJson && scheduleJson.trim()) {
            const times = scheduleJson.split(',').map(t => t.trim()).filter(t => t);
            if (times.length > 0) {
                return `Daily at ${times.join(', ')}`;
            }
        }
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
    if ('showDirectoryPicker' in window) {
        try {
            const dirHandle = await window.showDirectoryPicker();
            const path = dirHandle.name; // Browser returns folder name only
            document.getElementById(inputId).value = path;
        } catch (error) {
        }
    } else {
        window.toast.error('Your browser does not support the directory picker. Please paste the full path manually (e.g., C:\\Folder or \\\\SERVER\\Share\\Folder)');
    }
}

// Make browseFolder available globally
window.browseFolder = browseFolder;

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
    const inputField = document.getElementById('watchFolderInput');
    
    // Check if this is a cloud source (has cloudPath data attribute)
    const inputPath = inputField.dataset.cloudPath || inputField.value.trim();
    const cloudConfig = inputField.dataset.cloudConfig ? JSON.parse(inputField.dataset.cloudConfig) : null;
    
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
        schedule_times: scheduleTimes.join(','),  // Convert array to comma-separated string
        move_processed: moveProcessed,
        processed_path: moveProcessed ? processedPath : null,
        delete_after: deleteAfter,
        enabled: true,
        cloud_config: cloudConfig  // Include cloud config if present
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
    try {
        // Show progress bar
        const progressBar = document.getElementById(`progressBar_${id}`);
        const progressText = document.getElementById(`progressText_${id}`);
        const progressPercent = document.getElementById(`progressPercent_${id}`);
        const progressFill = document.getElementById(`progressFill_${id}`);
        const progressDetails = document.getElementById(`progressDetails_${id}`);
        
        if (progressBar) {
            progressBar.style.display = 'block';
            progressText.textContent = 'Starting job...';
            progressPercent.textContent = '0%';
            progressFill.style.width = '0%';
            progressDetails.textContent = '';
        }
        
        const response = await fetch(`/api/v1/watch-folders/${id}/run`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start job');
        }
        
        const result = await response.json();
        const taskId = result.task_id;
        const filesCount = result.files_count || 0;
        
        // Update progress bar
        if (progressText) {
            progressText.textContent = `Processing ${filesCount} files...`;
            progressDetails.textContent = 'Downloading and validating PDFs';
        }
        
        // Stop any existing poller for this job
        if (activeJobPollers.has(id)) {
            clearInterval(activeJobPollers.get(id).intervalId);
        }
        
        // Start polling for progress
        const pollInterval = setInterval(async () => {
            try {
                const statusResponse = await fetch(`/api/v1/watch-folders/tasks/${taskId}`);
                if (!statusResponse.ok) return;
                
                const taskStatus = await statusResponse.json();
                
                // Update progress
                if (taskStatus.status === 'PROGRESS' && taskStatus.result) {
                    const processed = taskStatus.result.processed || 0;
                    const total = taskStatus.result.total || filesCount;
                    const percent = total > 0 ? Math.round((processed / total) * 100) : 0;
                    
                    if (progressText) progressText.textContent = `Processing ${processed}/${total} files`;
                    if (progressPercent) progressPercent.textContent = `${percent}%`;
                    if (progressFill) progressFill.style.width = `${percent}%`;
                    if (progressDetails) progressDetails.textContent = taskStatus.result.current_file || '';
                }
                
                // Job completed
                if (taskStatus.status === 'SUCCESS' || taskStatus.status === 'FAILURE' || taskStatus.status === 'REVOKED') {
                    clearInterval(pollInterval);
                    activeJobPollers.delete(id);
                    
                    if (taskStatus.status === 'SUCCESS') {
                        const total = taskStatus.result?.total || filesCount;
                        if (progressBar) {
                            progressBar.style.background = 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)';
                            progressBar.style.borderLeftColor = '#4caf50';
                        }
                        if (progressText) progressText.textContent = `✅ Completed successfully!`;
                        if (progressPercent) progressPercent.textContent = '100%';
                        if (progressFill) {
                            progressFill.style.width = '100%';
                            progressFill.style.background = 'linear-gradient(90deg, #4caf50 0%, #388e3c 100%)';
                        }
                        if (progressDetails) progressDetails.textContent = `Processed ${total} files`;
                        
                        // Hide progress bar after 3 seconds
                        setTimeout(() => {
                            if (progressBar) progressBar.style.display = 'none';
                        }, 3000);
                    } else {
                        if (progressBar) {
                            progressBar.style.background = 'linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%)';
                            progressBar.style.borderLeftColor = '#f44336';
                        }
                        if (progressText) progressText.textContent = `❌ Job failed`;
                        if (progressDetails) progressDetails.textContent = taskStatus.error || 'Check logs for details';
                        
                        // Hide progress bar after 5 seconds
                        setTimeout(() => {
                            if (progressBar) progressBar.style.display = 'none';
                        }, 5000);
                    }
                    
                    // Reload job runs
                    await loadJobRuns(id);
                }
            } catch (error) {
                console.error('Error polling task status:', error);
            }
        }, 1500); // Poll every 1.5 seconds
        
        // Store the interval ID
        activeJobPollers.set(id, { taskId, intervalId: pollInterval });
        
    } catch (error) {
        console.error('Failed to run watch folder:', error);
        showToast(error.message || 'Failed to start job', 'error');
        
        // Show error in progress bar
        const progressBar = document.getElementById(`progressBar_${id}`);
        const progressText = document.getElementById(`progressText_${id}`);
        const progressDetails = document.getElementById(`progressDetails_${id}`);
        
        if (progressBar) {
            progressBar.style.display = 'block';
            progressBar.style.background = 'linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%)';
            progressBar.style.borderLeftColor = '#f44336';
        }
        if (progressText) progressText.textContent = '❌ Failed to start job';
        if (progressDetails) progressDetails.textContent = error.message;
        
        // Hide after 5 seconds
        setTimeout(() => {
            if (progressBar) progressBar.style.display = 'none';
        }, 5000);
    }
}

// Delete watch folder
async function deleteWatchFolder(id) {
    window.toast.confirm('Are you sure you want to delete this watch folder configuration?', async () => {
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
    });
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
    // Auto-refresh removed - users can click "Refresh Now" button if needed
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

