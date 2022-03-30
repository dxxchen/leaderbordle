from abc import ABC, abstractmethod


class VariantStats:
    def __init__(self, attempts=0, successes=0, distribution={}):
        self.attempts = attempts
        self.successes = successes
        self.distribution = distribution


class _Store:
    @abstractmethod
    def record_result(self, variant, user_id, result):
        pass

    @abstractmethod
    def read_variant_leaderboard(self, user_ids, variant):
        pass

    @abstractmethod
    def read_variant_stats(self, user_ids, variant):
        pass

    @abstractmethod
    def read_user_stats(self, user_id):
        pass


class InMemoryStore(_Store):
    def __init__(self, parsers):
        # results is a dict of dict of array {variant: {user_id: [results]}}
        self.results = {}
        for parser in parsers:
            self.results[parser.name()] = {}

    def record_result(self, variant, user_id, result):
        # This does not deduplicate results for the same iteration.
        if variant not in self.results:
            return

        self.results[variant].setdefault(user_id, []).append(result)

    def read_variant_leaderboard(self, user_ids, variant):
        pass

    def read_variant_stats(self, user_ids, variant):
        pass

    def read_user_stats(self, user_id):
        user_results = {}
        for variant_name, variant_results in self.results.items():
            if user_id not in variant_results:
                continue

            user_results[variant_name] = variant_results[user_id]

        all_stats = {}
        for variant_name, variant_results in user_results.items():
            stats = VariantStats()
            stats.attempts = len(variant_results)
            stats.successes = len([r for r in variant_results if r.success])

            unsorted_distribution = {}
            for result in variant_results:
                unsorted_distribution[result.guesses] = unsorted_distribution.setdefault(result.guesses, 0) + 1

            stats.distribution = dict(sorted(unsorted_distribution.items()))

            all_stats[variant_name] = stats

        return all_stats
