class Result:
    def __init__(self, iteration, success, guesses=None, time_secs=None, difficulty=None):
        self.iteration = iteration
        self.success = success
        self.guesses = int(guesses) if guesses is not None else None
        self.time_secs = time_secs
        self.difficulty = difficulty
