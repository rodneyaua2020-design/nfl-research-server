import contextlib

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from main import (
    schedule,
    weekly_research,
    game_stats,
    team_stats,
    team_roster,
    player,
    player_stats,
    player_gamelog,
    app as rest_app
)


# ---------------------------------------------------------
# MCP SERVER
# ---------------------------------------------------------

mcp = FastMCP(
    "NFL Research Server",
    instructions=(
        "Use these tools to retrieve NFL schedules, weekly research, "
        "game information, team statistics, rosters and player data."
    )
)


# ---------------------------------------------------------
# MCP TOOLS
# ---------------------------------------------------------

@mcp.tool()
def nfl_schedule(season: int, week: int):
    """
    Get the NFL regular-season schedule for a specific season and week.
    Example: season=2026, week=1
    """
    return schedule(season, week)


@mcp.tool()
def nfl_week_research(season: int, week: int):
    """
    Get the complete NFL research package for a particular regular-season week.
    Includes fixtures and available team/game information.
    """
    return weekly_research(season, week)


@mcp.tool()
def nfl_game(game_id: str):
    """
    Get detailed information and statistics for an NFL game using its ESPN game ID.
    """
    return game_stats(game_id)


@mcp.tool()
def nfl_team_stats(team: str):
    """
    Get NFL team statistics.
    Use team abbreviations such as KC, BUF, PHI, DAL, BAL.
    """
    return team_stats(team)


@mcp.tool()
def nfl_team_roster(team: str):
    """
    Get the current roster for an NFL team.
    Use an NFL team abbreviation such as KC or BUF.
    """
    return team_roster(team)


@mcp.tool()
def nfl_player(player_id: str):
    """
    Get information about an NFL player using the ESPN player ID.
    """
    return player(player_id)


@mcp.tool()
def nfl_player_stats(player_id: str, season: int = None):
    """
    Get season statistics for an NFL player.
    """
    return player_stats(player_id, season)


@mcp.tool()
def nfl_player_gamelog(player_id: str, season: int = None):
    """
    Get the game log for an NFL player.
    """
    return player_gamelog(player_id, season)


# ---------------------------------------------------------
# MCP SECURITY
# ---------------------------------------------------------

security = TransportSecuritySettings(
    allowed_hosts=[
        "nfl-research-server.onrender.com",
        "nfl-research-server.onrender.com:*"
    ],
    allowed_origins=[
        "https://claude.ai"
    ]
)


# ---------------------------------------------------------
# LIFESPAN
# ---------------------------------------------------------

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):

    async with mcp.session_manager.run():
        yield


# ---------------------------------------------------------
# COMBINED APPLICATION
# ---------------------------------------------------------

app = FastAPI(
    title="NFL Research MCP Server",
    lifespan=lifespan
)


# MCP endpoint will be:
# https://nfl-research-server.onrender.com/mcp

mcp.settings.streamable_http_path = "/"

app.mount(
    "/mcp",
    mcp.streamable_http_app(
        transport_security=security
    )
)


# Keep your existing REST API working too.

app.mount(
    "/",
    rest_app
)
