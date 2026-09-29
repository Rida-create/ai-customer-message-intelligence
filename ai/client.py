from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from config import settings
from schemas import AnalysisResult
from ai.prompts import SYSTEM_ANALYSIS_PROMPT
from logger import logger


class AIClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL

    def analyze_message_structured(self, cleaned_text: str) -> AnalysisResult:
        logger.info(f"[Hamna/GenAI] Dispatching message to model: {self.model}")

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_ANALYSIS_PROMPT},
                    {"role": "user", "content": f"Analyze this customer message:\n\"{cleaned_text}\""}
                ],
                response_format=AnalysisResult,
                temperature=0.2
            )

            parsed_result: AnalysisResult = completion.choices[0].message.parsed
            
            if not parsed_result:
                raise ValueError("Model response failed to parse into the required schema.")

            logger.info("[Hamna/GenAI] Successfully received and parsed structured response from LLM.")
            return parsed_result

        except RateLimitError as e:
            logger.error(f"[Hamna/GenAI] OpenAI Rate Limit Exceeded: {str(e)}")
            raise RuntimeError("Rate limit reached. Please wait a moment before trying again.")

        except APIConnectionError as e:
            logger.error(f"[Hamna/GenAI] Could not connect to OpenAI API: {str(e)}")
            raise RuntimeError("Failed to reach AI servers. Please check your network connection.")

        except APIError as e:
            logger.error(f"[Hamna/GenAI] OpenAI API error encountered: {str(e)}")
            raise RuntimeError("AI processing failed due to an upstream API error.")

        except Exception as e:
            logger.error(f"[Hamna/GenAI] Unexpected error during GenAI processing: {str(e)}")
            raise e
