import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
import config

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self, prompt_template: str, agent_type: str):
        self.model_name = config.CURRENT_MODELS.get(agent_type)
        if not self.model_name:
            logger.warning(f"Model for agent type '{agent_type}' not found in config. "f"Falling back to default spec/design model.")
            self.model_name = config.CURRENT_MODELS["spec_design"]
        logger.info(f"Initializing {self.__class__.__name__} with model: {self.model_name}")

        try:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=config.GEMINI_API_KEY,
                temperature=0.3,
                convert_system_message_to_human=True
            )
            self.prompt = ChatPromptTemplate.from_template(prompt_template)
            #chain using LCEL
            self.chain = self.prompt | self.llm | StrOutputParser()

        except Exception as e:
            logger.critical(f"Failed to initialize LangChain components for {self.__class__.__name__}: {e}", exc_info=True)
            raise