from tenacity import retry, retry_if_exception_type, wait_random_exponential, stop_after_attempt
import asyncio
import openai
from openai import AsyncOpenAI
from typing import TypeVar, List, Type
from pydantic import BaseModel
from utils import ListModel
client = AsyncOpenAI()


T = TypeVar('T', bound=BaseModel)

@retry(
    wait=wait_random_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((Exception)),
    stop=stop_after_attempt(5),
    before_sleep=lambda retry_state: print(f"Retrying attempt {retry_state.attempt_number} for OAI structured completion request...")
)
async def openai_client_structured_completion_request(
    messages: List[dict], 
    response_model: Type[ListModel],
    model: str = "gpt-4o-2024-08-06",
    temperature: float = 0.4
) -> ListModel:
    try:
        completion = await client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_model,
            temperature=temperature
        )
        return completion.choices[0].message.parsed
    except openai.APIError as e:
        print(f"OpenAI structured API Error: {e}")
        raise
    except asyncio.TimeoutError as e:
        print(f"TimeoutError in OpenAI structured API call: {e}")
        raise
    except Exception as e:
        print(f"Error in OpenAI structured API call: {e}")
        raise

@retry(
    wait=wait_random_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((Exception)),
    stop=stop_after_attempt(5),
    before_sleep=lambda retry_state: print(f"Retrying attempt {retry_state.attempt_number} for OAI completion request...")
)
async def openai_client_chat_completion_request(messages, model="gpt-4o", temperature=0.4, response_format="text", max_tokens=1024):
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={ "type": response_format },
            temperature=temperature,
            max_completion_tokens=max_tokens
        )
        return response
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        raise
    except asyncio.TimeoutError as e:
        print(f"TimeoutError in OpenAI API call: {e}")
        raise
    except Exception as e:
        print(f"Error in OpenAI API call: {e}")
        raise