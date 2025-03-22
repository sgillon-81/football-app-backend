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

# 🔥 Entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
