# Vantager Technical Assessment (Extended Multi-Needle in a Haystack)

This tool extracts structured information from text files using customisable schemas and OpenAI's language models.

## Installation

1. Install Poetry (if not already installed):

```
brew install poetry
```

2. Install dependencies:

```
poetry install
```

## Configuration

Set your OpenAI API key as an environment variable. You can do this in two ways:

1. Set it for your current shell session:

```
export OPENAI_API_KEY='<OPENAI_API_KEY>'
```

2. Or, create a `.env` file in the project root with the following content:

```
OPENAI_API_KEY=<OPENAI_API_KEY>
```

Poetry will automatically load environment variables from the `.env` file when running scripts.

## Usage

The main script is `extract.py`, which should be run using Poetry to ensure it uses the correct virtual environment and dependencies.

Basic usage (with default text file and schema):

```
poetry run python extract.py
```

This will process the default text file located at `data/haystack.txt`.

### Command-line Arguments

- `--text_file`: Path to the text file to process (default: "data/haystack.txt")
- `--schema`: Name of the schema to use for extraction (default: "TechCompany")
- `--use_examples`: Flag to use example needles
- `--examples`: List of example needles (use with --use_examples)
- `--remove_dialogue`: Flag to remove dialogue from the text before processing
- `--verify`: Flag to enable LLM verification of extracted information

### Examples

1. Using a custom text file:

```
poetry run python extract.py --text_file path/to/your/file.txt
```

2. Using example needles:

```
poetry run python extract.py --use_examples --examples "Example 1" "Example 2"
```

3. Remove dialogue from text (prior to extraction):

```
poetry run python extract.py --remove_dialogue
```

4. Enable LLM verification of extracted information:

```
poetry run python extract.py --verify
```

## Custom Schemas

You can create custom schemas to extract different types of information:

1. Define your schema in `utils/schemas.py`:

```python
from pydantic import BaseModel, Field

class CustomSchema(BaseModel):
    field1: str = Field(description="Description of field1")
    field2: int = Field(description="Description of field2")
    # Add more fields as needed
```

2. Import your new schema in `utils/__init__.py`

```python
from .schemas import TechCompany, CustomSchema  # Add your new schema here
```

3. Use your custom schema when running the script:

```
poetry run python extract.py --schema CustomSchema
```

## Output

The script will save the extracted information as a JSON file in the `data` directory. The filename will include the schema name and a timestamp.

## Notes

- The script uses a semaphore to limit concurrent API calls to 100.
- Extracted data is filtered to remove entries with insufficient information.
