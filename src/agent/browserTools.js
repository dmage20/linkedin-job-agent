/**
 * Browser Tools for Claude Agent
 * Defines tools and executors for browser automation
 */

export const BROWSER_TOOLS = [
  {
    name: "take_snapshot",
    description: "Take an accessibility snapshot of the current page to see what's visible. Returns a text-based representation of the page structure with interactive elements. Use this to understand the current state of the page before taking actions.",
    input_schema: {
      type: "object",
      properties: {},
      required: []
    }
  },
  {
    name: "click",
    description: "Click on an element on the page. Provide the text content of the element you want to click (e.g., 'Easy Apply', 'Submit', 'Next'). The tool will intelligently find and click the element.",
    input_schema: {
      type: "object",
      properties: {
        text: {
          type: "string",
          description: "The visible text on the element you want to click (e.g., 'Easy Apply', 'Submit application', 'Next', 'Continue')"
        },
        description: {
          type: "string",
          description: "Human-readable description of what you're clicking for logging purposes (e.g., 'Easy Apply button', 'Submit button')"
        }
      },
      required: ["text", "description"]
    }
  },
  {
    name: "type_text",
    description: "Type text into an input field. Describe the field you want to fill (e.g., 'phone number', 'email', 'first name') and the tool will find it intelligently.",
    input_schema: {
      type: "object",
      properties: {
        fieldLabel: {
          type: "string",
          description: "The label or placeholder text of the field, or description of what field it is (e.g., 'Phone number', 'Email', 'First name', 'City')"
        },
        text: {
          type: "string",
          description: "Text to type into the field"
        },
        description: {
          type: "string",
          description: "Human-readable description of what you're doing for logging (e.g., 'entering phone number', 'filling email field')"
        }
      },
      required: ["fieldLabel", "text", "description"]
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
    description: "Select an option from a dropdown/select element",
    input_schema: {
      type: "object",
      properties: {
        selector: {
          type: "string",
          description: "CSS selector for the select element"
        },
        value: {
          type: "string",
          description: "Value or visible text of the option to select"
        },
        description: {
          type: "string",
          description: "Human-readable description of the dropdown"
        }
      },
      required: ["selector", "value", "description"]
    }
  },
  {
    name: "upload_file",
    description: "Upload a file to a file input element",
    input_schema: {
      type: "object",
      properties: {
        selector: {
          type: "string",
          description: "CSS selector for the file input element"
        },
        filePath: {
          type: "string",
          description: "Path to the file to upload (use the resume path from user profile)"
        },
        description: {
          type: "string",
          description: "Human-readable description of the file input"
        }
      },
      required: ["selector", "filePath", "description"]
    }
  },
  {
    name: "wait",
    description: "Wait for a specified number of milliseconds. Useful for waiting for page loads or animations.",
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
    description: "Scroll the page to reveal more content",
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
    description: "Press a keyboard key (e.g., 'Enter', 'Escape', 'Tab')",
    input_schema: {
      type: "object",
      properties: {
        key: {
          type: "string",
          description: "Key name (e.g., 'Enter', 'Escape', 'Tab', 'ArrowDown')"
        }
      },
      required: ["key"]
    }
  },
  {
    name: "task_complete",
    description: "Signal that the job application has been successfully submitted and the task is complete. Use this only after you've confirmed the application was submitted successfully.",
    input_schema: {
      type: "object",
      properties: {
        success: {
          type: "boolean",
          description: "Whether the application was successfully submitted"
        },
        message: {
          type: "string",
          description: "Summary message about the outcome"
        }
      },
      required: ["success", "message"]
    }
  }
];

/**
 * Execute a browser tool action
 */
export class BrowserToolExecutor {
  constructor(page, userProfile) {
    this.page = page;
    this.userProfile = userProfile;
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
          return await this.click(toolInput.text, toolInput.description);

        case 'type_text':
          return await this.typeText(toolInput.fieldLabel, toolInput.text, toolInput.description);

        case 'navigate':
          return await this.navigate(toolInput.url);

        case 'select_option':
          return await this.selectOption(toolInput.selector, toolInput.value, toolInput.description);

        case 'upload_file':
          return await this.uploadFile(toolInput.selector, toolInput.filePath, toolInput.description);

        case 'wait':
          return await this.wait(toolInput.milliseconds);

        case 'scroll':
          return await this.scroll(toolInput.direction, toolInput.amount || 500);

        case 'press_key':
          return await this.pressKey(toolInput.key);

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
    // Get page snapshot using Playwright's ariaSnapshot
    const snapshot = await this.page.ariaSnapshot();

    // Also get current URL and title
    const url = this.page.url();
    const title = await this.page.title();

    // Get all visible buttons and their text
    const buttons = await this.page.locator('button:visible, [role="button"]:visible').evaluateAll(elements =>
      elements.map(el => ({
        text: el.textContent?.trim(),
        ariaLabel: el.getAttribute('aria-label'),
        type: el.tagName
      })).filter(b => b.text || b.ariaLabel)
    );

    // Get all visible input fields
    const inputs = await this.page.locator('input:visible, textarea:visible').evaluateAll(elements =>
      elements.map(el => ({
        type: el.type || 'text',
        placeholder: el.placeholder,
        label: el.getAttribute('aria-label'),
        name: el.name,
        id: el.id
      })).filter(i => i.placeholder || i.label || i.name)
    );

    console.log(`   📸 Snapshot taken: ${title}`);
    console.log(`   Found ${buttons.length} buttons, ${inputs.length} input fields`);

    let detailedInfo = `\n=== PAGE DETAILS ===\n`;
    detailedInfo += `URL: ${url}\n`;
    detailedInfo += `Title: ${title}\n\n`;

    if (buttons.length > 0) {
      detailedInfo += `Buttons visible on page:\n`;
      buttons.slice(0, 20).forEach((btn, i) => {
        const btnText = btn.text || btn.ariaLabel;
        if (btnText) {
          detailedInfo += `  - "${btnText}"\n`;
        }
      });
      detailedInfo += `\n`;
    }

    if (inputs.length > 0) {
      detailedInfo += `Input fields visible on page:\n`;
      inputs.slice(0, 20).forEach((input, i) => {
        const fieldLabel = input.label || input.placeholder || input.name || input.id;
        if (fieldLabel) {
          detailedInfo += `  - ${input.type}: "${fieldLabel}"\n`;
        }
      });
      detailedInfo += `\n`;
    }

    detailedInfo += `=== ACCESSIBILITY TREE ===\n${snapshot}`;

    return {
      url,
      title,
      snapshot: detailedInfo,
      buttons,
      inputs,
      message: "Page snapshot captured successfully"
    };
  }

  async click(text, description) {
    // Try multiple strategies to find and click the element
    const strategies = [
      // Strategy 1: Exact text match on buttons
      () => this.page.getByRole('button', { name: text, exact: false }),
      // Strategy 2: Partial text match on buttons
      () => this.page.getByRole('button').filter({ hasText: text }),
      // Strategy 3: Any element with matching text
      () => this.page.getByText(text, { exact: false }),
      // Strategy 4: Links with matching text
      () => this.page.getByRole('link', { name: text, exact: false }),
      // Strategy 5: Generic locator with text
      () => this.page.locator(`text=${text}`),
      // Strategy 6: Button containing the text (case insensitive)
      () => this.page.locator(`button:has-text("${text}")`),
      // Strategy 7: Any clickable element with the text
      () => this.page.locator(`[role="button"]:has-text("${text}")`)
    ];

    let lastError;
    for (const strategy of strategies) {
      try {
        const element = strategy();
        // Check if element exists with short timeout
        const count = await element.count();
        if (count > 0) {
          await element.first().click({ timeout: 5000 });
          await this.page.waitForLoadState('domcontentloaded', { timeout: 5000 }).catch(() => {});
          console.log(`   ✓ Clicked: ${description}`);
          return { success: true, message: `Clicked ${description}` };
        }
      } catch (error) {
        lastError = error;
        continue;
      }
    }

    throw new Error(`Could not find clickable element with text "${text}". Last error: ${lastError?.message}`);
  }

  async typeText(fieldLabel, text, description) {
    // Try multiple strategies to find the input field
    const strategies = [
      // Strategy 1: By label text
      () => this.page.getByLabel(fieldLabel, { exact: false }),
      // Strategy 2: By placeholder text
      () => this.page.getByPlaceholder(fieldLabel, { exact: false }),
      // Strategy 3: By role with name
      () => this.page.getByRole('textbox', { name: fieldLabel, exact: false }),
      // Strategy 4: Input with matching label (case insensitive)
      () => this.page.locator(`input[aria-label*="${fieldLabel}" i]`),
      // Strategy 5: Input with matching name attribute
      () => this.page.locator(`input[name*="${fieldLabel.toLowerCase().replace(/\s+/g, '')}"]`),
      // Strategy 6: Input with matching id
      () => this.page.locator(`input[id*="${fieldLabel.toLowerCase().replace(/\s+/g, '')}"]`),
      // Strategy 7: Any input/textarea near a label with this text
      () => this.page.locator(`label:has-text("${fieldLabel}") ~ input, label:has-text("${fieldLabel}") ~ textarea`)
    ];

    let lastError;
    for (const strategy of strategies) {
      try {
        const element = strategy();
        const count = await element.count();
        if (count > 0) {
          const field = element.first();
          await field.clear().catch(() => {}); // Clear might fail on some inputs, that's OK
          await field.fill(text);
          console.log(`   ✓ Typed into: ${description}`);
          return { success: true, message: `Typed text into ${description}` };
        }
      } catch (error) {
        lastError = error;
        continue;
      }
    }

    throw new Error(`Could not find input field for "${fieldLabel}". Last error: ${lastError?.message}`);
  }

  async navigate(url) {
    await this.page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    console.log(`   ✓ Navigated to: ${url}`);
    return { success: true, message: `Navigated to ${url}` };
  }

  async selectOption(selector, value, description) {
    // Try to select by value first, then by visible text
    try {
      await this.page.locator(selector).first().selectOption({ value });
    } catch {
      await this.page.locator(selector).first().selectOption({ label: value });
    }
    console.log(`   ✓ Selected option in: ${description}`);
    return { success: true, message: `Selected option in ${description}` };
  }

  async uploadFile(selector, filePath, description) {
    // Convert relative path to absolute if needed
    const absolutePath = filePath.startsWith('/') ? filePath : `${process.cwd()}/${filePath}`;
    await this.page.locator(selector).first().setInputFiles(absolutePath);
    console.log(`   ✓ Uploaded file to: ${description}`);
    return { success: true, message: `Uploaded file to ${description}` };
  }

  async wait(milliseconds) {
    await this.page.waitForTimeout(milliseconds);
    console.log(`   ✓ Waited ${milliseconds}ms`);
    return { success: true, message: `Waited ${milliseconds}ms` };
  }

  async scroll(direction, amount) {
    const scrollAmount = direction === 'down' ? amount : -amount;
    await this.page.evaluate((pixels) => window.scrollBy(0, pixels), scrollAmount);
    console.log(`   ✓ Scrolled ${direction} ${amount}px`);
    return { success: true, message: `Scrolled ${direction}` };
  }

  async pressKey(key) {
    await this.page.keyboard.press(key);
    console.log(`   ✓ Pressed key: ${key}`);
    return { success: true, message: `Pressed ${key}` };
  }
}
