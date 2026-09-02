from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/")
def home():
    return {"status": "NFL Research Server is running"}

@app.get("/schedule/{season}/{week}")
def schedule(season: int, week: int):
    url = (
        "https://site.api.espn.com/apis/site/v2/"
        f"sports/football/nfl/scoreboard?dates={season}&seasontype=2&week={week}"
    )

    data = requests.get(url, timeout=20).json()

    games = []

    for event in data.get("events", []):
        competition = event["competitions"][0]

        teams = competition["competitors"]

        home = next(x for x in teams if x["homeAway"] == "home")
        away = next(x for x in teams if x["homeAway"] == "away")

        games.append({
            "game": event["name"],
            "date": event["date"],
            "home": home["team"]["displayName"],
            "away": away["team"]["displayName"]
        })

    return {
        "season": season,
        "week": week,
        "games": games
    }
