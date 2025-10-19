/**
 * Browser Tools for Claude Agent using MCP Server
 * Uses Playwright MCP Server for robust browser automation
 */

export const MCP_BROWSER_TOOLS = [
  {
    name: "take_snapshot",
    description: "Take an accessibility snapshot of the current page. This returns a structured view of all interactive elements on the page with reference IDs that you can use to interact with them. ALWAYS use this before attempting to click or type to see what elements are available.",
    input_schema: {
      type: "object",
      properties: {},
      required: []
    }
  },
  {
    name: "click",
    description: "Click on an element. You must provide the exact 'ref' (reference ID) from the snapshot for the element you want to click.",
    input_schema: {
      type: "object",
      properties: {
        ref: {
          type: "string",
          description: "The reference ID from the snapshot (e.g., 'ref-5', 'ref-10')"
        },
        description: {
          type: "string",
          description: "Human-readable description of what you're clicking (e.g., 'Easy Apply button', 'Submit button')"
        }
      },
      required: ["ref", "description"]
    }
  },
  {
    name: "type_text",
    description: "Type text into an input field. You must provide the exact 'ref' from the snapshot for the field you want to fill.",
    input_schema: {
      type: "object",
      properties: {
        ref: {
          type: "string",
          description: "The reference ID from the snapshot for the input field"
        },
        text: {
          type: "string",
          description: "Text to type into the field"
        },
        description: {
          type: "string",
          description: "Human-readable description (e.g., 'entering phone number')"
        }
      },
      required: ["ref", "text", "description"]
    }
  },
  {
    name: "navigate",
    description: "Navigate to a specific URL",
    input_schema: {
      type: "object",
      properties: {
        url: {
          type: "string",
          description: "The URL to navigate to"
        }
      },
      required: ["url"]
    }
  },
  {
    name: "select_option",
    description: "Select an option from a dropdown. Provide the ref of the select element and the value to select.",
    input_schema: {
      type: "object",
      properties: {
        ref: {
          type: "string",
          description: "The reference ID of the select element"
        },
        value: {
          type: "string",
          description: "The value or text of the option to select"
        },
        description: {
          type: "string",
          description: "Human-readable description"
        }
      },
      required: ["ref", "value", "description"]
    }
  },
  {
    name: "wait",
    description: "Wait for a specified number of milliseconds",
    input_schema: {
      type: "object",
      properties: {
        milliseconds: {
          type: "number",
          description: "Number of milliseconds to wait"
        }
      },
      required: ["milliseconds"]
    }
  },
  {
    name: "scroll",
    description: "Scroll the page",
    input_schema: {
      type: "object",
      properties: {
        direction: {
          type: "string",
          enum: ["up", "down"],
          description: "Direction to scroll"
        },
        amount: {
          type: "number",
          description: "Number of pixels to scroll (default: 500)"
        }
      },
      required: ["direction"]
    }
  },
  {
    name: "press_key",
    description: "Press a keyboard key",
    input_schema: {
      type: "object",
      properties: {
        key: {
          type: "string",
          description: "Key to press (e.g., 'Enter', 'Escape', 'Tab')"
        }
      },
      required: ["key"]
    }
  },
  {
    name: "batch_fill_fields",
    description: "Fill multiple form fields in a single operation. This is much more efficient than filling fields one at a time. Use this when you've identified multiple fields that need to be filled on the current form page. You can mix different field types (textbox, combobox, checkbox, radio, slider).",
    input_schema: {
      type: "object",
      properties: {
        fields: {
          type: "array",
          description: "Array of fields to fill",
          items: {
            type: "object",
            properties: {
              name: {
                type: "string",
                description: "Human-readable field name (e.g., 'Phone number', 'Email address')"
              },
              type: {
                type: "string",
                enum: ["textbox", "checkbox", "radio", "combobox", "slider"],
                description: "Type of the field"
              },
              ref: {
                type: "string",
                description: "The reference ID from the snapshot"
              },
              value: {
                type: "string",
                description: "Value to fill in the field. For checkboxes: 'true' or 'false'. For combobox: the text of the option to select."
              }
            },
            required: ["name", "type", "ref", "value"]
          }
        }
      },
      required: ["fields"]
    }
  },
  {
    name: "task_complete",
    description: "Signal that the task is complete",
    input_schema: {
      type: "object",
      properties: {
        success: {
          type: "boolean",
          description: "Whether the task was successful"
        },
        message: {
          type: "string",
          description: "Summary message"
        }
      },
      required: ["success", "message"]
    }
  }
];

/**
 * Execute browser actions using MCP Server
 */
export class MCPBrowserToolExecutor {
  constructor(mcpClient, userProfile) {
    this.mcp = mcpClient;
    this.userProfile = userProfile;
    this.lastSnapshot = null;
  }

  async execute(toolName, toolInput) {
    console.log(`\n🔧 Executing: ${toolName}`);
    if (toolInput.description) {
      console.log(`   ${toolInput.description}`);
    }

    try {
      switch (toolName) {
        case 'take_snapshot':
          return await this.takeSnapshot();

        case 'click':
          return await this.click(toolInput.ref, toolInput.description);

        case 'type_text':
          return await this.typeText(toolInput.ref, toolInput.text, toolInput.description);

        case 'navigate':
          return await this.navigate(toolInput.url);

        case 'select_option':
          return await this.selectOption(toolInput.ref, toolInput.value, toolInput.description);

        case 'wait':
          return await this.wait(toolInput.milliseconds);

        case 'scroll':
          return await this.scroll(toolInput.direction, toolInput.amount || 500);

        case 'press_key':
          return await this.pressKey(toolInput.key);

        case 'batch_fill_fields':
          return await this.batchFillFields(toolInput.fields);

        case 'task_complete':
          return { success: toolInput.success, message: toolInput.message };

        default:
          return { error: `Unknown tool: ${toolName}` };
      }
    } catch (error) {
      console.log(`   ❌ Error: ${error.message}`);
      return { error: error.message };
    }
  }

  async takeSnapshot() {
    const result = await this.mcp.snapshot();

    // The MCP server returns a text-based accessibility snapshot
    // Parse it to extract useful information
    const snapshotText = result.content?.[0]?.text || result.snapshot || '';

    this.lastSnapshot = snapshotText;

    console.log(`   📸 Snapshot taken`);
    console.log(`   Snapshot length: ${snapshotText.length} characters`);

    // SMART TRUNCATION: Prioritize modal/dialog content
    const maxLength = 15000; // Increased from 10k to 15k for modals
    let truncatedSnapshot = snapshotText;

    // Check if there's a modal/dialog in the snapshot
    const modalKeywords = ['dialog', 'modal', 'popup', 'artdeco-modal', 'application-container'];
    const hasModal = modalKeywords.some(keyword =>
      snapshotText.toLowerCase().includes(keyword)
    );

    if (hasModal) {
      console.log(`   🔔 Modal/dialog detected in snapshot`);

      // Try to extract just the modal content
      // Look for common modal patterns
      let modalStart = -1;
      let modalEnd = -1;

      // Find the start of the modal
      for (const keyword of ['- dialog', 'heading "Sign in"', 'heading "Review"', 'heading "Contact info"']) {
        const idx = snapshotText.indexOf(keyword);
        if (idx !== -1) {
          modalStart = idx;
          break;
        }
      }

      if (modalStart !== -1) {
        // Take content from modal start
        modalEnd = Math.min(modalStart + maxLength, snapshotText.length);
        truncatedSnapshot = snapshotText.substring(modalStart, modalEnd);
        console.log(`   ✂️  Extracted modal content (${truncatedSnapshot.length} chars)`);

        if (modalEnd < snapshotText.length) {
          truncatedSnapshot += `\n\n... [Content after modal truncated. Focus on the modal/dialog above.]`;
        }
      } else {
        // Modal detected but couldn't extract - take last part (modals often at end)
        if (snapshotText.length > maxLength) {
          const startPos = Math.max(0, snapshotText.length - maxLength);
          truncatedSnapshot = `[Background content truncated...]\n\n` + snapshotText.substring(startPos);
          console.log(`   ⚠️  Modal detected but couldn't extract precisely. Showing last ${maxLength} chars (where modals usually are)`);
        }
      }
    } else if (snapshotText.length > maxLength) {
      // No modal - use standard truncation (first N chars)
      truncatedSnapshot = snapshotText.substring(0, maxLength) +
        `\n\n... [Snapshot truncated. Original length: ${snapshotText.length} chars. Scroll down if needed.]`;
      console.log(`   ⚠️  No modal detected. Truncated from ${snapshotText.length} to ${maxLength} chars`);
    }

    // Return the snapshot in a format Claude can understand
    return {
      snapshot: truncatedSnapshot,
      message: "Page snapshot captured. Look for elements with [ref=X] markers to interact with them."
    };
  }

  async click(ref, description) {
    const result = await this.mcp.click(description, ref);

    console.log(`   ✓ Clicked: ${description}`);

    // Wait a moment for the page to update
    await this.wait(1000);

    return {
      success: true,
      message: `Clicked ${description}`,
      result
    };
  }

  async typeText(ref, text, description) {
    const result = await this.mcp.type(description, ref, text);

    console.log(`   ✓ Typed into: ${description}`);

    return {
      success: true,
      message: `Typed text into ${description}`,
      result
    };
  }

  async navigate(url) {
    const result = await this.mcp.navigate(url);

    console.log(`   ✓ Navigated to: ${url}`);

    // Wait for page to load
    await this.wait(2000);

    return {
      success: true,
      message: `Navigated to ${url}`,
      result
    };
  }

  async selectOption(ref, value, description) {
    const result = await this.mcp.selectOption(description, ref, [value]);

    console.log(`   ✓ Selected option: ${value}`);

    return {
      success: true,
      message: `Selected ${value} in ${description}`,
      result
    };
  }

  async wait(milliseconds) {
    await this.mcp.waitFor(milliseconds);

    console.log(`   ✓ Waited ${milliseconds}ms`);

    return {
      success: true,
      message: `Waited ${milliseconds}ms`
    };
  }

  async scroll(direction, amount) {
    const result = await this.mcp.scroll(direction, amount);

    console.log(`   ✓ Scrolled ${direction} ${amount}px`);

    return {
      success: true,
      message: `Scrolled ${direction}`,
      result
    };
  }

  async pressKey(key) {
    const result = await this.mcp.pressKey(key);

    console.log(`   ✓ Pressed key: ${key}`);

    return {
      success: true,
      message: `Pressed ${key}`,
      result
    };
  }

  async batchFillFields(fields) {
    console.log(`   📝 Batch filling ${fields.length} fields...`);

    // Log each field for visibility
    for (const field of fields) {
      console.log(`      - ${field.name}: "${field.value}" (${field.type})`);
    }

    const result = await this.mcp.fillForm(fields);

    console.log(`   ✓ Batch filled ${fields.length} fields`);

    // Wait a moment for the page to update after all fills
    await this.wait(500);

    return {
      success: true,
      message: `Batch filled ${fields.length} fields: ${fields.map(f => f.name).join(', ')}`,
      result
    };
  }
}
