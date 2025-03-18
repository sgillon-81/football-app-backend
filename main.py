from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client, Client
import os

# 🔗 Supabase connection (Replace with your actual credentials)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://izwwqzpvnrijarabwink.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6d3dxenB2bnJpamFyYWJ3aW5rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIxNjA0MTIsImV4cCI6MjA1NzczNjQxMn0.FoB5Zp-NTlJf74VG4NgZ_j0s-n85JHdbdQr425suaQI")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# ✅ CORS Middleware (Allow frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🎯 Data Models
class Player(BaseModel):
    name: str
    position: str = Field(..., pattern="^(midfielder|forward|defender)$")
    foot: str = Field(..., pattern="^(left|right|both)$")
    goalkeeper: bool

class PlayerRating(BaseModel):
    coach: str
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

# ✅ Root Endpoint
@app.get("/")
async def root():
    return {"message": "Football Team API is running!"}

# 🔍 View all players
@app.get("/players")
async def get_players():
    try:
        response = supabase.table("players").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching players: {str(e)}")

# ➕ Add a new player
@app.post("/players")
async def add_player(player: Player):
    try:
        response = supabase.table("players").insert(player.dict()).execute()
        return {"message": "✅ Player added successfully", "player": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error adding player: {str(e)}")

# 🏆 Add or Update Player Ratings
@app.post("/players/{player_name}/ratings")
async def add_or_update_rating(player_name: str, rating: PlayerRating):
    try:
        player_lookup = supabase.table("players").select("id").eq("name", player_name).execute()
        if not player_lookup.data:
            raise HTTPException(status_code=404, detail=f"❌ Player '{player_name}' not found.")

        player_id = player_lookup.data[0]["id"]

        existing_rating = supabase.table("player_ratings").select("*").eq("player_id", player_id).eq("coach", rating.coach).execute()
        if existing_rating.data:
            response = supabase.table("player_ratings").update(rating.dict()).eq("player_id", player_id).eq("coach", rating.coach).execute()
            return {"message": f"✅ Rating updated for '{player_name}' by {rating.coach}", "data": response.data}
        else:
            response = supabase.table("player_ratings").insert({**rating.dict(), "player_id": player_id}).execute()
            return {"message": f"✅ Rating added for '{player_name}' by {rating.coach}", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error adding/updating rating: {str(e)}")

# 🔄 Update player availability (FIXED)
@app.put("/players/{player_name}/availability")
async def update_availability(player_name: str, availability: AvailabilityUpdate):
    try:
        # 🔍 Find the player by name
        player_lookup = supabase.table("players").select("id").eq("name", player_name).execute()

        if not player_lookup.data:
            raise HTTPException(status_code=404, detail=f"❌ Player '{player_name}' not found.")

        player_id = player_lookup.data[0]["id"]  # Extract player ID

        # 🔍 Check if the player already has an availability record
        existing_record = supabase.table("player_availability").select("player_id").eq("player_id", player_id).execute()

        if existing_record.data:
            # ✅ If exists, UPDATE the existing record
            response = supabase.table("player_availability").update({
                "available": availability.available
            }).eq("player_id", player_id).execute()
        else:
            # ✅ If not exists, INSERT a new record
            response = supabase.table("player_availability").insert({
                "player_id": player_id,
                "available": availability.available
            }).execute()

        return {"message": f"✅ Availability updated for {player_name}", "data": response.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error updating availability: {str(e)}")


# 🔍 Fetch Player Availability
@app.get("/players/{player_name}/availability")
async def get_availability(player_name: str):
    try:
        # 🔎 Find player by name
        player_lookup = supabase.table("players").select("id").eq("name", player_name).execute()

        if not player_lookup.data:
            raise HTTPException(status_code=404, detail=f"❌ Player '{player_name}' not found.")

        player_id = player_lookup.data[0]["id"]

        # 🔍 Fetch availability status
        availability_query = supabase.table("player_availability").select("available").eq("player_id", player_id).execute()

        if not availability_query.data:
            return {"player_name": player_name, "available": False}  # Default to unavailable

        return {"player_name": player_name, "available": bool(availability_query.data[0]["available"])}  # ✅ Ensure boolean

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error fetching availability: {str(e)}")

    
# Average Ratings
@app.get("/average_ratings")
async def get_all_average_ratings():
    try:
        # 🏆 Fetch all ratings from the database
        ratings_response = supabase.table("player_ratings").select(
            "player_id", "attack_skill", "defense_skill", "passing", "attitude", "teamwork"
        ).execute()

        if not ratings_response.data:
            return []  # ✅ Return an empty list instead of crashing

        # 🏆 Fetch player names from the database
        players_response = supabase.table("players").select("id", "name").execute()
        player_map = {p["id"]: p["name"] for p in players_response.data}

        player_ratings = {}

        # 🎯 Aggregate player ratings
        for rating in ratings_response.data:
            player_id = rating["player_id"]
            if player_id not in player_ratings:
                player_ratings[player_id] = {
                    "total": {"attack_skill": 0, "defense_skill": 0, "passing": 0, "attitude": 0, "teamwork": 0},
                    "count": 0
                }

            # Sum all ratings
            for key in ["attack_skill", "defense_skill", "passing", "attitude", "teamwork"]:
                player_ratings[player_id]["total"][key] += rating[key]

            player_ratings[player_id]["count"] += 1  # Increment count

        # 🎯 Compute averages safely
        average_ratings = []
        for player_id, data in player_ratings.items():
            avg = {key: round(value / max(1, data["count"]), 1) for key, value in data["total"].items()}
            avg["name"] = player_map.get(player_id, "Unknown Player")  # Get player name
            avg["overall_ability"] = round(
                max(avg["attack_skill"], avg["defense_skill"]) + avg["passing"] + avg["attitude"] + avg["teamwork"], 2
            )
            average_ratings.append(avg)

        return average_ratings  # ✅ Return the structured list

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error fetching average ratings: {str(e)}")
    

# ⚽ Select Teams (with Debugging & Equal Team Handling)
import logging

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/select_teams")
async def select_teams(data: TeamSelectionRequest):
    try:
        logger.info(f"🟢 Received team selection request: {data}")

        opponent_1_name = data.opponent_1_name
        opponent_2_name = data.opponent_2_name
        opponent_1_strength = data.opponent_1_strength
        opponent_2_strength = data.opponent_2_strength

        # 📥 Fetch all available players
        availability_query = supabase.table("player_availability").select("player_id").eq("available", True).execute()
        logger.info(f"📋 Available Players Query Result: {availability_query.data}")

        if not availability_query.data:
            logger.warning("❌ Not enough available players")
            return {"message": "❌ Not enough available players"}

        available_player_ids = [player["player_id"] for player in availability_query.data]

        # 📥 Fetch players' details
        players_query = supabase.table("players").select("id", "name", "position", "foot", "goalkeeper").in_("id", available_player_ids).execute()
        if not players_query.data:
            logger.warning("❌ No player data available")
            return {"message": "❌ No player data available"}

        players = players_query.data

        # 📥 Fetch players' ratings
        ratings_query = supabase.table("player_ratings").select("player_id", "attack_skill", "defense_skill", "passing", "attitude", "teamwork").in_("player_id", available_player_ids).execute()
        if not ratings_query.data:
            logger.warning("❌ No ratings available")
            return {"message": "❌ No ratings available"}

        ratings_dict = {}
        for rating in ratings_query.data:
            player_id = rating["player_id"]
            if player_id not in ratings_dict:
                ratings_dict[player_id] = {"attack_skill": [], "defense_skill": [], "passing": [], "attitude": [], "teamwork": []}
            for key in ["attack_skill", "defense_skill", "passing", "attitude", "teamwork"]:
                ratings_dict[player_id][key].append(rating[key])

        # 🎯 Compute average ratings for each player
        for player_id in ratings_dict:
            for key in ratings_dict[player_id]:
                ratings_dict[player_id][key] = sum(ratings_dict[player_id][key]) / len(ratings_dict[player_id][key])

        # 🎯 Assign ability score
        for player in players:
            player_id = player["id"]
            if player_id in ratings_dict:
                player["attack_skill"] = ratings_dict[player_id]["attack_skill"]
                player["defense_skill"] = ratings_dict[player_id]["defense_skill"]
                player["passing"] = ratings_dict[player_id]["passing"]
                player["attitude"] = ratings_dict[player_id]["attitude"]
                player["teamwork"] = ratings_dict[player_id]["teamwork"]
                player["ability"] = (
                    max(player["attack_skill"], player["defense_skill"]) +
                    player["passing"] + player["attitude"] + player["teamwork"]
                )
            else:
                player["ability"] = 0  # Fallback for players with no ratings

        # 📊 Sort players by ability (descending order)
        players_sorted = sorted(players, key=lambda x: x["ability"], reverse=True)
        logger.info(f"📊 Sorted Players: {players_sorted}")

        # 📌 Determine team selection strategy
        total_players = len(players_sorted)
        players_per_team = total_players // 2

        team1, team2 = [], []

        if abs(opponent_1_strength - opponent_2_strength) >= 2:
            # One opponent is much stronger
            strong_team, weak_team = (team1, team2) if opponent_1_strength > opponent_2_strength else (team2, team1)
            strong_team.extend(players_sorted[:players_per_team])
            weak_team.extend(players_sorted[players_per_team:])
        
        elif abs(opponent_1_strength - opponent_2_strength) == 1:
            # One opponent is slightly stronger
            top_half = players_sorted[:players_per_team]
            bottom_half = players_sorted[players_per_team:]
            for i in range(players_per_team):
                if i < int(players_per_team * 0.66):
                    team1.append(top_half[i])
                else:
                    team2.append(top_half[i])
            for i in range(players_per_team):
                if i < int(players_per_team * 0.33):
                    team1.append(bottom_half[i])
                else:
                    team2.append(bottom_half[i])
        
        else:
            # Teams should be evenly balanced
            for i, player in enumerate(players_sorted):
                if i % 2 == 0:
                    team1.append(player)
                else:
                    team2.append(player)

        # 📊 Compute team averages
        def calculate_team_averages(team):
            return {
                "average_ability": sum(p["ability"] for p in team) / len(team) if team else 0
            }

        team1_avg = calculate_team_averages(team1)
        team2_avg = calculate_team_averages(team2)

        teams = {
            opponent_1_name: {
                "players": [{"name": p["name"], "position": p["position"], "goalkeeper": p["goalkeeper"]} for p in team1],
                "average_ability": round(team1_avg["average_ability"], 2)
            },
            opponent_2_name: {
                "players": [{"name": p["name"], "position": p["position"], "goalkeeper": p["goalkeeper"]} for p in team2],
                "average_ability": round(team2_avg["average_ability"], 2)
            }
        }

        logger.info(f"🏆 Final Teams: {teams}")
        return {"teams": teams}

    except Exception as e:
        logger.error(f"❌ Error in team selection: {e}")
        raise HTTPException(status_code=500, detail="Team selection failed.")



# 🔥 Run FastAPI Server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
