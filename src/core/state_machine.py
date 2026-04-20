"""
Модуль core/state_machine.py
Машина состояний (State Machine) для переключения игровых состояний.
"""


class StateMachine:
    def __init__(self, initial_state=None):
        self.state = initial_state

    def change(self, new_state):
        self.state = new_state

    def handle_events(self, events):
        if self.state:
            self.state.handle_events(events)

    def update(self, dt):
        if self.state:
            self.state.update(dt)

    def draw(self, surface):
        if self.state:
            self.state.draw(surface)