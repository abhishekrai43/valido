# Valido Agent

Desktop agent for automated folder processing with Valido.

## Features

- **Scheduled Processing**: Process folders at specific times (e.g., 6:00 PM daily)
- **Multiple Folders**: Monitor multiple folders with different rulesets
- **Auto-Download Results**: CSV results automatically saved to output folder
- **File Management**: Move processed files or delete after processing
- **Cross-Platform**: Works on Windows and macOS

## Quick Start

### For Users (Non-Technical)

1. **Download the agent**:
   - Windows: `valido-agent.exe`
   - macOS: `valido-agent` (or `valido-agent.app`)

2. **Run the agent**:
   ```bash
   # Windows (double-click or run in PowerShell)
   .\valido-agent.exe --server http://192.168.1.50:9090
   
   # macOS (Terminal)
   ./valido-agent --server http://192.168.1.50:9090
   ```

3. **Configure folders** via Valido web UI at `http://192.168.1.50:9090`
   - Go to "Automation" tab
   - Add watch folders
   - Set schedule times
   - Agent will automatically pick up configurations

4. **Let it run**:
   - Agent runs in the background
   - Processes folders on schedule
   - Saves results to output folder
   - Check `valido-agent.log` for activity

## Configuration

Agent fetches configuration from Valido server. No local config needed!

### Optional: Local Config File

Create `agent_config.json` for offline configuration:

```json
{
  "server_url": "http://192.168.1.50:9090"
}
```


## Building from Source

### Requirements

- Python 3.11+
- pip

### Steps

1. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

2. **Build executable**:
   ```powershell
   # Windows
   .\build.ps1
   # macOS/Linux
   chmod +x build.sh
   ./build.sh
   ```

3. **Output**:
   - Windows: `dist/valido-agent.exe`
   - macOS: `dist/valido-agent`

## Usage Examples

### Example 1: End-of-Day Processing

Configure via web UI:
- Input: `C:\Invoices\ToProcess\`
- Output: `C:\Invoices\Results\`
- Schedule: `18:00` (6:00 PM)
- Ruleset: Invoice Validation

Agent will:
1. Check folder at 6:00 PM daily
2. Process all PDFs found
3. Save results to output folder
4. Move PDFs to `C:\Invoices\Processed\`

### Example 2: Multiple Times Per Day

Configure via web UI:
- Schedule: `["12:00", "18:00"]` (noon and 6 PM)

Agent processes folder twice daily.

### Example 3: Network Folders

Configure via web UI:
- Input: `\\FINANCE-PC\Invoices\`
- Output: `\\FINANCE-PC\Results\`

Works with UNC paths and mapped drives!

## Logs

Agent logs activity to `valido-agent.log`:

```
2025-11-06 18:00:00 - ValidoAgent - INFO - Processing folder: Invoices (C:\Invoices\ToProcess\)
2025-11-06 18:00:01 - ValidoAgent - INFO - Found 47 PDF files to process
2025-11-06 18:00:02 - ValidoAgent - INFO - Uploading 47 files to server...
2025-11-06 18:00:10 - ValidoAgent - INFO - Task submitted: abc-123-def
2025-11-06 18:00:12 - ValidoAgent - INFO - Progress: 25% - invoice_001.pdf
2025-11-06 18:01:30 - ValidoAgent - INFO - Task completed successfully
2025-11-06 18:01:31 - ValidoAgent - INFO - Results saved: C:\Invoices\Results\results_2025-11-06_18-01-30.zip
```

## Troubleshooting

### Agent won't start

- Check if server URL is correct
- Verify network connectivity: `ping 192.168.1.50`
- Check firewall settings

### No files being processed

- Check if watch folder is enabled in web UI
- Verify schedule times are correct
- Check `valido-agent.log` for errors
- Ensure PDFs exist in input folder

### Files not moving after processing

- Check "Move processed" is enabled in web UI
- Verify processed folder path exists
- Check folder permissions

## System Requirements

- **Windows**: Windows 7 or later
- **macOS**: macOS 10.14 (Mojave) or later
- **Network**: Access to Valido server on LAN
- **Disk**: ~50MB for agent
- **RAM**: ~100MB while running

## Security

- Agent communicates with Valido server over HTTP (LAN only)
- No data sent to external servers
- All processing happens on your network
- Agent only reads/writes folders you configure

## Support

This is a self-service product. Resources:

- Documentation: See web UI help section
- Logs: Check `valido-agent.log` for debugging
- Community: (forum link if available)

**No direct support provided. Product works as-is.**

## License

See main Valido license.
