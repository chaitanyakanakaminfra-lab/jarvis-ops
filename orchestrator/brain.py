import importlib
from pathlib import Path

import yaml
import structlog
from langchain_groq import ChatGroq
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool

from config.settings import get_settings

logger = structlog.get_logger(__name__)

REGISTRY_PATH = Path(__file__).parent.parent / "config" / "agent_registry.yaml"
PROMPTS_PATH  = Path(__file__).parent.parent / "config" / "prompts"


class JarvisBrain:

    def __init__(self):
        self.settings = get_settings()
        self._agent_instances: dict = {}
        self._executor: AgentExecutor | None = None
        self._memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10,
        )

    def initialise(self) -> None:
        logger.info("brain.initialising")
        registry = self._load_registry()
        tools = [t for t in (self._build_tool(a) for a in registry["agents"]) if t]
        logger.info("brain.tools_loaded", count=len(tools))

        system_prompt = self._load_prompt("orchestrator.txt")
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        llm = ChatGroq(
            api_key=self.settings.groq_api_key,
            model=self.settings.groq_model,
            temperature=0,
        )

        agent = create_tool_calling_agent(llm, tools, prompt)
        self._executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=self._memory,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
        )
        logger.info("brain.ready")

    async def process(self, user_input: str) -> str:
        if not self._executor:
            raise RuntimeError("Brain not initialised")
        logger.info("brain.processing", input=user_input)
        try:
            result = await self._executor.ainvoke({
                "input": user_input,
                "chat_history": self._memory.chat_memory.messages,
            })
            response = result.get("output", "Task completed.")
            logger.info("brain.response", response=response[:100])
            return response
        except Exception as e:
            logger.error("brain.error", error=str(e))
            return f"I encountered an error: {str(e)}"

    def _load_registry(self) -> dict:
        with open(REGISTRY_PATH) as f:
            return yaml.safe_load(f)

    def _load_prompt(self, filename: str) -> str:
        prompt_file = PROMPTS_PATH / filename
        if prompt_file.exists():
            return prompt_file.read_text()
        return "You are Jarvis, an AI DevOps assistant. Route commands to the right agent. Be concise."

    def _build_tool(self, config: dict) -> StructuredTool | None:
        try:
            module = importlib.import_module(config["module"])
            agent_class = getattr(module, config["class"])
            instance = agent_class()
            self._agent_instances[config["id"]] = instance

            def make_run(inst):
                def run(command: str) -> str:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        return loop.run_until_complete(inst.execute(command))
                    except RuntimeError:
                        return asyncio.run(inst.execute(command))
                return run

            return StructuredTool.from_function(
                func=make_run(instance),
                name=config["id"],
                description=(
                    f"{config['description']}. "
                    f"Triggered by: {', '.join(config.get('voice_phrases', [])[:3])}"
                ),
            )
        except Exception as e:
            logger.error("brain.tool_load_error", agent_id=config.get("id"), error=str(e))
            return None
