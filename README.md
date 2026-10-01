# medical_research_ai

A CrewAI-powered medical literature search and evidence extraction project. It
can be used through the command line or the Streamlit interface.

## Requirements

- Python 3.10-3.13
- An OpenAI API key for the command-line literature search and Streamlit search
- A Gemini API key for evidence extraction (or configure extraction to use OpenAI)

## Setup (Windows PowerShell)

From the project root, create and activate a virtual environment, then install
the project and its dependencies:

```bash
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Create a `.env` file in the project root and add the API keys you plan to use:

```dotenv
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

The command-line search agent uses `openai/gpt-4.1`. Evidence extraction uses
Gemini by default (`LLM_PROVIDER=gemini`, model `gemini-2.5-flash`). To use
OpenAI for extraction instead, add these settings to `.env`:

```dotenv
LLM_PROVIDER=openai
OPENAI_MODEL=openai/gpt-4.1
```

## Run a Literature Search

With the virtual environment active, run:

```bash
crewai run
```

The CLI asks for the task inputs, including `max_results` and `research_topic`.
Enter a value at each prompt; for example, use `10` for `max_results` and a
topic such as `type 2 diabetes management in older adults` for `research_topic`.
The run is cancelled if you press `Ctrl+C` or otherwise abort a prompt.

This command runs the crew in `crew.jsonc`, as configured in `pyproject.toml`.
`evidence_crew.jsonc` is an additional crew definition but is not selected by
the default `crewai run` command.

## Run the Streamlit App

From the project root, with dependencies installed and the `.env` file set up:

```bash
streamlit run frontend/app.py
```

Open the local URL printed by Streamlit. Search for papers in the sidebar, then
use **Evidence Extraction** there to extract evidence from papers saved in the
local database.

## Project Structure

- `agents/` - Agent definitions (JSONC)
- `crew.jsonc` - Default literature-search crew
- `evidence_crew.jsonc` - Separate evidence-extraction crew definition
- `frontend/app.py` - Streamlit interface
- `tools/` - Custom CrewAI tools (Python)
- `database/`, `services/` - Literature, LLM, and database implementation
- `Outputs/` - Generated export directories
- `knowledge/` - Knowledge files for agents

> **Note:** `custom:<name>` tool references execute `tools/<name>.py` as local
> Python code when the crew loads. Only run crew projects from sources you
> trust.
