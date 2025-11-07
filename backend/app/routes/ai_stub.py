import json
import os
from typing import List, Literal, Optional, Any, Dict, Union

# Assuming you've installed the OpenAI library
from openai import OpenAI
from pydantic import BaseModel, Field

# --- 1. Define the Strict Output Schema using Pydantic ---
# This schema dictates the exact JSON structure the AI MUST return.

class ExtractionRule(BaseModel):
    """Defines how to find and extract a specific piece of data."""
    field: str = Field(description="A descriptive name for the data to be extracted (e.g., 'Total GPA', 'Invoice Number').")
    regex_pattern: str = Field(description="The REGEX pattern to find and capture the value. Use a capturing group '()' to isolate the value.")
    strategy: Literal["first", "all", "last"] = Field(
        default="first", 
        description="Strategy for handling multiple matches: 'first' (default), 'all' (return a list of matches), or 'last'."
    )
    data_type: Literal["string", "int", "float"] = Field(
        default="string",
        description="The expected data type of the extracted value(s) after conversion."
    )

class ValidationRule(BaseModel):
    """Defines a validation check to perform on extracted data or the whole document."""
    type: Literal["contains_text", "not_contains_text", "numeric_aggregation"] = Field(
        description="The type of validation to perform."
    )
    # Required for all types
    description: str = Field(description="A brief, human-readable description of the validation rule.")
    
    # Required for 'contains_text' and 'not_contains_text'
    text: Optional[str] = Field(None, description="The specific text string to search for or avoid (e.g., 'Confidential', 'Signed').")
    case_sensitive: Optional[bool] = Field(None, description="Whether the text search should be case-sensitive.")
    
    # Required for 'numeric_aggregation'
    field_reference: Optional[str] = Field(None, description="References an 'ExtractionRule.field' to apply the condition to.")
    condition: Optional[Literal["all_greater_than", "any_less_than", "min_value", "max_value"]] = Field(
        None, description="The aggregation condition (e.g., 'all_greater_than' for GPA > 3.5)."
    )
    value: Optional[Union[int, float]] = Field(None, description="The numeric threshold for the condition.")

class RulesetOutput(BaseModel):
    """The final ruleset object that the LLM must generate."""
    name: str = Field(description="A unique, descriptive name for the ruleset (e.g., 'Report Card Validator').")
    source_text: str = Field(description="The original user-provided text prompt.")
    extractions: List[ExtractionRule] = Field(description="A list of all required data extraction rules.")
    validations: List[ValidationRule] = Field(description="A list of all required validation rules.")


# --- 2. Helper to Build the OpenAI Prompt ---

def _build_openai_prompt(user_prompt: str, ruleset_schema: Dict[str, Any]) -> List[Dict[str, str]]:
    """Constructs the messages for the OpenAI API call, including the System instruction."""
    
    system_instruction = f"""
    You are an expert document validation engine. Your task is to convert a user's free-text validation requirement 
    into a structured, machine-executable JSON object.

    Follow these rules strictly:
    1. The output MUST be a valid JSON object that strictly adheres to the provided JSON Schema. Do not include any text, markdown formatting (like ```json), or explanation outside of the JSON object itself.
    2. Analyze the user's intent to create appropriate rules in both the 'extractions' and 'validations' sections.
    3. Use accurate REGEX patterns in the 'ExtractionRule.regex_pattern' field to precisely capture the required value. The value MUST be in a capturing group '()'.
    4. For simple containment checks, use 'contains_text' or 'not_contains_text' validation types.
    5. For checks involving numbers (like 'GPA must be > 3.5'), you must create an 'ExtractionRule' with a 'float' or 'int' data_type, and a corresponding 'numeric_aggregation' 'ValidationRule'.
    
    JSON Schema to follow:
    {json.dumps(ruleset_schema, indent=2)}
    """
    
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]
    
    return messages


# --- 3. The Core AI Conversion Function ---

def generate_ruleset_from_prompt(text_prompt: str, client: OpenAI) -> Dict[str, Any]:
    """
    Translates a natural language validation prompt into a structured JSON ruleset 
    using the OpenAI API.
    """
    
    # 1. Get the JSON Schema from the Pydantic model
    ruleset_schema = RulesetOutput.model_json_schema()
    
    # 2. Build the messages for the LLM
    messages = _build_openai_prompt(text_prompt, ruleset_schema)

    try:
        # 3. Call the OpenAI API. The SDK may support structured response enforcement,
        # but different SDK versions use different parameter types. To keep this
        # code compatible across environments, request a normal chat completion and
        # parse the returned content as JSON.
        # Some SDK versions enforce strict types for `messages`. Cast to Any
        # so we avoid static type-checker issues while keeping runtime behavior.
        messages_param: Any = messages
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_param,
        )

        # 4. Parse the response content and load JSON. The model is instructed to
        # return only a JSON object, so we attempt to parse the message content.
        json_string = None
        # Try common response shapes safely
        json_string = None
        try:
            choice0 = response.choices[0]
        except Exception:
            raise RuntimeError("OpenAI response missing choices")

        # Newer SDKs expose message.content
        msg = getattr(choice0, "message", None)
        if msg is not None:
            json_string = getattr(msg, "content", None)

        # Fallback to direct 'text' attribute if present
        if not json_string:
            json_string = getattr(choice0, "text", None)

        if not isinstance(json_string, str):
            raise RuntimeError("Unexpected OpenAI response shape: no text content")

        # Strip common wrappers if the model accidentally included code fences
        if isinstance(json_string, str):
            json_string = json_string.strip()
            if json_string.startswith("```") and json_string.endswith("```"):
                # remove fenced block markers
                parts = json_string.split('\n')
                # remove first and last lines (the ``` markers)
                json_string = '\n'.join(parts[1:-1]).strip()

        # Parse JSON and validate with Pydantic
        ruleset_data = json.loads(json_string)
        validated_ruleset = RulesetOutput.model_validate(ruleset_data).model_dump()
        return validated_ruleset

    except Exception as e:
        # Log the error for debugging
        print(f"OpenAI API or Pydantic validation error: {e}")
        # Return a standard error response
        return {"error": "Failed to generate ruleset from prompt.", "detail": str(e)}

