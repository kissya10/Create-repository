from aiogram import Dispatcher
from .common import router as common_router
from .pets import router as pets_router
from .social import router as social_router
from .games import router as games_router
from .admin_tools import router as admin_router
from .top import router as top_router
from .boss import router as boss_router
from .minigames import router as minigames_router


def register_routers(dp: Dispatcher) -> None:
    for router in [
        common_router,
        pets_router,
        social_router,
        games_router,
        admin_router,
        top_router,
        boss_router,
        minigames_router,
    ]:
        dp.include_router(router)
