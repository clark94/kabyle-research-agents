"""A2A 0.3 JSON-RPC transport via official SDK 0.3.22; one network-facing coordinator."""
import argparse
import asyncio
import json
import os
from functools import lru_cache
from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
from .service import ResearchService


class ResearchExecutor(AgentExecutor):
    def __init__(self, factory):
        self.factory = factory

    async def execute(self, context, event_queue):
        question = context.get_user_input()
        answer = await asyncio.to_thread(self.factory().ask, question)
        await event_queue.enqueue_event(new_agent_text_message(json.dumps(answer, ensure_ascii=False)))

    async def cancel(self, context, event_queue):
        raise NotImplementedError('Synchronous message-only service does not support task cancellation')


def create_app(service=None, public_url=None):
    @lru_cache(maxsize=1)
    def get_service():
        return service or ResearchService()
    card = AgentCard(name='Kabyle Research Coordinator', version='0.2.0', protocol_version='0.3.0',
        description='Searches a validated Kabyle resource catalog with checked citations.',
        url=public_url or os.getenv('A2A_PUBLIC_URL', 'http://127.0.0.1:8002/'),
        default_input_modes=['text/plain'], default_output_modes=['text/plain'],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        skills=[AgentSkill(id='catalog-search', name='Catalog search',
            description='Lexical or hybrid retrieval of validated catalog entries.',
            tags=['kabyle', 'research'], examples=['un dictionnaire kabyle de la médecine'])])
    handler = DefaultRequestHandler(agent_executor=ResearchExecutor(get_service), task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=card, http_handler=handler).build()


def main():
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8002)
    args = parser.parse_args()
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == '__main__':
    main()
