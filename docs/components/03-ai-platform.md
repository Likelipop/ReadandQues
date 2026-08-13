# Component Guide: Shared AI Platform & LangGraph Workflows

This document details the Shared AI Platform, ModelGateway, versioned AI tool runtime, PostgreSQL `AIRunLog` ledgering, and LangGraph workflow integrations.

---

## 1. Architectural Mandate

According to [ADR-0003](file:///home/likelipop/Project/ReadandQues/docs/refactor/adr/0003-ai-tool-platform.md), all LLM calls in ReadAndQues route through a versioned `AITool` contract and `AIToolPolicy`. Direct, unmonitored LLM calls from views or raw scripts are strictly forbidden.

Every AI execution must produce:
- A unique `run_id` (e.g. `run_a1b2c3d4e5f67890`)
- Model name and version tag
- Execution duration in milliseconds
- Prompt, completion, and total token usage
- Persisted ledger entry in PostgreSQL `AIRunLog`

---

## 2. ModelGateway & Profiles

LLM instantiation is centralized in [service/ai_core/platform/gateway.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/ai_core/platform/gateway.py):

```python
from service.ai_core.platform import ModelGateway

# Get precise LLM (temperature=0.1)
llm = ModelGateway.get_llm(profile_name="precise")

# Get creative LLM (temperature=0.7)
creative_llm = ModelGateway.get_llm(profile_name="creative")
```

Available model profiles: `default`, `precise`, `creative`, `fast`.

---

## 3. Versioned AITool Contract & Registry

AI tools implement the `AITool` abstract base class in [service/ai_core/platform/contracts.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/ai_core/platform/contracts.py):

```python
from service.ai_core.platform import AITool, AIToolRunResult

class MyCustomTool(AITool):
    name = "my_custom_tool"
    version = "1.0.0"
    model_profile = "default"

    def run(self, input_data: dict, user_id: int = None) -> AIToolRunResult:
        # Implementation...
        pass
```

Tools are registered globally via `register_ai_tool()` and looked up using `get_ai_tool(tool_name, version)`.

Built-in registered tools:
- **`SmartParaphraseTool`** (`smart_paraphrase:1.0.0`): Paraphrases selected text within paragraph context.
- **`QuizGeneratorTool`** (`quiz_generator:1.0.0`): Generates multiple-choice reading comprehension questions.
- **`BatchParaphraseTool`** (`batch_paraphrase:1.0.0`): Processes batch paragraph paraphrasing.
- **`AskArticleTool`** (`ask_article:1.0.0`): Grounded article Q&A with quote citation verification.

---

## 4. AIToolPolicy & AIRunLog Persistence

Execution of AI tools is wrapped by `AIToolPolicy.execute()` in [service/ai_core/platform/policy.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/ai_core/platform/policy.py):

- Measures execution duration in ms.
- Computes SHA-256 cache key for input payload (when `use_cache=True`).
- Automatically logs run details to PostgreSQL `AIRunLog` table.

PostgreSQL `AIRunLog` Schema ([service/models.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/models.py)):
- `run_id`: Primary key
- `user_id`: Optional ID of requesting user
- `tool_name` & `tool_version`
- `model_name` & `status` (`completed` | `failed`)
- `prompt_tokens`, `completion_tokens`, `total_tokens`
- `duration_ms`
- `input_payload` & `output_payload` JSON fields

---

## 5. LangGraph Stateful Workflows

Complex multi-step AI reasoning uses **LangGraph** stateful graphs:

1. **`smart_paraphrase` Graph** ([service/ai_core/graphs/smart_paraphrase/graph.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/ai_core/graphs/smart_paraphrase/graph.py)): Generator node -> Validator node -> Conditional retry loop.
2. **`question_generator` Graph** ([service/ai_core/graphs/question_generator/graph.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/ai_core/graphs/question_generator/graph.py)): Question generator -> Validation check.
3. **`ask_article` Graph** ([service/ai_core/graphs/ask_article/graph.py](file:///home/likelipop/Project/ReadandQues/ReadAndQues/service/ai_core/graphs/ask_article/graph.py)): Chunking -> Scoped lexical retrieval -> Grounded generation -> Exact citation quote verification.

---

## 6. How to Add a New AI Tool

1. Create a tool script under `service/ai_core/tools/my_tool.py`.
2. Inherit from `AITool`, define `name`, `version`, and `model_profile`.
3. Wrap execution in `AIToolPolicy.execute()`.
4. Register the tool instance with `register_ai_tool()`.
5. Export the tool in `service/ai_core/tools/__init__.py`.
