"""User memory subgraph (add_user_info)."""

from __future__ import annotations

import logging
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from smart_house_agent.models.state import AgentState
from smart_house_agent.persistence.user_memory import UserMemoryStore

logger = logging.getLogger(__name__)


def make_user_memory_node(llm: BaseChatModel, memory_store: UserMemoryStore):
    def load_user_memory() -> str:
        return memory_store.read()

    def user_memory(state: AgentState):
        """
        This agent is responsible for meticulously managing the "CURRENT USER INFORMATION" (user memory)
        based on the ongoing conversation history. Its primary function is to identify, consolidate,
        and store factual, personal, or preference-based information about the user derived from
        their recent input.
        """
        memory = load_user_memory()

        memory_prompt = """
    You are collecting information about the user from user query and add information to "CURRENT USER INFORMATION"(If it exists) if there is new information about user.

    CURRENT USER INFORMATION(may be empty):
    {memory}

    INSTRUCTIONS:
    1. Review the chat history below carefully
    2. Identify new information about the user, such as:
        - Personal details (name, location, e.g.)
        - Preferences (likes, dislikes)
        - Interests and hobbies
        - Past experiences
    **3. Compare the identified information with the CURRENT USER INFORMATION.**
    **4. If no new or different information is found, output the CURRENT USER INFORMATION exactly as is.**
    **5. If new information *is* found:**
        **a.** Merge any new information with existing memory.
        **b.** If new information conflicts with existing memory, keep the most recent version.
        **c.** Format the *updated* memory as a clear, bulleted list.

    Important: Do NOT include summaries like "no update needed". Dont add your command.
    Your response must be in text format
    If no new data is available in user message, return the user information unmodified. Like this(may be empty):
    {memory}
    """

        user_msg = next(
            (msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            None,
        )

        system_prompt = SystemMessage(content=memory_prompt.format(memory=memory))

        rs = llm.invoke([system_prompt, user_msg])

        try:
            content_to_write = str(rs.content)

            memory_store.write(content_to_write)

            logger.info("Success: New response was written and saved to '%s'.", memory_store.path)
            return {"messages": [AIMessage(content="Success: New response was written and saved", name="add_user_info")]}

        except OSError as e:
            logger.error("File write error: %s", e)
        except AttributeError:
            logger.error("Error: Failed to get 'content' from LLM response. Response was: %s", rs)
        except Exception as e:
            logger.error("An unexpected error occurred (writing): %s", e)

    return user_memory


def build_add_user_info_graph(llm: BaseChatModel, memory_store: UserMemoryStore):
    graph = StateGraph(AgentState)
    graph.add_node("user_memory", make_user_memory_node(llm, memory_store))
    graph.add_edge(START, "user_memory")
    graph.add_edge("user_memory", END)
    return graph.compile(name="add_user_info")
