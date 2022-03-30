class Result:
    def __init__(self, iteration, success, guesses, time_secs=None, difficulty=None):
        self.iteration = iteration
        self.success = success
        self.guesses = int(guesses)
        self.time_secs = time_secs
        self.difficulty = difficulty
