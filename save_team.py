import os


def save_team_to_file(self, team_data):
    os.makedirs("teams", exist_ok=True)
    filename = f"teams/{self.username}_team.txt"
    try:
        with open(filename, "w") as f:
            for mon in team_data:
                details = mon.get("details", "???")
                condition = mon.get("condition", "???")
                moves = mon.get("moves", [])
                move_names = [m.get("move", "???") for m in moves]
                f.write(
                    f"{details} | HP: {condition} | Moves: {', '.join(move_names)}\n"
                )
        print(f"📁 {self.username}: Team saved to {filename}")
    except Exception as e:
        print(f"❌ Failed to write team file for {self.username}: {e}")
