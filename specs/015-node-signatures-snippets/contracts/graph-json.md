# Contract: graph.json optional code-entity metadata (schema_version 6.0.0)

**Feature**: `015-node-signatures-snippets`  
**Schema**: `6.0.0` (unchanged)  
**Compatibility**: Old graphs without these keys remain valid. New graphs remain valid for readers that ignore unknown metadata keys. Required node fields, edge types, and provenance values do not change.

## Optional function / method metadata

```json
{
  "id": "src/client/index.ts::method::createTask::10",
  "type": "method",
  "metadata": {
    "name": "createTask",
    "language": "typescript",
    "file": "src/client/index.ts",
    "start_line": 10,
    "end_line": 28,
    "qualified_name": "ClickUpClient.createTask",
    "signature": "async createTask(listId: string, data: { name: string; description?: string }): Promise<Task>",
    "parameters": [
      {"name": "listId", "type": "string", "kind": "positional", "required": true},
      {"name": "data", "type": "{ name: string; description?: string }", "kind": "positional", "required": true}
    ],
    "return_type": "Promise<Task>",
    "snippet": "async createTask(listId: string, data: { name: string; description?: string }): Promise<Task> {\n  return await this.http.post(`/list/${listId}/task`, data);\n}",
    "snippet_truncated": false
  }
}
```

`return_type` and parameter `type` are omitted when the source does not declare them. `signature_truncated` is omitted unless the 2048-byte signature bound cut the payload. `snippet` and `snippet_truncated` are both omitted when snippets are disabled or the file is a secret-pattern file.

## Optional class metadata

```json
{
  "id": "src/client/index.ts::class::ClickUpClient::1",
  "type": "class",
  "metadata": {
    "name": "ClickUpClient",
    "language": "typescript",
    "file": "src/client/index.ts",
    "start_line": 1,
    "signature": "class ClickUpClient",
    "snippet": "class ClickUpClient {\n  ...\n}",
    "snippet_truncated": true
  }
}
```

Class nodes do not include `parameters` or `return_type`.

## Languages

These keys are produced for `python`, `javascript`, `typescript`, and `dart` only. Other languages keep today's metadata.

## Overloads

One node for the implementation. `signature` lists each overload then the implementation, separated by ` ; `. `parameters` and `return_type` describe the implementation.

## Readers

- MUST ignore unknown metadata keys.
- MUST NOT require the new keys.
- MUST keep accepting `schema_version` `6.0.0`.
