from pydantic import BaseModel, Field
from .. import config  # Import from the parent directory

class AgentConfig(BaseModel):
    base_output_dir: str = Field(description="Base directory for generated code.")
    python_path: str = Field(description="Python executable path for generated run scripts.")
    model_name: str = Field(description="LLM model name for code generation.")
    api_delay_seconds: int = Field(description="Delay between API calls.")
    max_retries: int = Field(description="Maximum retry attempts for LLM calls.")

    @classmethod
    def from_central_config(cls) -> 'AgentConfig':
        return cls(
            base_output_dir=config.BASE_OUTPUT_DIR,
            python_path=config.PYTHON_EXECUTABLE,
            model_name=config.CURRENT_MODELS['coding'],
            api_delay_seconds=config.API_DELAY_SECONDS,
            max_retries=config.MAX_LLM_RETRIES
        )