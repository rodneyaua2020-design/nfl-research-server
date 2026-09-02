# ---------------------------------------------------------
# WEEKLY RESEARCH PACKAGE
# Example:
# /research/2026/1
# ---------------------------------------------------------

@app.get("/research/{season}/{week}")
def weekly_research(season: int, week: int):

    # 1. Get weekly schedule
    schedule_url = f"{ESPN_SITE}/scoreboard"

    schedule_data = fetch_json(
        schedule_url,
        {
            "dates": season,
            "seasontype": 2,
            "week": week
        }
    )

    research_games = []

    # 2. Loop through every game
    for event in schedule_data.get("events", []):

        game_id = event.get("id")

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

        home_team = home.get("team", {})
        away_team = away.get("team", {})

        home_abbr = home_team.get("abbreviation")
        away_abbr = away_team.get("abbreviation")

        # ---------------------------------------------
        # 3. Get detailed game information
        # ---------------------------------------------

        game_summary = {}

        if game_id:

            try:
                game_summary = fetch_json(
                    f"{ESPN_SITE}/summary",
                    {"event": game_id}
                )

            except Exception:
                game_summary = {}

        # ---------------------------------------------
        # 4. Team box score statistics
        # ---------------------------------------------

        team_stats = []

        boxscore = game_summary.get("boxscore", {})

        for entry in boxscore.get("teams", []):

            team = entry.get("team", {})

            stats = {}

            for stat in entry.get("statistics", []):

                stat_name = stat.get("name")

                stat_value = stat.get(
                    "displayValue",
                    stat.get("value")
                )

                if stat_name:
                    stats[stat_name] = stat_value

            team_stats.append({
                "team": team.get("displayName"),
                "abbreviation": team.get("abbreviation"),
                "stats": stats
            })

        # ---------------------------------------------
        # 5. Player statistics
        # ---------------------------------------------

        player_stats = []

        for team_entry in boxscore.get("players", []):

            team = team_entry.get("team", {})

            categories = []

            for category in team_entry.get("statistics", []):

                labels = category.get("labels", [])

                category_players = []

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

                    stats = {}

                    for index, label in enumerate(labels):

                        if index < len(raw_stats):
                            stats[label] = raw_stats[index]

                    category_players.append({
                        "player_id": athlete.get("id"),
                        "name": athlete.get("displayName"),
                        "position": athlete.get(
                            "position",
                            {}
                        ).get("abbreviation"),
                        "stats": stats
                    })

                categories.append({
                    "category": category.get("name"),
                    "players": category_players
                })

            player_stats.append({
                "team": team.get("displayName"),
                "abbreviation": team.get("abbreviation"),
                "categories": categories
            })

        # ---------------------------------------------
        # 6. Home team season stats
        # ---------------------------------------------

        home_season_stats = {}

        if home_abbr:

            try:
                home_season_stats = fetch_json(
                    f"{ESPN_SITE}/teams/{home_abbr}/statistics"
                )

            except Exception:
                home_season_stats = {}

        # ---------------------------------------------
        # 7. Away team season stats
        # ---------------------------------------------

        away_season_stats = {}

        if away_abbr:

            try:
                away_season_stats = fetch_json(
                    f"{ESPN_SITE}/teams/{away_abbr}/statistics"
                )

            except Exception:
                away_season_stats = {}

        # ---------------------------------------------
        # 8. Add everything to research package
        # ---------------------------------------------

        research_games.append({

            "game_id": game_id,

            "game": event.get("name"),

            "date": event.get("date"),

            "status": event.get(
                "status",
                {}
            ).get(
                "type",
                {}
            ).get("description"),

            "home": {
                "name": home_team.get("displayName"),
                "abbreviation": home_abbr,
                "record": home.get("records"),
                "score": home.get("score"),
                "season_stats": home_season_stats
            },

            "away": {
                "name": away_team.get("displayName"),
                "abbreviation": away_abbr,
                "record": away.get("records"),
                "score": away.get("score"),
                "season_stats": away_season_stats
            },

            "game_team_stats": team_stats,

            "game_player_stats": player_stats,

            "leaders": game_summary.get("leaders"),

            "injuries": game_summary.get("injuries"),

            "drives": game_summary.get("drives"),

            "scoring_plays": game_summary.get(
                "scoringPlays"
            ),

            "win_probability": game_summary.get(
                "winprobability"
            ),

            "pickcenter": game_summary.get("pickcenter")
        })

    return {
        "season": season,
        "week": week,
        "game_count": len(research_games),
        "games": research_games
    }@app.get("/research/{season}/{week}")
    def weekly_research(season: int, week: int):
