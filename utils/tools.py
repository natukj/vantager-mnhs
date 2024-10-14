import re
from typing import Type, Tuple, Dict, List, TypeVar, Generic, get_type_hints
from pydantic import BaseModel, create_model
import tiktoken

def count_tokens(text: str, encoding_name: str = "o200k_base") -> int:
    """
    count the number of tokens in the given text using the specified encoding.
    """
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(text))
    return num_tokens

def remove_dialogue(text: str) -> str:
    """
    remove any dialogue from the text, including quotation marks.
    """
    return re.sub(r'[“"](.+?)[”"]', '', text, flags=re.DOTALL)

def chunk_text(paragraphs: list, max_tokens: int = 32000) -> list:
    """
    split the paragraphs into chunks of at most max_tokens tokens.
    """
    chunks = []
    current_chunk = ''
    curent_tokens = 0
    for paragraph in paragraphs:
        paragraph.strip()
        paragraph_tokens = count_tokens(paragraph)
        if curent_tokens + paragraph_tokens > max_tokens:
            chunks.append(current_chunk)
            current_chunk = ''
            curent_tokens = 0
        current_chunk += paragraph + '\n\n'
        curent_tokens += paragraph_tokens

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def schema_to_descriptive_string(model: Type[BaseModel]) -> Tuple[str, Dict[str, str]]:
    """
    convert a Pydantic model to a descriptive string.
    """
    model_name = model.__name__
    fields_description = {}
    
    hints = get_type_hints(model)
    for field_name, field in model.model_fields.items():
        type_hint = str(hints[field_name])
        if type_hint.startswith(('typing.Union', 'typing.Optional')):
            type_name = type_hint.replace("typing.Union[", "").replace("typing.Optional[", "").replace(", NoneType]", "").replace("]", "")
        else:
            type_name = type_hint

        type_name = type_name.split(".")[-1]
        
        if type_name.startswith("<class '") and type_name.endswith("'>"):
            type_name = type_name[8:-2]
        
        if type_name.startswith("'") and type_name.endswith("'"):
            type_name = type_name[1:-1]
        
        field_description = field.description or "No description provided"
        fields_description[field_name] = f"({type_name}): {field_description}"
    
    return model_name, fields_description

T = TypeVar('T', bound=BaseModel)

class ListModel(Generic[T]):
    __root__: List[T]

    def __init__(self, items: List[T]):
        self.__root__ = items

    @property
    def items(self) -> List[T]:
        return self.__root__

def create_list_model(item_model: Type[T]) -> Type[BaseModel]:
    return create_model(
        f"{item_model.__name__}List",
        items=(List[item_model], ...),
        __base__=BaseModel
    )

def clean_field(value):
    if isinstance(value, str):
        value = value.strip()
        return None if value.lower() == "null" or value == "" else value
    return value if value is not None else None

def has_any_populated_field(obj):
    return any(clean_field(getattr(obj, field)) is not None for field in obj.__fields__)

def has_sufficient_populated_fields(obj, threshold=0.5):
    total_fields = len(obj.__fields__)
    populated_fields = sum(1 for field in obj.__fields__ if clean_field(getattr(obj, field)) is not None)
    return populated_fields / total_fields >= threshold

def get_relevant_text(chunk: str, item: dict, context_paragraphs: int = 3) -> str:
    """
    truncate the chunk around the item to provide context.

    Args:
    chunk (str): The text chunk.
    item (dict): The extracted information.
    context_paragraphs (int): The number of paragraphs to include before and after the matched text.

    Returns:
    str: The relevant text from the chunk.
    """
    paragraphs = [p.strip() for p in chunk.split('\n\n') if p.strip()]
    relevant_texts = set()

    for value in item.values():
        if value:
            escaped_value = re.escape(str(value))
            pattern = re.compile(f".*{escaped_value}.*", re.IGNORECASE | re.DOTALL)
            
            for i, paragraph in enumerate(paragraphs):
                if pattern.search(paragraph):
                    start = max(0, i - context_paragraphs)
                    end = min(len(paragraphs), i + context_paragraphs + 1)
                    # ensure the context is at least 2 * context_paragraphs + 1 paragraphs
                    while start > 0 and end - start < context_paragraphs * 2 + 1:
                        start -= 1
                    while end < len(paragraphs) and end - start < context_paragraphs * 2 + 1:
                        end += 1
                    
                    context = '\n\n'.join(paragraphs[start:end])
                    relevant_texts.add(context)
    return '\n\n'.join(relevant_texts)