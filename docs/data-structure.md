# AI Companion App Design Document

## Overview

This document outlines the file structure and organizational schema for an Obsidian-like AI companion app with Google Keep-style note display capabilities, relationship graph visualization, and Google Calendar integration.

## Core File Structure

```
KnowledgeVault/
├── Knowledge/             # Reference information and documentation
│   └── [topic].md
├── Canvases/             # Visual relationship maps
│   └── [title].canvas
├── Indexes/              # Search indexes and metadata
│   ├── tags.json        # Tag index
│   ├── links.json       # Internal links tracking
│   ├── timeline.json    # Chronological index
│   ├── display.json     # Display preferences for notes
│   └── relationship-graph.json  # Relationship network data
├── Memories/             # Conversation and interaction records
│   └── [YYYY-MM-DD]-[title].md
├── Notes/                # Quick capture notes (Google Keep style)
│   └── [title].md
├── Relationships/        # Information about people
│   └── [name].md
└── Tasks/                # Action items and to-dos
    └── [title].md
```

## Note Schema Definitions

### Memory Note

```yaml
---
type: memory
created: [ISO timestamp]
tags: [array of tags]
people: [array of people involved]
location: [physical or virtual location]
importance: [low|medium|high]
related: [array of related file links]
---
```

### Task Note

```yaml
---
type: task
created: [ISO timestamp]
due: [ISO timestamp]
status: [not-started|in-progress|completed|deferred]
priority: [low|medium|high]
tags: [array of tags]
assigned: [person assigned]
related: [array of related file links]
---
```

### Knowledge Note

```yaml
---
type: knowledge
created: [ISO timestamp]
modified: [ISO timestamp]
tags: [array of tags]
related: [array of related file links]
source: [original source if applicable]
---
```

### Person Note

```yaml
---
type: person
created: [ISO timestamp]
modified: [ISO timestamp]
tags: [array of tags]
relationship: [colleague|client|friend|family]
last_contact: [ISO timestamp]
---
```

### Keep-Style Note

```yaml
---
type: note
created: [ISO timestamp]
modified: [ISO timestamp]
tags: [array of tags]
color: [hex color code]
pinned: [boolean]
archived: [boolean]
display_mode: [list|grid|card]
media: [array of attached media references]
---
```

## Relationship Graph System

The relationship graph is stored in `indexes/relationship-graph.json`:

```json
{
  "nodes": [
    {
      "id": "person-1",
      "name": "Sarah Wong",
      "file": "relationships/sarah-wong.md",
      "groups": ["work", "tennis"],
      "attributes": {
        "closeness": 8,
        "frequency": "weekly",
        "first_met": "2023-05-12"
      }
    }
  ],
  "links": [
    {
      "source": "person-1",
      "target": "person-2",
      "relationship_types": ["colleague", "friend"],
      "strength": 0.8,
      "contexts": ["Project Alpha", "Tennis Club"],
      "notes": "Met through work, now play tennis together weekly"
    }
  ],
  "groups": [
    {
      "id": "work",
      "name": "Work Colleagues",
      "color": "#4285F4"
    },
    {
      "id": "tennis",
      "name": "Tennis Club",
      "color": "#0F9D58"
    }
  ]
}
```

### Relationship Visualization Features

- Interactive network graph with color-coded nodes
- Filter by relationship type or group
- Strength indicators for relationships
- Contextual information display
- Direct linking to person notes

## Google Calendar Integration

### Calendar Sync Configuration

Stored in `integrations/google/calendar-sync.json`:

```json
{
  "sync_settings": {
    "calendars": [
      {
        "google_id": "primary",
        "display_name": "Work Calendar",
        "color": "#4285F4",
        "sync_enabled": true
      },
      {
        "google_id": "family@group.calendar.google.com",
        "display_name": "Family",
        "color": "#0F9D58",
        "sync_enabled": true
      }
    ],
    "sync_period": {
      "past_days": 30,
      "future_days": 90
    },
    "sync_frequency": "15m",
    "last_sync": "2025-04-27T09:15:32Z"
  }
}
```

### Calendar-Note Linking

Stored in `indexes/calendar-references.json`:

```json
{
  "event_links": {
    "google_event_id_1": {
      "related_files": [
        "memories/2025-04-20-project-alpha-kickoff.md",
        "tasks/prepare-presentation.md"
      ],
      "notes": "Discussed timeline adjustments",
      "auto_create_memory": true
    }
  },
  "upcoming_reminders": [
    {
      "event_id": "google_event_id_2",
      "reminder_time": "2025-05-09T17:00:00Z",
      "message": "Review presentation materials before tomorrow's meeting"
    }
  ]
}
```

## Display Preferences for Notes

The Google Keep-style display is configured in `indexes/display.json`:

```json
{
  "display_settings": {
    "default_view": "grid",
    "default_sort": "modified_desc",
    "note_previews": true,
    "show_tags_in_preview": true
  },
  "note_customizations": {
    "note_id_1": {
      "color": "#f28b82",
      "pinned": true,
      "position": { "x": 0, "y": 0 }
    },
    "note_id_2": {
      "color": "#cbf0f8",
      "pinned": false,
      "position": { "x": 1, "y": 0 }
    }
  }
}
```

## Content Organization Guidelines

### When to use Memories vs. Knowledge

- **Memories**: Time-based records of specific interactions, conversations, and events (episodic memory)

  - Example: "Meeting notes from Project Alpha kickoff"
  - Typically organized by date

- **Knowledge**: Topic-based reference information and documentation (semantic memory)
  - Example: "Project Alpha specifications and timeline"
  - Organized by topic/subject

### When to use Notes (Keep-style)

- Quick ideas or thoughts
- Short reminders
- Information snippets
- Visual notes with color coding
- Content that benefits from a card-based interface

## Key Features

1. **Bidirectional linking** - Automatically track and update links between files
2. **Tag system** - Organize content with multiple tags
3. **Search functionality** - Full-text search across all content
4. **Timeline view** - Chronological view of all content
5. **Templates** - Easy creation of new notes using predefined structures
6. **Relationship graphs** - Visual representation of connections between people
7. **Calendar integration** - Sync with Google Calendar and link events to notes
8. **Visual note display** - Google Keep-style interface for quick notes

## Implementation Considerations

1. **Sync mechanism** - Real-time or periodic updates with Google services
2. **Graph visualization** - Library selection for rendering relationship graphs
3. **Search indexing** - Balance between performance and up-to-date results
4. **Authentication** - Secure access to Google APIs
5. **Local vs. cloud storage** - Data persistence strategy
