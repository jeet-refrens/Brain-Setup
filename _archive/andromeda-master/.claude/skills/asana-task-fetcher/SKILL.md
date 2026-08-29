---
name: asana-task-fetcher
description: Fetches an Asana task's title and description from a task URL so you can understand and work on the task. Use this skill whenever the user provides an Asana task URL (app.asana.com/...), asks you to "look at this Asana task", "work on this Asana ticket", "fetch this Asana task", or pastes a link that looks like an Asana task. Requires the ASANA_PAT environment variable to be set.
---

# Asana Task Fetcher

When the user provides an Asana task URL, fetch the task details and present them clearly so you can begin working on the task.

## How to fetch a task

### Step 1: Extract the task GID from the URL

Asana task URLs follow this pattern:
```
https://app.asana.com/0/<project_gid>/<task_gid>/f
```

The task GID is the last numeric segment before `/f` (or the end of the path). Extract it with:

```bash
TASK_URL="<the url the user provided>"
TASK_GID=$(echo "$TASK_URL" | grep -oE '[0-9]+' | tail -1)
```

### Step 2: Fetch the task via the Asana API

```bash
curl --silent --request GET \
  "https://app.asana.com/api/1.0/tasks/${TASK_GID}?opt_fields=gid,name,notes,html_notes,completed,due_on,assignee.name,custom_fields,parent.name,permalink_url" \
  --header "Authorization: Bearer ${ASANA_PAT}" \
  --header "Accept: application/json"
```

The response is wrapped in a `data` key:
```json
{
  "data": {
    "gid": "9876543210",
    "name": "Task title here",
    "notes": "Task description / body text here...",
    "completed": false,
    "due_on": "2026-03-20",
    "assignee": { "name": "Jane Doe" },
    "parent": { "name": "Parent task name" }
  }
}
```

### Step 3: Handle errors

- **401 Unauthorized**: `ASANA_PAT` is missing or invalid. Tell the user to set the `ASANA_PAT` environment variable with a valid Personal Access Token from https://app.asana.com/0/my-apps
- **404 Not Found**: The task GID doesn't exist or the PAT doesn't have access to it
- **429 Too Many Requests**: Rate limited. Check the `Retry-After` header and wait before retrying

### Step 4: Present the task and proceed

Once fetched, display the task clearly:

```
## Task: <name>
**GID:** <gid>
**Status:** <completed ? "Done" : "Open">
**Due:** <due_on or "not set">
**Assignee:** <assignee.name or "unassigned">
**Parent:** <parent.name or "none">

### Description
<notes, or "(no description)" if empty>
```

Then ask the user how they'd like to proceed, or if they said something like "work on this task", dive straight into it using the task title and description as your context.

## Tips

- The `notes` field is plain text. If you need rich formatting, `html_notes` has the HTML version.
- Custom fields (deadlines, priority, etc.) are in the `custom_fields` array — each entry has `name` and `display_value`.
- If the task has no description (`notes` is empty or null), say so explicitly rather than leaving a blank section.
- Subtasks are not returned by default — if the user needs subtasks, fetch `/tasks/{task_gid}/subtasks` separately.
