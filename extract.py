import os
import json
import datetime
import argparse
from typing import List, Type, TypeVar
from pydantic import BaseModel
import asyncio
from tqdm.asyncio import tqdm
import importlib
import llm, utils

T = TypeVar('T', bound=BaseModel)

semaphore = asyncio.Semaphore(100)

def get_schema(schema_name: str) -> Type[BaseModel]:
    try:
        return getattr(utils, schema_name)
    except AttributeError:
        try:
            schemas_module = importlib.import_module('utils.schemas')
            return getattr(schemas_module, schema_name)
        except (ImportError, AttributeError):
            raise ValueError(f"Schema '{schema_name}' not found in utils or utils.schemas")

async def process_chunk(schema: Type[T], chunk: str, sys_prompt: str) -> List[T]:
    """
    extract a list of needles from a chunk of text using a given schema and openai structured output api.

    Args:
    schema (Type[T]): The Pydantic model to use for structuring the output.
    chunk (str): The text chunk to process.
    sys_prompt (str): The system prompt to display to the model.

    Returns:
    List[T]: A list of extracted needles.
    """
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "Extract the information from the following:" "\n\n" + chunk}
    ]
    try:
        async with semaphore:
            result = await asyncio.wait_for(
                llm.openai_client_structured_completion_request(
                    messages, 
                    utils.create_list_model(schema), 
                    model="gpt-4o-2024-08-06", 
                    temperature=0.6),
                timeout=60
            )
        return [schema(**{k: utils.clean_field(v) for k, v in item.dict().items()}) for item in result.items]
    except asyncio.TimeoutError:
        print(f"Timeout processing chunk")
        return []
    except Exception as e:
        print(f"Error processing chunk: {e}")
        return []

async def process_chunks(schema: Type[T], chunks: List[str], sys_prompt: str) -> List[T]:
    tasks = [process_chunk(schema, chunk, sys_prompt) for chunk in chunks]
    needles = []
    for future in tqdm.as_completed(tasks, desc="Extracting Needles"):
        try:
            result = await future
            needles.extend(result)
        except Exception as e:
            print(f"Error in chunk processing: {e}")
    return needles

async def extract_multi_needle(schema: Type[T], haystack: str, example_needles: List[str] = None) -> List[T]:
    """
    Extracts and structures information from a large text corpus based on a schema.

    Args:
    schema (Type[T]): The Pydantic model defining the structure of the needle to be extracted.
    haystack (str): The large text corpus to search through (haystack).
    example_needles (List[str]): A list of example sentences (needles).

    Returns:
    List[T]: A list of unique extracted needles conforming to the provided schema.
    """
    unique_needles = set()
    extracted_needles = []
    paragraphs = haystack.split('\n\n')
    chunks = utils.chunk_text(paragraphs)
    model_name, fields_description = utils.schema_to_descriptive_string(schema)
    fields_str = "\n".join([f"{field}: {description}" for field, description in fields_description.items()])
    if example_needles:
        example_hidden_info = "\n".join(example_needles)
        sys_prompt = utils.struc_find_needle_sys.format(
            model_name=model_name,
            fields=fields_str,
            example_hidden_info=example_hidden_info
        )
    else:
        sys_prompt = utils.struc_find_needle_sys_no_ex.format(
            model_name=model_name,
            fields=fields_str
        )
    needles = await process_chunks(schema, chunks, sys_prompt)
    
    for needle in needles:
        if utils.has_sufficient_populated_fields(needle, threshold=0.5):
            needle_tuple = tuple(getattr(needle, field) for field in needle.__fields__)
            if needle_tuple not in unique_needles:
                unique_needles.add(needle_tuple)
                extracted_needles.append(needle)
    
    return extracted_needles

async def main(text_file: str, schema_name: str, use_examples: bool, example_needles: List[str], remove_dialogue: bool):
    with open(text_file, 'r') as f:
        text = f.read()

    if remove_dialogue:
        filtered_text = utils.remove_dialogue(text)
    else:
        filtered_text = text

    schema = get_schema(schema_name)

    if use_examples:
        extracted_needles = await extract_multi_needle(schema, filtered_text, example_needles)
    else:
        extracted_needles = await extract_multi_needle(schema, filtered_text)
    
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"extracted_needles_{schema_name}_{timestamp}.json"
    file_path = os.path.join(data_dir, filename)
    
    with open(file_path, 'w') as f:
        json.dump([needle.dict() for needle in extracted_needles], f, indent=2)
    
    print(f"Extracted needles saved to: {file_path}")
    print(f"Number of needles extracted: {len(extracted_needles)}")
    
    print("\nSample of extracted needles:")
    print(json.dumps([needle.dict() for needle in extracted_needles[:3]], indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract structured information from text.")
    parser.add_argument("--text_file", default="data/haystack.txt", help="Path to the text file to process (default: data/haystack.txt)")
    parser.add_argument("--schema", default="TechCompany", help="Name of the schema to use (default: TechCompany)")
    parser.add_argument("--use_examples", action="store_true", help="Use example needles")
    parser.add_argument("--examples", nargs="*", help="Example needles (use with --use_examples)")
    parser.add_argument("--remove_dialogue", action="store_true", help="Remove dialogue from the text")

    args = parser.parse_args()

    if args.use_examples and not args.examples:
        parser.error("--use_examples requires at least one example needle")

    asyncio.run(main(args.text_file, args.schema, args.use_examples, args.examples, args.remove_dialogue))
