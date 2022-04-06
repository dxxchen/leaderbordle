import re

from abc import ABC, abstractmethod
from common import Result
from datetime import date, timedelta


class VariantDetails:
    def __init__(self, first_iteration_date, is_timed=False, is_failable=True):
        self.first_iteration_date = first_iteration_date
        self.is_timed = is_timed
        self.is_failable = is_failable


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

    def title(self):
        """Returns a string that contains the emoji and name."""
        return '%s %s' % (self.emoji(), self.name())

    def linkified_title(self):
        """Returns a Discord-formatted string that contains the emoji and hyperlinked name."""
        return '%s [%s](%s)' % (self.emoji(), self.name(), self.url())

    def details(self):
        """Returns the details of this variant."""
        pass

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
        self.max_guesses = self._max_guesses()

    @abstractmethod
    def _matcher(self):
        """Returns an re.Pattern that matches an attempt."""
        pass

    def _max_guesses(self):
        """Returns the maximum number of guesses allowed."""
        return 6

    def parse(self, content):
        match = self.matcher.match(content)
        if match is None:
            return None

        iteration = match.group('iteration')
        success = match.group('guesses') != 'X'
        guesses = match.group('guesses') if success else self.max_guesses
        difficulty = 'hard' if match.group('hard') == '*' else ''

        return Result(
            iteration,
            success,
            guesses,
            difficulty=difficulty)


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

    def details(self):
        return VariantDetails(date(2022, 3, 20))

    def parse(self, content):
        match = self.matcher.match(content)
        if match is None:
            return None

        iteration = match.group('iteration')
        success = match.group('guesses') != 'X'
        guesses = match.group('guesses') if success else 7

        return Result(iteration, success, guesses)


class Chrono(_Variant):
    def __init__(self):
        self._medals = ['🥇', '🥈', '🥉']
        self.matcher = re.compile('Chrono \#(?P<iteration>\d+).*\n+(?P<medal>[🥇🥈🥉😬]).*\n⏱:\s+(?P<time_secs>\d+(\.\d+)?)')

    def name(self):
        return 'Chrono'

    def url(self):
        return 'https://chrono.quest/'

    def emoji(self):
        return '⏱'

    def info(self):
        'Put 6 events in chronological order.'

    def details(self):
        return VariantDetails(
            date(2022, 3, 2),
            is_timed=True)

    def parse(self, content):
        match = self.matcher.match(content)
        if match is None:
            return

        iteration = match.group('iteration')
        success = match.group('medal') != '😬'
        guesses = self._medals.index(match.group('medal')) + 1 if success else 3
        time_secs = float(match.group('time_secs'))

        return Result(iteration, success, guesses, time_secs=time_secs)


class Flagle(_StandardVariant):
    def name(self):
        return 'Flagle'

    def url(self):
        return 'https://www.flagle.io/'

    def emoji(self):
        return '🏁'

    def info(self):
        return 'Guess the country by parts of its flag.'

    def details(self):
        # Note that although the Flagle code says the first date is 2022-02-21 [1], its first
        # iteration is numbered 0 [2]. For simplicity, we will just say that it started on
        # 2022-02-22 instead (which would be iteration 1).
        #
        # [1] https://github.com/ryanbarouki/flagle/blob/1ec1d12cd141a3c0e1bd3d4f720fb33eff8fd60a/src/components/Share.js#L7
        # [2] https://github.com/ryanbarouki/flagle/blob/1ec1d12cd141a3c0e1bd3d4f720fb33eff8fd60a/src/components/Share.js#L30
        return VariantDetails(date(2022, 2, 22))

    def _matcher(self):
        return re.compile('\#Flagle \#(?P<iteration>\d+) (?P<guesses>\d+|X)(?P<hard>)/\d')


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

    def details(self):
        return VariantDetails(date(2022, 3, 12))

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

    def details(self):
        return VariantDetails(date(2022, 2, 26))

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

    def details(self):
        return VariantDetails(date(2022, 1, 19))

    def _matcher(self):
        return re.compile('Lewdle \D+(?P<iteration>\d+) (?P<guesses>\d+|X)(?P<hard>)/\d')


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

    def details(self):
        return VariantDetails(
            date(2022, 1, 30),
            is_failable=False)

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


class Werdel(_StandardVariant):
    def _max_guesses(self):
        return 8

    def name(self):
        return 'wɜːdəl'

    def url(self):
        return 'https://bennw.github.io/werdel/#daily'

    def emoji(self):
        return '💬'

    def info(self):
        return 'Wordle using the International Phonetic Alphabet and British pronunciation.'

    def details(self):
        return VariantDetails(date(2022, 2, 12))

    def _matcher(self):
        return re.compile('Daily wɜːdəl \#(?P<iteration>\d+) (?P<guesses>\d+|X)/\d(?P<hard>)')


class Worldle(_StandardVariant):
    def name(self):
        return 'Worldle'

    def url(self):
        return 'https://worldle.teuteuf.fr/'

    def emoji(self):
        return '🌎'

    def info(self):
        return 'Guess a country by its shape.'

    def details(self):
        return VariantDetails(date(2022, 1, 22))

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

    def details(self):
        return VariantDetails(date(2021, 6, 19))

    def _matcher(self):
        return re.compile('Wordle (?P<iteration>\d+) (?P<guesses>\d+|X)/\d(?P<hard>\*?)')

    
class Yeardle(_Variant):
    def __init__(self):
        self.matcher = re.compile('\#Yeardle \#(?P<iteration>\d+)\n+(?P<guess_emojis>.*)')

    def name(self):
        return 'Yeardle'

    def url(self):
        return 'https://histordle.com/yeardle/'

    def emoji(self):
        return '⌛'

    def info(self):
        return 'Guess a year from three historical events.'

    def details(self):
        return VariantDetails(date(2022, 3, 23))

    def parse(self, content):
        match = self.matcher.match(content)
        if match is None:
            return None

        iteration = match.group('iteration')
        guesses = match.group('guess_emojis').find('🟩') + 1
        if guesses > 0:
            success = True
        else:
            guesses = 8
            success = False

        return Result(iteration, success, guesses)


def get_variants():
    """Returns a dict {name, variant} of all variants supported by Leaderbordle.

    The returned list should be ordered by popularity.
    """
    variants = [
        Wordle(),
        Worldle(),
        Semantle(),
        Heardle(),
        Framed(),
        Flagle(),
        BTSHeardle(),
        Yeardle(),
        Chrono(),
        Lewdle(),
        Werdel()]

    return {v.name() : v for v in variants}
