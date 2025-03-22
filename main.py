from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client, Client
from typing import Literal, Optional, List
from uuid import UUID
import os
import logging
from datetime import date

# 🔗 Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://izwwqzpvnrijarabwink.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6d3dxenB2bnJpamFyYWJ3aW5rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIxNjA0MTIsImV4cCI6MjA1NzczNjQxMn0.FoB5Zp-NTlJf74VG4NgZ_j0s-n85JHdbdQr425suaQI")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ✅ FastAPI app & CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🎯 Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Constants
TeamName = Literal["Peebles 2013s", "Peebles 2014s", "Peebles 2015s", "Peebles 2016s"]
Positions = Literal["GK", "Def", "LB", "RB", "Mid", "LW", "RW", "Fwd"]

# ✅ Models
class Player(BaseModel):
    name: str
    position: str = Field(..., pattern="^(midfielder|forward|defender)$")
    foot: str = Field(..., pattern="^(left|right|both)$")
    goalkeeper: bool
    team_name: TeamName

class PlayerRating(BaseModel):
    coach_id: UUID
    attack_skill: int
    defense_skill: int
    passing: int
    attitude: int
    teamwork: int

class AvailabilityUpdate(BaseModel):
    available: bool

class TeamSelectionRequest(BaseModel):
    opponent_1_name: str
    opponent_2_name: str
    opponent_1_strength: int
    opponent_2_strength: int
    team_name: TeamName

class Coach(BaseModel):
    forename: str
    surname: str
    team_name: TeamName

class MatchCreate(BaseModel):
    team_name: TeamName
    coach_id: UUID
    opponent: str
    date: date
    home_or_away: Literal["Home", "Away"]
    game_comments: Optional[str] = None
    areas_for_dev: Optional[List[str]] = []

class MatchPlayerStat(BaseModel):
    player_id: int
    coach_id: UUID
    primary_position: Positions
    minutes_played: Optional[int] = None
    rating: Optional[int] = None
    crucial_tackles: Optional[int] = 0
    assists: Optional[int] = 0
    goals: Optional[int] = 0
    comments: Optional[str] = None
    outstanding_performance: Optional[bool] = False

class MatchWithStats(BaseModel):
    match: MatchCreate
    player_stats: List[MatchPlayerStat]

# ✅ Root
@app.get("/")
async def root():
    return {"message": "Football Team API is running!"}

# 🔍 Players
@app.get("/players")
async def get_players(team_name: Optional[str] = Query(None)):
    try:
        query = supabase.table("players").select("*")
        if team_name:
            query = query.eq("team_name", team_name)
        response = query.execute()
        return sorted(response.data, key=lambda p: p["name"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/players")
async def add_player(player: Player):
    try:
        response = supabase.table("players").insert(player.dict()).execute()
        return {"message": "✅ Player added", "player": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/players/{player_name}/ratings")
async def add_or_update_rating(player_name: str, rating: PlayerRating):
    try:
        player_lookup = supabase.table("players").select("id").eq("name", player_name).execute()
        if not player_lookup.data:
            raise HTTPException(status_code=404, detail="Player not found")
        player_id = player_lookup.data[0]["id"]

        coach_lookup = supabase.table("coaches").select("id").eq("id", str(rating.coach_id)).execute()
        if not coach_lookup.data:
            raise HTTPException(status_code=404, detail="Coach not found")

        existing = supabase.table("player_ratings") \
            .select("*") \
            .eq("player_id", player_id) \
            .eq("coach_id", str(rating.coach_id)) \
            .execute()

        payload = {**rating.dict(), "player_id": player_id}
        if existing.data:
            response = supabase.table("player_ratings").update(payload).eq("player_id", player_id).eq("coach_id", str(rating.coach_id)).execute()
        else:
            response = supabase.table("player_ratings").insert(payload).execute()

        return {"message": "✅ Rating submitted", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔄 Availability
@app.put("/players/{player_name}/availability")
async def update_availability(player_name: str, availability: AvailabilityUpdate):
    try:
        player_lookup = supabase.table("players").select("id").eq("name", player_name).execute()
        if not player_lookup.data:
            raise HTTPException(status_code=404, detail="Player not found")
        player_id = player_lookup.data[0]["id"]

        exists = supabase.table("player_availability").select("*").eq("player_id", player_id).execute()
        if exists.data:
            response = supabase.table("player_availability").update({"available": availability.available}).eq("player_id", player_id).execute()
        else:
            response = supabase.table("player_availability").insert({"player_id": player_id, "available": availability.available}).execute()

        return {"message": "✅ Availability updated", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/players/{player_name}/availability")
async def get_availability(player_name: str):
    try:
        player_lookup = supabase.table("players").select("id").eq("name", player_name).execute()
        if not player_lookup.data:
            raise HTTPException(status_code=404, detail="Player not found")
        player_id = player_lookup.data[0]["id"]

        availability = supabase.table("player_availability").select("available").eq("player_id", player_id).execute()
        return {"player_name": player_name, "available": bool(availability.data[0]["available"])} if availability.data else {"player_name": player_name, "available": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🧠 Matches with player stats
@app.post("/matches")
async def create_match_with_stats(payload: MatchWithStats):
    try:
        match = payload.match
        player_stats = payload.player_stats

        logger.info(f"📦 Match received: {match}")
        logger.info(f"👥 Player stats received: {player_stats}")

        # Check if match already exists
        existing = supabase.table("matches").select("id") \
            .eq("team_name", match.team_name) \
            .eq("opponent", match.opponent) \
            .eq("date", match.date).execute()

        if existing.data:
            match_id = existing.data[0]["id"]
            logger.info(f"🔁 Reusing existing match ID: {match_id}")
        else:
            # Serialize UUID and date to strings
            match_data = match.dict(exclude={"coach_id"})  # ✅ Exclude coach_id from match insert
            match_data["date"] = match_data["date"].isoformat()

            match_insert = supabase.table("matches").insert(match_data).execute()
            match_id = match_insert.data[0]["id"]
            logger.info(f"🆕 Created new match ID: {match_id}")

        # Add player stats
        for stat in player_stats:
            stat_data = stat.dict()
            stat_data["match_id"] = match_id
            stat_data["coach_id"] = str(stat_data["coach_id"])
            supabase.table("match_player_stats").insert(stat_data).execute()

        return {"message": "✅ Match and stats submitted", "match_id": match_id}

    except Exception as e:
        logger.error(f"❌ Error submitting match and stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




# 👤 Coach management
@app.post("/coaches")
async def add_coach(coach: Coach):
    try:
        response = supabase.table("coaches").insert(coach.dict()).execute()
        return {"message": "✅ Coach added", "coach": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/coaches")
async def get_coaches(team_name: Optional[str] = Query(None)):
    try:
        query = supabase.table("coaches").select("*")
        if team_name:
            query = query.eq("team_name", team_name)
        response = query.execute()
        return sorted(response.data, key=lambda c: (c["surname"], c["forename"]))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Now top-level — this fixes the 404!
@app.post("/select_teams")
async def select_teams(data: TeamSelectionRequest):
    try:
        # 1. Get list of available players for the selected team
        available_query = supabase.table("player_availability").select("player_id").eq("available", True).execute()
        available_ids = [x["player_id"] for x in available_query.data]

        players_query = supabase.table("players").select("*").in_("id", available_ids).eq("team_name", data.team_name).execute()
        players = players_query.data or []

        if len(players) < 2:
            return {
                "message": "❌ Not enough available players to form two teams",
                "teams": {},
                "average_ability": None
            }

        # 2. Get player ratings
        ratings_query = supabase.table("player_ratings").select("*").in_("player_id", available_ids).execute()
        ratings_dict = {}
        for r in ratings_query.data:
            pid = r["player_id"]
            ratings_dict.setdefault(pid, {"attack_skill": [], "defense_skill": [], "passing": [], "attitude": [], "teamwork": []})
            for key in ratings_dict[pid]:
                ratings_dict[pid][key].append(r[key])

        for player in players:
            pid = player["id"]
            if pid in ratings_dict:
                for key in ratings_dict[pid]:
                    player[key] = sum(ratings_dict[pid][key]) / len(ratings_dict[pid][key])
                player["ability"] = (
                    max(player["attack_skill"], player["defense_skill"]) +
                    player["passing"] + player["attitude"] + player["teamwork"]
                )
            else:
                player["ability"] = 0  # Fallback if no ratings

        # 3. Sort and assign players
        players_sorted = sorted(players, key=lambda p: p["ability"], reverse=True)
        team1, team2 = [], []
        players_per_team = len(players_sorted) // 2

        if abs(data.opponent_1_strength - data.opponent_2_strength) >= 2:
            strong, weak = (team1, team2) if data.opponent_1_strength > data.opponent_2_strength else (team2, team1)
            strong.extend(players_sorted[:players_per_team])
            weak.extend(players_sorted[players_per_team:])
        elif abs(data.opponent_1_strength - data.opponent_2_strength) == 1:
            top = players_sorted[:players_per_team]
            bottom = players_sorted[players_per_team:]
            for i in range(players_per_team):
                (team1 if i < players_per_team * 0.66 else team2).append(top[i])
            for i in range(players_per_team):
                (team1 if i < players_per_team * 0.33 else team2).append(bottom[i])
        else:
            for i, p in enumerate(players_sorted):
                (team1 if i % 2 == 0 else team2).append(p)

        def sort_team(team): 
            return sorted(team, key=lambda p: (
                {"defender": 0, "midfielder": 1, "forward": 2}.get(p["position"], 99),
                p["name"]
            ))

        def avg(team): return round(sum(p["ability"] for p in team) / len(team), 2) if team else 0

        return {
            "message": "✅ Teams generated",
            "teams": {
                data.opponent_1_name: {
                    "players": [{"name": p["name"], "position": p["position"], "goalkeeper": p["goalkeeper"]} for p in sort_team(team1)],
                    "average_ability": avg(team1)
                },
                data.opponent_2_name: {
                    "players": [{"name": p["name"], "position": p["position"], "goalkeeper": p["goalkeeper"]} for p in sort_team(team2)],
                    "average_ability": avg(team2)
                }
            }
        }

    except Exception as e:
        logger.error(f"❌ Error in team selection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




# 🔥 Entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
