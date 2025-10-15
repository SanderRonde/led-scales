# LED Control System - API Specification v1.0

## Overview

This is a comprehensive API specification for the LED Control System. The system provides both HTTP REST endpoints and Socket.IO real-time communication for controlling LED effects, managing power state, brightness, and presets.

**Base URL**: `http://localhost:5001` (configurable via `web_port` in config)

**Transport Protocols**:

-   HTTP/REST for state changes and configuration
-   Socket.IO for real-time LED updates and bidirectional communication

---

## Table of Contents

1. [HTTP REST API](#http-rest-api)
    - [Effects Management](#effects-management)
    - [State Management](#state-management)
    - [Presets Management](#presets-management)
    - [Configuration](#configuration)
    - [Static Assets](#static-assets)
2. [Socket.IO API](#socketio-api)
    - [Events from Server](#events-from-server)
    - [Connection Handling](#connection-handling)
3. [Data Models](#data-models)
4. [Authentication](#authentication)
5. [Error Handling](#error-handling)
6. [Examples](#examples)

---

## HTTP REST API

### Effects Management

#### GET /effects

Get all available effects with their parameters and current effect.

**Request:**

```http
GET /effects HTTP/1.1
Host: localhost:5001
```

**Response:** `200 OK`

```json
{
    "effect_parameters": {
        "RainbowRadialEffect": {
            "speed": {
                "type": "float",
                "description": "Speed of the rainbow animation",
                "value": 0.5
            },
            "intensity": {
                "type": "float",
                "description": "Intensity of the colors",
                "value": 1.0
            }
        },
        "SingleColorEffect": {
            "color": {
                "type": "color",
                "description": "The color to display",
                "value": {
                    "r": 255,
                    "g": 0,
                    "b": 0
                }
            }
        },
        "RandomColorHexEffect": {
            "transition_speed": {
                "type": "float",
                "description": "Speed of color transitions",
                "value": 0.3
            }
        }
    },
    "effect_names": {
        "RainbowRadialEffect": "Rainbow Radial",
        "SingleColorEffect": "Single Color",
        "RandomColorHexEffect": "Random Color Hex",
        "RainbowSpinEffect": "Rainbow Spin",
        "MultiColorRadialEffect": "Multi Color Radial"
    },
    "current_effect": "RainbowRadialEffect"
}
```

**Response Fields:**

-   `effect_parameters` (object): Map of effect class names to their parameter definitions
-   `effect_names` (object): Map of effect class names to human-readable names
-   `current_effect` (string): The currently active effect class name

---

#### POST /effects

Set the current effect and optionally update its parameters.

**Request:**

```http
POST /effects HTTP/1.1
Host: localhost:5001
Content-Type: application/json

{
  "effect_name": "SingleColorEffect",
  "parameters": {
    "color": {
      "r": 255,
      "g": 128,
      "b": 0
    }
  }
}
```

**Request Body:**

-   `effect_name` (string, required): The class name of the effect to activate
-   `parameters` (object, optional): Key-value pairs of parameter names and values

**Response:** `200 OK`

```json
{
    "success": true
}
```

**Error Responses:**

`400 Bad Request` - Missing effect name

```json
{
    "success": false,
    "error": "No effect name provided"
}
```

`404 Not Found` - Effect not found

```json
{
    "success": false,
    "error": "Effect \"InvalidEffect\" not found"
}
```

**Side Effects:**

-   Saves configuration to disk (`~/.led_config.json`)
-   Clears `active_preset_id` since effect/parameters were modified
-   Starts the effect if not already running
-   Emits `effects_update` and `state_update` Socket.IO events to all connected clients

---

### State Management

#### GET /state

Get the current power state, target power state, and brightness.

**Request:**

```http
GET /state HTTP/1.1
Host: localhost:5001
```

**Response:** `200 OK`

```json
{
    "power_state": true,
    "target_power_state": true,
    "brightness": 0.85,
    "active_preset_id": 1697123456789
}
```

**Response Fields:**

-   `power_state` (boolean): Current power state (may be transitioning)
-   `target_power_state` (boolean): Target power state after fade completes
-   `brightness` (float): Brightness level (0.0 to 1.0)
-   `active_preset_id` (number|null): ID of the currently active preset, or null if no preset is active

---

#### POST /state

Update the power state and/or brightness.

**Request:**

```http
POST /state HTTP/1.1
Host: localhost:5001
Content-Type: application/json

{
  "power_state": false,
  "brightness": 0.5
}
```

**Request Body:**

-   `power_state` (boolean, optional): Set the target power state
-   `brightness` (float, optional): Set the brightness (0.0 to 1.0)

**Response:** `200 OK`

```json
{
    "success": true,
    "power_state": true,
    "target_power_state": false,
    "brightness": 0.5,
    "active_preset_id": null
}
```

**Notes:**

-   Power state changes trigger a 300ms fade transition
-   During the fade, `power_state` and `target_power_state` will differ
-   Brightness is clamped to range [0.0, 1.0]

**Side Effects:**

-   Saves configuration to disk
-   Starts fade transition for power changes
-   Clears `active_preset_id` when brightness is modified
-   Emits `state_update` Socket.IO event to all connected clients

---

### Presets Management

#### GET /presets

Get all saved presets.

**Request:**

```http
GET /presets HTTP/1.1
Host: localhost:5001
```

**Response:** `200 OK`

```json
[
    {
        "id": 1697123456789,
        "name": "Cozy Orange",
        "effect": "SingleColorEffect",
        "brightness": 0.6,
        "parameters": {
            "color": {
                "r": 255,
                "g": 128,
                "b": 0
            }
        }
    },
    {
        "id": 1697123456790,
        "name": "Rainbow Party",
        "effect": "RainbowRadialEffect",
        "brightness": 1.0,
        "parameters": {
            "speed": 0.8
        }
    }
]
```

**Response:** Array of preset objects with:

-   `id` (number): Unique identifier (Unix timestamp in milliseconds)
-   `name` (string): User-defined preset name
-   `effect` (string): Effect class name
-   `brightness` (float): Brightness level (0.0 to 1.0)
-   `parameters` (object): Effect parameters

---

#### POST /presets

Create a new preset or update an existing one.

**Request (Create New):**

```http
POST /presets HTTP/1.1
Host: localhost:5001
Content-Type: application/json

{
  "name": "Cool Blue",
  "effect": "SingleColorEffect",
  "brightness": 0.7,
  "parameters": {
    "color": {
      "r": 0,
      "g": 100,
      "b": 255
    }
  }
}
```

**Request (Update Existing):**

```http
POST /presets HTTP/1.1
Host: localhost:5001
Content-Type: application/json

{
  "id": 1697123456789,
  "name": "Updated Name",
  "effect": "SingleColorEffect",
  "brightness": 0.8,
  "parameters": {
    "color": {
      "r": 200,
      "g": 100,
      "b": 50
    }
  }
}
```

**Request Body:**

-   `id` (number, optional): If provided, updates existing preset with this ID
-   `name` (string, required): Preset name
-   `effect` (string, required): Effect class name
-   `brightness` (float, required): Brightness level (0.0 to 1.0)
-   `parameters` (object, required): Effect parameters

**Response:** `200 OK`

```json
{
    "id": 1697123456791,
    "name": "Cool Blue",
    "effect": "SingleColorEffect",
    "brightness": 0.7,
    "parameters": {
        "color": {
            "r": 0,
            "g": 100,
            "b": 255
        }
    }
}
```

**Error Response:** `400 Bad Request`

```json
{
    "error": "Invalid preset data"
}
```

**Side Effects:**

-   Saves configuration to disk
-   Emits `presets_update` Socket.IO event to all connected clients

---

#### DELETE /presets/{preset_id}

Delete a preset by ID.

**Request:**

```http
DELETE /presets/1697123456789 HTTP/1.1
Host: localhost:5001
```

**Response:** `200 OK`

```json
{
    "success": true
}
```

**Side Effects:**

-   Saves configuration to disk
-   Emits `presets_update` Socket.IO event to all connected clients

---

#### POST /presets/apply

Apply a preset to the LED system.

**Request:**

```http
POST /presets/apply HTTP/1.1
Host: localhost:5001
Content-Type: application/json

{
  "id": 1697123456789,
  "effect": "SingleColorEffect",
  "brightness": 0.7,
  "parameters": {
    "color": {
      "r": 0,
      "g": 100,
      "b": 255
    }
  }
}
```

**Request Body:**

-   `id` (number, optional): Preset ID to set as active
-   `effect` (string, required): Effect class name
-   `brightness` (float, optional): Brightness level (0.0 to 1.0)
-   `parameters` (object, optional): Effect parameters

**Response:** `200 OK`

```json
{
    "success": true
}
```

**Error Response:** `400 Bad Request`

```json
{
    "error": "No preset data provided"
}
```

**Side Effects:**

-   Changes current effect
-   Updates effect parameters
-   Sets brightness
-   Sets `active_preset_id` to the preset's ID
-   Saves configuration to disk
-   Starts effect if not running
-   Emits `effects_update` and `state_update` Socket.IO events

---

### Configuration

#### GET /config

Get the visualizer configuration (LED layout and controller type).

**Request:**

```http
GET /config HTTP/1.1
Host: localhost:5001
```

**Response (Hexagon Layout):** `200 OK`

```json
{
  "type": "hex",
  "led_count": 488,
  "hexagons": [
    {
      "x": 0,
      "y": 1,
      "ordered_leds": [216, 217, 218, 219, 220, 248, 249, 250, 251, 252, ...]
    },
    {
      "x": 0,
      "y": 2,
      "ordered_leds": [189, 190, 191, 192, 193, 303, 304, 305, 306, ...]
    }
  ]
}
```

**Response (Scale Panel Layout):** `200 OK`

```json
{
    "type": "scale",
    "led_count": 648,
    "panels": [
        {
            "panel_index": 0,
            "x_offset": 0,
            "y_offset": 0,
            "led_positions": [
                { "index": 0, "x": 27.5, "y": 27.5 },
                { "index": 1, "x": 82.5, "y": 27.5 }
            ]
        }
    ],
    "spacing": 55,
    "panel_width": 330,
    "panel_height": 632.5
}
```

**Response Fields:**

Common:

-   `type` (string): Layout type - `"hex"` or `"scale"`
-   `led_count` (number): Total number of LEDs

Hex Layout:

-   `hexagons` (array): Array of hexagon objects
    -   `x` (number): Hexagon X position
    -   `y` (number): Hexagon Y position (may be half-integer for offset rows)
    -   `ordered_leds` (array): LED indices in this hexagon, in spiral order

Scale Layout:

-   `panels` (array): Array of panel objects
    -   `panel_index` (number): Panel index
    -   `x_offset` (number): Panel X offset in mm
    -   `y_offset` (number): Panel Y offset in mm
    -   `led_positions` (array): LED positions within panel
        -   `index` (number): Global LED index
        -   `x` (number): X position in mm
        -   `y` (number): Y position in mm
-   `spacing` (number): Spacing between LEDs in mm
-   `panel_width` (number): Panel width in mm
-   `panel_height` (number): Panel height in mm

---

### Static Assets

#### GET /

Serves the main visualizer web interface.

**Request:**

```http
GET / HTTP/1.1
Host: localhost:5001
```

**Response:** `200 OK`

```html
<!DOCTYPE html>
<html>
    <head>
        <title>LED Visualizer</title>
        ...
    </head>
    <body>
        ...
    </body>
</html>
```

---

#### GET /static/{filename}

Serves static files (JavaScript, CSS, images).

**Request:**

```http
GET /static/js/index.js HTTP/1.1
Host: localhost:5001
```

**Response:** `200 OK`

```javascript
// JavaScript content
```

**Supported File Types:**

-   `.js` - JavaScript files (MIME: `application/javascript`)
-   `.css` - CSS files (MIME: `text/css`)
-   `.html` - HTML files (MIME: `text/html`)
-   `.json` - JSON files (MIME: `application/json`)
-   `.svg` - SVG images (MIME: `image/svg+xml`)

---

## Socket.IO API

### Connection

**Endpoint:** `ws://localhost:5001/socket.io/`

**Namespace:** `/` (default namespace)

**CORS:** Allowed from all origins (`*`)

**Protocol:** Socket.IO v4 compatible

### Connection Handling

#### Event: `connect`

Emitted by client when connecting to the server.

**Server Response:**

Upon connection, the server automatically emits three events:

1. `state_update` - Current power and brightness state
2. `effects_update` - Available effects and current effect
3. `presets_update` - All saved presets

**Example Client Code:**

```javascript
import io from "socket.io-client";

const socket = io("http://localhost:5001");

socket.on("connect", () => {
    console.log("Connected to LED server");
});
```

---

### Events from Server

#### Event: `led_update`

Real-time LED color data. Emitted continuously (approx 20-200 times per second depending on configuration).

**Payload:**

```json
{
  "leds": [
    {"r": 255, "g": 0, "b": 0, "w": 0},
    {"r": 255, "g": 32, "b": 0, "w": 0},
    {"r": 255, "g": 64, "b": 0, "w": 0},
    ...
  ]
}
```

**Payload Fields:**

-   `leds` (array): Array of LED color objects in index order
    -   `r` (number): Red component (0-255)
    -   `g` (number): Green component (0-255)
    -   `b` (number): Blue component (0-255)
    -   `w` (number): White component (0-255)

**Client Handler Example:**

```javascript
socket.on("led_update", (data) => {
    // Update visualizer with new LED colors
    data.leds.forEach((color, index) => {
        updateLED(index, color);
    });
});
```

---

#### Event: `state_update`

Emitted when power state or brightness changes.

**Payload:**

```json
{
    "power_state": true,
    "target_power_state": false,
    "brightness": 0.75,
    "active_preset_id": 1697123456789
}
```

**Payload Fields:**

-   `power_state` (boolean): Current power state
-   `target_power_state` (boolean): Target power state (differs during fade)
-   `brightness` (float): Brightness level (0.0 to 1.0)
-   `active_preset_id` (number|null): ID of the currently active preset, or null if no preset is active

**Triggered By:**

-   Client connects
-   POST /state endpoint called
-   Preset applied

**Client Handler Example:**

```javascript
socket.on("state_update", (data) => {
    console.log(
        `Power: ${data.power_state}, Brightness: ${data.brightness * 100}%`
    );
    console.log(`Active preset: ${data.active_preset_id || "None"}`);
    updatePowerButton(data.power_state);
    updateBrightnessSlider(data.brightness);
    highlightActivePreset(data.active_preset_id);
});
```

---

#### Event: `effects_update`

Emitted when the current effect or available effects change.

**Payload:**

```json
{
    "effect_parameters": {
        "RainbowRadialEffect": {
            "speed": {
                "type": "float",
                "description": "Animation speed",
                "value": 0.5
            }
        },
        "SingleColorEffect": {
            "color": {
                "type": "color",
                "description": "Display color",
                "value": { "r": 255, "g": 0, "b": 0 }
            }
        }
    },
    "effect_names": {
        "RainbowRadialEffect": "Rainbow Radial",
        "SingleColorEffect": "Single Color"
    },
    "current_effect": "RainbowRadialEffect"
}
```

**Payload Fields:**

-   `effect_parameters` (object): Map of effect class names to parameter definitions
-   `effect_names` (object): Map of effect class names to display names
-   `current_effect` (string): Currently active effect class name

**Triggered By:**

-   Client connects
-   POST /effects endpoint called
-   Effect changed via preset

**Client Handler Example:**

```javascript
socket.on("effects_update", (data) => {
    console.log(`Current effect: ${data.effect_names[data.current_effect]}`);
    populateEffectDropdown(data.effect_names);
    populateParameterControls(data.effect_parameters[data.current_effect]);
});
```

---

#### Event: `presets_update`

Emitted when presets are added, modified, or deleted.

**Payload:**

```json
[
    {
        "id": 1697123456789,
        "name": "Cozy Orange",
        "effect": "SingleColorEffect",
        "brightness": 0.6,
        "parameters": {
            "color": { "r": 255, "g": 128, "b": 0 }
        }
    },
    {
        "id": 1697123456790,
        "name": "Party Mode",
        "effect": "RainbowSpinEffect",
        "brightness": 1.0,
        "parameters": {
            "speed": 0.9
        }
    }
]
```

**Payload:** Array of preset objects (see [GET /presets](#get-presets) for structure)

**Triggered By:**

-   Client connects
-   POST /presets endpoint called (create/update)
-   DELETE /presets/{id} endpoint called

**Client Handler Example:**

```javascript
socket.on("presets_update", (presets) => {
    console.log(`${presets.length} presets available`);
    renderPresetList(presets);
});
```

---

## Data Models

### Parameter Types

Parameters define configurable aspects of effects. There are four types:

#### Float Parameter

```json
{
    "type": "float",
    "description": "A floating point value",
    "value": 0.75
}
```

-   **Range:** 0.0 to 1.0 (normalized)
-   **Used for:** Speed, intensity, opacity, etc.

#### Color Parameter

```json
{
    "type": "color",
    "description": "An RGB color",
    "value": {
        "r": 255,
        "g": 128,
        "b": 64
    }
}
```

-   **Components:** r, g, b (0-255 each)
-   **Note:** White component (w) is not user-configurable

#### Enum Parameter

```json
{
    "type": "enum",
    "description": "A choice from predefined values",
    "value": "fast",
    "enum_values": ["slow", "medium", "fast"]
}
```

-   **Used for:** Mode selection, pattern types, etc.

#### Color List Parameter

```json
{
    "type": "color_list",
    "description": "A list of colors",
    "value": [
        { "r": 255, "g": 0, "b": 0 },
        { "r": 0, "g": 255, "b": 0 },
        { "r": 0, "g": 0, "b": 255 }
    ]
}
```

-   **Used for:** Multi-color effects, gradients, palettes

---

### RGBW Color Model

All LED colors use RGBW format:

```json
{
    "r": 255,
    "g": 128,
    "b": 0,
    "w": 0
}
```

-   `r` (number): Red component (0-255)
-   `g` (number): Green component (0-255)
-   `b` (number): Blue component (0-255)
-   `w` (number): White component (0-255)

**Note:** The white component is typically controlled internally by the system and not exposed in user-facing color parameters.

---

### Effect Definition

An effect is a Python class that generates LED animations. Each effect has:

-   **Class name**: e.g., `RainbowRadialEffect`
-   **Display name**: e.g., `"Rainbow Radial"`
-   **Parameters**: Configurable values (see Parameter Types)

Common effects include:

-   `RainbowRadialEffect` - Rainbow emanating from center
-   `RainbowSpinEffect` - Rotating rainbow pattern
-   `SingleColorEffect` - Static single color
-   `SingleColorRadialEffect` - Single color pulsing from center
-   `MultiColorRadialEffect` - Multiple colors pulsing from center
-   `RandomColorSingleEffect` - Random colors for all LEDs
-   `RandomColorDualEffect` - Random colors in pairs
-   `RandomColorHexEffect` - Random colors per hexagon (hex layout only)

---

## Authentication

**Current Status:** No authentication is implemented.

**Security Note:** The API is designed for local network use. If exposing to the internet, implement:

-   Authentication (API keys or OAuth)
-   HTTPS/WSS encryption
-   Rate limiting
-   Input validation

---

## Error Handling

### HTTP Error Responses

All error responses follow this format:

```json
{
    "error": "Human-readable error message",
    "success": false
}
```

**Common Status Codes:**

-   `400 Bad Request` - Invalid request data
-   `404 Not Found` - Resource not found (effect, preset, etc.)
-   `500 Internal Server Error` - Server-side error

### Socket.IO Error Handling

Socket.IO connections may fail or disconnect. Handle these events:

```javascript
socket.on("connect_error", (error) => {
    console.error("Connection failed:", error);
});

socket.on("disconnect", (reason) => {
    console.log("Disconnected:", reason);
    // Attempt reconnection
});
```

Socket.IO client will automatically attempt to reconnect on disconnection.

---

## Examples

### Example 1: Basic Client Connection

```javascript
import io from "socket.io-client";

// Connect to the server
const socket = io("http://localhost:5001");

// Listen for LED updates
socket.on("led_update", (data) => {
    console.log(`Received colors for ${data.leds.length} LEDs`);
});

// Listen for state changes
socket.on("state_update", (state) => {
    console.log(`Power: ${state.power_state}, Brightness: ${state.brightness}`);
});

// Listen for effect changes
socket.on("effects_update", (effects) => {
    console.log(`Current effect: ${effects.current_effect}`);
});
```

---

### Example 2: Change Effect with Parameters

```javascript
// Set effect to single color orange
async function setOrangeColor() {
    const response = await fetch("http://localhost:5001/effects", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            effect_name: "SingleColorEffect",
            parameters: {
                color: {
                    r: 255,
                    g: 128,
                    b: 0,
                },
            },
        }),
    });

    const result = await response.json();
    console.log("Effect applied:", result.success);
}
```

---

### Example 3: Power Control with Fade

```javascript
// Turn off LEDs (with 300ms fade)
async function powerOff() {
    const response = await fetch("http://localhost:5001/state", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            power_state: false,
        }),
    });

    const state = await response.json();
    console.log("Target power state:", state.target_power_state);

    // The actual power_state will transition over 300ms
    setTimeout(() => {
        console.log("Fade complete");
    }, 300);
}
```

---

### Example 4: Brightness Control

```javascript
// Set brightness to 50%
async function setBrightness(percent) {
    const response = await fetch("http://localhost:5001/state", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            brightness: percent / 100,
        }),
    });

    const state = await response.json();
    console.log("New brightness:", state.brightness);
}

setBrightness(50);
```

---

### Example 5: Save and Apply Preset

```javascript
// Save current state as a preset
async function savePreset(name) {
    // First, get current state
    const stateResponse = await fetch("http://localhost:5001/state");
    const state = await stateResponse.json();

    const effectsResponse = await fetch("http://localhost:5001/effects");
    const effects = await effectsResponse.json();

    // Get current effect parameters
    const currentEffectParams =
        effects.effect_parameters[effects.current_effect];

    // Extract parameter values
    const parameters = {};
    for (const [paramName, param] of Object.entries(currentEffectParams)) {
        parameters[paramName] = param.value;
    }

    // Save preset
    const saveResponse = await fetch("http://localhost:5001/presets", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            name: name,
            effect: effects.current_effect,
            brightness: state.brightness,
            parameters: parameters,
        }),
    });

    const savedPreset = await saveResponse.json();
    console.log("Preset saved:", savedPreset);
    return savedPreset;
}

// Apply a preset
async function applyPreset(preset) {
    const response = await fetch("http://localhost:5001/presets/apply", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            id: preset.id,
            effect: preset.effect,
            brightness: preset.brightness,
            parameters: preset.parameters,
        }),
    });

    const result = await response.json();
    console.log("Preset applied:", result.success);

    // The active_preset_id will now be set to preset.id
    // You'll receive a state_update event with the new active_preset_id
}

// Usage
const myPreset = await savePreset("My Favorite");
// Later...
await applyPreset(myPreset);
```

---

### Example 6: Active Preset Tracking

```javascript
// This example demonstrates how active_preset_id is tracked and cleared

// 1. Apply a preset
async function demonstrateActivePreset() {
    // Get a preset
    const presetsResponse = await fetch("http://localhost:5001/presets");
    const presets = await presetsResponse.json();
    const myPreset = presets[0]; // Use first preset

    // Apply the preset
    await fetch("http://localhost:5001/presets/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id: myPreset.id,
            effect: myPreset.effect,
            brightness: myPreset.brightness,
            parameters: myPreset.parameters,
        }),
    });

    // Check state - active_preset_id should be set
    let stateResponse = await fetch("http://localhost:5001/state");
    let state = await stateResponse.json();
    console.log(`Active preset after applying: ${state.active_preset_id}`);
    // Output: Active preset after applying: 1697123456789

    // 2. Change brightness - this will clear active_preset_id
    await fetch("http://localhost:5001/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brightness: 0.8 }),
    });

    // Check state again - active_preset_id should be null
    stateResponse = await fetch("http://localhost:5001/state");
    state = await stateResponse.json();
    console.log(
        `Active preset after brightness change: ${state.active_preset_id}`
    );
    // Output: Active preset after brightness change: null

    // 3. Apply preset again
    await fetch("http://localhost:5001/presets/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id: myPreset.id,
            effect: myPreset.effect,
            brightness: myPreset.brightness,
            parameters: myPreset.parameters,
        }),
    });

    // 4. Change effect - this will also clear active_preset_id
    await fetch("http://localhost:5001/effects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            effect_name: "RainbowRadialEffect",
            parameters: { speed: 0.5 },
        }),
    });

    // Check state - active_preset_id should be null again
    stateResponse = await fetch("http://localhost:5001/state");
    state = await stateResponse.json();
    console.log(`Active preset after effect change: ${state.active_preset_id}`);
    // Output: Active preset after effect change: null
}

// Listen for state updates via WebSocket
socket.on("state_update", (data) => {
    if (data.active_preset_id) {
        console.log(`Preset ${data.active_preset_id} is active`);
        // Highlight the active preset in UI
    } else {
        console.log("No preset is active (manual settings)");
        // Clear any preset highlighting in UI
    }
});
```

---

### Example 7: List All Effects

```javascript
async function listEffects() {
    const response = await fetch("http://localhost:5001/effects");
    const data = await response.json();

    console.log("Available Effects:");
    for (const [className, displayName] of Object.entries(data.effect_names)) {
        console.log(`- ${displayName} (${className})`);

        const params = data.effect_parameters[className];
        if (params) {
            console.log("  Parameters:");
            for (const [paramName, param] of Object.entries(params)) {
                console.log(
                    `    - ${paramName}: ${param.type} = ${JSON.stringify(
                        param.value
                    )}`
                );
            }
        }
    }
}
```

---

### Example 8: Python Client Example

```python
import requests
import socketio

# HTTP REST client
class LEDClient:
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url

    def get_state(self):
        response = requests.get(f'{self.base_url}/state')
        return response.json()

    def set_power(self, power_on):
        response = requests.post(
            f'{self.base_url}/state',
            json={'power_state': power_on}
        )
        return response.json()

    def set_brightness(self, brightness):
        response = requests.post(
            f'{self.base_url}/state',
            json={'brightness': brightness}
        )
        return response.json()

    def set_effect(self, effect_name, parameters=None):
        data = {'effect_name': effect_name}
        if parameters:
            data['parameters'] = parameters
        response = requests.post(
            f'{self.base_url}/effects',
            json=data
        )
        return response.json()

    def get_presets(self):
        response = requests.get(f'{self.base_url}/presets')
        return response.json()

# Socket.IO client
sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to LED server')

@sio.on('led_update')
def on_led_update(data):
    print(f'Received {len(data["leds"])} LED colors')

@sio.on('state_update')
def on_state_update(data):
    print(f'Power: {data["power_state"]}, Brightness: {data["brightness"]}')

# Usage
if __name__ == '__main__':
    # REST API
    client = LEDClient()
    print(client.get_state())
    client.set_effect('SingleColorEffect', {
        'color': {'r': 255, 'g': 0, 'b': 0}
    })

    # Socket.IO
    sio.connect('http://localhost:5001')
    sio.wait()
```

---

### Example 9: Retrieve LED Layout Configuration

```javascript
async function getLayoutInfo() {
    const response = await fetch("http://localhost:5001/config");
    const config = await response.json();

    console.log(`Layout type: ${config.type}`);
    console.log(`Total LEDs: ${config.led_count}`);

    if (config.type === "hex") {
        console.log(`Hexagons: ${config.hexagons.length}`);
        config.hexagons.forEach((hex, index) => {
            console.log(
                `  Hex ${index}: position (${hex.x}, ${hex.y}), ${hex.ordered_leds.length} LEDs`
            );
        });
    } else if (config.type === "scale") {
        console.log(`Panels: ${config.panels.length}`);
        console.log(
            `Panel size: ${config.panel_width}mm x ${config.panel_height}mm`
        );
    }
}
```

---

## Implementation Notes

### Configuration Persistence

All configuration is stored in a single JSON file at `~/.led_config.json`. This includes:

-   Current effect and parameters
-   Power state
-   Brightness level
-   Active preset ID
-   All saved presets

The file is automatically saved whenever:

-   Effect is changed
-   Parameters are updated
-   Power state is changed
-   Brightness is changed
-   Presets are created, updated, or deleted
-   Active preset is changed

### Active Preset Tracking

The system tracks which preset is currently active via the `active_preset_id` field:

-   **Set on preset application**: When a preset is applied via `POST /presets/apply`, the `active_preset_id` is set to the preset's ID
-   **Cleared on manual changes**: The `active_preset_id` is set to `null` when:
    -   A different effect is selected via `POST /effects`
    -   Effect parameters are modified via `POST /effects`
    -   Brightness is changed via `POST /state`
-   **Persisted**: The active preset ID is saved to `~/.led_config.json` and restored on restart
-   **Included in state**: The `active_preset_id` is included in all state responses and `state_update` Socket.IO events

This allows UI clients to highlight which preset is currently active and automatically clear the highlight when the user makes manual adjustments.

### Fade Transition

Power state changes include a 300ms fade transition:

-   **Fade duration**: 300ms (configurable via `_fade_duration` in code)
-   **During fade**: `power_state` differs from `target_power_state`
-   **After fade**: `power_state` equals `target_power_state`

The fade is implemented by gradually adjusting brightness from 0 to current brightness (fade in) or current brightness to 0 (fade out).

### Effect Loop Timing

Effects run in a continuous loop with sleep times:

-   **Mock mode**: 50ms sleep (20 FPS)
-   **Real hardware**: 5ms sleep (up to 200 FPS)

The actual FPS depends on effect complexity and hardware performance.

### Debug Mode

When started with `--debug` flag, the server prints FPS statistics every second:

```
FPS: 47.23
FPS: 48.01
FPS: 47.89
```

This is useful for performance tuning but should not be used in production.

---

## Version History

-   **v1.1** (2025) - Active Preset Tracking
    -   Added `active_preset_id` field to state responses
    -   Tracks which preset is currently active
    -   Automatically clears when manual changes are made
    -   Persists active preset across restarts
-   **v1.0** (2024) - Initial API specification
    -   HTTP REST endpoints for effects, state, presets, configuration
    -   Socket.IO real-time LED updates
    -   Support for hexagon and scale panel layouts
    -   Preset management
    -   Power control with fade transitions
    -   Brightness control

---

## Support & Contact

For issues or questions about this API:

1. Check the README.md file
2. Review the source code in `leds/leds.py`
3. Examine client examples in `leds/static/js/`

---

## License

This API specification and implementation are part of the LED Control System project.
