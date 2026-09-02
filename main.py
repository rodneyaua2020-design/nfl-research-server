from fastapi import FastAPI, HTTPException
import requests

app = FastAPI(
    title="NFL Research Server",
    description="NFL schedules, game stats, team stats and player stats",
    version="1.0"
)

ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ESPN_WEB = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch_json(url, params=None):
    try:
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to retrieve NFL data: {str(e)}"
        )


# ---------------------------------------------------------
# SERVER STATUS
# ---------------------------------------------------------

@app.get("/")
def home():
    return {
        "status": "NFL Research Server is running",
        "available_endpoints": {
            "schedule": "/schedule/{season}/{week}",
            "game_stats": "/game/{game_id}",
            "team_stats": "/team/{team}/stats",
            "team_roster": "/team/{team}/roster",
            "player": "/player/{player_id}",
            "player_stats": "/player/{player_id}/stats",
            "player_gamelog": "/player/{player_id}/gamelog"
        }
    }


# ---------------------------------------------------------
# NFL WEEKLY SCHEDULE
# ---------------------------------------------------------

@app.get("/schedule/{season}/{week}")
def schedule(season: int, week: int):

    url = (
        f"{ESPN_SITE}/scoreboard"
    )

    params = {
        "dates": season,
        "seasontype": 2,
        "week": week
    }

    data = fetch_json(url, params)

    games = []

    for event in data.get("events", []):

        competitions = event.get("competitions", [])

        if not competitions:
            continue

        competition = competitions[0]

        teams = competition.get("competitors", [])

        try:
            home = next(
                x for x in teams
                if x.get("homeAway") == "home"
            )

            away = next(
                x for x in teams
                if x.get("homeAway") == "away"
            )

        except StopIteration:
            continue

        games.append({
            "game_id": event.get("id"),
            "game": event.get("name"),
            "date": event.get("date"),
            "home": home.get("team", {}).get("displayName"),
            "home_abbreviation": home.get("team", {}).get("abbreviation"),
            "away": away.get("team", {}).get("displayName"),
            "away_abbreviation": away.get("team", {}).get("abbreviation"),
            "status": event.get("status", {})
                .get("type", {})
                .get("description")
        })

    return {
        "season": season,
        "week": week,
        "games": games
    }


# ---------------------------------------------------------
# GAME STATS / BOX SCORE
# ---------------------------------------------------------

@app.get("/game/{game_id}")
def game_stats(game_id: str):

    url = f"{ESPN_SITE}/summary"

    data = fetch_json(
        url,
        {"event": game_id}
    )

    boxscore = data.get("boxscore", {})

    team_stats = []

    for entry in boxscore.get("teams", []):

        team = entry.get("team", {})

        stats = {}

        for stat in entry.get("statistics", []):
            stats[stat.get("name")] = stat.get(
                "displayValue",
                stat.get("value")
            )

        team_stats.append({
            "team_id": team.get("id"),
            "team": team.get("displayName"),
            "abbreviation": team.get("abbreviation"),
            "stats": stats
        })

    player_stats = []

    for team_entry in boxscore.get("players", []):

        team = team_entry.get("team", {})

        categories = []

        for category in team_entry.get("statistics", []):

            labels = category.get("labels", [])

            players = []

            for athlete_entry in category.get("athletes", []):

                athlete = athlete_entry.get("athlete", {})

                stats = athlete_entry.get("stats", [])

                player_stat_dict = {}

                for i, label in enumerate(labels):
                    if i < len(stats):
                        player_stat_dict[label] = stats[i]

                players.append({
                    "player_id": athlete.get("id"),
                    "name": athlete.get("displayName"),
                    "position": athlete.get(
                        "position", {}
                    ).get("abbreviation"),
                    "stats": player_stat_dict
                })

            categories.append({
                "category": category.get("name"),
                "players": players
            })

        player_stats.append({
            "team": team.get("displayName"),
            "abbreviation": team.get("abbreviation"),
            "categories": categories
        })

    return {
        "game_id": game_id,
        "header": data.get("header"),
        "team_stats": team_stats,
        "player_stats": player_stats,
        "leaders": data.get("leaders"),
        "scoring_plays": data.get("scoringPlays"),
        "drives": data.get("drives"),
        "win_probability": data.get("winprobability"),
        "injuries": data.get("injuries")
    }


# ---------------------------------------------------------
# TEAM SEASON STATS
# Example:
# /team/kc/stats
# /team/buf/stats
# ---------------------------------------------------------

@app.get("/team/{team}/stats")
def team_stats(team: str):

    url = f"{ESPN_SITE}/teams/{team}/statistics"

    data = fetch_json(url)

    return {
        "team": team.upper(),
        "data": data
    }


# ---------------------------------------------------------
# TEAM ROSTER
# ---------------------------------------------------------

@app.get("/team/{team}/roster")
def team_roster(team: str):

    url = f"{ESPN_SITE}/teams/{team}/roster"

    data = fetch_json(url)

    players = []

    for group in data.get("athletes", []):

        position_group = group.get("position")

        for athlete in group.get("items", []):

            players.append({
                "player_id": athlete.get("id"),
                "name": athlete.get("fullName"),
                "display_name": athlete.get("displayName"),
                "position": athlete.get(
                    "position", {}
                ).get("abbreviation"),
                "jersey": athlete.get("jersey"),
                "age": athlete.get("age"),
                "height": athlete.get("displayHeight"),
                "weight": athlete.get("displayWeight"),
                "status": athlete.get("status"),
                "position_group": position_group
            })

    return {
        "team": team.upper(),
        "players": players
    }


# ---------------------------------------------------------
# PLAYER INFORMATION
# Example:
# /player/4430807
# ---------------------------------------------------------

@app.get("/player/{player_id}")
def player(player_id: str):

    url = f"{ESPN_WEB}/athletes/{player_id}"

    data = fetch_json(url)

    return data


# ---------------------------------------------------------
# PLAYER SEASON / CAREER STATS
# ---------------------------------------------------------

@app.get("/player/{player_id}/stats")
def player_stats(
    player_id: str,
    season: int = None
):

    url = f"{ESPN_WEB}/athletes/{player_id}/stats"

    params = {}

    if season:
        params["season"] = season
        params["seasontype"] = 2

    data = fetch_json(
        url,
        params if params else None
    )

    return {
        "player_id": player_id,
        "season": season,
        "data": data
    }


# ---------------------------------------------------------
# PLAYER GAME LOG
# ---------------------------------------------------------

@app.get("/player/{player_id}/gamelog")
def player_gamelog(
    player_id: str,
    season: int = None
):

    url = f"{ESPN_WEB}/athletes/{player_id}/gamelog"

    params = {}

    if season:
        params["season"] = season

    data = fetch_json(
        url,
        params if params else None
    )

    return {
        "player_id": player_id,
        "season": season,
        "data": data
    }
