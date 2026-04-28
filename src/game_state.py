class GameState:
    MAIN_MENU = "main_menu"
    EXPLORING = "exploring"
    DIALOGUE = "exploring_dialogue"
    TRANSITION_BATTLE = "transition_battle"
    BATTLE = "battle"
    PAUSE = "pause_menu"
    TRANSITION_LOCATION = "transition_location"
    CREDITS = "credits"

    def __init__(self):
        # Множество побеждённых боссов (location_id: int)
        self.defeated_bosses: set[int] = set()

    def defeat_boss(self, location_id: int):
        self.defeated_bosses.add(location_id)

    def is_boss_defeated(self, location_id: int) -> bool:
        return location_id in self.defeated_bosses