"""TypeScript signatures shaped like ClickUpClient methods."""

from pathlib import Path

from grapheinstein.core.parsers.extract import extract_file

SOURCE = """
export class ClickUpClient {
  /**
   * Create a task.
   * @param listId list
   * @param data payload
   */
  async createTask(
    listId: string,
    data: { name: string; description?: string },
  ): Promise<Task> {
    return await this.http.post(`/list/${listId}/task`, data);
  }
  async setCustomFieldValue(
    taskId: string,
    fieldId: string,
    value: string | number | boolean | { add?: number[]; rem?: number[] },
  ): Promise<void> {
    await this.http.post(`/task/${taskId}/field/${fieldId}`, { value });
  }
  async createWebhook(
    workspaceId: string,
    data: { endpoint: string; events: string[] },
  ): Promise<Webhook> {
    return await this.http.post(`/team/${workspaceId}/webhook`, data);
  }
}

function over(a: string): string;
function over(a: number): number;
function over(a: string | number): string | number {
  return a;
}
"""


def _entities(tmp_path: Path):
    path = tmp_path / "index.ts"
    path.write_text(SOURCE, encoding="utf-8")
    result = extract_file(path, "typescript", file_id="src/client/index.ts")
    assert not result.skipped
    return {(entity.kind, entity.name): entity for entity in result.entities}


def test_typescript_clickup_methods(tmp_path: Path):
    entities = _entities(tmp_path)
    create = entities[("method", "createTask")]
    by_name = {param["name"]: param for param in create.parameters or []}
    assert by_name["listId"]["type"] == "string"
    assert by_name["listId"]["kind"] == "positional"
    assert by_name["listId"]["required"] is True
    assert by_name["data"]["type"] == "{ name: string; description?: string }"
    assert create.return_type == "Promise<Task>"
    assert create.signature is not None
    assert "async createTask" in create.signature
    assert create.snippet is not None
    assert "/**" not in create.snippet
    assert "return await this.http.post" in create.snippet

    field = entities[("method", "setCustomFieldValue")]
    value = {param["name"]: param for param in field.parameters or []}["value"]
    assert value["type"] == "string | number | boolean | { add?: number[]; rem?: number[] }"
    assert field.return_type == "Promise<void>"

    hook = entities[("method", "createWebhook")]
    hook_params = {param["name"]: param for param in hook.parameters or []}
    assert hook_params["workspaceId"]["type"] == "string"
    assert hook_params["data"]["type"] == "{ endpoint: string; events: string[] }"
    assert hook.return_type == "Promise<Webhook>"

    client = entities[("class", "ClickUpClient")]
    assert client.parameters is None
    assert client.signature == "class ClickUpClient"
    assert client.snippet is not None
    assert "createTask" in client.snippet


def test_typescript_overloads_keep_implementation_parameters(tmp_path: Path):
    over = _entities(tmp_path)[("function", "over")]
    assert over.signature is not None
    assert over.signature.index("function over(a: string): string") < over.signature.index(
        "function over(a: number): number"
    )
    assert over.signature.endswith("function over(a: string | number): string | number")
    assert over.parameters == [
        {
            "name": "a",
            "type": "string | number",
            "kind": "positional",
            "required": True,
        }
    ]
    assert over.return_type == "string | number"
