"""
Manages the story
"""
from datetime import datetime

import eel
from PyQt5.QtCore import QSettings

from rlbot_gui.story.story_challenge_setup import run_challenge, configure_challenge


CURRENT_STATE = None

##### EEL -- these are the hooks exposed to JS
@eel.expose
def story_story_test():
    print("In story_story_test()")
    eel.spawn(story_test)


@eel.expose
def story_load_save():
    """Loads a previous save if available."""
    global CURRENT_STATE
    settings = QSettings("rlbotgui", "story_save")
    state = settings.value("save")
    if state:
        print(f"Save state: {state}")
        CURRENT_STATE = StoryState.from_dict(state)
    return state


@eel.expose
def story_new_save(name, color_secondary):
    global CURRENT_STATE
    CURRENT_STATE = StoryState.new(name, color_secondary)
    return story_save_state()


@eel.expose
def story_delete_save():
    global CURRENT_STATE
    CURRENT_STATE = None
    QSettings("rlbotgui", "story_save").remove("save")


@eel.expose
def story_save_state():
    settings = QSettings("rlbotgui", "story_save")
    serialized = CURRENT_STATE.__dict__
    settings.setValue("save", serialized)
    return serialized


@eel.expose
def launch_challenge(challenge_id):
    if challenge_id == "INTRO-1":
        launch_intro_1()


@eel.expose
def purchase_upgrade(id, current_currency):
    CURRENT_STATE.add_purchase(id, current_currency)
    flush_save_state()

##### Reverse eel's


def flush_save_state():
    serialized = story_save_state()
    eel.loadUpdatedSaveState(serialized)


#################################


class StoryState:
    """Represents users game state"""

    def __init__(self):
        self.version = 1
        self.team_info = {"name": "", "color_secondary": ""}
        self.teammates = []
        self.challenges_attempts = {}  # many entries per challenge
        self.challenges_completed = {}  # one entry per challenge

        self.upgrades = {"currency": 0}

    def add_purchase(self, id, current_currency):
        """The only validation we do is to make sure current_currency is correct.
        This is NOT a security mechanism, this is a bug prevention mechanism to
        avoid accidental double clicks.
        """
        if (self.upgrades["currency"] == current_currency):
            self.upgrades[id] = True
            self.upgrades["currency"] -= 1


    def add_match_result(
        self, challenge_id: str, challenge_completed: bool, game_results
    ):
        """game_results should be the output of packet_to_game_results.
        You have to call it anyways to figure out if the player 
        completed the challenge so that's why we don't call it again here.
        """
        if challenge_id not in self.challenges_attempts:
            # no defaultdict because we serialize the data
            self.challenges_attempts[challenge_id] = []
        self.challenges_attempts[challenge_id].append(
            {"game_results": game_results, "challenge_completed": challenge_completed}
        )

        if challenge_completed:
            index = len(self.challenges_attempts[challenge_id]) - 1
            self.challenges_completed[challenge_id] = index
            self.upgrades["currency"] += 1


    @staticmethod
    def new(name, color_secondary):
        s = StoryState()
        s.team_info = {"name": name, "color_secondary": color_secondary}
        return s

    @staticmethod
    def from_dict(source):
        """No validation done here."""
        s = StoryState()
        s.__dict__.update(source)
        return s


def launch_intro_1():
    print("In launch_intro_1")

    intro_1 = {
        "id": "INTRO-1",
        "humanTeamSize": 1,
        "opponentBots": ["psyonix-pro"],
        "max_score": "3 Goals",
        "map": "BeckwithPark",
        "display": "Win something so we know you can drive"
    }
    match_config = configure_challenge(intro_1, CURRENT_STATE, [])
    completed, results = run_challenge(match_config, intro_1, CURRENT_STATE.upgrades)
    CURRENT_STATE.add_match_result(intro_1["id"], completed, results)

    flush_save_state()