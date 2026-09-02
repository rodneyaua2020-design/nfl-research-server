from fastapi import FastAPI, HTTPException
import requests

app = FastAPI(
    title="NFL Research Server",
    description="NFL schedules, game data, team data, player data and weekly research",
    version="1.2"
)

# ---------------------------------------------------------
# ESPN BASE URLS
# ---------------------------------------------------------

ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

ESPN_WEB = (
    "https://site.web.api.espn.com/apis/common/v3/"
    "sports/football/nfl"
)

ESPN_CORE = (
    "https://sports.core.api.espn.com/v2/"
    "sports/football/leagues/nfl"
)

ESPN_CDN = "https://cdn.espn.com/core/nfl"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9"
}


# ---------------------------------------------------------
# GENERIC JSON FETCHER
# ---------------------------------------------------------

def fetch_json(
    url,
    params=None,
    allow_failure=False
):
    try:

        # Some ESPN Core refs contain http://
        # Force HTTPS when possible.
        if url.startswith("http://"):
            url = "https://" + url[7:]

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=25
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "content-type",
            ""
        ).lower()

        if (
            "json" not in content_type
            and not response.text.strip().startswith(
                ("{", "[")
            )
        ):
            raise ValueError(
                "ESPN returned non-JSON content"
            )

        return response.json()

    except Exception as e:

        if allow_failure:
            return {}

        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to retrieve NFL data. "
                f"Error: {str(e)}"
            )
        )


# ---------------------------------------------------------
# EXTRACT ID FROM ESPN REF
# ---------------------------------------------------------

def id_from_ref(ref):

    if not ref:
        return None

    base = ref.split("?")[0]

    return base.rstrip("/").split("/")[-1]


# ---------------------------------------------------------
# FETCH TEAM DETAILS FROM CORE API
# ---------------------------------------------------------

def get_team_from_ref(team_ref):

    if not team_ref:

        return {
            "id": None,
            "name": None,
            "displayName": None,
            "abbreviation": None
        }

    data = fetch_json(
        team_ref,
        allow_failure=True
    )

    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "displayName": (
            data.get("displayName")
            or data.get("name")
        ),
        "abbreviation": data.get("abbreviation")
    }


# ---------------------------------------------------------
# GET SCORE FROM CORE API
# ---------------------------------------------------------

def get_score(score_object):

    if not score_object:
        return None

    # Sometimes score is embedded directly
    if "value" in score_object:
        return score_object.get("value")

    if "displayValue" in score_object:
        return score_object.get(
            "displayValue"
        )

    score_ref = score_object.get("$ref")

    if score_ref:

        score_data = fetch_json(
            score_ref,
            allow_failure=True
        )

        return (
            score_data.get("displayValue")
            or score_data.get("value")
        )

    return None


# ---------------------------------------------------------
# GET NFL WEEK FROM ESPN CORE API
# ---------------------------------------------------------

def get_week_schedule(
    season: int,
    week: int
):

    url = (
        f"{ESPN_CORE}/seasons/"
        f"{season}/types/2/weeks/"
        f"{week}/events"
    )

    data = fetch_json(
        url,
        {
            "limit": 50,
            "lang": "en",
            "region": "us"
        }
    )

    items = data.get("items", [])

    games = []

    for item in items:

        event_ref = item.get("$ref")

        if not event_ref:
            continue

        event = fetch_json(
            event_ref,
            allow_failure=True
        )

        if not event:
            continue

        event_id = event.get(
            "id",
            id_from_ref(event_ref)
        )

        competitions = event.get(
            "competitions",
            []
        )

        if not competitions:
            continue

        competition = competitions[0]

        competitors = competition.get(
            "competitors",
            []
        )

        home_competitor = None
        away_competitor = None

        for competitor in competitors:

            if competitor.get(
                "homeAway"
            ) == "home":

                home_competitor = competitor

            elif competitor.get(
                "homeAway"
            ) == "away":

                away_competitor = competitor


        if not home_competitor:
            continue

        if not away_competitor:
            continue


        home_team_ref = (
            home_competitor.get(
                "team",
                {}
            ).get("$ref")
        )

        away_team_ref = (
            away_competitor.get(
                "team",
                {}
            ).get("$ref")
        )


        home_team = get_team_from_ref(
            home_team_ref
        )

        away_team = get_team_from_ref(
            away_team_ref
        )


        home_score = get_score(
            home_competitor.get(
                "score",
                {}
            )
        )

        away_score = get_score(
            away_competitor.get(
                "score",
                {}
            )
        )


        status = competition.get(
            "status",
            {}
        )

        if "$ref" in status:

            status_data = fetch_json(
                status["$ref"],
                allow_failure=True
            )

            status_name = (
                status_data
                .get("type", {})
                .get("description")
            )

        else:

            status_name = (
                status
                .get("type", {})
                .get("description")
            )


        games.append({

            "game_id":
                event_id,

            "game":
                event.get(
                    "name"
                ),

            "short_name":
                event.get(
                    "shortName"
                ),

            "date":
                event.get(
                    "date"
                ),

            "status":
                status_name,

            "home": {

                "team_id":
                    home_team.get("id"),

                "name":
                    home_team.get(
                        "displayName"
                    ),

                "abbreviation":
                    home_team.get(
                        "abbreviation"
                    ),

                "score":
                    home_score
            },

            "away": {

                "team_id":
                    away_team.get("id"),

                "name":
                    away_team.get(
                        "displayName"
                    ),

                "abbreviation":
                    away_team.get(
                        "abbreviation"
                    ),

                "score":
                    away_score
            }
        })


    return {

        "source":
            "sports.core.api.espn.com",

        "games":
            games
    }


# ---------------------------------------------------------
# SERVER STATUS
# ---------------------------------------------------------

@app.get("/")
def home():

    return {

        "status":
            "NFL Research Server is running",

        "version":
            "1.2",

        "schedule_source":
            "ESPN Core API",

        "available_endpoints": {

            "schedule":
                "/schedule/{season}/{week}",

            "research":
                "/research/{season}/{week}",

            "game_stats":
                "/game/{game_id}",

            "team_stats":
                "/team/{team}/stats",

            "team_roster":
                "/team/{team}/roster",

            "player":
                "/player/{player_id}",

            "player_stats":
                "/player/{player_id}/stats",

            "player_gamelog":
                "/player/{player_id}/gamelog"
        }
    }


# ---------------------------------------------------------
# WEEKLY SCHEDULE
# ---------------------------------------------------------

@app.get("/schedule/{season}/{week}")
def schedule(
    season: int,
    week: int
):

    result = get_week_schedule(
        season,
        week
    )

    return {

        "season":
            season,

        "week":
            week,

        "source":
            result["source"],

        "game_count":
            len(result["games"]),

        "games":
            result["games"]
    }


# ---------------------------------------------------------
# GAME DATA
# ---------------------------------------------------------

@app.get("/game/{game_id}")
def game_stats(
    game_id: str
):

    # -----------------------------------------
    # First try ESPN Core event endpoint
    # -----------------------------------------

    core_event = fetch_json(

        f"{ESPN_CORE}/events/{game_id}",

        allow_failure=True
    )


    # -----------------------------------------
    # Try site summary for richer stats
    # -----------------------------------------

    site_summary = fetch_json(

        f"{ESPN_SITE}/summary",

        {
            "event":
                game_id
        },

        allow_failure=True
    )


    # -----------------------------------------
    # Try CDN full game package
    # -----------------------------------------

    cdn_game = fetch_json(

        f"{ESPN_CDN}/game",

        {
            "xhr":
                1,

            "gameId":
                game_id
        },

        allow_failure=True
    )


    return {

        "game_id":
            game_id,

        "core_event_available":
            bool(core_event),

        "site_summary_available":
            bool(site_summary),

        "cdn_game_available":
            bool(cdn_game),

        "core_event":
            core_event,

        "site_summary":
            site_summary,

        "cdn_game":
            cdn_game
    }


# ---------------------------------------------------------
# TEAM STATS
# ---------------------------------------------------------

@app.get("/team/{team}/stats")
def team_stats(
    team: str
):

    data = fetch_json(

        f"{ESPN_SITE}/teams/"
        f"{team}/statistics",

        allow_failure=True
    )


    return {

        "team":
            team.upper(),

        "available":
            bool(data),

        "data":
            data
    }


# ---------------------------------------------------------
# TEAM ROSTER
# ---------------------------------------------------------

@app.get("/team/{team}/roster")
def team_roster(
    team: str
):

    data = fetch_json(

        f"{ESPN_SITE}/teams/"
        f"{team}/roster",

        allow_failure=True
    )


    return {

        "team":
            team.upper(),

        "available":
            bool(data),

        "data":
            data
    }


# ---------------------------------------------------------
# PLAYER PROFILE
# ---------------------------------------------------------

@app.get("/player/{player_id}")
def player(
    player_id: str
):

    data = fetch_json(

        f"{ESPN_WEB}/athletes/"
        f"{player_id}",

        allow_failure=True
    )


    return {

        "player_id":
            player_id,

        "available":
            bool(data),

        "data":
            data
    }


# ---------------------------------------------------------
# PLAYER STATS
# ---------------------------------------------------------

@app.get(
    "/player/{player_id}/stats"
)
def player_stats(
    player_id: str,
    season: int = None
):

    params = {}

    if season:

        params["season"] = season
        params["seasontype"] = 2


    data = fetch_json(

        f"{ESPN_WEB}/athletes/"
        f"{player_id}/stats",

        params if params else None,

        allow_failure=True
    )


    return {

        "player_id":
            player_id,

        "season":
            season,

        "available":
            bool(data),

        "data":
            data
    }


# ---------------------------------------------------------
# PLAYER GAME LOG
# ---------------------------------------------------------

@app.get(
    "/player/{player_id}/gamelog"
)
def player_gamelog(
    player_id: str,
    season: int = None
):

    params = {}

    if season:
        params["season"] = season


    data = fetch_json(

        f"{ESPN_WEB}/athletes/"
        f"{player_id}/gamelog",

        params if params else None,

        allow_failure=True
    )


    return {

        "player_id":
            player_id,

        "season":
            season,

        "available":
            bool(data),

        "data":
            data
    }


# ---------------------------------------------------------
# WEEKLY RESEARCH PACKAGE
# ---------------------------------------------------------

@app.get(
    "/research/{season}/{week}"
)
def weekly_research(
    season: int,
    week: int
):

    schedule_result = get_week_schedule(
        season,
        week
    )

    schedule_games = schedule_result[
        "games"
    ]

    research_games = []


    for game in schedule_games:

        game_id = game.get(
            "game_id"
        )

        home = game.get(
            "home",
            {}
        )

        away = game.get(
            "away",
            {}
        )


        # -------------------------------------
        # CORE EVENT
        # -------------------------------------

        core_event = {}

        if game_id:

            core_event = fetch_json(

                f"{ESPN_CORE}/events/"
                f"{game_id}",

                allow_failure=True
            )


        # -------------------------------------
        # SITE GAME SUMMARY
        # -------------------------------------

        site_summary = {}

        if game_id:

            site_summary = fetch_json(

                f"{ESPN_SITE}/summary",

                {
                    "event":
                        game_id
                },

                allow_failure=True
            )


        # -------------------------------------
        # CDN GAME PACKAGE
        # -------------------------------------

        cdn_game = {}

        if game_id:

            cdn_game = fetch_json(

                f"{ESPN_CDN}/game",

                {
                    "xhr":
                        1,

                    "gameId":
                        game_id
                },

                allow_failure=True
            )


        # -------------------------------------
        # HOME TEAM STATS
        # -------------------------------------

        home_stats = {}

        home_abbr = home.get(
            "abbreviation"
        )

        if home_abbr:

            home_stats = fetch_json(

                f"{ESPN_SITE}/teams/"
                f"{home_abbr}/statistics",

                allow_failure=True
            )


        # -------------------------------------
        # AWAY TEAM STATS
        # -------------------------------------

        away_stats = {}

        away_abbr = away.get(
            "abbreviation"
        )

        if away_abbr:

            away_stats = fetch_json(

                f"{ESPN_SITE}/teams/"
                f"{away_abbr}/statistics",

                allow_failure=True
            )


        research_games.append({

            "game_id":
                game_id,

            "game":
                game.get("game"),

            "date":
                game.get("date"),

            "status":
                game.get("status"),

            "home": {

                "team_id":
                    home.get(
                        "team_id"
                    ),

                "name":
                    home.get(
                        "name"
                    ),

                "abbreviation":
                    home_abbr,

                "score":
                    home.get(
                        "score"
                    ),

                "season_stats":
                    home_stats
            },

            "away": {

                "team_id":
                    away.get(
                        "team_id"
                    ),

                "name":
                    away.get(
                        "name"
                    ),

                "abbreviation":
                    away_abbr,

                "score":
                    away.get(
                        "score"
                    ),

                "season_stats":
                    away_stats
            },

            "data_sources": {

                "core_event_available":
                    bool(
                        core_event
                    ),

                "site_summary_available":
                    bool(
                        site_summary
                    ),

                "cdn_game_available":
                    bool(
                        cdn_game
                    )
            },

            "core_event":
                core_event,

            "game_summary":
                site_summary,

            "cdn_game":
                cdn_game
        })


    return {

        "season":
            season,

        "week":
            week,

        "schedule_source":
            schedule_result[
                "source"
            ],

        "game_count":
            len(
                research_games
            ),

        "games":
            research_games
    }
