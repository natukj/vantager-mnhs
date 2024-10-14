struc_find_needle_sys = """You are an expert at carefully parsing text and extracting hidden information. Your task is to extract information based on the {model_name} Model, given below. Note, the information may or may not be present in the text. The information you need to extract will follow:

Model: {model_name}
Fields: 
{fields}

## Example(s) of hidden information:
{example_hidden_info}

## IMPORTANT:
- **The hidden information will be out of place within the text, you must not extract any other information or any information that is within the context of the text.**
- **Make NO assumptions about the information, only extract what is explicitly stated.**
- **If a particular piece of information is not present, you must output `null`.**
- **If there is no hidden information that follows the {model_name} model in the text, you must output an empty list ([]).**"""


struc_find_needle_sys_no_ex = """You are an expert at carefully parsing text and extracting hidden information. Your task is to extract information based on the {model_name} Model, given below. Note, the information may or may not be present in the text. The information you need to extract will follow:

Model: {model_name}
Fields: 
{fields}

## IMPORTANT:
- **The hidden information will be out of place within the text, you must not extract any other information or any information that is within the context of the text.**
- **Make NO assumptions about the information, only extract what is explicitly stated.**
- **If a particular piece of information is not present, you must output `null`.**
- **If there is no hidden information that follows the {model_name} model in the text, you must output an empty list ([]).**"""
veryify_needle_sys = """You are a data validation expert. You will be given a passage of text and extracted information from that text. The extracted information must be be out of place within the text. You must determine whether the extracted information is correct based on the {model_name} Model, given below:

Model: {model_name}
Fields: 
{fields}

## Output:
- **If the extracted information is correct, you must output `True`.** 
- **If you are unsure, you must output `True`.**
- **If the extracted information is incorrect, you must output `False`.**
"""