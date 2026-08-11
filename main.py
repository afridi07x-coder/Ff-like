import asyncio
import httpx
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="Universal Like Merger API")

# Only LIVE APIs (tested with uid=1558038734).
# Removed dead ones:
#   like-api-ob54-phi.vercel.app  -> DEPLOYMENT_NOT_FOUND (404)
#   boss20.vercel.app             -> DEPLOYMENT_DISABLED (402)
#   like-api-eight-kohl.vercel.app-> "Server error or Invalid Token/UID"
#   ajay-100-like-api-gnbm        -> 500 "Failed to retrieve initial player info."
ROCKY_API = "https://rockgamer.vercel.app/like"
AUTOLIKE_API = "https://autolikeapi-eta.vercel.app/like"
SRC_TEST_API = "https://like-api-src-test.vercel.app/like"


def pick(data: dict, *keys):
    for k in keys:
        if data.get(k):
            return data.get(k)
    return None


@app.get("/")
async def home():
    return {"status": "API is running successfully!"}


@app.get("/like")
async def merge_likes(
    uid: str = Query(..., description="Player UID"),
    server_name: str = Query(..., description="Server/Region name"),
):
    total_likes_given = 0
    likes_before = None
    likes_after = None
    player_nickname = "Unknown"

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        # 1. Rocky API first
        try:
            res1 = await client.get(
                ROCKY_API, params={"uid": uid, "server_name": server_name}
            )
            if res1.status_code == 200:
                data = res1.json()
                if "LikesGivenByAPI" in data or data.get("status") in [1, 2]:
                    total_likes_given += data.get("LikesGivenByAPI", 0)
                    likes_before = pick(data, "LikesbeforeCommand", "LikesBeforeCommand")
                    likes_after = pick(data, "LikesafterCommand", "LikesAfterCommand")
                    if data.get("PlayerNickname"):
                        player_nickname = data.get("PlayerNickname")
        except Exception as e:
            print(f"Rocky API Error: {e}")

        # 2. Remaining live APIs (parallel)
        other_apis = [
            (AUTOLIKE_API, {"uid": uid, "server_name": server_name, "key": "JMLB"}),
            (SRC_TEST_API, {"uid": uid, "server_name": server_name}),
        ]

        tasks = [client.get(url, params=p) for url, p in other_apis]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    for res in responses:
        if isinstance(res, httpx.Response) and res.status_code == 200:
            try:
                data = res.json()
                if "LikesGivenByAPI" in data or data.get("status") in [1, 2]:
                    total_likes_given += data.get("LikesGivenByAPI", 0)

                    before = pick(data, "LikesbeforeCommand", "LikesBeforeCommand")
                    after = pick(data, "LikesafterCommand", "LikesAfterCommand")

                    if likes_before is None and before:
                        likes_before = before
                    if after:
                        likes_after = after

                    nickname = data.get("PlayerNickname")
                    if player_nickname == "Unknown" and nickname and nickname != "NA":
                        player_nickname = nickname
            except Exception as e:
                print(f"Error parsing JSON: {e}")

    if likes_before is None and likes_after is None:
        raise HTTPException(
            status_code=500,
            detail="All upstream Like APIs failed to respond properly.",
        )

    return {
        "LikesGivenByAPI": total_likes_given,
        "LikesafterCommand": likes_after if likes_after else likes_before,
        "LikesbeforeCommand": likes_before,
        "PlayerNickname": player_nickname,
        "UID": int(uid) if uid.isdigit() else uid,
    }
