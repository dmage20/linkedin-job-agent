/**
 * MCP Client for Playwright MCP Server
 * Handles communication with the Playwright MCP server via stdio
 */

import { spawn } from 'child_process';
import { EventEmitter } from 'events';

export class PlaywrightMCPClient extends EventEmitter {
  constructor() {
    super();
    this.process = null;
    this.messageId = 0;
    this.pendingRequests = new Map();
    this.buffer = '';
    this.initialized = false;
  }

  /**
   * Start the Playwright MCP server
   */
  async start() {
    console.log('🚀 Starting Playwright MCP Server...');

    // Spawn the MCP server process with browser visible
    // --browser chromium = use Chromium (already installed)
    // The MCP server will open the browser automatically
    this.process = spawn('npx', [
      '@playwright/mcp@latest',
      '--browser', 'chromium'
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        PLAYWRIGHT_HEADLESS: 'false' // Ensure browser is visible
      }
    });

    // Handle stdout (responses from server)
    this.process.stdout.on('data', (data) => {
      this.handleData(data);
    });

    // Handle stderr (logs from server)
    this.process.stderr.on('data', (data) => {
      const message = data.toString().trim();
      if (message) {
        console.log(`[MCP Server] ${message}`);
      }
    });

    // Handle process exit
    this.process.on('exit', (code) => {
      console.log(`MCP Server exited with code ${code}`);
    });

    // Give the process a moment to start
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Initialize the MCP connection
    console.log('Initializing MCP connection...');
    await this.initialize();

    // List available tools to see what's available
    console.log('Listing available tools...');
    const tools = await this.listTools();
    console.log('Available MCP tools:', tools.tools?.map(t => t.name).join(', ') || 'none');

    console.log('✓ Playwright MCP Server started\n');

    // Give browser time to start
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  /**
   * Handle incoming data from the server
   */
  handleData(data) {
    this.buffer += data.toString();

    // Process complete JSON-RPC messages
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop() || ''; // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.trim()) {
        try {
          const message = JSON.parse(line);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse MCP message:', line, error);
        }
      }
    }
  }

  /**
   * Handle a parsed message from the server
   */
  handleMessage(message) {
    if (message.id !== undefined && this.pendingRequests.has(message.id)) {
      // This is a response to a request we sent
      const { resolve, reject } = this.pendingRequests.get(message.id);
      this.pendingRequests.delete(message.id);

      if (message.error) {
        reject(new Error(message.error.message || 'MCP Error'));
      } else {
        resolve(message.result);
      }
    }
  }

  /**
   * Send a JSON-RPC request to the server
   */
  async sendRequest(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++this.messageId;
      const request = {
        jsonrpc: '2.0',
        id,
        method,
        params
      };

      // Store the promise handlers
      this.pendingRequests.set(id, { resolve, reject });

      // Send the request
      this.process.stdin.write(JSON.stringify(request) + '\n');

      // Set timeout
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error(`Request timeout: ${method}`));
        }
      }, 30000); // 30 second timeout
    });
  }

  /**
   * Initialize the MCP connection
   */
  async initialize() {
    const result = await this.sendRequest('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'linkedin-job-agent',
        version: '1.0.0'
      }
    });

    this.initialized = true;
    return result;
  }

  /**
   * List available tools
   */
  async listTools() {
    return await this.sendRequest('tools/list');
  }

  /**
   * Call a tool
   */
  async callTool(name, args = {}) {
    return await this.sendRequest('tools/call', {
      name,
      arguments: args
    });
  }

  /**
   * Browser-specific methods
   */

  async navigate(url) {
    return await this.callTool('browser_navigate', { url });
  }

  async snapshot() {
    return await this.callTool('browser_snapshot');
  }

  async click(element, ref) {
    return await this.callTool('browser_click', { element, ref });
  }

  async type(element, ref, text, slowly = false, submit = false) {
    return await this.callTool('browser_type', { element, ref, text, slowly, submit });
  }

  async selectOption(element, ref, values) {
    return await this.callTool('browser_select_option', { element, ref, values });
  }

  async fill(selector, value) {
    // For simple fill operations
    return await this.callTool('browser_fill_form', {
      fields: [{ selector, value }]
    });
  }

  async waitFor(time) {
    return await this.callTool('browser_wait_for', { time: time / 1000 });
  }

  async scroll(direction, amount) {
    // MCP server doesn't have a scroll tool, we'll evaluate JavaScript
    return await this.callTool('browser_evaluate', {
      function: `() => window.scrollBy(0, ${direction === 'down' ? amount : -amount})`
    });
  }

  async pressKey(key) {
    return await this.callTool('browser_press_key', { key });
  }

  async takeScreenshot(filename) {
    return await this.callTool('browser_take_screenshot', { filename });
  }

  /**
   * Close the MCP server
   */
  async close() {
    if (this.process) {
      this.process.kill();
      this.process = null;
    }
  }
}
