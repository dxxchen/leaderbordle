import re

from abc import ABC, abstractmethod
from common import Result

class _Variant(ABC):
    """An abstract Wordle variant."""

    @abstractmethod
    def name(self):
        """Returns the variant name."""
        pass

    @abstractmethod
    def url(self):
        """Returns the URL for the variant."""

    def emoji(self):
        """Returns an emoji representing this variant."""
        return ''

    def info(self):
        """Returns an info string describing the variant."""
        return 'No information provided.'

    @abstractmethod
    def parse(self, content):
        """Parses message content into a Result.

        Args:
          content:
            The string content of the message to parse.

        Returns:
            A Result object representing the result of an attempt or None if the message content
            does not represent an attempt of this variant.
        """
        pass


class _StandardVariant(_Variant):
    """An abstract variant whose message content mostly follows the Wordle standard.

    The Wordle standard message content is of the form
    '<name> <iteration> <guesses|X>/<max_guesses>'.

    Subclasses must implement _matcher() to return a regular expression with the following named
    capture groups:
      * iteration - the iteration of the attempt.
      * guesses - the number of guesses made.
      * hard - whether the attempt used hard mode. If the variant does not support hard mode, this
        must be an empty capture group.
    """

    def __init__(self):
        self.matcher = self._matcher()

    @abstractmethod
    def _matcher(self):
        """Returns an re.Pattern that matches an attempt."""
        pass

    def parse(self, content):
        match = self.matcher.match(content)
        if match is None:
            return None

        iteration = match.group('iteration')
        success = match.group('guesses') != 'X'
        guesses = match.group('guesses') if success else 6
        difficulty = 'hard' if match.group('hard') == '*' else ''

        return Result(
            iteration,
            success,
            guesses,
            difficulty=difficulty)


class Framed(_Variant):
    def __init__(self):
        self.matcher = re.compile('Framed \#(?P<iteration>\d+)\n+.*?(?P<guess_emojis>[🟥🟩 ]+)')

    def name(self):
        return 'Framed'

    def url(self):
        return 'https://framed.wtf/'

    def emoji(self):
        return '🎥'

    def info(self):
        return 'Guess a movie from six still frames.'

    def parse(self, content):
        match = self.matcher.match(content)
        if match is None:
            return None

        iteration = match.group('iteration')
        success = '🟩' in match.group('guess_emojis')
        guesses = match.group('guess_emojis').replace(' ', '').index('🟩') + 1 if success else 6

        return Result(iteration, success, guesses)


class Heardle(_Variant):
    def __init__(self):
        self.matcher = re.compile('\#Heardle \#(?P<iteration>\d+)\n+(?P<success>[🔈🔉🔊🔇])(?P<guess_emojis>.*)')

    def name(self):
        return 'Heardle'

    def url(self):
        return 'https://www.heardle.app/'

    def emoji(self):
        return '🔉'

    def info(self):
        return 'Guess a song from its intro.'

    def parse(self, content):
        match = self.matcher.match(content)
        if match is None:
            return None

        iteration = match.group('iteration')
        success = match.group('success') != '🔇'
        guesses = match.group('guess_emojis').index('🟩') + 1 if success else 6

        return Result(iteration, success, guesses)


class Lewdle(_StandardVariant):
    def name(self):
        return 'Lewdle'

    def url(self):
        return 'https://www.lewdlegame.com/'

    def emoji(self):
        return '🍆'

    def info(self):
        return 'Just like Wordle but with rude words.'

    def _matcher(self):
        return re.compile('Lewdle \D+(?P<iteration>\d+) (?P<guesses>\d+|X)(?P<hard>)/\d')


class Worldle(_StandardVariant):
    def name(self):
        return 'Worldle'

    def url(self):
        return 'https://worldle.teuteuf.fr/'

    def emoji(self):
        return '🌎'

    def info(self):
        return 'Guess a country by its shape.'

    def _matcher(self):
        return re.compile('\#Worldle \#(?P<iteration>\d+) (?P<guesses>\d+|X)/\d(?P<hard>)', re.MULTILINE)


class Wordle(_StandardVariant):
    def name(self):
        return 'Wordle'

    def url(self):
        return 'https://www.nytimes.com/games/wordle/index.html'

    def emoji(self):
        return '🟩'

    def info(self):
        return 'The original Wordle.'

    def _matcher(self):
        return re.compile('Wordle (?P<iteration>\d+) (?P<guesses>\d+|X)/\d(?P<hard>\*?)')


class Semantle(_Variant):
    def __init__(self):
        self.first_guess_matcher = re.compile('I got Semantle (?P<iteration>\d+) on my first guess!')
        self.matcher = re.compile('I solved Semantle \#(?P<iteration>\d+) in (?P<guesses>\d+) guesses.')

    def name(self):
        return 'Semantle'

    def url(self):
        return 'https://semantle.novalis.org/'

    def emoji(self):
        return '📙'

    def info(self):
        return 'Guess a word by its semantic similarity to others.'

    def parse(self, content):
        match = self.matcher.match(content)
        if match is not None:
            iteration = match.group('iteration')
            success = True # Semantle doesn't allow you to share if you fail
            guesses = match.group('guesses')
        else:
            match = self.first_guess_matcher.match(content)
            if match is not None:
                iteration = match.group('iteration')
                success = True
                guesses = 1
            else:
                return None

        return Result(iteration, success, guesses)
    
class BTSHeardle(_Variant):
    def __init__(self):
        self.matcher = re.compile('\#BTSHeardle(?P<iteration>\d+)\s+(?P<guesses>\d+|X)/\d')

    def name(self):
        return 'BTSHeardle'

    def url(self):
        return 'https://www.bts-heardle.app/'

    def emoji(self):
        return '💜'

    def info(self):
        return 'Guess the BTS song of the day in 7 tries.'

    def parse(self, content):
        match = self.matcher.match(content)
        if match is None:
            return None

        iteration = match.group('iteration')
        success = match.group('guesses') != 'X'
        guesses = match.group('guesses') if success else 7

        return Result(iteration, success, guesses)


def get_variants():
    """Returns all variants supported by Leaderbordle."""
    return [
        Wordle(),
        Worldle(),
        Semantle(),
        Heardle(),
        BTSHeardle(),
        Framed(),
        Lewdle()]
