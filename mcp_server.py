import contextlib

from starlette.applications import Starlette
from starlette.routing import Mount

from mcp.server.fastmcp import FastMCP

from main import (
    schedule,
    weekly_research,
    game_stats,
    team_stats,
    team_roster,
    player,
    player_stats,
    player_gamelog,
)


mcp = FastMCP(
    "NFL Research Server",
    instructions=(
        "Use these tools to retrieve NFL schedules, weekly research, "
        "game information, team statistics, rosters and player data."
    ),
    json_response=True
)


@mcp.tool()
def nfl_schedule(season: int, week: int):
    """Get an NFL regular-season schedule for a season and week."""
    return schedule(season, week)


@mcp.tool()
def nfl_week_research(season: int, week: int):
    """Get the NFL weekly research package."""
    return weekly_research(season, week)


@mcp.tool()
def nfl_game(game_id: str):
    """Get information for an NFL game."""
    return game_stats(game_id)


@mcp.tool()
def nfl_team_stats(team: str):
    """Get statistics for an NFL team."""
    return team_stats(team)


@mcp.tool()
def nfl_team_roster(team: str):
    """Get an NFL team roster."""
    return team_roster(team)


@mcp.tool()
def nfl_player(player_id: str):
    """Get information about an NFL player."""
    return player(player_id)


@mcp.tool()
def nfl_player_stats(player_id: str, season: int = None):
    """Get NFL player statistics."""
    return player_stats(player_id, season)


@mcp.tool()
def nfl_player_gamelog(player_id: str, season: int = None):
    """Get an NFL player's game log."""
    return player_gamelog(player_id, season)


@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Mount("/", app=mcp.streamable_http_app())
    ],
    lifespan=lifespan
)
