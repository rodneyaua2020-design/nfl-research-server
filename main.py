from fastapi import FastAPI, HTTPException
import requests

app = FastAPI(
    title="NFL Research Server",
    description="NFL schedules, game stats, team stats, player stats and weekly research",
    version="1.1"
)

# ---------------------------------------------------------
# ESPN BASE URLS
# ---------------------------------------------------------

ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ESPN_WEB = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl"
ESPN_CDN = "https://cdn.espn.com/core/nfl"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.espn.com/",
}


# ---------------------------------------------------------
# GENERIC REQUEST FUNCTION
# ---------------------------------------------------------

def fetch_json(url, params=None, allow_failure=False):

    try:
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=25
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        if allow_failure:
            return {}

        raise HTTPException(
            status_code=502,
            detail=f"Unable to retrieve NFL data: {str(e)}"
        )


# ---------------------------------------------------------
# SCHEDULE FETCHER WITH FALLBACK
# ---------------------------------------------------------

def get_week_schedule(season: int, week: int):

    # First attempt: site.api.espn.com
    primary_url = f"{ESPN_SITE}/scoreboard"

    try:

        response = requests.get(
            primary_url,
            params={
                "dates": season,
                "seasontype": 2,
                "week": week
            },
            headers=HEADERS,
            timeout=20
        )

        if response.status_code == 200:

            data = response.json()

            if data.get("events"):
                return {
                    "source": "site.api.espn.com",
                    "data": data
                }

    except Exception:
        pass


    # -----------------------------------------------------
    # FALLBACK: ESPN CDN
    # -----------------------------------------------------

    fallback_url = f"{ESPN_CDN}/schedule"

    try:

        response = requests.get(
            fallback_url,
            params={
                "xhr": 1,
                "year": season,
                "week": week
            },
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        return {
            "source": "cdn.espn.com",
            "data": data
        }

    except Exception as e:

        raise HTTPException(
            status_code=502,
            detail=(
                "Both ESPN schedule sources failed. "
                f"Final error: {str(e)}"
            )
        )


# ---------------------------------------------------------
# NORMALIZE SCHEDULE DATA
# ---------------------------------------------------------

def normalize_schedule(schedule_package):

    source = schedule_package["source"]
    data = schedule_package["data"]

    games = []


    # -----------------------------------------------------
    # SITE API FORMAT
    # -----------------------------------------------------

    if source == "site.api.espn.com":

        for event in data.get("events", []):

            competitions = event.get("competitions", [])

            if not competitions:
                continue

            competition = competitions[0]

            competitors = competition.get("competitors", [])

            try:

                home = next(
                    x for x in competitors
                    if x.get("homeAway") == "home"
                )

                away = next(
                    x for x in competitors
                    if x.get("homeAway") == "away"
                )

            except StopIteration:
                continue

            games.append({

                "game_id": event.get("id"),

                "game": event.get("name"),

                "date": event.get("date"),

                "home": {
                    "name": home.get("team", {}).get("displayName"),
                    "abbreviation": home.get("team", {}).get("abbreviation"),
                    "team_id": home.get("team", {}).get("id"),
                    "score": home.get("score"),
                    "records": home.get("records")
                },

                "away": {
                    "name": away.get("team", {}).get("displayName"),
                    "abbreviation": away.get("team", {}).get("abbreviation"),
                    "team_id": away.get("team", {}).get("id"),
                    "score": away.get("score"),
                    "records": away.get("records")
                },

                "status": event.get(
                    "status",
                    {}
                ).get(
                    "type",
                    {}
                ).get("description")
            })


    # -----------------------------------------------------
    # CDN FORMAT
    # -----------------------------------------------------

    else:

        content = data.get("content", {})

        schedule = content.get("schedule", {})

        entries = schedule.get("events", [])

        if not entries:

            entries = content.get("events", [])

        if not entries:

            entries = data.get("events", [])


        for event in entries:

            competitions = event.get("competitions", [])

            if not competitions:
                continue

            competition = competitions[0]

            competitors = competition.get("competitors", [])

            try:

                home = next(
                    x for x in competitors
                    if x.get("homeAway") == "home"
                )

                away = next(
                    x for x in competitors
                    if x.get("homeAway") == "away"
                )

            except StopIteration:
                continue

            games.append({

                "game_id": event.get("id"),

                "game": event.get(
                    "name",
                    event.get("shortName")
                ),

                "date": event.get("date"),

                "home": {
                    "name": home.get("team", {}).get("displayName"),
                    "abbreviation": home.get("team", {}).get("abbreviation"),
                    "team_id": home.get("team", {}).get("id"),
                    "score": home.get("score"),
                    "records": home.get("records")
                },

                "away": {
                    "name": away.get("team", {}).get("displayName"),
                    "abbreviation": away.get("team", {}).get("abbreviation"),
                    "team_id": away.get("team", {}).get("id"),
                    "score": away.get("score"),
                    "records": away.get("records")
                },

                "status": event.get(
                    "status",
                    {}
                ).get(
                    "type",
                    {}
                ).get("description")
            })


    return games


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.get("/")
def home():

    return {

        "status": "NFL Research Server is running",

        "version": "1.1",

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
def schedule(season: int, week: int):

    schedule_package = get_week_schedule(
        season,
        week
    )

    games = normalize_schedule(
        schedule_package
    )

    return {

        "season": season,

        "week": week,

        "source": schedule_package["source"],

        "game_count": len(games),

        "games": games
    }


# ---------------------------------------------------------
# GAME DATA
# ---------------------------------------------------------

@app.get("/game/{game_id}")
def game_stats(game_id: str):

    # -----------------------------------------------------
    # First attempt ESPN site summary
    # -----------------------------------------------------

    site_data = fetch_json(
        f"{ESPN_SITE}/summary",
        {
            "event": game_id
        },
        allow_failure=True
    )


    if site_data:

        boxscore = site_data.get(
            "boxscore",
            {}
        )

        team_stats = []

        for entry in boxscore.get(
            "teams",
            []
        ):

            team = entry.get(
                "team",
                {}
            )

            stats = {}

            for stat in entry.get(
                "statistics",
                []
            ):

                name = stat.get("name")

                if name:

                    stats[name] = stat.get(
                        "displayValue",
                        stat.get("value")
                    )

            team_stats.append({

                "team_id":
                    team.get("id"),

                "team":
                    team.get("displayName"),

                "abbreviation":
                    team.get("abbreviation"),

                "stats":
                    stats
            })


        player_stats = []

        for team_entry in boxscore.get(
            "players",
            []
        ):

            team = team_entry.get(
                "team",
                {}
            )

            categories = []

            for category in team_entry.get(
                "statistics",
                []
            ):

                labels = category.get(
                    "labels",
                    []
                )

                players = []

                for athlete_entry in category.get(
                    "athletes",
                    []
                ):

                    athlete = athlete_entry.get(
                        "athlete",
                        {}
                    )

                    raw_stats = athlete_entry.get(
                        "stats",
                        []
                    )

                    stat_dict = {}

                    for index, label in enumerate(
                        labels
                    ):

                        if index < len(raw_stats):

                            stat_dict[label] = (
                                raw_stats[index]
                            )

                    players.append({

                        "player_id":
                            athlete.get("id"),

                        "name":
                            athlete.get(
                                "displayName"
                            ),

                        "position":
                            athlete.get(
                                "position",
                                {}
                            ).get(
                                "abbreviation"
                            ),

                        "stats":
                            stat_dict
                    })


                categories.append({

                    "category":
                        category.get("name"),

                    "players":
                        players
                })


            player_stats.append({

                "team":
                    team.get("displayName"),

                "abbreviation":
                    team.get("abbreviation"),

                "categories":
                    categories
            })


        return {

            "game_id":
                game_id,

            "source":
                "site.api.espn.com",

            "header":
                site_data.get("header"),

            "team_stats":
                team_stats,

            "player_stats":
                player_stats,

            "leaders":
                site_data.get("leaders"),

            "injuries":
                site_data.get("injuries"),

            "scoring_plays":
                site_data.get(
                    "scoringPlays"
                ),

            "drives":
                site_data.get("drives"),

            "win_probability":
                site_data.get(
                    "winprobability"
                ),

            "pickcenter":
                site_data.get(
                    "pickcenter"
                )
        }


    # -----------------------------------------------------
    # FALLBACK: ESPN CDN BOX SCORE
    # -----------------------------------------------------

    cdn_data = fetch_json(
        f"{ESPN_CDN}/boxscore",
        {
            "xhr": 1,
            "gameId": game_id
        }
    )


    return {

        "game_id": game_id,

        "source": "cdn.espn.com",

        "data": cdn_data
    }


# ---------------------------------------------------------
# TEAM STATS
# ---------------------------------------------------------

@app.get("/team/{team}/stats")
def team_stats(team: str):

    data = fetch_json(
        f"{ESPN_SITE}/teams/{team}/statistics",
        allow_failure=True
    )


    if not data:

        return {

            "team": team.upper(),

            "available": False,

            "message": (
                "ESPN team statistics endpoint "
                "was unavailable from this server."
            )
        }


    return {

        "team": team.upper(),

        "available": True,

        "data": data
    }


# ---------------------------------------------------------
# TEAM ROSTER
# ---------------------------------------------------------

@app.get("/team/{team}/roster")
def team_roster(team: str):

    data = fetch_json(
        f"{ESPN_SITE}/teams/{team}/roster",
        allow_failure=True
    )


    if not data:

        return {

            "team":
                team.upper(),

            "available":
                False,

            "players":
                []
        }


    players = []


    for group in data.get(
        "athletes",
        []
    ):

        position_group = group.get(
            "position"
        )


        for athlete in group.get(
            "items",
            []
        ):

            players.append({

                "player_id":
                    athlete.get("id"),

                "name":
                    athlete.get("fullName"),

                "display_name":
                    athlete.get("displayName"),

                "position":
                    athlete.get(
                        "position",
                        {}
                    ).get(
                        "abbreviation"
                    ),

                "jersey":
                    athlete.get("jersey"),

                "age":
                    athlete.get("age"),

                "height":
                    athlete.get(
                        "displayHeight"
                    ),

                "weight":
                    athlete.get(
                        "displayWeight"
                    ),

                "status":
                    athlete.get("status"),

                "position_group":
                    position_group
            })


    return {

        "team":
            team.upper(),

        "available":
            True,

        "players":
            players
    }


# ---------------------------------------------------------
# PLAYER PROFILE
# ---------------------------------------------------------

@app.get("/player/{player_id}")
def player(player_id: str):

    data = fetch_json(
        f"{ESPN_WEB}/athletes/{player_id}",
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

@app.get("/player/{player_id}/stats")
def player_stats(
    player_id: str,
    season: int = None
):

    params = {}

    if season:

        params["season"] = season
        params["seasontype"] = 2


    data = fetch_json(

        f"{ESPN_WEB}/athletes/{player_id}/stats",

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

@app.get("/player/{player_id}/gamelog")
def player_gamelog(
    player_id: str,
    season: int = None
):

    params = {}

    if season:
        params["season"] = season


    data = fetch_json(

        f"{ESPN_WEB}/athletes/{player_id}/gamelog",

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

@app.get("/research/{season}/{week}")
def weekly_research(
    season: int,
    week: int
):

    schedule_package = get_week_schedule(
        season,
        week
    )

    games = normalize_schedule(
        schedule_package
    )


    research_games = []


    for game in games:

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

        home_abbr = home.get(
            "abbreviation"
        )

        away_abbr = away.get(
            "abbreviation"
        )


        # -------------------------------------------------
        # GAME DETAILS
        # -------------------------------------------------

        game_data = {}

        if game_id:

            site_summary = fetch_json(

                f"{ESPN_SITE}/summary",

                {
                    "event": game_id
                },

                allow_failure=True
            )


            if site_summary:

                game_data = site_summary

            else:

                game_data = fetch_json(

                    f"{ESPN_CDN}/boxscore",

                    {
                        "xhr": 1,
                        "gameId": game_id
                    },

                    allow_failure=True
                )


        # -------------------------------------------------
        # HOME TEAM STATS
        # -------------------------------------------------

        home_stats = {}

        if home_abbr:

            home_stats = fetch_json(

                f"{ESPN_SITE}/teams/"
                f"{home_abbr}/statistics",

                allow_failure=True
            )


        # -------------------------------------------------
        # AWAY TEAM STATS
        # -------------------------------------------------

        away_stats = {}

        if away_abbr:

            away_stats = fetch_json(

                f"{ESPN_SITE}/teams/"
                f"{away_abbr}/statistics",

                allow_failure=True
            )


        # -------------------------------------------------
        # HOME ROSTER
        # -------------------------------------------------

        home_roster = {}

        if home_abbr:

            home_roster = fetch_json(

                f"{ESPN_SITE}/teams/"
                f"{home_abbr}/roster",

                allow_failure=True
            )


        # -------------------------------------------------
        # AWAY ROSTER
        # -------------------------------------------------

        away_roster = {}

        if away_abbr:

            away_roster = fetch_json(

                f"{ESPN_SITE}/teams/"
                f"{away_abbr}/roster",

                allow_failure=True
            )


        # -------------------------------------------------
        # CREATE GAME RESEARCH OBJECT
        # -------------------------------------------------

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

                "name":
                    home.get("name"),

                "abbreviation":
                    home_abbr,

                "team_id":
                    home.get("team_id"),

                "record":
                    home.get("records"),

                "score":
                    home.get("score"),

                "season_stats":
                    home_stats,

                "roster":
                    home_roster
            },

            "away": {

                "name":
                    away.get("name"),

                "abbreviation":
                    away_abbr,

                "team_id":
                    away.get("team_id"),

                "record":
                    away.get("records"),

                "score":
                    away.get("score"),

                "season_stats":
                    away_stats,

                "roster":
                    away_roster
            },

            "game_data":
                game_data
        })


    return {

        "season":
            season,

        "week":
            week,

        "schedule_source":
            schedule_package["source"],

        "game_count":
            len(research_games),

        "games":
            research_games
    }
