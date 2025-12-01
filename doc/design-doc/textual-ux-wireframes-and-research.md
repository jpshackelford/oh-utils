# Textual Conversation Manager: UX Wireframes and Research

## 1. Key Use Cases Analysis

Based on user feedback, we have four primary use cases:

1. **Conversation Display** - List conversations with full details, smart polling
2. **Conversation Details** - Select conversation to see detailed information
3. **Monitoring Active Conversations** - Real-time view of running conversations with activity feed
4. **Start New Conversation** - Quick conversation creation with prompt

## 2. WebSocket API Research

### 2.1 Current Knowledge

From the OpenHands WebSocket documentation, we know:

**Connection**: Uses Socket.IO with query parameters:
- `conversation_id`: Target conversation
- `latest_event_id`: For event synchronization (-1 for new)
- `providers_set`: Optional provider configuration

**Event Structure**:
```typescript
interface OpenHandsEvent {
  id: string;           // Unique event ID
  source: string;       // "user" or "agent"
  timestamp: string;    // ISO timestamp
  message?: string;     // For message events
  type?: string;        // Event type (e.g., "message")
  action?: string;      // Action type (e.g., "run", "edit", "write")
  args?: any;           // Action arguments
  result?: any;         // Action result
}
```

**Known Action Types**:
- `run` - Command execution
- `edit` - File editing
- `write` - File writing
- `browse` - Browser actions
- `message` - User/agent messages

### 2.2 Research Needed

**Priority 1: Action Types and Tool Calls**
- [ ] Complete list of action types available
- [ ] Tool call event structure and content
- [ ] File operation details (paths, operation types)
- [ ] Shell command execution events
- [ ] Browser interaction events

**Priority 2: Agent State Events**
- [ ] "Thinking" or reasoning step events
- [ ] Agent status changes (active, waiting, idle)
- [ ] Error and exception events
- [ ] Task completion/failure events

**Priority 3: Conversation State**
- [ ] Conversation status change events
- [ ] Runtime startup/shutdown events
- [ ] Session management events

### 2.3 Research Plan

1. **Set up WebSocket monitoring** on active conversations
2. **Capture event samples** during typical agent workflows
3. **Document event patterns** for different tool usage
4. **Identify brief status indicators** suitable for monitoring view

## 3. Wireframes

### 3.1 Main Conversation List View (Full Width)

```
┌─ OpenHands Conversation Manager ─────────────────────────────────────────────────────────────────┐
│ 🔄 Auto-refresh: 2m │ 📡 Connected │ 🎯 Active: 3 │ ⏸️  Waiting: 1 │ 🔍 Search │ ➕ New │ ⚙️  Settings │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ #  │ Status │ ID       │ Runtime ID    │ Title                           │ Last Activity    │ Actions │
├────┼────────┼──────────┼───────────────┼─────────────────────────────────┼──────────────────┼─────────┤
│ 1  │ 🟢 RUN │ a1b2c3d4 │ work-1-xyz123 │ Build chat application          │ 2m ago: run cmd  │ [View]  │
│ 2  │ ⏸️  WAIT│ e5f6g7h8 │ work-2-abc456 │ API server development          │ 5m ago: waiting  │ [Send]  │
│ 3  │ 🟢 RUN │ i9j0k1l2 │ work-3-def789 │ Data processing pipeline        │ 1m ago: edit file│ [View]  │
│ 4  │ 🔴 STOP│ m3n4o5p6 │ ─             │ Machine learning model          │ 1h ago: stopped  │ [Wake]  │
│ 5  │ 🟡 IDLE│ q7r8s9t0 │ work-4-ghi012 │ Web scraper implementation      │ 30m ago: idle    │ [View]  │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Showing 5 of 23 conversations │ Page 1 of 5 │ [Prev] [Next] │ Filter: [All ▼] [Active] [Waiting] │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Full width table** with all essential columns
- **Smart status indicators**: 🟢 Running, ⏸️ Waiting for input, 🔴 Stopped, 🟡 Idle
- **Last activity summary**: Brief description of most recent action
- **Quick action buttons**: Context-sensitive actions per conversation
- **Header stats**: Quick overview of active/waiting conversations
- **Filtering options**: Show all, active only, waiting only

### 3.2 Conversation Details Panel (Toggled Below)

When a conversation is selected, details panel slides down below the table:

```
┌─ Conversation Details: Build chat application (a1b2c3d4) ─────────────────────────────────────────┐
│ Status: 🟢 RUNNING │ Runtime: work-1-xyz123 │ Created: Dec 1, 10:30 AM │ [Close Details] [Wake] [Stop] │
├─────────────────────┬───────────────────────────────────────────────────────────────────────────────┤
│ 📁 Changed Files    │ 💬 Recent Activity                                                           │
│ ┌─────────────────┐ │ ┌───────────────────────────────────────────────────────────────────────┐ │
│ │ ├── app.py (M)  │ │ │ 2m ago: 🔧 run: npm install express                                   │ │
│ │ ├── config.json │ │ │ 3m ago: 💭 Agent: Installing Express framework for the server        │ │
│ │ ├── package.json│ │ │ 4m ago: ✏️  edit: app.js (added route handlers)                       │ │
│ │ └── routes/     │ │ │ 5m ago: 💬 User: Add authentication to the login endpoint            │ │
│ │     └── auth.js │ │ │ 6m ago: 🔧 run: mkdir routes                                          │ │
│ └─────────────────┘ │ │ 7m ago: ✏️  edit: app.js (created basic Express server)               │ │
│ [📥 Download Files] │ │ 8m ago: 💭 Agent: I'll create a basic Express.js server structure    │ │
│ [📦 Download All]   │ └───────────────────────────────────────────────────────────────────────┘ │
│                     │ [📜 View Full History] [💬 Send Message]                                     │
└─────────────────────┴───────────────────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Collapsible details**: Slides down when conversation selected
- **File tree**: Shows changed files with modification indicators
- **Activity feed**: Recent actions with icons and brief descriptions
- **Action buttons**: Download files, send messages, view full history

### 3.3 Active Monitoring View

Special view for monitoring only running conversations:

```
┌─ Active Conversations Monitor ─────────────────────────────────────────────────────────────────────┐
│ 🔄 Live Updates │ 📡 3 Active │ ⏸️  1 Waiting │ [Back to All] [Settings] │ Auto-scroll: ON │ 🔇 Quiet │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 🟢 Build chat application (a1b2c3d4) │ work-1-xyz123                                                │
│    💭 Agent: Now I'll add error handling to the authentication middleware...                        │
│    🔧 Currently: editing auth.js                                                                    │
│                                                                                                     │
│ 🟢 Data processing pipeline (i9j0k1l2) │ work-3-def789                                             │
│    🔧 Running: python data_processor.py --validate                                                  │
│    📊 Progress: Processing batch 3/10                                                               │
│                                                                                                     │
│ ⏸️  API server development (e5f6g7h8) │ work-2-abc456                                               │
│    💬 Waiting for input: "Should I use JWT or session-based auth?"                                  │
│    ⏰ Waiting since: 5 minutes ago                                                                   │
│    [💬 Send Response] ────────────────────────────────────────────────────────────────────────────│
│    │ Quick responses: [JWT] [Sessions] [Let me think...] │ Custom: [________________] [Send] │     │
│    └──────────────────────────────────────────────────────────────────────────────────────────────│
│                                                                                                     │
│ 🟡 Web scraper (q7r8s9t0) │ work-4-ghi012                                                          │
│    😴 Idle: No activity for 30 minutes                                                              │
│    🔧 Last action: Successfully scraped 1,247 product listings                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Activity Log (last 10 events):                                                                     │
│ 14:32:15 │ chat-app     │ 🔧 run: npm test                                                          │
│ 14:31:45 │ data-proc    │ ✏️  edit: config.yaml (updated batch size)                               │
│ 14:31:20 │ chat-app     │ 💭 Agent: Running tests to verify authentication works                   │
│ 14:30:55 │ api-server   │ ❓ Waiting: Authentication method decision needed                         │
│ 14:30:30 │ data-proc    │ 🔧 run: python validate_schema.py                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Live activity feed**: Real-time updates of what agents are doing
- **Compact conversation cards**: 2-3 lines per active conversation
- **Waiting conversation interaction**: Quick response options for waiting conversations
- **Activity log**: Chronological feed of recent events across all conversations
- **Visual status indicators**: Different icons for different activity types

### 3.4 New Conversation Dialog

Modal dialog for starting new conversations:

```
                    ┌─ Start New Conversation ─────────────────────────────┐
                    │                                                      │
                    │ 💬 Initial Prompt:                                   │
                    │ ┌──────────────────────────────────────────────────┐ │
                    │ │ Help me build a REST API for a todo application  │ │
                    │ │ using Python and FastAPI. I want to include     │ │
                    │ │ user authentication and data persistence.       │ │
                    │ │                                                  │ │
                    │ │                                                  │ │
                    │ └──────────────────────────────────────────────────┘ │
                    │                                                      │
                    │ ⚙️  Advanced Options: [Show ▼]                       │
                    │                                                      │
                    │ 📋 Quick Templates:                                   │
                    │ [Web App] [API] [Data Analysis] [DevOps] [Debug]     │
                    │                                                      │
                    │              [Cancel] [Start Conversation]           │
                    └──────────────────────────────────────────────────────┘
```

## 4. User Interaction Storyboards

### 4.1 Monitoring Active Work

**Scenario**: User wants to monitor progress on multiple active conversations

1. **Launch app** → Shows main conversation list
2. **Click "Active" filter** → Table filters to show only running conversations
3. **Click "Monitor View"** → Switches to active monitoring layout
4. **Real-time updates** → Activity feed shows live progress
5. **Conversation needs input** → Visual indicator and quick response options appear
6. **Send quick response** → Agent continues work immediately

### 4.2 Starting New Conversation

**Scenario**: User wants to start a new coding project

1. **Click "➕ New"** → New conversation modal opens
2. **Type prompt** → "Build a React dashboard for analytics"
3. **Select template** → Click "Web App" for common settings
4. **Click "Start"** → Modal closes, new conversation appears in list
5. **Auto-switch to monitoring** → Shows new conversation starting up
6. **First agent message** → Appears in activity feed

### 4.3 Responding to Waiting Conversation

**Scenario**: Agent needs user input to continue

1. **Notification** → "API server development needs input"
2. **Conversation shows ⏸️ WAIT** → Status updates in main table
3. **Click "Send" action** → Quick response options appear
4. **Select response** → "Use JWT authentication"
5. **Agent continues** → Status changes back to 🟢 RUN
6. **Activity resumes** → New actions appear in monitoring view

## 5. Smart Polling Strategy

### 5.1 Adaptive Refresh Rates

**Normal State** (no active conversations):
- Refresh every **3 minutes**
- Low API usage for idle monitoring

**Active Conversations Present**:
- Refresh every **30 seconds**
- Balance between responsiveness and API load

**During Active Operations** (waking, creating):
- Refresh every **10 seconds** for 2 minutes
- Then return to normal active rate

**WebSocket Connected**:
- Real-time updates for connected conversations
- Fallback to polling for disconnected ones

### 5.2 Smart Update Logic

```python
class SmartPollingManager:
    def calculate_refresh_interval(self) -> int:
        active_count = len(self.get_active_conversations())
        recent_operations = self.get_recent_operations(minutes=5)
        
        if recent_operations:
            return 10  # Fast refresh during operations
        elif active_count > 0:
            return 30  # Medium refresh with active conversations
        else:
            return 180  # Slow refresh when idle
```

## 6. WebSocket Event Mapping

### 6.1 Event Types for Monitoring

**High Priority Events** (show in activity feed):
- `action: "run"` → 🔧 Command execution
- `action: "edit"` → ✏️ File editing
- `action: "write"` → 📝 File creation
- `type: "message", source: "agent"` → 💭 Agent thinking/planning
- `type: "message", source: "user"` → 💬 User input

**Status Indicators**:
- Agent actively working → 🟢 RUN
- Waiting for user input → ⏸️ WAIT
- No activity for >15 minutes → 🟡 IDLE
- Runtime stopped → 🔴 STOP

### 6.2 Brief Message Generation

**Tool Calls**:
- `run: "npm install express"` → "🔧 Installing Express framework"
- `edit: "app.js"` → "✏️ Editing app.js"
- `browse: "localhost:3000"` → "🌐 Testing local server"

**Agent Messages** (truncated):
- Long reasoning → First sentence + "..."
- Code explanations → "Implementing [feature]..."
- Error handling → "Fixing [error type]..."

## 7. Implementation Priorities

### 7.1 Phase 1: Basic Layout
- Full-width conversation table
- Collapsible details panel
- Smart polling implementation

### 7.2 Phase 2: WebSocket Integration
- Real-time event monitoring
- Activity feed implementation
- Status indicator updates

### 7.3 Phase 3: Advanced Features
- Active monitoring view
- Quick response system
- New conversation workflow

## 8. Research Action Items

1. **Set up WebSocket test environment**
2. **Capture comprehensive event samples**
3. **Document all action types and structures**
4. **Design brief message generation rules**
5. **Test polling vs WebSocket performance**
6. **Validate UX with real usage scenarios**