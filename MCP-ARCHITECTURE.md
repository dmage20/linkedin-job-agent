# MCP-Powered Architecture

## Overview

The agent now uses the **Playwright MCP Server** - the same technology that powers Claude Code's browser automation. This makes it significantly more robust and intelligent.

## What Changed

### Before (Direct Playwright)
```
Your App → Playwright → Browser
  ↓
Claude tries to guess CSS selectors
Brittle, breaks easily
```

### After (MCP Server)
```
Your App → MCP Client → Playwright MCP Server → Browser
  ↓
Claude uses refs from snapshots
Robust, adapts to changes
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                 Main Application                        │
│                  (src/index.js)                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              MCP Claude Agent                           │
│           (src/agent/mcpClaudeAgent.js)                 │
│                                                         │
│  Agent Loop:                                            │
│  1. Claude requests snapshot                            │
│  2. Gets accessibility tree with refs                   │
│  3. Decides which element to interact with              │
│  4. Uses ref to click/type                              │
│  5. Repeats until task complete                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           MCP Browser Tool Executor                     │
│         (src/agent/mcpBrowserTools.js)                  │
│                                                         │
│  Translates Claude's tool calls to MCP requests         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              MCP Client                                 │
│           (src/agent/mcpClient.js)                      │
│                                                         │
│  Manages connection to MCP server via stdio             │
│  Sends JSON-RPC requests                                │
│  Receives responses                                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│          Playwright MCP Server                          │
│          (@playwright/mcp package)                      │
│                                                         │
│  Running as separate process                            │
│  Creates accessibility snapshots                        │
│  Assigns refs to elements                               │
│  Executes browser actions                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│               Browser (Chromium)                        │
│          Actual browser automation                      │
└─────────────────────────────────────────────────────────┘
```

## How It Works

### 1. MCP Server Startup

When you run `npm start`, the app spawns the Playwright MCP server:

```javascript
this.mcpClient = new PlaywrightMCPClient();
await this.mcpClient.start();
// Spawns: npx @playwright/mcp@latest
```

The server runs as a separate process and communicates via **stdin/stdout** using **JSON-RPC**.

### 2. Taking Snapshots

Claude requests a snapshot to see the page:

```javascript
// Claude calls the tool
{ name: "take_snapshot" }

// MCP Client sends JSON-RPC request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "browser_snapshot"
  }
}

// MCP Server returns accessibility tree with refs
{
  "result": {
    "content": [{
      "type": "text",
      "text": "- button \"Easy Apply\" [ref=5]\n- button \"Save\" [ref=6]\n- textbox \"Phone number\" [ref=10]"
    }]
  }
}
```

### 3. Interacting with Elements

Claude uses the **ref** from the snapshot to interact:

```javascript
// Claude sees in snapshot: button "Easy Apply" [ref=5]

// Claude calls the tool
{
  name: "click",
  ref: "5",
  description: "Easy Apply button"
}

// MCP Client sends to server
{
  "method": "tools/call",
  "params": {
    "name": "browser_click",
    "arguments": {
      "element": "Easy Apply button",
      "ref": "5"
    }
  }
}

// MCP Server finds element by ref and clicks it
```

## Key Advantages

### 1. **Precise Element Targeting**
- No guessing CSS selectors
- Refs are stable and accurate
- The MCP server handles all the complexity

### 2. **Adaptive to UI Changes**
- Even if LinkedIn changes their CSS classes
- The accessibility tree and refs still work
- Claude can reason about the page structure

### 3. **Same as Claude Code**
- Uses the exact same MCP server I (Claude Code) use
- Proven, battle-tested technology
- Regular updates from the Playwright team

### 4. **Better Snapshots**
- Structured accessibility tree
- Clear element hierarchy
- All interactive elements labeled

## File Structure

```
src/
├── index.js                     # Main entry point (MCP version)
├── index.direct.js              # Backup (direct Playwright)
├── index.old.js                 # Original (scripted version)
└── agent/
    ├── mcpClient.js            # MCP server communication
    ├── mcpClaudeAgent.js       # Claude agent using MCP
    ├── mcpBrowserTools.js      # Tool definitions for MCP
    ├── claudeAgent.js          # Old agent (direct Playwright)
    └── browserTools.js         # Old tools (direct Playwright)
```

## Communication Protocol

The MCP client and server communicate using **JSON-RPC 2.0** over stdio:

### Example Exchange

**Request (stdin to MCP server):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "browser_snapshot",
    "arguments": {}
  }
}
```

**Response (stdout from MCP server):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "- button \"Easy Apply\" [ref=5]..."
    }]
  }
}
```

## Usage

### Running the Agent

Same as before:
```bash
npm start https://www.linkedin.com/jobs/view/XXXXXXXX
```

### What Happens

1. **MCP Server starts** - Spawned as child process
2. **Browser opens** - Via MCP server
3. **Manual login** - You log in manually
4. **Claude takes over** - Using MCP tools
5. **Snapshot → Ref → Action** - Precise automation
6. **Completion** - Screenshot saved

### Example Agent Flow

```
Iteration 1:
  Claude: "I'll navigate to the job URL"
  Tool: navigate(url)
  MCP: Opens URL in browser

Iteration 2:
  Claude: "Let me see what's on the page"
  Tool: take_snapshot()
  MCP: Returns accessibility tree
  Result: "button 'Easy Apply' [ref=5]"

Iteration 3:
  Claude: "I'll click the Easy Apply button"
  Tool: click(ref="5")
  MCP: Clicks element with ref=5

Iteration 4:
  Claude: "Let me see the form"
  Tool: take_snapshot()
  MCP: Returns form fields
  Result: "textbox 'Phone number' [ref=10]"

Iteration 5:
  Claude: "I'll fill the phone number"
  Tool: type_text(ref="10", text="+1234567890")
  MCP: Types into element with ref=10

...and so on
```

## Advantages Over Direct Playwright

| Feature | Direct Playwright | MCP Server |
|---------|------------------|------------|
| Element Finding | Manual strategies | Automatic refs |
| Resilience | Brittle | Robust |
| Snapshots | Custom extraction | Accessibility tree |
| Updates | Manual | Automatic (from Playwright) |
| Precision | Hit or miss | Exact targeting |
| Maintenance | High | Low |

## Debugging

### View MCP Server Logs

The MCP server outputs to stderr, which is logged to the console:
```
[MCP Server] Browser opened
[MCP Server] Snapshot requested
```

### Check Communication

The MCP client logs all requests and responses for debugging.

### Inspect Snapshots

Claude sees the raw accessibility tree. You can see what Claude sees in the console output after each snapshot.

## Troubleshooting

### "MCP Server failed to start"
- Check that `@playwright/mcp` is installed
- Ensure `npx` is available
- Check Node.js version (need 18+)

### "Could not find element with ref"
- The page may have changed after the snapshot
- Take a fresh snapshot before each action
- Check if element is actually visible

### "Timeout waiting for response"
- The MCP server may be slow
- Increase timeout in `mcpClient.js`
- Check browser isn't hanging

## Future Enhancements

- [ ] Session persistence (save browser state)
- [ ] Multiple browser contexts (parallel applications)
- [ ] Video recording of automation
- [ ] Headless mode option
- [ ] Custom MCP tools for LinkedIn-specific actions

## Comparison: How I (Claude Code) Use It

This is exactly how I use Playwright through MCP:

1. **Take snapshot** → See accessibility tree with refs
2. **Analyze** → Decide which element to interact with
3. **Use ref** → Click/type using the ref
4. **Repeat** → Continue until task complete

Your agent now works the same way! 🎉

## Cost Impact

Using MCP doesn't change API costs significantly:
- Snapshots are slightly larger (accessibility trees)
- But interactions are more efficient (fewer retries)
- Overall: similar or better token efficiency

---

**You now have the same browser automation capabilities as Claude Code!**
