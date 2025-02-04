import os
import json
import csv
import datetime
import argparse
from typing import List, Type, TypeVar
from pydantic import BaseModel
import asyncio
from tqdm.asyncio import tqdm_asyncio
import importlib
import llm, utils

T = TypeVar('T', bound=BaseModel)

def get_schema(schema_name: str) -> Type[BaseModel]:
    try:
        return getattr(utils, schema_name)
    except AttributeError:
        try:
            schemas_module = importlib.import_module('utils.schemas')
            return getattr(schemas_module, schema_name)
        except (ImportError, AttributeError):
            raise ValueError(f"Schema '{schema_name}' not found in utils or utils.schemas")
        
async def verify_needle(item: dict, chunk: str, verify_prompt: str) -> bool:
    """
    llm verification of extracted information.

    Args:
    item (dict): The extracted information.
    chunk (str): The text chunk from which the information was extracted.
    verify_prompt (str): The system prompt for verification.

    Returns:
    bool: True if the information is verified, False otherwise.
    """
    relevant_text = utils.get_relevant_text(chunk, item)
    
    messages = [
        {"role": "system", "content": verify_prompt},
        {"role": "user", "content": f"Text:\n{relevant_text}\n\nExtracted Information:\n{json.dumps(item, indent=2)}"}
    ]
    try:
        response = await llm.openai_client_chat_completion_request(
            messages, 
            model="gpt-4o-mini", 
            temperature=0.4,
            response_format="text",
            max_tokens=1
        )
        result = response.choices[0].message.content.strip().lower()
        if result == 'false':
            print(f"Verification failed for: {item}")
        return result == 'true'
    except Exception as e:
        print(f"Error verifying needle: {e}")
        return False

async def process_chunk(schema: Type[T], chunk: str, sys_prompt: str, verify_prompt: str = None) -> List[T]:
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
        result = await llm.openai_client_structured_completion_request(
            messages, 
            utils.create_list_model(schema), 
            model="gpt-4o-2024-08-06", 
            temperature=0.6
        )
        extracted_items = [schema(**{k: utils.clean_field(v) for k, v in item.dict().items()}) for item in result.items]
        filtered_items = [item for item in extracted_items if utils.has_sufficient_populated_fields(item, threshold=0.5)]
        if verify_prompt:
            verified_items = []
            for item in filtered_items:
                if await verify_needle(item.model_dump(), chunk, verify_prompt):
                    verified_items.append(item)
            return verified_items
        else:
            return filtered_items
    except Exception as e:
        print(f"Error processing chunk: {e}")
        return []

async def process_chunks(schema: Type[T], chunks: List[str], sys_prompt: str, verify_prompt: str = None) -> List[T]:
    semaphore = asyncio.Semaphore(300)
    async def sem_task(chunk: str):
        async with semaphore:
            return await process_chunk(schema, chunk, sys_prompt, verify_prompt)
    tasks = [sem_task(chunk) for chunk in chunks]
    results = await tqdm_asyncio.gather(*tasks, desc="Extracting Needles")
    return [item for result in results for item in result]

async def extract_multi_needle(schema: Type[T], haystack: str, example_needles: List[str] = None, verify: bool = False) -> List[T]:
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
    fields_str = "\n".join([f"{field} {description}" for field, description in fields_description.items()])
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
    if verify:
        verify_prompt = utils.veryify_needle_sys.format(
            model_name=model_name,
            fields=fields_str
        )
        needles = await process_chunks(schema, chunks, sys_prompt, verify_prompt)
    else:
        needles = await process_chunks(schema, chunks, sys_prompt)
    
    for needle in needles:
            needle_tuple = tuple(getattr(needle, field) for field in needle.model_fields)
            if needle_tuple not in unique_needles:
                unique_needles.add(needle_tuple)
                extracted_needles.append(needle)
    
    return extracted_needles

async def main(text_file: str, schema_name: str, use_examples: bool, example_needles: List[str], remove_dialogue: bool, verify: bool):
    with open(text_file, 'r') as f:
        text = f.read()

    if remove_dialogue:
        filtered_text = utils.remove_dialogue(text)
    else:
        filtered_text = text

    schema = get_schema(schema_name)

    if use_examples:
        extracted_needles = await extract_multi_needle(schema, filtered_text, example_needles, verify=verify)
    else:
        extracted_needles = await extract_multi_needle(schema, filtered_text, verify=verify)
    
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    save_json = False
    if save_json:
        # save extracted needles to a json file
        filename = f"extracted_needles_{schema_name}_{timestamp}.json"
        file_path = os.path.join(data_dir, filename)
        with open(file_path, 'w') as f:
            json.dump([needle.model_dump() for needle in extracted_needles], f, indent=2)
        print(f"Extracted needles saved to: {file_path}")
    # save extracted needles to a csv file
    csv_filename = f"extracted_needles_{schema_name}_{timestamp}.csv"
    csv_file_path = os.path.join(data_dir, csv_filename)
    with open(csv_file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=extracted_needles[0].model_fields.keys())
        writer.writeheader()
        for needle in extracted_needles:
            writer.writerow(needle.model_dump())
    print("\nSample of extracted needles:")
    print(json.dumps([needle.model_dump() for needle in extracted_needles[:3]], indent=2))
    print(f"Extracted needles saved to: {csv_file_path}")
    print(f"Number of needles extracted: {len(extracted_needles)}")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract structured information from text.")
    parser.add_argument("--text_file", default="data/haystack.txt", help="Path to the text file to process (default: data/haystack.txt)")
    parser.add_argument("--schema", default="TechCompany", help="Name of the schema to use (default: TechCompany)")
    parser.add_argument("--use_examples", action="store_true", help="Use example needles")
    parser.add_argument("--examples", nargs="*", help="Example needles (use with --use_examples)")
    parser.add_argument("--remove_dialogue", action="store_true", help="Remove dialogue from the text")
    parser.add_argument("--verify", action="store_true", help="Verify extracted information using LLM")

    args = parser.parse_args()

    if args.use_examples and not args.examples:
        parser.error("--use_examples requires at least one example needle")

    asyncio.run(main(args.text_file, args.schema, args.use_examples, args.examples, args.remove_dialogue, args.verify))
